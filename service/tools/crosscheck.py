#!/usr/bin/env python
"""crosscheck.py - check OnSet's analysis of each track against independent sources.

  crosscheck.py OUT_DIR [--titles NAME ...] [--all] [--gemini gemini.json] [--workspace workspace.db]

Sources, all read-only:
  onset      OnSet's stored analysis (sections, cues, BPM, key, grid)
  rekordbox  rekordbox's own phrase analysis, grid, BPM and key, as OnSet stored them on import
  essentia   Essentia's three key profiles (deep analysis)
  allin1     the All-In-One structure model (deep analysis, run whole, not chunked)
  spectral   measured here from the audio: low-band (kick and bass) energy per bar, kick onsets
  gemini     optional: Gemini listening to the audio, from a JSON file (see --gemini)

Writes OUT_DIR/crosscheck.json, one OUT_DIR/<track>.png per track with every source's markers,
and prints a markdown report. Never opens the workspace for writing and never starts the service.
"""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from onset_service.aireads import _colour, _png, _text
from onset_service.tonal import camelot

WORKSPACE = Path.home() / "AppData/Local/Onset/Onset/data/workspace/workspace.db"

# Tolerances. Bars count from zero on the track's own (rekordbox) grid.
TEMPO_TOL = .01          # BPMs agree within 1%; a ratio of 2 or 1/2 within 2% is half or double time
EVENT_TOL = 2            # events agree within 2 bars (rekordbox phrases are 4–8 bars long)...
OUTRO_TOL = 4            # ...outros within 4: where an outro starts is a matter of degree
GRID_PHASE = .12         # the grid is on the kick when the kick lands within 12% of a beat of it
PRESENT_DB = 6           # a bar has its bass when its low band is within 6 dB of the track's loud level
ABSENT_DB = 10           # and lacks it when 10 dB or more below

ITEMS = {
    "tempo": "BPM, including half or double time",
    "grid": "Grid on the kick",
    "key": "Key (Camelot)",
    "groove": "First full groove (kick and bass in): current stored D behaviour",
    "drop": "Main drop candidates (the requested D target; not yet implemented)",
    "breakdown": "First breakdown after the groove",
    "outro": "Outro start",
}


def mmss(t):
    return None if t is None else f"{int(t // 60)}:{t % 60:04.1f}"


def bar_of(t, downbeats):
    return None if t is None else int(np.argmin(np.abs(np.asarray(downbeats) - t)))


def seconds(text):
    if text in (None, "", "null"):
        return None
    m = re.fullmatch(r"\s*(\d+):(\d{1,2}(?:\.\d+)?)\s*", str(text))
    return int(m[1]) * 60 + float(m[2]) if m and float(m[2]) < 60 else None


def gemini_for_track(p, results):
    """Prefer the submitted audio path; never pick an arbitrary substring match."""
    normal = lambda s: str(s).replace("\\", "/").casefold()
    exact = [v for k, v in results.items() if normal(k) == normal(p["path"])]
    if len(exact) == 1:
        return exact[0]
    title = (p.get("title") or "").casefold()
    matches = [v for k, v in results.items() if title and title in normal(k)]
    return matches[0] if len(matches) == 1 else None


def profiles(db, titles, everything):
    con = sqlite3.connect(f"file:{Path(db).resolve().as_posix()}?mode=ro", uri=True)
    try:
        out = []
        for (raw,) in con.execute("select profile from tracks"):
            p = json.loads(raw)
            if not (p.get("analysis") or {}).get("downbeats"):
                continue
            if everything or any(t.lower() in (p.get("title") or "").lower() for t in titles):
                out.append(p)
        return out
    finally:
        con.close()


