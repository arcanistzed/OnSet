// The particle layer: a pool of sparks updated by a compute pass and drawn additively over
// the scene before the post pass, so bloom lights them like anything else bright.
// `common.wgsl` is prepended, so `frame` and its helpers are available here; the layer's
// own inputs come in `params` (`onset_render::particles::Params`).
//
// Particles live in the scenes' centred space: x in [-aspect, aspect], y up in [-1, 1].
// Lifetimes count in beats while the music plays (seconds otherwise), so a spark lives
// about a beat whatever the tempo.

struct Particle {
    pos_vel: vec4<f32>, // position, velocity (centred units per second)
    life: vec4<f32>,    // life left, full life (beats), size, kind (0 spark, 1 spray, 2 debris, 3 puff)
    col: vec4<f32>,     // colour (linear rgb, > 1 blooms), seed 0..1
};

struct Params {
    frame_: vec4<f32>, // dt (s), active particles, spark amount 0..1, aspect
    kick: vec4<f32>,   // first index, count, strength, unused   (a burst of sparks)
    snare: vec4<f32>,  // same: a wider spray
    drop: vec4<f32>,   // same: debris over the whole screen
    cue: vec4<f32>,    // same: a puff in the cue's colour
};

@group(1) @binding(0) var<uniform> params: Params;
@group(1) @binding(1) var<storage, read_write> pool: array<Particle>;
@group(1) @binding(2) var<storage, read> pool_ro: array<Particle>;

const SPARK: f32 = 0.0;
const SPRAY: f32 = 1.0;
const DEBRIS: f32 = 2.0;
const PUFF: f32 = 3.0;

// Four independent 0..1 randoms for particle i, different every frame.
fn rand4(i: u32) -> vec4<f32> {
    let salt = floor(frame.time * 60.0) + seed() * 1000.0;
    let fi = f32(i);
    return vec4<f32>(
        hash21(vec2<f32>(fi, salt)),
        hash21(vec2<f32>(fi + 4096.0, salt + 1.0)),
        hash21(vec2<f32>(fi + 8192.0, salt + 2.0)),
        hash21(vec2<f32>(fi + 12288.0, salt + 3.0)),
    );
}

// Whether particle i falls in a burst's ring of indices (`count` long from `first`).
fn in_burst(i: u32, burst: vec4<f32>, total: u32) -> bool {
    let n = u32(burst.y);
    if (n == 0u) {
        return false;
    }
    let first = u32(burst.x);
    let offset = (i + total - first) % total;
    return offset < n;
}

fn spawn(i: u32, kind: f32, strength: f32) -> Particle {
    let r = rand4(i);
    let aspect = params.frame_.w;
    let angle = r.x * TAU;
    let dir = vec2<f32>(cos(angle), sin(angle));
    let tint = palette(r.y * 0.6 + music_time() * 0.05);
    var p: Particle;
    if (kind == DEBRIS) {
        // Thrown from wherever they were lying, outwards and up, heavy and slow to fade.
        let pos = vec2<f32>((r.x * 2.0 - 1.0) * aspect, r.y * 2.0 - 1.0);
        let out = normalize(pos + vec2<f32>(0.0, 1e-3));
        let vel = out * (0.6 + 1.2 * r.z) * (0.5 + strength) + vec2<f32>(0.0, 0.5 * r.w);
        p.pos_vel = vec4<f32>(pos, vel);
        let full = 1.5 + 2.0 * r.z;
        p.life = vec4<f32>(full, full, 0.012 + 0.024 * r.w, DEBRIS);
        p.col = vec4<f32>(tint * (1.6 + 0.8 * strength), r.w);
    } else if (kind == SPRAY) {
        // A ring around the centre, pushed out and sideways: wider and softer than the kick.
        let radius = 0.12 + 0.28 * r.y;
        let pos = dir * radius * vec2<f32>(1.3, 1.0);
        let side = vec2<f32>(-dir.y, dir.x) * (r.z - 0.5) * 0.8;
        let vel = (dir * (0.4 + 0.7 * r.z) + side) * (0.5 + 0.7 * strength);
        p.pos_vel = vec4<f32>(pos, vel);
        let full = 0.8 + 0.7 * r.w;
        p.life = vec4<f32>(full, full, 0.005 + 0.008 * r.w, SPRAY);
        p.col = vec4<f32>(mix(tint, vec3<f32>(1.0), 0.3) * (1.4 + 0.6 * strength), r.z);
    } else if (kind == PUFF) {
        // A slow cloud in the cue's own colour, kept vivid when the cue is dark.
        let pos = dir * sqrt(r.y) * 0.12;
        let vel = dir * (0.08 + 0.25 * r.z);
        p.pos_vel = vec4<f32>(pos, vel);
        let full = 1.0 + 1.0 * r.w;
        var c = frame.cue.rgb;
        c = max(c, vec3<f32>(luma(c) + 0.2) * normalize(c + vec3<f32>(0.05)) * 0.6);
        p.life = vec4<f32>(full, full, 0.012 + 0.016 * r.z, PUFF);
        p.col = vec4<f32>(c * 1.6, r.x);
    } else {
        // Sparks: straight out from the centre, fast, a beat long.
        let pos = dir * r.y * 0.04;
        let vel = dir * (0.9 + 1.4 * r.z) * (0.5 + 0.9 * strength);
        p.pos_vel = vec4<f32>(pos, vel);
        let full = 0.6 + 0.6 * r.w;
        p.life = vec4<f32>(full, full, 0.004 + 0.009 * r.w, SPARK);
        p.col = vec4<f32>(tint * (1.8 + 1.2 * strength), r.z);
    }
    return p;
}

