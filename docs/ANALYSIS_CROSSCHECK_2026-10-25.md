# Analysis cross-check: seven tracks, with Gemini

The seven authorized Gemini audio reads are complete. Their answers **do not settle
most drop positions**. No cue, grid, key, tempo, approval or rekordbox record was
changed. Agreement below describes estimates, not verified musical accuracy.

The DJ chose the **main payoff drop** as the future D target, keeping first full
groove separate. That change is still unimplemented. Existing D cues retain their
old first-groove meaning; do not simply relabel or approve them as main drops.

## Evidence and reproducibility

- Tool: [crosscheck.py](../service/tools/crosscheck.py). It opens the workspace
  read-only and retains all source estimates. It does not start the service.
- Original measurements and images: `.test-desktop/crosscheck/`, excluded from git.
- Completed Gemini answers, revised JSON comparison and replay script:
  `service/.artifacts/claude-takeover-20261025/`, excluded from git.
- This comparison **reused the earlier spectral and allin1 beat measurements**
  after checking all seven current track revisions exactly against the original
  report. Audio was not decoded again. The original PNGs do not include Gemini.
- Gemini listened to the seven audio proxies in the previously approved worker.
  Codex let that worker finish and did not submit duplicate uploads. Its raw
  answers, including confidence claims and notes, remain in the private evidence.
  Those confidence claims are not calibrated probabilities.
- Regression verification: `service/.venv/Scripts/python.exe -m pytest service/tests/test_crosscheck.py -q`
  — **8 passed**. These validate evidence handling, not musical labels.

## Main-drop disagreements

Times below follow each source's event on the stored grid, except Gemini's column,
which gives its raw audio timestamp. Stored D is shown for comparison, not as a
main-drop estimate. All these cues are proposed or stale, not newly approved.

| Track | Stored D | rekordbox first Chorus | Spectral candidate | allin1 first chorus | Gemini main drop |
|---|---|---|---|---|---|
| La Danza | 0:03.9 (stale) | 0:45.8 | 1:04.8 | 0:34.4 | 1:16 |
| Lock In | 0:43.0 | 0:43.0 | 0:13.2 | 1:07.9 | 0:27 |
| Joya (Radio Edit) | 0:03.6 | 0:07.1 | 2:08.0 | 1:04.0 | 1:25 |
| Follow | 0:34.1 | 1:04.4 | 0:34.1 | 2:03.0 | 1:15 |
| Safe And Sound | 1:04.1 | 0:38.5 | 1:04.1 | 1:42.5 | 0:45 |
| Beautiful Places | 0:50.1 | 0:50.1 | 0:50.1 | 0:18.7 | 0:44 |
| Ray Of Solar | 1:25.7 | 1:25.7 | 1:25.7 | 0:28.8 | 0:57 |

La Danza, Lock In, Joya and Follow have four distinct main-drop estimates outside
the two-bar tolerance. On Safe And Sound, rekordbox and Gemini are within two
**stored** bars, but the grid is at half the independently estimated tempo; two
stored bars cover about 6.4 seconds. On Beautiful Places and Ray Of Solar,
rekordbox and the spectral candidate agree while both other sources disagree.
None of these source counts alone closes the semantic acceptance gate.

The first Chorus, first sustained low-band return and main musical payoff are
different definitions. The spectral method measures energy below 120 Hz; it does
not separate a kick from a bassline or establish which return is the main payoff.
The first non-intro allin1 label is also only a proxy for full groove.

## Other findings

| Item | Evidence | Status |
|---|---|---|
| Safe And Sound tempo | stored/rekordbox 75; allin1 149.88; Gemini 150 | candidate 150, half/double-time ambiguity retained; no grid or tempo edit |
| Follow key | OnSet 2B; rekordbox and Essentia 10A | candidate 10A, no edit |
| Lock In key | OnSet 6A; rekordbox and Essentia 5A | candidate 5A, no edit |
| Safe And Sound key | OnSet 9A; rekordbox 8A; Essentia 8B | unresolved |
| Ray Of Solar grid | kick +0.44 beat; allin1 +0.42 beat | needs inspection against actual waveform |
| Beautiful Places grid | kick −0.38 beat; allin1 −0.49 beat | needs inspection against actual waveform |

All other tempo estimates agree within 1%; Gemini's 144 BPM estimate for Lock In
falls within 1% of 145. Keys agree across the three reported sources on La Danza,
Joya, Beautiful Places and Ray Of Solar. These are source agreements, not new
verified labels. OnSet uses rekordbox's grid, so their grid votes are not
independent; estimates derived from the same audio features may share errors.

The stricter event comparison leaves **Joya's outro, Follow's outro, Beautiful
Places' breakdown and Lock In's breakdown unresolved** where the earlier report
had accepted one cluster or bridged several estimates. Lock In's outro has a
three-source candidate at stored bar 121 (3:21.9), versus OnSet bar 129; Gemini's
outro is elsewhere. La Danza's breakdown/outro and Joya's breakdown remain open.
Full individual estimates and reasons are in the private JSON.

## Comparison rules and limits

Event clusters must fit entirely within two bars (four for outros). Equal-sized
competing clusters remain ambiguous, including overlapping clusters with different
endpoints. A large bass-energy step cannot settle a split vote by itself.
Corrections against a stored value are **candidates**. An `agree` status means one
cluster has more support; it does not mean unanimity, validated correctness or
permission to change the library. Raw estimates remain visible alongside it.

Exact submitted audio paths take priority over title matching; ambiguous title
matches are ignored. Malformed timestamps and timestamps outside the track are
not snapped to its final bar. Independent tempo disagreements are retained.
Essentia contributes a key only when its available profiles have a strict
majority; a three-way split does not produce an arbitrary winner.

Internal bar numbers are zero-based and refer to the current stored grid. Gemini's
written bar-number descriptions are not used; its seconds are mapped to that grid.
Original per-source timestamps and semantic interpretations remain distinguishable.

## Remaining user checks

For **Ray Of Solar**, inspect the waveform around 1:25 in rekordbox; for **Beautiful
Places**, around 0:50. Determine whether beat lines sit on the kick peaks or
halfway between them. These two checks can confirm or reject the suspected
half-beat offset; do not move either grid automatically.

The automated pass is complete, but it has not supplied verified main-drop labels.
The next implementation must separate main-payoff candidates from first-groove
evidence and preserve uncertainty, human corrections and explicit approvals. It
must show the proposed effects before changing existing real-library cues.