def spectral(path, downbeats, duration):
    """Low-band energy per bar, kick onsets, grid offset and the events they imply."""
    import librosa
    y, sr = librosa.load(path, sr=22050, mono=True)
    hop = 512
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop)) ** 2
    f = librosa.fft_frequencies(sr=sr, n_fft=2048)
    times = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=hop)
    db = lambda rows: 10 * np.log10(S[rows].sum(axis=0) + 1e-10)
    low, full = db(f < 120), db(np.ones_like(f, bool))
    edges = np.append(downbeats, duration)
    per_bar = lambda curve: np.array([curve[(times >= a) & (times < b)].mean() if np.any((times >= a) & (times < b)) else -100
                                      for a, b in zip(edges[:-1], edges[1:])])
    low_bar, full_bar = per_bar(low), per_bar(full)
    ref = float(np.percentile(low_bar, 85))
    present, absent = low_bar >= ref - PRESENT_DB, low_bar <= ref - ABSENT_DB
    n = len(low_bar)

    def sustained(mask, start, length):
        return next((b for b in range(start, n - length + 1) if mask[b:b + length].all()), None)

    # Groove: the first 8 bars in a row with the bass in. Main drop: the groove itself after an
    # intro without bass; when the bass is in almost from the start, its return after the first
    # gap of 4+ bars. Breakdown: the first such gap after the main drop.
    groove = sustained(present, 0, min(8, n))
    drop = breakdown = None
    if groove is not None:
        drop = groove
        if groove < 8:
            gap = sustained(absent, groove + 1, 4)
            back = sustained(present, gap, min(8, n - gap)) if gap is not None else None
            drop = back if back is not None else groove
        breakdown = sustained(absent, drop + 4, 4)
    outro, best = None, 3.
    for k in range(int(n * .6), n - 4):
        before, after = full_bar[max(0, k - 16):k].mean(), full_bar[k:].mean()
        if before - after > best:
            outro, best = k, before - after
    step = lambda b: None if b is None else round(float(low_bar[b:b + 4].mean() - low_bar[max(0, b - 4):b].mean()), 1) if b > 0 else None

    # Where in the grid's beat the kick (30–90 Hz onsets) and the hats (6–11 kHz onsets) fall, from
    # their onset strength folded onto the beat: 0 is on the grid's beat, .5 halfway between. Peak
    # picking kicks from the low band is unreliable, because house basslines sit there off the beat.
    fine = 128
    F = np.abs(librosa.stft(y[:sr * 180], n_fft=2048, hop_length=fine)) ** 2
    beat_len = float(np.median(np.diff(downbeats))) / 4

    def fold(lo, hi):
        env = librosa.onset.onset_strength(S=librosa.power_to_db(F[(f >= lo) & (f < hi)]), sr=sr, hop_length=fine)
        phase = ((librosa.frames_to_time(np.arange(len(env)), sr=sr, hop_length=fine) - downbeats[0]) / beat_len) % 1
        curve = np.array([env[np.floor(phase * 16).astype(int) == k].mean() for k in range(16)])
        return round(float(curve.argmax()) / 16, 2)

    wrap = lambda x: round((x + .5) % 1 - .5, 2)
    return {"low_db": low_bar.round(1).tolist(), "full_db": full_bar.round(1).tolist(), "loud_low_db": round(ref, 1),
            "groove": groove, "drop": drop, "breakdown": breakdown, "outro": outro,
            "step_db": {"groove": step(groove), "drop": step(drop), "breakdown": step(breakdown)},
            "outro_step_db": round(best, 1) if outro is not None else None,
            "kick_phase": wrap(fold(30, 90)), "hat_phase": wrap(fold(6000, 11000))}


def allin1_beats(p):
    """Tempo, beats per bar, downbeat offset and phase from allin1's beat and downbeat activations
    (100 frames a second), against the track's grid. None when allin1 did not run."""
    from scipy.signal import find_peaks
    act = ((((p["analysis"].get("deep") or {}).get("models") or {}).get("allin1") or {}).get("data") or {}).get("activations") or {}
    if not act.get("path") or not Path(act["path"]).is_file():
        return None
    z, fps = np.load(act["path"]), 100.
    beats = find_peaks(z["beat"], height=.3, distance=int(.25 * fps))[0] / fps
    bars = find_peaks(z["downbeat"], height=.3, distance=int(1. * fps))[0] / fps
    gap = np.diff(beats)
    gap = gap[(gap > .25) & (gap < 1.5)]
    if len(gap) < 8 or len(bars) < 4:
        return None
    # Frames are 10 ms apart, so one interval's tempo is coarse; average the regular ones.
    period = float(gap[np.abs(gap / np.median(gap) - 1) <= .15].mean())
    grid = np.asarray(p["analysis"]["downbeats"], dtype=float)
    beat_len = float(np.median(np.diff(grid))) / 4
    offset = np.array([t - grid[np.argmin(np.abs(grid - t))] for t in bars]) / beat_len
    whole = np.round(offset) % 4
    fraction = (offset + .5) % 1 - .5
    return {"bpm": round(60 / period, 2), "beats_per_bar": round(float(np.median(np.diff(bars))) / period, 2),
            "downbeat_beat": int(np.bincount(whole.astype(int), minlength=4).argmax()) + 1,
            "offset_beats": round(float(np.median(fraction)), 2)}


