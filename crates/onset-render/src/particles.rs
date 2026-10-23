//! The particle layer: a fixed pool of sparks that a compute pass moves every frame and an
//! instanced pass draws additively over the scene, before bloom, so the brightest of them
//! glow. Scenes know nothing about it. Sparks burst from the centre on the kick, a wider
//! spray on the snare, debris flies over the whole screen on the drop and a small puff in
//! the cue's colour marks a cue passing. Each burst takes the next run of slots in the
//! pool (a ring), so a long-lived spark is only ever overwritten once the ring wraps.
use onset_core::quality::Quality;

use crate::gpu::Gpu;
use crate::scene::{COMMON_WGSL, FrameBindings, ShaderError};
use crate::stage::HDR_FORMAT;

const SHADER: &str = include_str!("../../../assets/shaders/particles.wgsl");

/// Slots in the pool; the quality level says how many are in use.
pub const MAX_PARTICLES: u32 = 16_384;
/// Bytes of one `Particle` in `particles.wgsl` (three vec4).
const PARTICLE_BYTES: u64 = 48;
const WORKGROUP: u32 = 64;

/// Mirrors `struct Params` in `particles.wgsl`.
#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, bytemuck::Pod, bytemuck::Zeroable)]
pub struct Params {
    /// dt (s), active particles, spark amount, aspect.
    pub frame: [f32; 4],
    /// First index, count, strength, unused.
    pub kick: [f32; 4],
    pub snare: [f32; 4],
    pub drop: [f32; 4],
    pub cue: [f32; 4],
}

/// What the layer needs from the frame beyond the `Frame` uniform it shares with the scenes.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ParticleFrame {
    /// Seconds since the last frame.
    pub dt: f32,
    /// The beat-locked kick and snare, 1 at the hit decaying to 0.
    pub kick: f32,
    pub snare: f32,
    /// The show director's drop and cue markers, decaying from 1.
    pub drop_hit: f32,
    pub cue_hit: f32,
    /// `FxSettings::sparks`, 0..1.
    pub amount: f32,
    pub quality: Quality,
    /// Render width over height.
    pub aspect: f32,
}

/// Particles in use at each quality level: fewer slots to move and draw on a slow GPU.
pub fn pool_size(quality: Quality) -> u32 {
    match quality {
        Quality::Low => MAX_PARTICLES / 4,
        Quality::Medium => MAX_PARTICLES / 2,
        Quality::High | Quality::Ultra => MAX_PARTICLES,
    }
}

/// A hit that just rose this much above its last value is a new one, not the tail of the
/// old one decaying.
const RISE: f32 = 0.25;

pub struct ParticleLayer {
    params: wgpu::Buffer,
    _pool: wgpu::Buffer,
    update: wgpu::ComputePipeline,
    draw: wgpu::RenderPipeline,
    update_group: wgpu::BindGroup,
    draw_group: wgpu::BindGroup,
    /// Next free slot of the ring.
    cursor: u32,
    /// Last frame's kick, snare, drop and cue, to spot a new hit.
    prev: [f32; 4],
}

