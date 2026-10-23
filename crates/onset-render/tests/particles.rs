//! The particle layer through the whole renderer: a kick must add light to a dark scene, a
//! drop must add more, and with no hits the sparks must die away within a few beats.
use onset_core::music_state::MusicState;
use onset_core::show::{FxSettings, ShowEvent};
use onset_render::headless::Headless;
use onset_render::renderer::{Quality, RenderSettings, Renderer};
use onset_render::scene::FullscreenScene;

const SIZE: (u32, u32) = (160, 90);
const FPS: f32 = 30.0;
const BPM: f32 = 128.0;

/// A scene that draws almost nothing, so any light is the particles'.
const DARK: &str = r"
@fragment
fn fs_main(in: VsOut) -> @location(0) vec4<f32> {
    return vec4<f32>(0.02, 0.02, 0.03, 1.0);
}
";

fn renderer(h: &Headless, particles: bool) -> Renderer {
    let mut r = Renderer::new(&h.gpu, SIZE, h.format);
    let scene = FullscreenScene::new(&h.gpu, "dark", DARK, r.scene_format(), &r.bindings().layout)
        .expect("compile");
    r.add_scene(Box::new(scene));
    r.set_show_card(false);
    r.set_settings(
        &h.gpu,
        RenderSettings {
            auto: false,
            adaptive: false,
            quality: Quality::Low,
            fx: FxSettings {
                particles,
                sparks: 1.0,
                ..FxSettings::default()
            },
            ..RenderSettings::default()
        },
    );
    r
}

/// Playing at `t` seconds with the given kick envelope.
fn state(t: f32, kick: f32) -> MusicState {
    let beats = t * BPM / 60.0;
    let mut ms = MusicState {
        time_s: f64::from(t),
        playhead_s: f64::from(t) + 30.0,
        playing: true,
        bpm: BPM,
        bpm_grid: BPM,
        beat_phase: beats.fract(),
        bar_phase: (beats / 4.0).fract(),
        ..MusicState::default()
    };
    ms.hits.kick = kick;
    ms
}

fn light(px: &[u8]) -> f64 {
    px.as_chunks::<4>()
        .0
        .iter()
        .map(|p| f64::from(p[0]) + f64::from(p[1]) + f64::from(p[2]))
        .sum()
}

/// Renders the same timeline with the layer on or off: a kick at frame 10, a drop at frame
/// 40, then silence. Returns the light two frames after the kick, two after the drop, and
/// after four seconds of nothing.
fn run(h: &Headless, particles: bool) -> [f64; 3] {
    let mut r = renderer(h, particles);
    let mut out = [0.0; 3];
    for f in 0..(10 + 30 + (4.0 * FPS) as u32) {
        let t = f as f32 / FPS;
        let kick = if f == 10 { 1.0 } else { 0.0 };
        if f == 40 {
            r.preview_event(ShowEvent::Drop);
        }
        let ms = state(t, kick);
        let read = f == 12 || f == 42 || f == 10 + 30 + (4.0 * FPS) as u32 - 1;
        let px = h.render_with(|gpu, view| {
            let mut enc = gpu
                .device
                .create_command_encoder(&wgpu::CommandEncoderDescriptor { label: Some("p") });
            r.render(gpu, &mut enc, view, &ms, t);
            gpu.queue.submit([enc.finish()]);
        });
        if read {
            let slot = if f == 12 {
                0
            } else if f == 42 {
                1
            } else {
                2
            };
            out[slot] = light(&px);
        }
    }
    out
}

#[test]
fn a_kick_throws_sparks_a_drop_throws_more_and_both_fade() {
    let h = Headless::new(SIZE, true).expect("adapter");
    let off = run(&h, false);
    let on = run(&h, true);
    println!("off {off:?}\non  {on:?}");
    let pixels = f64::from(SIZE.0 * SIZE.1);
    // Two frames after the kick the sparks are a visible cloud around the centre.
    assert!(
        on[0] > off[0] + 2.0 * pixels,
        "the kick added no light: {} vs {}",
        on[0],
        off[0]
    );
    // The drop throws debris over the whole screen: more light than the kick.
    assert!(
        on[1] - off[1] > 1.5 * (on[0] - off[0]),
        "the drop should outshine the kick: {} vs {}",
        on[1] - off[1],
        on[0] - off[0]
    );
    // Four seconds of silence later the pool is dead and the picture is the scene's own.
    assert!(
        (on[2] - off[2]).abs() < 0.2 * pixels,
        "sparks did not die away: {} vs {}",
        on[2],
        off[2]
    );
}
