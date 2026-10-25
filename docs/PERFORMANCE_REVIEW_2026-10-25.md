# Performance review, 2026-10-25

Where OnSet can use less CPU, GPU, RAM, disk and power without losing what the DJ relies on: beat-locked visuals with fresh state, smooth frames, the DJ's corrections and approvals, and deep-analysis results that are never silently thrown away.

**Scope and method.** Phase 1 was read-only. Nothing was built, run or profiled: C: had under 4 GB free and D:\Offload was unplugged. Findings come from reading `crates/`, `service/` and `ui/` on `merge-autocue` at `ca870da`, plus the particle layer on `claude/kind-shamir-4b8d38` (`eee3c53`). The disk figures come from one read-only `du`/`find` of the real workspace, taken while OnSet was running. CPU and GPU savings are estimates from counting operations, not measurements; each item says what would confirm it. Phase 2 measures each item and then implements it, one at a time, when the coordinator gives this work a build slot.

## Evidence already on record

- Visuals (IMPLEMENTATION_STATUS, "Live-show performance"): at 2256×1504 on the Iris Xe the GPU is the limit. A mean frame takes 21–24 ms (p99 52–66 ms), and the visuals process uses about 1% CPU and 698 MB. Medium runs at about 52 fps (REVIEW_VISUALS). The CPU-side work already done (live view only on change, tick in MMCSS, rekordbox scans only for playing decks without an id) cut the worst state age under load from 101 to 40 ms.
- Preparation: a four-track deep job took 86 min (CONTINUATION_2026-10-24). EDMFormer peaked at 7.1 GB on a 240 s track and was killed; 225 s chunks bring it to 4.5 GB. WSL is capped at 7.8 GB. Saved-set listing went from 393 s to 3.3 s. The cold warm-up takes about 2.5 min. Backups filled the disk twice (162 copies, 14 GB) before pruning was added.

## Workspace disk use, measured 2026-10-25

`%LOCALAPPDATA%\Onset\Onset\data\workspace`: about 33 GB in all.

| Item | Size | Notes |
|---|---|---|
| `features/` | 26 GB | 196 cache folders for 160 tracks, plus `native-stages/` (171 folders) |
| `features/native-stages/<key>/audio.wav` | 5.6 GB (164) | mono float32 PCM of each track at its own rate |
| `features/<key>/audio.wav` | 5.6 GB (159) | **byte-identical copies** of the file above (md5 checked on one pair; sizes match for 154 pairs). Copied for the deep worker (`analysis.py:215-217`) |
| Demucs stems, WAV | 15.1 GB (103 × 4) | `deep/htdemucs/audio/*.wav`, 16-bit, written before feec729 |
| Demucs stems, FLAC | 0.24 GB (4 × 4) | since feec729 |
| `deep/allin1-embeddings.npz` | 0.70 GB (11) | about 64 MB a track; about 10 GB if allin1 ran on all 160 |
| other `.npz` | 0.35 GB | some folders hold up to 7 superseded feature `.npz` files |
| `workspace-backups/` | 5.0 GB | 14 full copies of the database (each 290–400 MB). Several were made within a minute of each other (three at 05:44 on 10-24, two at 00:57 on 10-23) |
| `workspace.db` | 382 MB | plus a 5.7 MB WAL |
| `models/` | 1.6 GB | needed |

Together, the duplicate PCM, the superseded cache folders and back-to-back backups of an unchanged database come to about 7–10 GB. That is more than the free space C: had today.

## Ranked plan

The order weighs saving against effort and risk. "Re-run" means a change that alters the deep cache key and so forces every model to run again on the next re-analysis (about 20 min per track). Those items are grouped behind P1.

### P0: quick, safe, and large for their size