impl ParticleLayer {
    /// Compiles the layer against the scenes' frame bindings (group 0) and the HDR target.
    /// A shader that fails to compile is an error, so the show can run without the layer.
    #[allow(clippy::too_many_lines)] // one pipeline and layout table
    pub fn new(gpu: &Gpu, frame_layout: &wgpu::BindGroupLayout) -> Result<Self, ShaderError> {
        let device = &gpu.device;
        let params = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("particle params"),
            size: std::mem::size_of::<Params>() as u64,
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        // Zeroed: every slot starts dead (life 0).
        let pool = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("particle pool"),
            size: u64::from(MAX_PARTICLES) * PARTICLE_BYTES,
            usage: wgpu::BufferUsages::STORAGE,
            mapped_at_creation: false,
        });
        let uniform_entry = |visibility| wgpu::BindGroupLayoutEntry {
            binding: 0,
            visibility,
            ty: wgpu::BindingType::Buffer {
                ty: wgpu::BufferBindingType::Uniform,
                has_dynamic_offset: false,
                min_binding_size: None,
            },
            count: None,
        };
        let storage_entry = |binding, visibility, read_only| wgpu::BindGroupLayoutEntry {
            binding,
            visibility,
            ty: wgpu::BindingType::Buffer {
                ty: wgpu::BufferBindingType::Storage { read_only },
                has_dynamic_offset: false,
                min_binding_size: None,
            },
            count: None,
        };
        let update_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("particle update"),
            entries: &[
                uniform_entry(wgpu::ShaderStages::COMPUTE),
                storage_entry(1, wgpu::ShaderStages::COMPUTE, false),
            ],
        });
        let draw_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("particle draw"),
            entries: &[
                uniform_entry(wgpu::ShaderStages::VERTEX),
                storage_entry(2, wgpu::ShaderStages::VERTEX, true),
            ],
        });
        let group = |label, layout, binding| {
            device.create_bind_group(&wgpu::BindGroupDescriptor {
                label: Some(label),
                layout,
                entries: &[
                    wgpu::BindGroupEntry {
                        binding: 0,
                        resource: params.as_entire_binding(),
                    },
                    wgpu::BindGroupEntry {
                        binding,
                        resource: pool.as_entire_binding(),
                    },
                ],
            })
        };
        let update_group = group("particle update", &update_layout, 1);
        let draw_group = group("particle draw", &draw_layout, 2);

        let scope = device.push_error_scope(wgpu::ErrorFilter::Validation);
        let source = format!("{COMMON_WGSL}\n{SHADER}");
        let module = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("particles"),
            source: wgpu::ShaderSource::Wgsl(source.into()),
        });
        let update_pipeline_layout =
            device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: Some("particle update"),
                bind_group_layouts: &[Some(frame_layout), Some(&update_layout)],
                immediate_size: 0,
            });
        let update = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("particle update"),
            layout: Some(&update_pipeline_layout),
            module: &module,
            entry_point: Some("cs_update"),
            compilation_options: wgpu::PipelineCompilationOptions::default(),
            cache: None,
        });
        let draw_pipeline_layout =
            device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: Some("particle draw"),
                bind_group_layouts: &[Some(frame_layout), Some(&draw_layout)],
                immediate_size: 0,
            });
        let draw = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("particle draw"),
            layout: Some(&draw_pipeline_layout),
            vertex: wgpu::VertexState {
                module: &module,
                entry_point: Some("vs_particle"),
                compilation_options: wgpu::PipelineCompilationOptions::default(),
                buffers: &[],
            },
            fragment: Some(wgpu::FragmentState {
                module: &module,
                entry_point: Some("fs_particle"),
                compilation_options: wgpu::PipelineCompilationOptions::default(),
                targets: &[Some(wgpu::ColorTargetState {
                    format: HDR_FORMAT,
                    blend: Some(wgpu::BlendState {
                        color: wgpu::BlendComponent {
                            src_factor: wgpu::BlendFactor::One,
                            dst_factor: wgpu::BlendFactor::One,
                            operation: wgpu::BlendOperation::Add,
                        },
                        alpha: wgpu::BlendComponent::OVER,
                    }),
                    write_mask: wgpu::ColorWrites::COLOR,
                })],
            }),
            primitive: wgpu::PrimitiveState::default(),
            depth_stencil: None,
            multisample: wgpu::MultisampleState::default(),
            multiview_mask: None,
            cache: None,
        });
        if let Some(e) = pollster::block_on(scope.pop()) {
            return Err(ShaderError {
                name: "particles".to_string(),
                message: match &e {
                    wgpu::Error::Validation { description, .. } => description.clone(),
                    other => other.to_string(),
                },
            });
        }
        Ok(Self {
            params,
            _pool: pool,
            update,
            draw,
            update_group,
            draw_group,
            cursor: 0,
            prev: [0.0; 4],
        })
    }

    /// Claims `count` slots of the ring for a burst and returns its `Params` entry.
    fn burst(&mut self, total: u32, count: u32, strength: f32) -> [f32; 4] {
        let count = count.min(total);
        let first = self.cursor % total.max(1);
        self.cursor = (first + count) % total.max(1);
        [first as f32, count as f32, strength, 0.0]
    }

    /// A new hit's strength when `now` just rose above last frame's value, else 0.
    fn rose(prev: &mut f32, now: f32) -> f32 {
        let hit = if now > *prev + RISE { now } else { 0.0 };
        *prev = now;
        hit
    }

    /// The bursts this frame and the spark budget, from the hits' rising edges.
    fn params(&mut self, f: &ParticleFrame) -> Params {
        let total = pool_size(f.quality);
        let amount = f.amount.clamp(0.0, 1.0);
        // The amount scales every burst; at its default a kick throws about 3% of the pool.
        let budget = |fraction: f32, strength: f32| {
            (total as f32 * fraction * amount * 2.0 * (0.5 + 0.5 * strength)) as u32
        };
        let [kick, snare, drop, cue] = {
            let p = &mut self.prev;
            [
                Self::rose(&mut p[0], f.kick),
                Self::rose(&mut p[1], f.snare),
                Self::rose(&mut p[2], f.drop_hit),
                Self::rose(&mut p[3], f.cue_hit),
            ]
        };
        let burst = |layer: &mut Self, fraction: f32, strength: f32| {
            if strength > 0.0 {
                layer.burst(total, budget(fraction, strength), strength)
            } else {
                [0.0; 4]
            }
        };
        let cue = burst(self, 0.03, cue);
        let snare = burst(self, 0.04, snare);
        let kick = burst(self, 0.05, kick);
        let drop = burst(self, 0.45, drop);
        Params {
            frame: [f.dt.max(0.0), total as f32, amount, f.aspect.max(1e-3)],
            kick,
            snare,
            drop,
            cue,
        }
    }

    /// Moves the pool one step and draws it over `target` (loaded, not cleared).
    pub fn render(
        &mut self,
        gpu: &Gpu,
        encoder: &mut wgpu::CommandEncoder,
        target: &wgpu::TextureView,
        frame: &FrameBindings,
        input: &ParticleFrame,
    ) {
        let params = self.params(input);
        gpu.queue
            .write_buffer(&self.params, 0, bytemuck::bytes_of(&params));
        let total = pool_size(input.quality);
        {
            let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("particle update"),
                timestamp_writes: None,
            });
            pass.set_pipeline(&self.update);
            pass.set_bind_group(0, frame.bind_group(), &[]);
            pass.set_bind_group(1, &self.update_group, &[]);
            pass.dispatch_workgroups(total.div_ceil(WORKGROUP), 1, 1);
        }
        let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            label: Some("particles"),
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view: target,
                depth_slice: None,
                resolve_target: None,
                ops: wgpu::Operations {
                    load: wgpu::LoadOp::Load,
                    store: wgpu::StoreOp::Store,
                },
            })],
            ..Default::default()
        });
        pass.set_pipeline(&self.draw);
        pass.set_bind_group(0, frame.bind_group(), &[]);
        pass.set_bind_group(1, &self.draw_group, &[]);
        pass.draw(0..6, 0..total);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_hit_counts_once_until_it_decays_and_returns() {
        let mut prev = 0.0;
        assert!((ParticleLayer::rose(&mut prev, 1.0) - 1.0).abs() < f32::EPSILON);
        assert!(ParticleLayer::rose(&mut prev, 0.8).abs() < f32::EPSILON, "decaying");
        assert!(ParticleLayer::rose(&mut prev, 0.3).abs() < f32::EPSILON);
        assert!((ParticleLayer::rose(&mut prev, 0.9) - 0.9).abs() < f32::EPSILON);
    }

    #[test]
    fn the_pool_shrinks_at_low_quality() {
        assert!(pool_size(Quality::Low) < pool_size(Quality::Medium));
        assert!(pool_size(Quality::Medium) < pool_size(Quality::High));
        assert_eq!(pool_size(Quality::Ultra), MAX_PARTICLES);
        assert_eq!(std::mem::size_of::<Params>(), 80);
    }
}