def sources(p, spec, beats, gemini):
    a = p["analysis"]
    downbeats = np.asarray(a["downbeats"])
    rb = p.get("rekordbox_observation") or {}
    rbs = rb.get("rekordbox_sections") or {}
    rbm = p.get("rekordbox_metadata") or {}
    sec = a.get("sections") or {}
    models = (a.get("deep") or {}).get("models", {})
    ess = (models.get("essentia") or {}).get("data") or {}
    ess_keys = [camelot(f"{v['key']} {v['scale']}") for v in ess.values() if isinstance(v, dict) and v.get("key")]
    ess_majority = next((k for k in ess_keys if ess_keys.count(k) > len(ess_keys) / 2), None)
    allin = [s for s in ((models.get("allin1") or {}).get("data") or {}).get("segments", [])]
    first = lambda label: next((bar_of(s["start"], downbeats) for s in allin if s.get("label") == label), None)
    g = gemini or {}
    def gemini_bar(field):
        t = seconds(g.get(field))
        return bar_of(t, downbeats) if t is not None and 0 <= t < float(a["duration"]) else None
    out = {
        "tempo": {"onset": a.get("bpm"), "rekordbox": rbm.get("bpm") or rb.get("bpm"),
                  "allin1": (beats or {}).get("bpm"), "gemini": g.get("bpm")},
        "key": {"onset": (a.get("key") or {}).get("camelot"), "rekordbox": camelot(rbm.get("key")),
                "essentia": ess_majority},
        "groove": {"onset": sec.get("drop"), "spectral": spec["groove"], "gemini": gemini_bar("drop"),
                   "allin1": next((bar_of(s["start"], downbeats) for s in allin if s.get("label") not in ("intro", "start")), None)},
        "drop": {"rekordbox": rbs.get("drop"), "spectral": spec["drop"], "allin1": first("chorus"),
                 "gemini": gemini_bar("main_drop")},
        "breakdown": {"onset": sec.get("breakdown"), "rekordbox": rbs.get("breakdown"), "spectral": spec["breakdown"],
                      "gemini": gemini_bar("breakdown"), "allin1": first("break")},
        "outro": {"onset": sec.get("outro"), "rekordbox": rbs.get("outro"), "spectral": spec["outro"],
                  "gemini": gemini_bar("outro"), "allin1": first("outro")},
    }
    return {item: {k: v for k, v in values.items() if v is not None} for item, values in out.items()}


def judge_tempo(values):
    """The grid's tempo against the others: the same within 1%, or half or double within 2%."""
    if not values:
        return {"status": "no evidence"}
    reference = values.get("rekordbox") or values.get("onset")
    if not reference:
        return {"status": "single source", "reason": "no stored grid tempo to compare"}
    ratio = lambda v: v / reference
    same = [k for k, v in values.items() if abs(ratio(v) - 1) <= TEMPO_TOL]
    double = [k for k, v in values.items() if abs(ratio(v) / 2 - 1) <= .02]
    half = [k for k, v in values.items() if abs(ratio(v) * 2 - 1) <= .02]
    independent = [k for k in values if k not in ("onset", "rekordbox")]
    categories = {"same" if k in same else "double" if k in double else "half" if k in half else "other"
                  for k in independent}
    if len(categories) > 1:
        return {"status": "ambiguous", "value": reference,
                "reason": "independent tempo estimates disagree: " + ", ".join(f"{k} {values[k]}" for k in independent)}
    if any(k in double for k in independent) and not any(k in same for k in independent):
        return {"status": "candidate", "value": round(reference * 2, 2),
                "reason": f"{', '.join(k for k in independent if k in double)} count beats twice as fast as the {reference} BPM grid: "
                          "the grid is half time"}
    if any(k in half for k in independent) and not any(k in same for k in independent):
        return {"status": "candidate", "value": round(reference / 2, 2),
                "reason": f"{', '.join(k for k in independent if k in half)} count beats half as fast as the {reference} BPM grid"}
    if any(k in same for k in independent):
        return {"status": "agree", "value": reference, "reason": f"{', '.join(same)} within 1%"}
    if not independent:
        return {"status": "single source", "value": reference, "reason": "only OnSet and rekordbox, which share one grid"}
    return {"status": "ambiguous", "value": reference, "reason": "sources split: " + ", ".join(f"{k} {v}" for k, v in values.items())}


