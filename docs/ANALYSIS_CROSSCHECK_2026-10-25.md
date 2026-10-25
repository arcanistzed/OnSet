# Analysis cross-check: the seven re-analysed tracks

OnSet's analysis of each track is checked against independent sources, item by item. Items
where the sources agree are settled; where they disagree and the evidence is strong, the check
decides and says why; only what stays genuinely open goes to the DJ, as yes/no questions.
Nothing here approves a cue or writes to rekordbox.

**Status:** first pass without Gemini. Gemini's listening is the tie-breaker for the main-drop
splits below; it runs once the DJ confirms uploading these seven tracks' audio.

Tool: [service/tools/crosscheck.py](../service/tools/crosscheck.py), which reads the workspace
read-only and runs on any set of tracks (`--titles …`) or the whole library (`--all`). Evidence
images and the full JSON stay out of git in `.test-desktop/crosscheck/`.

## Sources

| Source | What it gives | Independent of OnSet? |
|---|---|---|
| OnSet | its stored sections, cues, BPM, key | — |
| rekordbox | its own phrase analysis (Intro, Verse, Chorus, Outro…), grid, BPM, key | yes; OnSet takes its grid from rekordbox |
| Essentia | key, by three profiles (majority used) | yes |
| allin1 | structure segments, and a beat/downbeat model run whole (not chunked) | yes |
| Spectral | measured from the audio: bass presence per bar (below 120 Hz), and where the kick (30–90 Hz) and hats (6–11 kHz) fall within the grid's beat | yes |
| Gemini | listening to the audio: drop, breakdown, outro, BPM | pending |

## Items and tolerances

| Item | Agree when | Notes |
|---|---|---|
| Tempo | within 1% | half or double time within 2%; allin1's beat model (averaged over many beats) is the independent count |
| Grid | the kick lands within 12% of a beat of the grid's beats, and allin1's downbeats are on beat 1 | a quarter beat when allin1 is exactly on the grid and the track has no steady four-to-the-floor kick |
| Key | two sources name the same Camelot key | |
| First full groove | within 2 bars | what OnSet's **D** cue marks: the first 8 bars in a row with the bass in |
| Main drop | within 2 bars | rekordbox's first Chorus; spectrally, the bass returning after a 4+ bar gap (or the groove itself after an intro without bass) |
| Breakdown | within 2 bars | the first 4+ bars without bass after the main drop |
| Outro | within 4 bars | where an outro starts is a matter of degree |

**Decision rule.** An item is *agreed* when at least two sources, one of them not OnSet, fall
within the tolerance and OnSet is among them; *decided* when they agree and OnSet doesn't (the
agreed value is the answer); also *decided* when only two sources disagree and the audio shows
a step of 9 dB or more at one of them. Three or more sources that all disagree stay *open*.
*Confirm* means two independent sources contradict rekordbox, which needs a look before anyone
acts on it.

## Results

| Track | Tempo | Grid | Key | First groove (D) | Main drop | Breakdown | Outro |
|---|---|---|---|---|---|---|---|
| La Danza | ✓ 126.27 | ✓ | ✓ 12A | ✓ bar 2, 0:03.9 | **open**: 18 / 24 / 34 | **open** | **open** |
| Lock In | ✓ 145 | ✓ | **5A** (OnSet 6A) | **open** | **open** | **bar 69** (OnSet 41) | **bar 123** (OnSet 129) |
| Joya (Radio Edit) | ✓ 135 | ✓ | ✓ 4B | ✓ bar 4, 0:07.1 | **open**: 4 / 36 / 72 | **open** | ✓ bar 135 |
| Follow | ✓ 127 | ✓ | **10A** (OnSet 2B) | ✓ bar 18 | **open**: 18 / 34 / 65 | ✓ bar 26 | **bar 110** (OnSet 117) |
| Safe And Sound | **150** (grid 75) | ✓ | **open**: 9A / 8A / 8B | ✓ bar 20 | **open**: 12 / 20 / 32 | ✓ bar 28 | spectral only, bar 53 |
| Beautiful Places | ✓ 130 | **confirm** | ✓ 9A | ✓ bar 27 | ✓ bar 27 | ✓ bar 61 | ✓ bar 93 |
| Ray Of Solar | ✓ 135 | **confirm** | ✓ 11A | ✓ bar 48 | ✓ bar 48 | ✓ bar 64 | ✓ bar 131 |

✓ OnSet agrees with independent sources. **Bold values** are decided against OnSet.

## What was decided, and why

- **Safe And Sound is 150 BPM, not 75.** allin1's beat model counts 149.88 BPM against the
  grid's 75, and rekordbox's grid is itself the source of the 75. The grid is half time: its
  bars are two real bars long. OnSet's cues on it are still on real beats, but any BPM display,
  tempo matching or transition maths should use 150.
- **La Danza's D cue at 0:03.9 is right for what D marks.** OnSet and the spectral measurement
  both find the bass in from bar 2, and rekordbox calls that phrase a "Bridge". What is open is
  whether the cue labelled *drop* should mark this first groove or the main drop later on
  (rekordbox's Chorus at 0:45.8, or the bass returning at 1:04.8 after a short gap).
- **Keys:** Follow is 10A (rekordbox and Essentia; OnSet said 2B) and Lock In is 5A (rekordbox
  and Essentia; OnSet said 6A). OnSet's own key estimate is the outlier on both.
- **Lock In's breakdown is bar 69 (1:55.9)** and its **outro bar 123**: rekordbox and allin1
  agree on both; OnSet said bars 41 and 129. **Follow's outro is bar 110 (3:28.0)**: rekordbox,
  allin1 and the spectral measure within 4 bars; OnSet said 117.

## Needs a look: two grids may be half a beat off

On **Ray Of Solar** and **Beautiful Places** the kick lands about halfway between the grid's
beats (+0.44 and −0.38 of a beat) and the hats land on them, the reverse of the usual house
pattern; allin1's downbeats are offset by the same half beat (+0.42 and −0.49). On the other
five tracks the kick lands on the grid's beats. Two independent sources agree, but they
contradict rekordbox, and every OnSet cue on these two tracks follows that grid, so it is a
question rather than a decision (see below).

## Still open

- **Main drop** on La Danza, Joya, Follow, Safe And Sound and Lock In: three sources, three
  answers. Gemini's listening is the planned tie-breaker.
- **Breakdown** on La Danza and Joya, **outro** on La Danza, **first groove** on Lock In, and
  **Safe And Sound's key** (9A, 8A and 8B: Essentia hears the relative major of rekordbox's 8A).

## Questions for the DJ (no musical training needed)

Only the grid question is ready; the drop questions wait for Gemini, which may settle them.

1. **Ray Of Solar.** In rekordbox, load it, zoom the waveform in around 1:25 and look at the
   beat-grid lines. Do the lines sit on the tall low (kick) peaks of the waveform? *yes / no /
   they sit halfway between them*
2. **Beautiful Places.** The same, around 0:50.

If both lines sit on the kicks, rekordbox's grids stand and the check's half-beat reading is
the error. If they sit halfway between, the grid needs moving by half a beat in rekordbox before
any cue on those tracks is trusted.