@compute @workgroup_size(64)
fn cs_update(@builtin(global_invocation_id) gid: vec3<u32>) {
    let i = gid.x;
    let total = u32(params.frame_.y);
    if (i >= total) {
        return;
    }
    // Spawns, later bursts winning: a drop's debris takes the slot over a kick's spark.
    if (in_burst(i, params.cue, total)) {
        pool[i] = spawn(i, PUFF, params.cue.z);
    }
    if (in_burst(i, params.snare, total)) {
        pool[i] = spawn(i, SPRAY, params.snare.z);
    }
    if (in_burst(i, params.kick, total)) {
        pool[i] = spawn(i, SPARK, params.kick.z);
    }
    if (in_burst(i, params.drop, total)) {
        pool[i] = spawn(i, DEBRIS, params.drop.z);
    }

    var p = pool[i];
    if (p.life.x <= 0.0) {
        return;
    }
    let dt = params.frame_.x;
    let aspect = params.frame_.w;
    let playing = frame.playing > 0.5 && frame.bpm > 1.0;
    let beats_per_s = select(1.0, frame.bpm / 60.0, playing);
    p.life.x = p.life.x - dt * beats_per_s;

    var pos = p.pos_vel.xy;
    var vel = p.pos_vel.zw;
    let kind = p.life.w;
    // The bass pushes everything outwards; debris also falls.
    let out = normalize(pos + vec2<f32>(1e-4, 0.0));
    vel = vel + out * bass() * 1.2 * dt;
    if (kind == DEBRIS) {
        vel.y = vel.y - 0.7 * dt;
    }
    // A slow current that turns with the music (skipped at Low quality: it costs a noise
    // lookup per particle).
    if (quality() >= 1.0) {
        let a = noise2(pos * 2.5 + vec2<f32>(music_time() * 0.7, p.col.w * 7.0)) * TAU * 2.0;
        let swirl = select(0.25, 0.08, kind == SPARK);
        vel = vel + vec2<f32>(cos(a), sin(a)) * swirl * dt;
    }
    let damping = select(1.4, 2.2, kind == SPARK);
    vel = vel * exp(-damping * dt);
    pos = pos + vel * dt;
    if (abs(pos.x) > aspect + 0.1 || abs(pos.y) > 1.1) {
        p.life.x = 0.0;
    }
    p.pos_vel = vec4<f32>(pos, vel);
    pool[i] = p;
}

struct PsOut {
    @builtin(position) pos: vec4<f32>,
    @location(0) uv: vec2<f32>,
    @location(1) col: vec3<f32>,
};

// Two triangles per particle, corners from the vertex index.
@vertex
fn vs_particle(@builtin(vertex_index) v: u32, @builtin(instance_index) i: u32) -> PsOut {
    var out: PsOut;
    let p = pool_ro[i];
    if (p.life.x <= 0.0) {
        // Dead: every corner at one point off screen, so nothing is rasterised.
        out.pos = vec4<f32>(2.0, 2.0, 0.0, 1.0);
        out.uv = vec2<f32>(0.0);
        out.col = vec3<f32>(0.0);
        return out;
    }
    let k = select(select(select(v, 2u, v == 3u), 1u, v == 4u), 3u, v == 5u);
    let corner = vec2<f32>(f32(k & 1u), f32(k >> 1u)) * 2.0 - 1.0;
    let t = clamp(p.life.x / max(p.life.y, 1e-3), 0.0, 1.0);
    let kind = p.life.w;
    // Sparks shrink as they die; debris keeps its size and fades.
    let size = p.life.z * select(mix(0.3, 1.0, t), 1.0, kind == DEBRIS) * (1.0 + 0.5 * params.frame_.z);
    let world = p.pos_vel.xy + corner * size;
    out.pos = vec4<f32>(world.x / max(params.frame_.w, 1e-3), world.y, 0.0, 1.0);
    out.uv = corner;
    let fade = smoothstep(0.0, 0.12, t) * pow(t, 0.6);
    out.col = p.col.rgb * fade;
    return out;
}

@fragment
fn fs_particle(in: PsOut) -> @location(0) vec4<f32> {
    let d = length(in.uv);
    if (d > 1.0) {
        discard;
    }
    // A hot core with a soft skirt; additive blending stacks overlapping sparks into light.
    let core = exp(-d * d * 5.0);
    let skirt = (1.0 - d) * 0.2;
    return vec4<f32>(in.col * (core + skirt), 1.0);
}
