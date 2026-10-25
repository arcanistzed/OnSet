# OnSet value assessment, 2026-10-25

This document asks where OnSet gives a DJ something that rekordbox, Ableton and the
specialist tools around them do not already give, and where it does not. It also covers
how OnSet's features line up with what working DJs actually do when they prepare and play.
It was written from the repository and from web research; nothing was built or run, and
nothing here was checked by listening or at the decks.

The basis:

- **OnSet today.** This doc reads [HANDOFF](HANDOFF.md), [PROJECT_PLAN](PROJECT_PLAN.md),
  [PLAN_PROGRESS](PLAN_PROGRESS.md), [CONTINUATION_2026-10-24](CONTINUATION_2026-10-24.md),
  and the source in `service/onset_service`, `ui/src` and `crates/`.
- **The alternatives.** Vendor pages, release notes, manuals and reviews, as of October
  2026. They are cited inline. Vendor marketing is labelled as such, and claims that could
  not be confirmed are marked *unconfirmed*.
- **DJ practice.** DJ TechTools, Digital DJ Tips, Crossfader, CDM, vendor forums and
  interviews. Reddit could not be read directly. No DJ survey newer than the Digital DJ Tips
  2022 census was found, and that census is mostly hobbyists. Practice claims are therefore
  labelled **[wide]** when several independent sources agree, or **[opinion]** when one
  voice says it.

**Two kinds of evidence are kept apart throughout:**

- **Engineering evidence:** the code exists, tests pass, a run completed, or something was
  seen in the app.
- **Musical or live evidence:** someone listened, or it was used at the decks.

For most of OnSet's distinctive features only the first kind exists. The open gates are the
same ones PLAN_PROGRESS lists: M3 listening, M4 transition quality and M6 real rekordbox
acceptance.

**Revision, same day: accuracy evidence now comes from a cross-check.** The user does not
want to do listening reviews. In their words: "review it very throughly and ensure it's
accurate based on the phrase analysis from Rekordbox, the audio analysis from Gemini, and
the detailed spectogram analysis." Another session is building that three-way cross-check.
DJ yes/no questions are asked only where the sources genuinely disagree.

So in this document "accuracy evidence" means:

- **Agreement scores** between OnSet's analysis and three independent sources: rekordbox's
  phrase analysis, Gemini listening to the audio, and the detailed spectrogram read.
- **The DJ's answers** to the questions the cross-check raises.

This is a third kind of evidence, between engineering and listening. Agreement is not
ground truth:

- rekordbox's phrases are themselves called error-prone by DJs.
- Gemini and the spectrogram reads are model opinions. Earlier reads of Stop It disagreed
  by up to 32 bars.
- All the sources can share a bias, for example treating the first energy jump as the drop.

High agreement raises confidence, and disagreement finds the tracks worth a DJ's question.
Neither proves a cue is where the DJ would put it.

## 1. Summary

OnSet's defensible value is narrower than its feature list. Three things nobody else ships:

1. **Reviewable automatic cues with an exact write preview and a restorable database
   backup.** rekordbox 7 now places cues itself (Intelligent Cue Creation, learning from
   cues the DJ has already set; SMART CUE since 7.2.14). Mixed In Key and Lexicon generate
   cues too. All of them write straight away or through an XML import:

   - none has a per-cue approval queue;
   - none shows the exact changes before writing;
   - none can restore the DJ's library afterwards.

   DJs already treat automatic cues as a first draft they check, and they complain loudest
   about drop and mix-point cues **[wide]**. OnSet's workflow fits that practice exactly. The
   write path itself is engineering verified on the real library: one track's memory write, a
   repair of 609 pads, a playlist and a comment were checked in rekordbox, and a restore was
   rehearsed. Whether the placed cues are *musically* right is not yet verified.
2. **Pair-specific transition options.** For a given outgoing and incoming track, OnSet
   gives a technique, the exact windows, the rate and key shift, a check for clashing
   vocals and bass, and a local rehearsal render. Competitors offer track lists instead:

   - similarity lists (rekordbox Track Suggestion, VirtualDJ Genius DJ);
   - compatibility filters (Mixed In Key, Lexicon "Find Mixable Tracks");
   - harmonic ordering (DJ.Studio Harmonize).

   None scores how A's outro meets B's intro. This is OnSet's most novel feature and its
   least verified one. No transition has a listening verdict yet; the verdict buttons exist
   but no ratings have been collected.
3. **Visuals that follow a laptop rekordbox deck by its structure, with no extra
   hardware.** Resolume and PRO DJ LINK Bridge need CDJs or DJMs. rekordbox Video plays
   files. SoundSwitch, inside rekordbox since 7.2.19 (September 2026), does *lighting*, not
   video. The only comparable tool is the community project rkbx_link. It reads the same
   rekordbox memory and outputs Ableton Link, OSC and sACN, but it renders nothing.

Where OnSet is redundant or behind:

- stems;
- the key and BPM shown;
- basic phrase labels;
- a general "what goes next" suggestion list;
- cloud and sync;
- lighting (now native to rekordbox through SoundSwitch).

