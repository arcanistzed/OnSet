# OnSet continuation: 2026-10-25

## Scope and recovered decisions

The DJ asked Codex to take over unfinished Claude work after its usage ran out,
then limited the review to OnSet. All seven active OnSet sessions' saved user and
assistant histories, including carried-forward summaries, were read. The private
history index and extracts remain excluded in
`service/.artifacts/claude-takeover-20261025/`. Repeated API request envelopes were
not treated as additional conversation turns.

The previous instruction to leave installer recovery to Claude no longer blocks
this takeover. Claude's later history records successful recovery of the October
24 installer; the old file-lock screenshot is historical, not a current failure.
The installed executable was checked read-only during this takeover: 31,958,016
bytes, SHA-256 `73cc99c23dba35e2e68077532ef6d0ae68543160c811e894f9368e0211749476`,
matching the recovered `3630ea4` installed-payload record. This does not verify
the new `1952716` candidate.

Decisions recovered from the latest relevant user messages:

- Build the committed `1952716` candidate, including particles, on C: with a disk
  guard; D: is unplugged. Use two compile jobs and stop below 3 GiB free. Preserve
  unrelated data and do not overlap heavy build/test jobs.
- Skip the particle test rerun after its linear rebase: its rendering tree was
  unchanged from the prior passing checks. Do not imply fresh test execution.
- Review the seven tracks by an automated source cross-check; the user explicitly
  approved those seven audio uploads to Gemini. Do not restart the earlier manual
  first-groove listening exercise by default.
- D should target the main payoff drop; first sustained groove remains separate
  analysis information. At takeover this was unimplemented; the opt-in workflow
  below now exists in source. Stored D values do not acquire new meaning merely
  from a report or a template change.
- The DJ has no projector. Visual acceptance can use the laptop screen; an
  external projector is not a prerequisite.
- No current instruction authorizes pushing this local batch, approving cues or
  writing changes to the real rekordbox collection.

## Work already complete in source

The `1952716` candidate includes cue click/drag separation, bulk-analysis
confirmation, backup-restore preview, review navigation, batch write preview,
performance items 1–4, the pre-gig readiness check, configurable cue templates and
fast review, ear-following fixes and compute particles. These are not a new work
queue. Prior engineering results are recorded in their original commits and
session histories; new installed-app and subjective acceptance remain distinct.

## Takeover work and evidence

Packaging completed from the existing clean detached checkout
`C:\Users\water\Projects\onset-pkg` at `1952716323b4e4fff42811f87fb9e029eb4276e2`,
with a distinct `target` folder. The portable runtime is reused after checking
that its dependency manifests and runtime packaging scripts have not changed
since the previous packaging baseline. UI TypeScript and Vite production build
passed. Rust release compilation passed in 21m 45s and NSIS produced the installer.
The `binrw` future-compatibility warning did not fail compilation.

Retained candidate: `service/.artifacts/release-1952716/OnSet_0.0.1_x64-setup.exe`,
104,550,677 bytes, SHA-256
`d2e2772e6c4659d13006ec7122c6317e7928af5eec36267ad7d21de73e226c9d`.
The private manifest records 10,355 declared resource files and the main executable
(10,356 files / 505,669,868 bytes total). The exact NSIS-patched executable captured
during bundling matches the manifest. This establishes declared payload identity,
not installed acceptance. The packaging checkout remained clean at the named commit.

The build guard's original process exit-code field is **null**. Its PowerShell 5.1
polling pattern lost the child's exit status and falsely reported failure after
the successful bundle/hash output. An isolated child exiting 7 reproduced this;
holding the process handle first preserves the status. The private guard is fixed
for future runs; the original result is preserved, not rewritten as exit 0.
`build-completion-verification.json` separately corroborates completion from the
finished bundle output, final packaging hash and independently hashed artifact.

The private build guard records disk space every 30 seconds, checks every three
seconds, and terminates only its owned build process tree below 3 GiB. Its stdout,
stderr, disk watch and final result stay in the private takeover folder.

A consistent full native SQLite backup, `native-before.db` (400,838,656 bytes),
passed `pragma integrity_check` without starting the service. The private
`workspace-before.json` records hashes and complete row digests for all seven
tables: 160 tracks, 160 aliases, 185 revisions, 16 edits, 17 jobs, 61,179 artifacts
and two settings. Check the source again immediately before installation; this
snapshot does not establish post-upgrade preservation yet.

Claude's Gemini worker survived its chat usage limit and completed all seven
approved audio reads. No duplicate requests were submitted by Codex. The completed
comparison is in [the cross-check report](ANALYSIS_CROSSCHECK_2026-10-25.md).
It reuses the original spectral/beat measurements after exact checks of all seven
track revisions; it does not claim fresh audio measurement or updated PNGs.
Gemini does not settle the four-way main-drop splits on La Danza, Lock In, Joya
and Follow. No answers were imported as corrections or approvals.