def judge_grid(p, spec, beats):
    """OnSet uses rekordbox's grid. The kick's place in the grid's beat (spectral) and allin1's
    downbeats check whether the grid's beats sit on the kick, and whether its bars start on beat 1."""
    a, rb = p["analysis"], p.get("rekordbox_observation") or {}
    rb_first = (rb.get("downbeats") or [None])[0]
    on_first = a["downbeats"][0]
    same = "OnSet uses rekordbox's grid; " if rb_first is not None and abs(on_first - rb_first) <= .02 else "OnSet's grid differs from rekordbox's; "
    kick, hats = spec["kick_phase"], spec["hat_phase"]
    detail = f"the kick lands at {kick:+.2f} of a beat from the grid's beats and the hats at {hats:+.2f}"
    if beats:
        detail += f"; allin1's downbeats sit {beats['offset_beats']:+.2f} of a beat off, on grid beat {beats['downbeat_beat']}"
    on = lambda x: x is not None and abs(x) <= GRID_PHASE
    off = lambda x: x is not None and abs(abs(x) - .5) <= GRID_PHASE + .05
    allin_on = beats is None or on(beats["offset_beats"])
    if on(kick) and allin_on and (beats is None or beats["downbeat_beat"] == 1):
        return {"status": "agree", "value": on_first, "reason": same + detail}
    if beats is not None and on(beats["offset_beats"]) and beats["downbeat_beat"] == 1 and abs(kick) <= .25:
        # Half-time and broken-beat tracks have no kick on every beat; allin1 then carries it.
        return {"status": "agree", "value": on_first, "reason": same + detail + " (no steady four-to-the-floor kick)"}
    if off(kick) and beats is not None and off(beats["offset_beats"]):
        return {"status": "confirm", "value": on_first,
                "reason": same + detail + ": both say the grid's beats sit halfway between the kicks, "
                          "on the off-beat hats. That contradicts rekordbox, so it needs a look."}
    if on(kick) and beats is not None and on(beats["offset_beats"]) and beats["downbeat_beat"] != 1:
        return {"status": "confirm", "value": on_first,
                "reason": same + detail + ": the beats are right, but allin1 starts the bar on another beat"}
    return {"status": "ambiguous", "value": on_first, "reason": same + detail}


def judge_key(values):
    if not values:
        return {"status": "no evidence"}
    counts = {}
    for v in values.values():
        counts[v] = counts.get(v, 0) + 1
    best = max(counts, key=counts.get)
    if counts[best] >= 2 and values.get("onset") == best:
        return {"status": "agree", "value": best, "reason": f"{', '.join(k for k, v in values.items() if v == best)} say {best}"}
    if counts[best] >= 2:
        return {"status": "candidate", "value": best,
                "reason": f"{', '.join(k for k, v in values.items() if v == best)} say {best}; OnSet says {values.get('onset')}"}
    return {"status": "ambiguous", "value": values.get("onset"), "reason": "every source names a different key"}


def judge_event(item, values, spec):
    if not values:
        return {"status": "no evidence"}
    tol = OUTRO_TOL if item == "outro" else EVENT_TOL
    # A cluster's entire span must fit the tolerance. A middle vote must not join two
    # incompatible endpoints, and equal-sized competing clusters cannot decide a cue.
    ordered = sorted(values.items(), key=lambda pair: pair[1])
    clusters = [dict((k, w) for k, w in ordered[i:] if w - v <= tol)
                for i, (_, v) in enumerate(ordered)]
    size = max(map(len, clusters))
    winners = [c for c in clusters if len(c) == size]
    cluster = winners[0]
    if len(winners) > 1 and size >= 2:
        return {"status": "ambiguous", "value": values.get("onset"),
                "reason": "equally supported competing event clusters: " +
                          "; ".join(", ".join(f"{k} bar {v}" for k, v in c.items()) for c in winners)}
    independent = [k for k in cluster if k != "onset"]
    value = int(np.median(list(cluster.values())))
    onset = values.get("onset")
    if len(cluster) >= 2 and independent:
        if onset is None or abs(onset - value) <= tol:
            return {"status": "agree", "value": value, "reason": f"{', '.join(cluster)} within {tol} bars"}
        return {"status": "candidate", "value": value,
                "reason": f"{', '.join(cluster)} agree on bar {value}; OnSet says bar {onset}"}
    if len(values) == 1:
        return {"status": "single source", "value": next(iter(values.values())), "reason": f"only {next(iter(values))} has it"}
    return {"status": "ambiguous", "value": onset, "reason": "sources split: " + ", ".join(f"{k} bar {v}" for k, v in values.items())}