The analysis models (allin1, EDMFormer, Beat This!, Demucs, Essentia) are a means, not a
selling point. DJs ask for phrase counters and correct cues, not deeper structure analysis
**[opinion, repeated]**. The models only earn their cost if the cross-check shows that OnSet's
resolved structure agrees with the independent sources more often than rekordbox's phrases
alone, or settles disagreements the DJ then confirms.

The biggest structural risk is reach:

- **The live link needs rekordbox running on a laptop.** Most working club DJs play USB
  sticks on CDJs **[wide; no current share figure]**, and a USB-on-CDJ set has no rekordbox
  process to read.
- **It depends on memory offsets for each rekordbox version**, and AlphaTheta is tightening
  its protocols (a PRO DJ LINK security notice in August 2026; LINK EXPORT hardening in
  7.2.17).
- **Writes depend on the community's SQLCipher key extraction.**

The most valuable work therefore makes preparation output that survives whatever setup the
DJ plays on: cues and playlists in rekordbox, then a USB export. The rekordbox-specific live
features stay a bonus for laptop, controller and streaming DJs.

## 2. Feature-by-feature comparison

Abbreviations:

| Short form | Means |
|---|---|
| RB | rekordbox 7.2.x |
| SSL | Serato DJ Pro (Serato is owned by AlphaTheta) |
| TP4 | Traktor Pro 4 |
| EDJ | Engine DJ |
| djay | djay Pro AI |
| MIK | Mixed In Key 11 |
| Lex | Lexicon DJ |
| DJS | DJ.Studio |
| Res | Resolume Arena |
| VDJ | VirtualDJ 2026 |
| SSw | SoundSwitch |

Values in the OnSet evidence column:

- **eng** = engineering verified;
- **real RB** = checked in real rekordbox;
- **unheard** = no listening check;
- **base** = implemented baseline only.