1. **The show window busy-spins when it cannot draw** (CPU, power; S; no risk to the picture). `onset-visuals/src/app.rs:829-833` asks for a redraw after every `RedrawRequested`, and `:909` sets `ControlFlow::Poll`. When `acquire_frame` returns `None` (`Occluded`/`Timeout`, `:165`), for example while minimised, the loop asks for the next frame at once, on an above-normal-priority thread. Fix: if no frame was acquired, wait about 100 ms (`ControlFlow::WaitUntil`) before redrawing. *Measure:* CPU time of the visuals process with the show window minimised, before and after.
2. **Stop copying decoded audio twice** (disk 5.6 GB now, about 63 MB per 6-min track; S; no re-run). The deep cache already checks `pcm_sha256` (`analysis.py:230`), so the copy at `:215-217` can be deleted once `deep-results.json` is complete and re-created only when a deep run needs it (`:216` already does this when the file is missing). Better still, give the worker the `native-stages` path directly. Keep the PCM format as it is: changing it changes `pcm_sha256` and forces a re-run. *Measure:* `features/*/audio.wav` total before and after; one deep re-analysis of a cached track must report `cache_hit` with no model run.
3. **`Store.invalidate` rewrites every matching artifact one commit at a time** (CPU and latency on every cue click or edit; S; low risk). `store.py:404-410` parses every `transition`/`set`/`write-preview` artifact (tens of thousands) and commits each match separately, each commit with its `guard` and `remember` overhead. Fix: skip artifacts already stale, and write all of them in one transaction. *Measure:* time a `review` RPC on a copy of the workspace (`.test-desktop/<name>`).
4. **Job progress is saved and broadcast 2–5 times a second** (CPU, SSD writes, UI re-renders over 86-min jobs; S; low risk). `deep.py:83` (every 0.5 s) and `processes.py:23` (every 0.2 s) call `checkpoint` → `store.job` (commit, fsync'd `remember`) plus a `job-progress` event that re-renders the whole `App` (`main.tsx:129`). Fix: check for cancellation on every call, but save and emit only when the stage changes or at most every 2–5 s. The stall watchdog's 300 s limit is unaffected. *Measure:* the service's write bytes and CPU during a deep job on a copy.
5. **Engine-side recomputation at 120 Hz of inputs that arrive at 25 Hz** (CPU during shows, roughly 1–7% of a core; S; no risk). The deck-by-ear `verdict()` runs twice per tick (`onset-engine/src/lib.rs:947`, `:1279`), but samples arrive at 25 Hz (`deck_ear.rs:120`). The stream matcher re-scores every candidate each tick (`lib.rs:1115` → `stream_match.rs:131-151`). Fix: cache each result and recompute only when a new sample arrives. The output is identical between samples. *Measure:* time `verdict()` and `StreamMatcher::best()`, and engine-thread CPU with two playing decks in the simulator.
6. **rekordbox reader call counts** (CPU; S–M; low risk). For each deck on each tick: all 9 anchors re-read for the stale check (`reader.rs:213-219`, `:412-420`), every player's position re-read for `track_id` (`:327-351`), and position and tempo as separate reads (`:581-605`). That is about 100 `ReadProcessMemory` calls per tick with 4 decks. All of these fields lie within about 430 bytes of each deck object, so one read per deck and one pass over the players per tick are enough, and the stale and id checks can run at about 4 Hz. Also confirm whether `find_pid` (a full process snapshot) can run every tick once `MAX_FAILURES` is reached (`reader.rs:1639-1641`); if so, limit it to the 2 s `RETRY`. *Measure:* a call counter in `Process::read_exact` and engine CPU with rekordbox open (empty decks, then two playing).
7. **The audio-device watcher enumerates every device every 3 s, even with capture off** (wakeups; S; no risk). `lib.rs:288-312`, started unconditionally at `:607`. Run it only while capture is on, which is only during a show.

### P1: medium effort, large saving

8. **A deep cache keyed by audio and model, not by grid or code** (hours of CPU per re-analysis, plus GB of orphaned folders; M; **this item decides whether a re-run happens**). The key is `digest([native_key, deep, experimental, model_signature])` (`analysis.py:79-84`). `native_key` includes the grid, BPM override, previous beats and phrase anchor, and `model_signature` hashes the whole `deep_worker.py` and the lock files. So a grid correction, an `ALGORITHM` bump, adding one experimental model, or any worker edit moves the folder and runs every model again. Old folders are never removed (196 folders for 160 tracks). Fix: store each model's output under `pcm_sha256` + model name + that model's own version and parameters, and run the grid-dependent resolution step on top. A migration adopts existing complete outputs (worker_format 2, stems, pcm hash matching) so nothing re-runs. Then add a cleanup that first reports the unreferenced folders and recycles them only with the user's approval. Every worker change below (items 12–14) should land after this. *Measure:* number of models that run after a grid edit on a copy (should be none), and the size of unreferenced folders.
9. **The library ships every full analysis about three times per UI action** (CPU, RAM, latency; S–M; low risk). After every `run()`, `refresh()` (`main.tsx:121-123`) calls `tracks`, `review-queue` and `sets`, and the last two load `store.tracks()` again (`service.py:275`, `:736`). One profile carries its spectrogram (64 × about 700 values), waveform, beats and deep outputs, so a `tracks` call is plausibly tens of MB, parsed three times (Python, serde, JS) while the single-threaded service blocks. Fix: a summary `tracks` without spectrogram, waveform, beats or deep data; the full `track` only for the selected one; and use the profile that `review`/`edit` already return instead of calling `refresh()`. *Measure:* response bytes per method (log the line length in `rpc.emit`, `rpc.py:14`) and the time from click to update.
10. **Database growth: full before/after profiles in every edit, no WAL limit, full-copy backups** (disk, backup time; M; undo must stay exact). `record_edit` stores both profiles in full (`store.py:358-362`), about 0.8 MB per click. There is no `journal_size_limit`, checkpoint or VACUUM (`store.py:21-23`). Every start, quit and shutdown copies the database, then runs an integrity check and a full hash (`workspace.py:127-138`). Fix: store edits without the `analysis` part, which edits never change, and rebuild it on undo (test the round trip). Skip an automatic backup when the database hash equals the newest backup's. Consider compressing automatic backups, set `journal_size_limit`, and run `wal_checkpoint(TRUNCATE)` at idle. `synchronous=NORMAL` is safe in WAL mode but trades away durability of the last commit on power loss, so it is the user's call. *Measure:* `sum(length(before_value)+length(after_value)) FROM edits`, `PRAGMA page_count`, and the size of the backup folder over a day.
11. **Engine rate outside a show** (power; M; low risk). The desktop starts the engine at launch (`onset-desktop/src/main.rs:981`) and it ticks at 120 Hz, though outside a show only the 30 Hz live view reads it. Tick at 30 Hz outside a show and about 10 Hz while rekordbox is absent. First make the poll-counted constants (`STALE_POLLS` `reader.rs:1079`, `MAX_FAILURES` `:1451`) time-based so detection times do not change. *Measure:* wakeups (`powercfg /energy` or ETW) and package power with the app idle.

### P2: worker changes (each one a re-run unless P1 item 8 lands first)

12. **allin1 runs htdemucs again** (minutes of CPU and a 2–3 GB process per track). `deep_worker.py:219-220` passes `demix_dir`, but our own Demucs output (`:180`) is not placed where allin1 looks for it. Pre-populating `demix_dir/htdemucs/<name>/{bass,drums,other,vocals}.wav` from our stems lets allin1 skip separation. Check first: allin1's environment pins demucs 4.1.0 against our 4.0.1, so compare segments on about 3 tracks.
13. **Peak memory and threads in the worker** (about 1 GB at peak). The parent imports torch (`:131`) and stays resident while the EDMFormer and allin1 children run (`:152-158`). Run the isolated models before torch is loaded, or run every model in its own child. Threads: `torch.set_num_threads(4)` (`:134`), but Demucs and onnxruntime use their defaults; set `OMP_NUM_THREADS` explicitly. Essentia runs `KeyExtractor` three times (`:191-192`).
14. **A persistent WSL worker per job, overlapping the next track's native stage** (about 15–60 s per track, 1–3 h over 160 tracks; M). Each track pays `wsl.exe printenv` (`deep.py:53-57`, 14 s warm and over 60 s cold) and a fresh Python with torch. Overlap only when there is memory to spare; the pagefile incidents show what happens otherwise.

### P3: the renderer (needs GPU timing first)

GPU timing is missing (`renderer.rs:972` passes `gpu_ms: None`). Add per-pass `TIMESTAMP_QUERY` timing (scene, particles, bloom, composite) before changing anything here, because two runs of the same build varied more than two builds did.

15. **Adaptive resolution** reallocates every target, including the feedback buffers, on each step (`renderer.rs:501-509`, `stage.rs:236-259`). That causes a hitch, and trails lose their history. Transition frames, which draw two scenes, count as slow (`:464-499`, 21 ms threshold), and recovery needs 600 smooth frames in a row. Leave transitions out of the count, and render into fixed targets through a viewport instead of reallocating.
16. **Composite**: `post.wgsl` (about lines 228-235) runs two hue rotations for inversion, plus a hue shift, on every pixel even when both are off. Put them behind a branch on the uniform. The picture is identical while both are off.
17. **Bloom chain in `Rg11b10Ufloat`** instead of `Rgba16Float` (`scene.rs:23`), if the adapter supports it (`RG11B10UFLOAT_RENDERABLE`). Keep the feedback buffers at 16-bit. Check for banding by eye.
18. **Particles (`eee3c53`)**: pools of 4k/8k/16k (Low/Medium/High). At a drop, 45% of the pool becomes 17–51 px debris, roughly 2× full-frame blended overdraw for about a beat at Medium. That is exactly when a slow frame shows most and pushes adaptive resolution down. Lower the debris share or size at Low and Medium, and skip the dispatch and draw when the CPU knows no particle is alive. Decide this together with the particle branch's merge (REVIEW_VISUALS §7.4).

### P4: small

- Peak RAM during deck scans: `process.rs:245-275` allocates up to 1 GB per region. Scan through a reused 16 MB window with overlap.
- Per-tick allocations: `TrackMeta` clone (`lib.rs:1236`), `format!` in `status_now` (`:773`), path normalisation per open file (`reader.rs:1198-1222`). The audio callback allocates a `Vec` per block on the real-time thread (`capture.rs`, `push_downmixed`); a preallocated ring buffer matters for timing stability more than for CPU. A real-input FFT with reused buffers in `analyzer.rs` halves that FFT work.
- Previews hash both full sources and load every profile before checking the cache (`preview.py:16-25`, `service.py:589`).
- UI: memoize the filtered library and its rows, keep the audio position in a child component, and key `Spectrogram` on `track.revision` (`main.tsx:95-98`). 160 rows do not need virtualization.
- `track` is not in `LIGHT_METHODS` (`service.py:79-82`), so opening a track waits for the cold warm-up (about 2.5 min). It only reads the database.
- The live-view thread checks window visibility at 30 Hz even when every window is hidden; back off to about 4 Hz.

## Already efficient: do not chase

The native stage decodes once and shares one STFT across all features. Native and deep caches are verified by hash, and per-model checkpoints resume. Stems are FLAC since feec729, EDMFormer is chunked, and one heavy job runs at a time. The live view sends only on change. Capture runs only during a show. The open-files watcher and deck scans are rate-limited. The recorder is off unless `--record` is given. Text layout is cached, frame bind groups are prebuilt, and per-frame uploads are tiny. The sidecar drops to EcoQoS during a show. Media is served as file URLs.

## Found in passing (not performance)

`load_audio` returns mono (`cues.py:62`), so Demucs and allin1 always separate a mono downmix, and the widen-to-stereo step (`deep_worker.py:100-114`) runs on every track. Stems carry no stereo image. Whether that matters for separation quality is a listening question, and fixing it would change `pcm_sha256` (a re-run).

## Measurements to take in phase 2, in this order

All on copies (`.test-desktop/<name>` or D:\Offload), never against the live workspace while OnSet is open, with builds limited to `-j 2..4` and run alone.

1. Visuals process CPU while minimised (item 1), and engine CPU in four states: rekordbox absent; open with empty decks; two decks playing; simulator (items 5–7, 11).
2. `ReadProcessMemory` calls per tick and `verdict()` time (items 5, 6).
3. `review` RPC time and `tracks` response size on a workspace copy (items 3, 9).
4. Service write bytes during a 2-track deep job on a copy (item 4).
5. Models that run after a grid edit on a cached track (item 8, baseline should be "all").
6. GPU per-pass timing at Medium on the laptop screen, then a 1080p projector (P3).

## Proposed phase 2 order

Items 1, 2, 3, 4, then 5–7, then 9, 10 and 8. Items 12–14 come only after 8, and P3 only after GPU timing exists. Each change gets a regression test and a before/after number recorded here. Clearing the existing duplicate `audio.wav` files and the superseded cache folders is the user's decision, made only after a report of what would go. The `audio-copies` tool (item 2) removes only byte-identical copies, which the next deep run can re-create; anything else is recycled, not deleted.

## Phase 2 progress

Items 2–4 are done in source, as Python service changes with regression tests. The full service suite (181 tests) passed on 2026-10-25. None of them is in an installed build yet.

- **Item 2, `8a39d4e`.** Cached deep results are matched against the native PCM's hash. The worker's `audio.wav` copy is made only when a model has to run, and it is removed once every model completes. `deep-results.json` keeps the same `pcm_sha256`, so existing results are reused and nothing re-runs. The copies left by earlier runs stay until the user asks: `onset_service --home <workspace> audio-copies` (also an RPC) lists them, and `--apply` removes only those whose deep results are complete and whose native PCM is byte-identical. The service refuses to start on a workspace the app holds, so close OnSet first. On the real workspace that is up to 5.6 GB; not run.
- **Item 3, `3a84f3b`.** `Store.invalidate` selects only records whose JSON contains the track's id, skips ones already stale, and writes the rest in one commit. On a scratch store of 30,000 transitions over 160 tracks: 2.71 s before, 0.47 s after, 0.32 s when nothing is left to mark. Not yet timed on a copy of the real workspace.
- **Item 4, `3bdca60`.** A job checkpoint is saved and pushed to the screens when its stage changes, when a paused job resumes, at most once a second while only the fraction moves, and otherwise every 30 s (the stall limit is 300 s). The deep worker's loop used to save and push twice a second; it now does so once per model plus the heartbeat. Write bytes during a real deep job are not yet measured.

- **Item 1, `3a40ed9`.** When the show window cannot draw a frame (minimised, occluded or a timed-out surface), the loop now waits 100 ms (`ControlFlow::WaitUntil`) before trying again instead of asking for the next redraw at once, and a minimised window skips acquiring a surface texture. Drawn frames still go back to back, paced by the present. onset-visuals unit tests (14, two new) and clippy pass. The CPU of a minimised show window is not yet measured before and after; that needs a release build and a show.