The read-only cross-check tool now retains ambiguous competing vote clusters,
prevents an intermediate vote from joining incompatible event endpoints, and
does not declare a bass-energy jump conclusive evidence of a musical drop.
Suggested corrections are labelled candidates. Exact audio paths take priority
over title matching; ambiguous matches and out-of-duration timestamps are not
silently assigned to a track or clamped to its last bar. Mixed independent tempo
estimates remain unresolved. Raw Gemini answers accompany future JSON reports.

Verification: `service/.venv/Scripts/python.exe -m pytest service/tests/test_crosscheck.py -q`
— **8 passed**. These are evidence-handling regressions, not musical validation.
No analysis service was started against the real workspace.

## Main-payoff cue workflow: source verified

The schema-v2 cue template offers **Main payoff after the build** alongside the
legacy first-full-groove scheme. Existing templates and the default stay on the
legacy scheme. In Settings → Cue template → Preview, a track can have a separately
stored main-payoff candidate time, an absent-event choice or a cleared selection.
The original time, aligned bar/time and first-groove evidence remain separate.
This is an unverified selected estimate, not a new automatic detector or approval.

B/C/D follow that selected anchor only under the main-payoff preset. Unknown or
absent main payoff creates no new B/C/D; it never silently substitutes first
groove. E, G and loops keep their previous anchors. Exact read-only previews show
additions, updates, removals and retained cue meanings before application, and
changed input rejects stale previews. Applying proposals records undo history and
invalidates dependent plans/write previews.

Reviewed and hand-moved cues retain their time, name and meaning across an anchor
change and repeated reanalysis; old approval becomes stale rather than becoming
approval of a new event. Rejections remain rejected. A durable retained-decision
marker protects these cues until an explicit review/reset; reset does not erase
a hand-moved position. Mutation locks cover the relevant read/modify/write paths
and final job placement, so a concurrent edit cannot slip past the preview guard.

Verification: **221 service tests passed** (one existing silent-audio librosa
warning), **67 UI tests passed**, production UI build passed and independent source
review has no remaining actionable findings. Service command:
`service/.venv/Scripts/python.exe -m pytest service/tests -q --basetemp=.test-desktop/payoff-full-20261025g`.
No real workspace edits, cue approvals, uploads or rekordbox writes occurred.
These changes are **not in the earlier `1952716` installer**. The combined build
and installed UI acceptance follow; automatic main-payoff detection and disputed
timestamps remain open.

## Remaining gates

1. Packaging and declared payload verification of `1952716` are complete. The user
   chose to finish the cue-anchor change and package one combined build before
   installation; keep `1952716` as a verified baseline, not the combined candidate.
   Obtain action-time confirmation for installation, recheck the native workspace,
   install and verify the payload and preserved library.
2. The automated seven-track comparison is complete; semantic disagreements and
   two suspected grid offsets remain open. Model agreement does not establish
   listening ground truth. Do not automatically import its answers as edits or
   approvals.
3. The selectable main-payoff workflow is implemented and source verified. Verify
   it in the combined installed candidate; automatic detection and the disputed
   event positions remain open. Preserve human decisions and exact previews.
4. Verify changed review/template/readiness screens and ear/particles on the new
   installed candidate. Live blends and visual preference need the DJ's decks or
   observations; a laptop screen is sufficient.
5. The restart-proof MASTER investigation still needs the DJ to choose/accept
   the proposed live experiment. Do not start another long reverse-engineering
   session or press deck controls on their behalf.

P3.3–P3.5, P5.2 and V2 remain open for semantic and musical acceptance. No phase
or full-plan completion is claimed here.

## Approved cleanup

The user explicitly approved permanent removal of the main checkout's
`target/debug` and the 158 independently hash-verified temporary deep PCM copies.
This superseded the earlier Recycle Bin-only approval for those copies. Before
deletion, all 158 copy/original pairs matched fresh SHA-256 checks and the original
allowlist; all roots and reparse checks passed. A UTC timestamp formatting mismatch
was resolved by comparing parsed instants before any deletion.

Removed with no failures: 19,881 debug files / 12,907,524,158 bytes and 158 duplicate
copies / 5,563,936,696 bytes, totaling 18,471,460,854 logical bytes (17.20 GiB).
Actual C: free space rose from 7,083,667,456 to 24,761,737,216 bytes: 16.46 GiB
reclaimed and 23.06 GiB free at completion. Logical size and disk allocation differ.

Retained: 164 native decoded files (5,611,292,552 bytes), 428 stems
(15,307,955,561 bytes), the unmatched deep PCM copy, all workspace backups, native
history snapshot, source files, portable runtime, installer and the separate
packaging target. The real workspace database's SHA-256 after cleanup exactly
matches its pre-upgrade snapshot fingerprint. No database edits or model runs
were performed by cleanup. Future debug builds/tests must rebuild deleted output.

Private evidence: `cleanup-audit-158-20261025.json`,
`cleanup-result-20261025.json` and `workspace-after-cleanup.json` in the takeover
folder. The input allowlist and individual audio paths remain excluded from git.