| Capability | OnSet | Best native or specialist alternative | Verdict | OnSet evidence |
|---|---|---|---|---|
| BPM and beat grid | Imports RB's grid as the destination; runs Beat This! and DSP alongside and flags conflicts; never rewrites RB's grid | RB analysis (dynamic grid, Cloud Analysis); Serato 5 beta Lucid Beatgrids; TP4 Flexible Beatgrids | Parity at best. OnSet's value is flagging a bad grid before cues go on it, not a better grid | eng; unheard (no beat labels) |
| Key | Native chroma plus Essentia, local keys per section and per mix window, tuning, alternatives, sounding key at the played rate | RB key detection; MIK (around 86% on dance music in an older Dubspot test) | Behind or at parity on the global key (MIK is the reference DJs trust); ahead on the key at the actual mix window and rate | base; unheard |
| Phrase and structure | allin1, EDMFormer, energy baseline, a sequence model with competing sources; AI structure reads stored as unverified | RB phrase analysis (Intro/Up/Down/Chorus/Verse/Outro, editable; reputation "often needs edits"); VDJ structure detection | Unproven. Richer sources, but disagreement is large (Stop It: 0 to 32 bars across reads; La Danza drop 0:04 to 2:06 across sources) | eng (all six models ran on four tracks); unheard |
| Stems | Demucs offline (FLAC), used for vocal activity, stem-blend and a Stems tab | Real-time stems in RB, Serato, TP4, EDJ, djay, VDJ; Ableton 12.3 offline | Redundant as a performance feature; useful only as analysis input | eng |
| Energy | Separate drive, density, tension and contrast curves; 1–10 calibrated to the DJ's own ratings | MIK Energy Level (distrusted by many DJs **[opinion, several]**); RB My Tag set by hand | Potential lead if calibrated to the DJ; uncalibrated today (no personal labels) | base |
| Genre and details | Discogs-EffNet genre, nearest-neighbour genres from the DJ's own tags, cited web claims from AI providers | RB Track Suggestion modes (Mood, Era); Lex tags and smartlists; manual tags | Modest. Cited claims are unusual; genre suggestions from the DJ's own tags are useful for library hygiene | eng (Stop It); genre unheard |
| Automatic cues | Six-role scheme (A first beat, B 32 bars and C 16 bars before the drop, D drop, E breakdown, F outro; optional loops); review queue ranked by impact; per-cue approval; stale when grid or audio changes | RB Intelligent Cue Creation (learns the DJ's own placement) and SMART CUE; MIK up to 8 cues via XML (memory cues can block it); Lex template cue generator | **Ahead on control and safety**; parity or behind on placement until listening proves otherwise. RB learns the DJ's own style; OnSet uses a fixed scheme | real RB (write path); unheard (placement) |
| Writing to RB | Direct `master.db` write via SQLCipher; exact preview; manual cues kept; consistent backup; restore manifest; refuses while RB runs; pad numbering fixed | MIK, DJS and Lex go through RB XML import or library conversion; no vendor offers a restorable DB backup | **Clearly ahead** on safety and exactness; carries the risk of an unofficial DB path | real RB, 2026-10-22 |
| Mix-point links | `mixplan.py` links each out cue to the in cues of good followers | RB **Mix Point Link** (on all plans per the RB overview page) | Possibly redundant. `mixplan.py`'s docstring says RB has no mix-point link of its own (checked against 7.2.18 tables); RB now advertises one. Needs a look at what RB stores | needs checking |
| Transition options | 18 techniques; per-pair windows, rate and key shift, vocal and bass clash checks, up to three options with reasons and uncertainty | djay Automix AI (picks points automatically; method undocumented); djay Crossfader Fusion presets; DJS transition editor (manual); MIK Pro mix-out suggestions | **Ahead (novel)** on explained, pair-specific options; unverified musically | base; no listening verdicts |
| Rehearsal | Local renders of 11 techniques with click and markers; two-track manual players | DJS renders a whole set mix; djay Automix plays it; practising at the decks | Parity with DJS; behind the decks themselves. Useful to triage options before practising | eng (renders); unheard |
| Set planning | Deterministic beam search (width 128), three alternatives, constraints, pins, partial replanning, comparison with AI providers, exports including an RB playlist | DJS (timeline, Harmonize, RB playlist export with transition hot cues); RB Intelligent Playlist; Lex smartlists | Ahead on constraints and explanations; over-built for club practice (see §5) | eng; flow unheard |
| Next-track suggestions | Fallback routes in the planner; nothing live | RB Track Suggestion (5 modes, Radar AI); VDJ Genius DJ; Lex Find Mixable Tracks | **Behind live**: O1's fallback tracks are not in the live view | not delivered live |
| Live advice | Live view: title, key, BPM, section, next section, beats to it, drop countdown, next cue | CDJ-3000 and RB phrase and bar meters, beat countdown to memory cue | Parity for basic counters; ahead on drop countdown from corrected structure. Plan progress, plan-match check and fallbacks (O1) are missing | eng (followed MASTER on 7.2.19) |
| Live deck state | Memory reader per RB version; guided calibration; track by content id; MASTER from a flag (the cross-launch route was withdrawn) | PRO DJ LINK Bridge (CDJ and DJM only, licensed partners); Beat Link Trigger (CDJ network, unofficial); rkbx_link (same memory approach, Link, OSC and sACN out); Ableton Link (tempo and phase only) | Ahead of official routes for laptop RB; on a par with rkbx_link; zero reach for USB-on-CDJ sets | real RB 7.2.19 |
| Visuals | 14 wgpu scenes; beat-locked kick and snare from the RB grid (+35 ms measured lag); director intensity from structure; deck-by-ear blend shares; lyrics (LRCLIB); projector window | RB Video (file playback, 1080p, overlays); Serato Video; VDJ thousands of audio-reactive visualisations; Res (FFT, Link, Bridge); Synesthesia | **Ahead for structure-aware generative visuals on laptop RB without a VJ**; behind Res and VDJ on breadth and stability | eng; not watched in a real set by the DJ |
| Lighting | None | RB Lighting (RB-DMX1, US$399), SSw inside RB 7.2.19 (paid licence), Hue and Nanoleaf | Absent; native now | — |
| Recording and replay | `.onsetrec` of engine state for tuning scenes | RB recording; OBS | Engineering tool, not DJ value | eng (synthetic fixture only) |
| AI advisers | Claude, Codex, Gemini, ChatGPT: cited details, set critiques, structure reads, all stored as unverified | None in DJ apps | Novel but low weight; reads disagree with each other | eng (three tracks) |
| Library hygiene | Identity, aliases, relocation, portable export, workspace backups | Lex (duplicates, metadata cleanup, sync between apps), RB | Behind Lex; not OnSet's job | eng |

## 3. Ahead, at parity, redundant

**Clearly ahead.** These hold even before listening, because they are about control, not
taste.

- The approval, preview, write and restore pipeline for cues, playlists and comments in
  rekordbox's own database.
- Transitions explained per pair, with the reason, windows, rate and key at the overlap, and
  the uncertainty stated.
- A structure-aware show on a laptop rekordbox deck without CDJs, Bridge or a VJ.

**Potentially ahead, unproven.** Each of these needs cross-check agreement scores,
plus the DJ's answers where sources disagree.

- Cue placement accuracy.
- Phrase and section accuracy from the multi-model resolution.
- Energy curves calibrated to the DJ.
- The drop countdown from corrected structure rather than rekordbox's phrases.

**At parity.**

- The key and BPM shown.
- Basic phrase and bar counters live.
- Rehearsal renders (DJ.Studio does the same at set scale).
- Constrained set ordering (DJ.Studio is the comparison).

**Redundant.**

- Stems as a listening or performance feature: every DJ app has them in real time.
- Global key detection as a headline feature.
- A general "what goes next" list.
- Possibly `mixplan.py`'s cue-to-cue links, if rekordbox's Mix Point Link stores something
  equivalent.
- Lighting, which OnSet does not do and need not now.

## 4. Risks to OnSet's position

| Risk | Likelihood | Effect | Mitigation |
|---|---|---|---|
| **Reach:** most club DJs play USB on CDJs, so there is no rekordbox process to read | High, already true | Live view and visuals unusable at most club gigs | Make preparation output the product. Consider a PRO DJ LINK path for CDJs (Beat Link-style; unofficial, needs the network) only if visuals become central |
| **Memory offsets per rekordbox version:** each update needs calibration; MASTER across launches already failed once (withdrawn routes, 2026-10-23) | Certain, recurring | Live link breaks after an update until recalibrated, possibly before a gig | Keep the guided calibrator; ship offsets fast; say clearly in the UI when the version is uncalibrated; fall back to audio-only visuals |
| **Protocol tightening:** August 2026 PRO DJ LINK security notice; 7.2.17 LINK EXPORT hardening | Medium | Process memory protection or database changes could close the reader or the write path | Keep an XML export path for cues and playlists as a fallback (it loses the restorable backup but survives) |
| **Unofficial DB writes:** SQLCipher key from community extraction; pyrekordbox warns about corruption | Medium | A schema or key change blocks writes; a bad write would cost trust badly | Already mitigated: preview, backup, savepoints, refusal while RB runs, restore rehearsal. Keep the real-library gate (V3) strict |
| **rekordbox adds the feature:** Intelligent Cue Creation already learns the DJ's cues; SMART CUE (undocumented); Mix Point Link; SoundSwitch auto-lighting; Radar suggestions | High for cues and lighting, medium for transition scoring, low for audio-reactive video | OnSet's cue placement becomes redundant if RB's is good enough | Compete on review and control rather than placement; benchmark OnSet's cues against RB's own on the same tracks |
| **Consolidation:** AlphaTheta owns Pioneer, rekordbox and Serato; inMusic owns Engine and SoundSwitch and is buying Traktor (NI) | Ongoing | Fewer neutral integration points | Stay rekordbox-first; avoid features only one vendor can deliver |
| **Heavy local models:** Demucs stems at 13.5 GB per 99 tracks before FLAC; EDMFormer runs out of memory on long tracks; jobs of hours; C: is short of space | Certain on this laptop | Prep feels slower than RB's Cloud Analysis; disk pressure | Make deep analysis opt-in per track or for flagged disagreements, not library-wide by default |
| **Unproven accuracy:** no listening benchmark; sources disagree by up to 32 bars | Certain until the cross-check reports | Cannot honestly claim better cues or structure | Run the three-way cross-check (rekordbox phrases, Gemini audio, spectrogram) before adding analysis features; publish agreement per event type; never present agreement as ground truth |
| **Shared bias in the cross-check:** sources agree on the same mistake, e.g. an energy jump read as the drop | Medium | High agreement hides a wrong cue | Report agreement separately for each pair of sources; send any unanimous-but-unusual answer (drop in the first 8 bars, no outro) to the DJ as a yes/no question; track the DJ's corrections as the only ground truth |
| **Laptop risk in the booth:** DJs see the laptop as a single point of failure **[wide]** | High | DJs will not run an extra app beside rekordbox at a gig unless it is clearly read-only and light | Keep show mode read-only, pause jobs, measure CPU; already in O4 |

## 5. Workflow fit: what DJs do, and how OnSet serves it

Each workflow is ranked by how often a DJ feels the need.

### 5.1 Preparation

| Rank | What DJs need and do | Sources | OnSet today | Fit | Add, change or drop |
|---|---|---|---|---|---|
| 1, every new track | **Get a track gig-ready:** a checked grid, an accurate first-beat cue, mix-in and mix-out memory cues. 1–3 minutes per track by hand. Top hot-cue row for structure (intro, build 8–16 bars before the drop, drop, breakdown, outro); bottom row for performance. Personal colour schemes. Auto cues are trusted only as a draft; drop and first-beat placement is where they fail | Crossfader hot-cue guide (2025); DJ TechTools prep-time threads; MIK complaints ("redid 25,000 cues"; misses the first beat "7 out of 10") **[wide]** | Six-role scheme close to the common convention; review queue ranked by impact; approval; exact write | **Good**, best-fitting feature | **Add:** a fast review loop (one key to approve, audition at cue, next track), measured in seconds per track. **Add:** a user-defined cue template (which roles, which pads, bars before the drop, colours where RB honours them). RB already learns placement from the DJ's cues; OnSet should at least let the DJ set the scheme. **Change:** default to memory cues for mix-in and mix-out, hot cues only for structure |
| 2, every gig | **A library and USB that won't fail:** database corruption, firmware, bad grids with sync on; DJs back up music but not the database | CDM failure guide (2024); Zedd's Ultra 2023 USB failure **[wide]** | Consistent RB backup and restore for its own writes; workspace backups; grid conflict flags | **Partial**; serves its own writes, not the gig | **Add:** a pre-gig check of the playlists for the gig: missing files, grids flagged as conflicting, tracks without a first-beat cue, unapproved D. OnSet has the data. **Do not** build USB export (rekordbox does it) |
| 3, per gig | **Loose set preparation:** an opener, a pool of 50–60 tracks, reorderable blocks of 3–6, then reading the room. Full plans are for mixtapes, radio and corporate gigs. Harmonic mixing is a hint, not a rule | DJ TechTools "how much prep"; Moudaber, Väth, Vood interviews; MusicRadar on harmonic mixing **[wide]** | Planner produces one ordered set (beam search, three alternatives); brief with many constraints | **Poor fit for club DJs**; good for mixtapes and radio | **Change:** make the main output a *pool with routes*: the tracks grouped into blocks, each with good next options and their transitions, rather than one fixed order. Keep the full-order planner for recorded mixes. **Simplify** the brief to slot (warm-up, peak, closing), length, energy arc and must-plays |
| 4, per gig | **Remember which pairs work:** "goes with…" comments; requests for a Match button in djay | DJ TechTools; Algoriddim community **[opinion, repeated]** | Transition verdicts (works, needs changes, doesn't) stored per option; comment block written to RB | **Good, unused** | **Add:** write approved pairings back into RB, e.g. as a playlist of "goes with" tracks or a short comment line, so they show on CDJs. This makes the verdicts useful at the gig |
| 5, per batch | **Metadata and tag hygiene;** personal energy and vibe tags (My Tag Low/Mid/High/Peak; time of night); distrust of MIK energy | Crossfader; DJ Will Gill; Algoriddim and Engine forums **[wide]** | Genre suggestions from the DJ's own tags; energy calibrated to the DJ's ratings (unlabelled) | **Partial** | **Add:** propose RB My Tag values (energy, slot) from OnSet's curves, for approval and written like cues. That puts the energy work where DJs already filter. **Drop** any absolute 1–10 energy display until calibrated |
| 6, per practice | **Record practice mixes and review the transitions** (timecode the bad ones; check bass clashes and phrase alignment) | Digital DJ Tips practice guides **[wide among educators]** | Rehearsal renders; verdicts; nothing that reads a recorded mix | **Partial** | **Add, later:** import a recorded practice mix, find where each transition happened (OnSet knows the tracks), and file a verdict per pair. This is a natural source of the listening labels M4 needs |
| 7, rare | Deep structure analysis as such | Algoriddim requests ask for phrase counters, not analysis depth **[opinion]** | Six models, about 86 minutes for four tracks on this laptop | **Over-built** | **Simplify:** native analysis plus rekordbox's phrases by default; run deep models on tracks where the sources disagree, or on request |

### 5.2 Performance

| Rank | What DJs need and do | Sources | OnSet today | Fit | Add, change or drop |
|---|---|---|---|---|---|
| 1, every mix | **See the phrase position and the time to the next section at a glance;** a countdown to the memory cue | DJ TechTools CDJ phrase threads; Algoriddim phrase requests **[wide]** | Live view: section, next section, beats to it, drop countdown, next cue | **Good for laptop RB users** | Keep; **check** that the countdown uses the DJ's corrected structure. On CDJs, the same value reaches the DJ only through the cues OnSet wrote, another reason to put preparation first |
| 2, every track | **Choose the next track from the pool by reading the room** (floor density, time of night, slot etiquette); software suggestions rarely trusted | Digital DJ Tips poll; Electronic Beats; Magnetic warm-up etiquette **[wide]** | Plan exists, but the live view shows no plan progress, no next options and no fallbacks (O1 not delivered live) | **Not served** | **Add:** in the live view, the 3–5 best next tracks from the gig's pool for the deck now playing, each with the prepared transition and its window, plus a "more energy / same / less" toggle. The DJ chooses; nothing is loaded. This is O1's fallback list made useful |
| 3, every gig | **Not crash; not add load:** laptops in the booth are a single point of failure | CDM; DJ TechTools; Bonedo **[wide]** | Show mode pauses jobs, read-only, no writes during the show (O4) | **Good** | **Add:** a visible "show-safe" state (service idle, CPU budget) and a one-click way to run only the live view and visuals |
| 4, subset of DJs | **Visuals without a VJ:** small venues, mobile and streaming DJs. Big clubs have a VJ or lighting operator. Lighting is now inside RB via SoundSwitch | Digital DJ Tips visuals Q&amp;A; rekordbox 7.2.19 SoundSwitch news **[wide]**; demand among small-club and streaming DJs *unconfirmed* | 14 scenes; beat-locked hits; structure director; lyrics; projector window | **Good for that subset**; laptop RB only | **Add:** OBS-friendly output (Spout or NDI, or a window capture preset) and a now-playing overlay for streamers. **Consider:** Ableton Link and OSC output of phrase and section, so Resolume or TouchDesigner users can use OnSet's structure (rkbx_link already sells this) |
| 5, a few | **Streaming** (about 11% regularly, about 30% have tried, 2022 census); Twitch DJ category since 2024 | MusicTech; Digital DJ Tips census | Visuals and lyrics usable as a stream scene | **Partial** | As in rank 4 |
| 6, occasional | Recording the set and exporting a tracklist | Plug the Jack; DJ Class **[wide]** | `.onsetrec` records engine state for development, not audio or a tracklist | **Not served** | **Add:** a timestamped tracklist from the live link (title, artist, start time per MASTER change). Cheap, since the live link already knows it |
| — | Lighting | rekordbox Lighting, SoundSwitch | None | — | **Do not build.** It is native now |

## 6. Double down, cut, simplify

**Double down on:**

- **Cue review and safe writing.** This is OnSet's strongest fit with practice, and rekordbox
  has nothing like it. Make it fast, configurable and benchmarked against rekordbox's own
  automatic cues.
- **Transitions explained per pair, with verdicts that reach the gig.** Collect verdicts and
  write approved pairings into rekordbox.
- **A pre-gig readiness check** for the gig's playlists.
- **Structure-aware visuals for laptop rekordbox DJs,** plus OBS and Link/OSC outputs.

**Simplify:**

- **Deep analysis:** opt-in, or only where sources disagree.
- **The set brief:** slot, length, arc and must-plays first; the rest under "more".
- **Planner output:** pools and blocks with routes for club DJs; a full order for recorded
  mixes.
- **AI advisers:** keep cited track details; the set critiques and structure reads are
  opinions with no reliability weight, so do not surface them prominently.

**Cut or leave to others:**

- a stems playback and performance surface (keep stems only as analysis input);
- lighting;
- library conversion and duplicate cleanup (Lexicon);
- cloud sync;
- `mixplan.py`'s separate CSV path once the planner covers it, if rekordbox's Mix Point Link
  turns out to overlap (check first).

## 7. Recommendations ranked by value to a DJ

| # | Recommendation | Why it ranks here | Kind of work | Evidence needed |
|---|---|---|---|---|
| 1 | **Finish the three-way cross-check** (rekordbox phrases, Gemini audio analysis, spectrogram read) over the analysed tracks: agreement scores per event (first groove or D, breakdown, outro, mix windows) and per source pair, with DJ yes/no questions only where the sources disagree. It replaces the listening review in REVIEW_LISTENING_2026-10-22 | No accuracy claim in §1 can be made until it reports; it also decides whether deep analysis earns its cost | Engineering, plus a few minutes of DJ answers per disputed track | Agreement scores (not ground truth) plus the DJ's answers |
| 2 | **Fast cue review with a DJ-defined cue template** (roles, pads, bars before the drop, memory or hot) | Every new track; the core of the "draft then check" practice | UI and service | Yes, measure seconds per track and edits per cue |
| 3 | **Compare OnSet's cues with rekordbox's Intelligent Cue Creation** on the cross-checked tracks: how often each set of cues lands where the other two sources agree, and which the DJ picks on disputed tracks | Decides whether OnSet competes on placement or only on control. Because rekordbox's phrases are one of the cross-check sources, the comparison leans towards rekordbox; count rekordbox-only agreement separately | Engineering plus the DJ's answers | Cross-check agreement; DJ choice on disputes |
| 4 | **Pre-gig readiness check** for a playlist: missing files, grid conflicts, missing first-beat cue, unapproved D, stale approvals | Every gig; prevents the failures DJs fear most; data already exists | Service and UI, small | No for the check; yes for usefulness |
| 5 | **Live next-track options from the gig pool** (3–5 tracks with the prepared transition; more, same or less energy) | Every track, for laptop RB DJs; delivers O1's missing half | Live view and engine | Yes, at the decks |
| 6 | **Write approved pairings and energy or slot tags into rekordbox** (My Tag or comment, previewed and approved like cues) | Makes preparation visible on CDJs, where most club DJs play | rekordbox write path, using the existing preview and backup | Yes, check in rekordbox and on CDJs |
| 7 | **Pool-and-blocks planner output** alongside the full order | Matches how club DJs prepare | Planner and UI | Yes, DJ judgement |
| 8 | **Make deep analysis opt-in, or limited to disagreements** | Cuts hours and gigabytes from prep; no loss until the cross-check shows the deep models raise agreement or settle disputes the DJ confirms. The cross-check itself can be the trigger: run deep models only on tracks where rekordbox, Gemini and the spectrogram disagree | Service settings | Cross-check agreement with and without deep models, after #1 |
| 9 | **Visual outputs for streamers and VJs:** Spout or NDI, a now-playing overlay, Ableton Link and OSC with phrase and section | Serves the subset that already runs the laptop; small work | Rust | Yes, in OBS and Resolume |
| 10 | **Tracklist from the live link** | Cheap; occasional need | Rust | Light |
| 11 | **Check rekordbox Mix Point Link** against `mixplan.py`'s assumption, and correct the docstring | Avoids building something native | Reading rekordbox 7.2.19's database and UI | No |
| 12 | **XML fallback for cues and playlists** in case the SQLCipher path closes | Insurance against the main platform risk | Service | Yes, import in rekordbox |
| 13 | **Practice-mix import** to find transitions in a recording and collect verdicts per pair | Feeds M4 labels; matches the most-recommended practice habit | Larger: audio alignment | Yes |

Deliberately not recommended:

- a CDJ/PRO DJ LINK reader: it is unofficial, needs network hardware, and the licensed Bridge
  partners already cover it;
- lighting;
- library conversion;
- more structure models before the benchmark.

## 8. What this assessment cannot say

- **Whether OnSet's cues, sections or transitions are musically better than rekordbox's.**
  Six models completing on four tracks is engineering evidence only. The planned three-way
  cross-check will give agreement scores, but agreement is not ground truth:
  - rekordbox's phrases are one of the sources, so they can't judge themselves.
  - Gemini and the spectrogram reads are model opinions.
  - All the sources may share a bias.
  
  The DJ's answers on disputed tracks are the only ground truth the plan now collects, and
  they cover disputed tracks only. A wrong cue that every source agrees on can still go
  unnoticed until it is played.
- **Whether transitions work.** The cross-check covers structure, not how two tracks sound
  together. Transition quality has no evidence source until the DJ gives verdicts, either
  from playing the pairs or through the practice-mix import (#13).
- **How many target users run rekordbox on a laptop at gigs.** No current share was found;
  the 2022 census (about 21,000 respondents, mostly hobbyists) had just over half on
  controllers and laptops and about a quarter on CDJs or standalones.
- **What rekordbox's SMART CUE does, and what Mix Point Link stores.** Both are unconfirmed
  from public sources.
- **Whether DJs value generated transition suggestions.** No evidence either way was found.
- **Whether small-club and streaming DJs want automatic visuals.** No survey was found.

## Sources

Feature inventory (as of October 2026):

- rekordbox: [feature overview](https://rekordbox.com/en/feature/overview/),
  [7.2.16 notes](https://rekordbox.com/en/2026/07/rekordbox-v7216-release-information/),
  [7.2.14 notes (SMART CUE)](https://rekordbox.com/en/2026/04/rekordbox-v7214-release-information/),
  [release notes](https://rekordbox.com/support/releasenote/),
  [operation FAQ (phrase, Track Suggestion)](https://rekordbox.com/en/support/faq/operation-hints-7/),
  [video FAQ](https://rekordbox.com/en/support/faq/video-7/),
  [lighting FAQ](https://rekordbox.com/en/support/faq/lighting-5/),
  [developer page (XML)](https://rekordbox.com/en/support/developer/),
  [SoundSwitch support announcement](https://rekordbox.com/en/2026/09/rekordbox-for-mac-windows-and-pro-dj-link-bridge-support-soundswitch/),
  [The FADER on 7.2.19 and Bridge](https://www.thefader.com/2026/09/24/rekordbox-pro-dj-link-bridge-lighting-software),
  [DJ Mag on the PRO DJ LINK security notice](https://djmag.com/news/alphatheta-issues-security-warning-rekordbox-and-cdjxdj-users-over-pro-dj-link-data-risk),
  [loop.fans review of rekordbox AI features](https://music.loop.fans/ai/rekordbox-ai-review-a-new-era-of-intelligent-djing-in-the-pioneer-ecosystem),
  [PRO DJ LINK Bridge](https://www.pioneerdj.com/en/product/software-interfaces/pro-dj-link-bridge/),
  [pyrekordbox](https://pyrekordbox.readthedocs.io/en/stable/quickstart.html)
- Serato: [expansions](https://serato.com/dj/pro/expansions),
  [MusicTech on DJ 5.0 beta](https://musictech.com/news/gear/public-beta-serato-dj-5-0-new-features/),
  [MusicTech on the AlphaTheta acquisition](https://musictech.com/news/gear/pioneer-dj-alphatheta-acquires-serato/)
- Traktor: [NI Traktor Pro 4](https://www.native-instruments.com/zh/press-area/djing/traktor-pro-4/),
  [ProSoundWeb on inMusic acquiring NI](https://www.prosoundweb.com/inmusic-signs-agreement-to-acquire-native-instruments/)
- Engine DJ: [Engine DJ 5.0](https://enginedj.com/news/articles/introducing-engine-dj-5-0),
  [stems in 4.2](https://enginedj.com/news/articles/engine-dj-stems-now-available-in-version-4-2),
  [djworx on StageLinQ](https://djworx.com/stagelinq-soundswitch-resolume-denon-djs-visual-trinity/)
- djay: [Automix manual](https://help.algoriddim.com/user-manual/djay-pro-mac/mixing-basics/using-automix),
  [djay Pro 5 press release](https://algoriddim.com/press_releases/447-algoriddim-unveils-djay-pro-5-with-next-generation-neural-mix-crossfader-fusion-and-fluid-beatgrid-)
- Ableton: [Link documentation](https://ableton.github.io/link/),
  [MusicTech on Live 12.3](https://musictech.com/news/music/ableton-live-12-3/)
- Specialists: [Mixed In Key with rekordbox](https://mixedinkey.com/workflows/use-mixed-in-key-with-rekordbox/),
  [Magnetic MIK 11 review](https://magneticmag.com/2025/01/mixed-in-key-11-review/),
  [Lexicon](https://www.lexicondj.com/),
  [Lexicon cue generator](https://Rekord.cloud/wiki/cuepoint-generator),
  [DJ.Studio](https://dj.studio/),
  [DJ.Studio rekordbox export](https://rekordbox.com/en/connect/djstudio/dj-set-preparation/),
  [Resolume sync to Pioneer players](https://www.resolume.com/support/en/sync-to-pioneer-dj-players),
  [VirtualDJ](https://virtualdj.com/products/virtualdj/),
  [Synesthesia](https://synesthesia.live/),
  [rkbx_link](https://github.com/grufkork/rkbx_link),
  [Beat Link Trigger](https://github.com/Deep-Symmetry/beat-link-trigger)

DJ practice:

- Library and organisation:
  [Crossfader library tips](https://wearecrossfader.co.uk/blog/five-library-management-tips-in-rekordbox/),
  [DJ Will Gill on organising music](https://djwillgill.com/how-to-organize-dj-music/),
  [MusicTech on Lexicon](https://musictech.com/news/gear/dj-library-management-lexicon/),
  [CDM guide to USB and rekordbox failures](https://cdm.link/how-to-avoid-usb-and-rekordbox-djing-failures-a-complete-guide/),
  [EDM.com on worst-case planning](https://edm.com/gear-tech/new-free-tool-helps-djs-plan-worst-case-scenarios/)
- Analysis and cues:
  [Dubspot on MIK accuracy](https://blog.dubspot.com/harmonic-mixing-pt-3-lab-report-is-mixed-in-key-accurate),
  [Digital DJ Tips on Mixed In Key](https://www.digitaldjtips.com/is-it-still-worth-using-mixed-in-key/),
  [Algoriddim community on MIK energy](https://community.algoriddim.com/t/mixed-in-key-djay-pro-is-it-worth-it-for-energy-tagging/40191),
  [Digital DJ Tips on the rekordbox auto-loop bug](https://www.digitaldjtips.com/rekordbox-auto-loop-bug-how-to-fix-it/),
  [Crossfader hot cue guide](https://wearecrossfader.co.uk/blog/hot-cues-complete-guide/),
  [DJ TechTools on prep time](https://forum.djtechtools.com/t/prep-time-on-tracks-setting-cues-etc/39806),
  [DJ TechTools on how much prep goes into sets](https://forum.djtechtools.com/t/how-much-prep-goes-into-your-sets/68039),
  [Algoriddim phrase requests](https://community.algoriddim.com/t/phrase-analysis-tool-energy-cue-countdowns/42806),
  [Algoriddim Match request](https://community.algoriddim.com/t/match-button-to-save-tracks-that-work-well-together/42162)
- Set planning and reading the room:
  [Digital DJ Tips on what separates great DJs](https://www.digitaldjtips.com/what-separates-good-from-great-djs/),
  [Electronic Groove on reading the room](https://electronicgroove.com/dj-rituals-reading-the-room/),
  [Magnetic interview with Enzo Vood](https://magneticmag.com/2026/09/enzo-vood-interview/),
  [MusicRadar on harmonic mixing](https://www.musicradar.com/news/harmonic-mixing),
  [Magnetic on opening-DJ etiquette](https://magneticmag.com/2019/03/artist-advice-etiquette-for-opening-djs/),
  [Digital DJ Tips on warm-up sets](https://www.digitaldjtips.com/how-to-dj-warm-up-sets/)
- Practice: [Digital DJ Tips on recording sets](https://www.digitaldjtips.com/recording-your-dj-sets-habit/),
  [Digital DJ Tips on practice sessions](https://www.digitaldjtips.com/5-steps-to-better-practice-sessions/)
- Booth and hardware:
  [DJ TechTools on counting phrases on CDJs](https://forum.djtechtools.com/t/cdj-2000-nexus-any-tips-for-counting-bars-phrases/54825),
  [CDM on laptops in the booth](https://cdm.link/lets-talk-laptops-dj-booth/),
  [Digital DJ Tips 2022 census](https://www.digitaldjtips.com/2022/03/here-are-the-results-from-our-2022-census-the-biggest-dj-survey-in-the-world/),
  [rekordbox FAQ on PRO DJ LINK modes](https://rekordbox.com/en/support/faq/trouble-shooting-5)
- Visuals and streaming:
  [Digital DJ Tips on visuals behind the DJ](https://www.digitaldjtips.com/your-questions-how-do-i-set-up-visuals-behind-me/),
  [Digital DJ Tips RB-DMX1 review](https://www.digitaldjtips.com/reviews/rbdmx1/),
  [MusicTech on the Twitch DJ category](https://musictech.com/news/industry/twitch-to-launch-official-dj-category/),
  [Digital DJ Tips on Serato's Twitch extension](https://www.digitaldjtips.com/serato-twitch-visuals-extension/)
