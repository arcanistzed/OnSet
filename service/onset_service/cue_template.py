"""The DJ's cue template: which cue roles OnSet places, how many bars before the drop B and C sit,
and how each role is written to rekordbox (memory cue, hot cue and on which pad).

The defaults reproduce the fixed scheme OnSet used before templates (cues.py: CUE_SCHEME, HOT_SLOT).
The template shapes proposals only. Approved, rejected and hand-moved cues are never changed by it,
and nothing reaches rekordbox without the usual approval and write preview."""
from .cues import CUE_SCHEME, HOT_SLOT, derive_cues
from .util import digest

SCHEMA_VERSION = 1
# rekordbox numbers pads A..H as djmdCue.Kind 1, 2, 3, 5, 6, 7, 8, 9 (Kind 4 is a memory loop).
PAD_KIND = {"A": 1, "B": 2, "C": 3, "D": 5, "E": 6, "F": 7, "G": 8, "H": 9}
ROLES = tuple(CUE_SCHEME)                       # A B C D E F G L I
BEFORE_DROP = ("B", "C")                        # roles placed a number of bars before the first drop
DEFAULT_BEFORE = {"B": 32, "C": 16}
MAX_BARS_BEFORE = 64
SETTING = "cue_template"
_KIND_PAD = {kind: pad for pad, kind in PAD_KIND.items()}


def default():
    return {"schema_version": SCHEMA_VERSION, "bars_before_drop": dict(DEFAULT_BEFORE),
            "roles": {r: {"enabled": True, "memory": True, "hot": r in HOT_SLOT,
                          "pad": _KIND_PAD.get(HOT_SLOT.get(r))} for r in ROLES}}


def validate(value):
    """A complete, checked template from a partial one; raises ValueError on anything unusable."""
    value = value or {}
    if not isinstance(value, dict):
        raise ValueError("Cue template must be an object")
    if value.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise ValueError("Unsupported cue template version")
    template = default()
    before = value.get("bars_before_drop", {})
    if not isinstance(before, dict) or set(before) - set(BEFORE_DROP):
        raise ValueError("Bars before the drop can be set for B and C only")
    for role, bars in before.items():
        if not isinstance(bars, int) or isinstance(bars, bool) or not 1 <= bars <= MAX_BARS_BEFORE:
            raise ValueError(f"{role}: bars before the drop must be a whole number from 1 to {MAX_BARS_BEFORE}")
        template["bars_before_drop"][role] = bars
    roles = value.get("roles", {})
    if not isinstance(roles, dict) or set(roles) - set(ROLES):
        raise ValueError("Unknown cue role in the template")
    for role, settings in roles.items():
        if not isinstance(settings, dict) or set(settings) - {"enabled", "memory", "hot", "pad"}:
            raise ValueError(f"{role}: unknown template field")
        merged = {**template["roles"][role], **settings}
        if not all(isinstance(merged[k], bool) for k in ("enabled", "memory", "hot")):
            raise ValueError(f"{role}: enabled, memory and hot must be true or false")
        if merged["pad"] is not None and merged["pad"] not in PAD_KIND:
            raise ValueError(f"{role}: pad must be one of A to H")
        if merged["hot"] and merged["pad"] is None:
            raise ValueError(f"{role}: choose a pad for its hot cue")
        template["roles"][role] = merged
    pads = [s["pad"] for s in template["roles"].values() if s["enabled"] and s["hot"]]
    clash = sorted({p for p in pads if pads.count(p) > 1})
    if clash:
        raise ValueError(f"Two hot cues share pad {', '.join(clash)}")
    return template


def load(store):
    return validate(store.setting(SETTING) or {})


def place(analysis, template):
    """The cues an analysis result proposes under `template`: [(role, name, start, end), ...]."""
    if not analysis or not analysis.get("cues"):
        return list(analysis.get("cues", []) if analysis else [])   # silent or failed tracks keep none
    cues = derive_cues(analysis.get("sections") or {}, analysis.get("downbeats") or [], second_drop=True,
                       end_loop_bars=8, intro_loop_bars=8, duration=analysis.get("duration"),
                       bars_before=template["bars_before_drop"])
    return [c for c in cues if template["roles"][c[0]]["enabled"]]


def write_kind(template, role, hot, loop):
    """rekordbox's djmdCue.Kind for writing `role`, or None when the template leaves it out."""
    settings = template["roles"].get(role)
    if settings is None or not settings["enabled"]:
        return None
    if hot:
        return PAD_KIND[settings["pad"]] if settings["hot"] and settings["pad"] else None
    return (4 if loop else 0) if settings["memory"] else None


def reapply(store, track_ids, template):
    """Re-places the still-open proposals of `track_ids` under `template`, from each track's stored
    sections and grid (no reanalysis). Approved, rejected, removal-approved and hand-moved cues stay as
    they are. Returns what changed."""
    moved = added = removed = kept = tracks = 0
    open_states = {"proposed", "stale"}
    for track_id in track_ids:
        p = store.get(track_id)
        analysis = p.get("analysis") or {}
        if not analysis.get("cues") or not analysis.get("downbeats"):
            continue
        wanted = {c[0]: c for c in place(analysis, template)}
        changed = False
        cues = []
        for cue in p["cues"]:
            open_ = cue["review"] in open_states and not cue.get("manual")
            if not open_:
                kept += 1
                cues.append(cue)
                continue
            target = wanted.get(cue["role"])
            if target is None:
                removed += 1
                changed = True
                continue
            end = target[3] if len(target) > 3 else None
            if abs(cue["time"] - target[2]) > 1e-6 or cue.get("end") != end:
                cue = {**cue, "time": target[2], "end": end, "review": "proposed"}
                moved += 1
                changed = True
            cues.append(cue)
        present = {c["role"] for c in cues}
        for role, target in wanted.items():
            if role in present:
                continue
            cues.append({"id": digest([track_id, p.get("revision"), role])[:24], "role": role, "name": target[1],
                         "time": target[2], "end": target[3] if len(target) > 3 else None, "review": "proposed",
                         "revision": p.get("revision"), "confidence": "unverified",
                         "source": p.get("analysis_source") or "native-v1"})
            added += 1
            changed = True
        if changed:
            order = {r: i for i, r in enumerate(ROLES)}
            p["cues"] = sorted(cues, key=lambda c: order.get(c["role"], len(order)))
            store.save(p)
            tracks += 1
    return {"tracks": tracks, "moved": moved, "added": added, "removed": removed, "kept": kept}