COLOURS = {"onset": (80, 220, 255), "rekordbox": (255, 150, 30), "spectral": (60, 230, 90),
           "gemini": (255, 60, 220), "allin1": (230, 230, 230)}


def render(p, spec, found, out):
    """The stored spectrogram on the bar grid, a low-band strip, and one marker lane per source."""
    a = p["analysis"]
    values = np.asarray(a["spectrogram"]["values"], dtype=float)
    downbeats = np.asarray(a["downbeats"])
    duration = float(a["spectrogram"].get("duration") or a["duration"])
    px, band_px, header, lane = 8, 3, 9, 6
    bands, frames = values.shape
    edges = np.append(downbeats, duration)
    cols = np.concatenate([np.clip(((edges[b] + (np.arange(px) + .5) / px * (edges[b + 1] - edges[b])) / duration * frames).astype(int), 0, frames - 1)
                           for b in range(len(downbeats))])
    level = (values[::-1, cols] - values.min()) / max(1e-9, values.max() - values.min())
    body = np.repeat(_colour(level), band_px, axis=0)
    low = np.asarray(spec["low_db"])
    strip = np.repeat(_colour(np.repeat((low - low.min()) / max(1e-9, low.max() - low.min()), px)[None, :]), 10, axis=0)
    lanes = len(COLOURS) * lane
    img = np.zeros((header + lanes + body.shape[0] + 2 + strip.shape[0], body.shape[1], 3), dtype=np.uint8)
    img[header + lanes:header + lanes + body.shape[0]] = body
    img[-strip.shape[0]:] = strip
    for b in range(0, len(downbeats), 4):
        x = b * px
        img[header + lanes:, x] = (255, 255, 255) if b % 16 == 0 else (110, 110, 120)
        if b % 16 == 0:
            img[:header, x] = (255, 255, 255)
            _text(img, x + 2, 2, str(b))
    for row, (source, colour) in enumerate(COLOURS.items()):
        y = header + row * lane
        img[y:y + lane, :2] = colour
        for item in ("groove", "drop", "breakdown", "outro"):
            bar = found[item].get(source)
            if bar is not None:
                x = min(int(bar) * px, img.shape[1] - 2)
                img[y:y + lane - 1, x:x + 2] = colour
                img[header + lanes:header + lanes + body.shape[0], x] = colour
    out.write_bytes(_png(img))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--titles", nargs="*", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--gemini")
    ap.add_argument("--workspace", default=str(WORKSPACE))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    gemini = json.loads(Path(args.gemini).read_text(encoding="utf-8")) if args.gemini else {}
    report = []
    for p in profiles(args.workspace, args.titles, args.all):
        a = p["analysis"]
        spec = spectral(p["path"], np.asarray(a["downbeats"], dtype=float), float(a["duration"]))
        g = gemini_for_track(p, gemini)
        beats = allin1_beats(p)
        found = sources(p, spec, beats, g)
        verdicts = {"tempo": judge_tempo(found["tempo"]), "grid": judge_grid(p, spec, beats), "key": judge_key(found["key"])}
        for item in ("groove", "drop", "breakdown", "outro"):
            verdicts[item] = judge_event(item, found[item], spec)
        for item in ("groove", "drop", "breakdown", "outro"):
            if isinstance(verdicts[item].get("value"), int):
                verdicts[item]["time"] = mmss(a["downbeats"][verdicts[item]["value"]])
        png = out / (re.sub(r"[^\w.-]+", "_", p["title"])[:60] + ".png")
        render(p, spec, found, png)
        report.append({"title": p["title"], "track_id": p["id"], "revision": p["revision"], "sources": found,
                       "verdicts": verdicts, "spectral": {k: v for k, v in spec.items() if k not in ("low_db", "full_db")},
                       "allin1_beats": beats, "gemini": g,
                       "cues": [(c["role"], round(c["time"], 3), c["review"]) for c in p["cues"]], "png": png.name})
        print(f"{p['title'][:40]}: " + ", ".join(f"{k} {v['status']}" for k, v in verdicts.items()), flush=True)
    (out / "crosscheck.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
