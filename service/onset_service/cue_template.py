"""The DJ's cue template: which cue roles OnSet places, how many bars before the drop B and C sit,
and how each role is written to rekordbox (memory cue, hot cue and on which pad).

The defaults reproduce the fixed scheme OnSet used before templates (cues.py: CUE_SCHEME, HOT_SLOT).
The template shapes proposals only. Approved, rejected and hand-moved cues are never changed by it,
and nothing reaches rekordbox without the usual approval and write preview."""
from .cues import CUE_SCHEME, HOT_SLOT, derive_cues
from .util import digest
from .payoff import anchor_event, cue_anchor

SCHEMA_VERSION = 2
# rekordbox numbers pads A..H as djmdCue.Kind 1, 2, 3, 5, 6, 7, 8, 9 (Kind 4 is a memory loop).
PAD_KIND = {"A": 1, "B": 2, "C": 3, "D": 5, "E": 6, "F": 7, "G": 8, "H": 9}
ROLES = tuple(CUE_SCHEME)                       # A B C D E F G L I
BEFORE_DROP = ("B", "C")                        # roles placed a number of bars before the first drop
DEFAULT_BEFORE = {"B": 32, "C": 16}
MAX_BARS_BEFORE = 64
SETTING = "cue_template"
_KIND_PAD = {kind: pad for pad, kind in PAD_KIND.items()}


def default():
    return {"schema_version": SCHEMA_VERSION, "drop_anchor": "first_full_groove", "bars_before_drop": dict(DEFAULT_BEFORE),
            "roles": {r: {"enabled": True, "memory": True, "hot": r in HOT_SLOT,
                          "pad": _KIND_PAD.get(HOT_SLOT.get(r))} for r in ROLES}}


def validate(value):
    """A complete, checked template from a partial one; raises ValueError on anything unusable."""
    value = value or {}
    if not isinstance(value, dict):
        raise ValueError("Cue template must be an object")
    if value.get("schema_version", SCHEMA_VERSION) not in (1, SCHEMA_VERSION):
        raise ValueError("Unsupported cue template version")
    template = default()
    template["drop_anchor"] = value.get("drop_anchor", "first_full_groove")
    if template["drop_anchor"] not in {"main_payoff", "first_full_groove"}:
        raise ValueError("Choose main payoff or first full groove for D")
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


def placement_analysis(analysis, main_payoff=None):
    if main_payoff is None:
        return analysis
    events = analysis.get("events") or []
    if not isinstance(events, list):
        events = []
    return {**analysis, "events": [e for e in events if isinstance(e, dict) and e.get("kind") != "main_payoff"] + [main_payoff]}


def place(analysis, template, main_payoff=None):
    """The cues an analysis result proposes under `template`: [(role, name, start, end), ...]."""
    if not analysis or not analysis.get("cues"):
        return list(analysis.get("cues", []) if analysis else [])   # silent or failed tracks keep none
    cues = derive_cues(analysis.get("sections") or {}, analysis.get("downbeats") or [], second_drop=True,
                       end_loop_bars=8, intro_loop_bars=8, duration=analysis.get("duration"),
                       bars_before=template["bars_before_drop"])
    if template["drop_anchor"] == "main_payoff":
        event = anchor_event(placement_analysis(analysis, main_payoff), "main_payoff")
        # Only B/C/D move with this choice. E/G and loop anchors keep their existing
        # first-groove interpretation; changing them needs a separate review.
        cues = [c for c in cues if c[0] not in {"B", "C", "D"}]
        bar = event.get("aligned_bar")
        if bar is not None:
            grid = analysis["downbeats"]
            for role in ("B", "C", "D"):
                offset = template["bars_before_drop"].get(role, 0)
                if bar >= offset:
                    name = f"{role} main payoff" + (f" -{offset}" if offset else "")
                    cues.append((role, name, grid[bar - offset], None))
    return [c for c in cues if template["roles"][c[0]]["enabled"]]


def write_kind(template, role, hot, loop):
    """rekordbox's djmdCue.Kind for writing `role`, or None when the template leaves it out."""
    settings = template["roles"].get(role)
    if settings is None or not settings["enabled"]:
        return None
    if hot:
        return PAD_KIND[settings["pad"]] if settings["hot"] and settings["pad"] else None
    return (4 if loop else 0) if settings["memory"] else None


def _changes(store, track_ids, template):
    """Re-places the still-open proposals of `track_ids` under `template`, from each track's stored
    sections and grid (no reanalysis). Approved, rejected, removal-approved and hand-moved cues stay as
    they are. Returns what changed."""
    moved = added = removed = kept = tracks = 0
    details, updates, inputs = [], [], []
    open_states = {"proposed", "stale"}
    for track_id in dict.fromkeys(track_ids):
        p = store.get(track_id)
        # Hash one profile at a time; a library preview must not retain several
        # copies of every track's feature arrays just to guard against stale edits.
        inputs.append((track_id, digest(p)))
        analysis = p.get("analysis") or {}
        if not analysis.get("cues") or not analysis.get("downbeats"):
            continue
        wanted = {c[0]: c for c in place(analysis, template, p.get("main_payoff"))}
        events = placement_analysis(analysis, p.get("main_payoff"))
        detail = {"track_id": track_id, "title": p.get("title") or track_id,
                  "first_full_groove": anchor_event(events, "first_full_groove"),
                  "main_payoff": anchor_event(events, "main_payoff"), "changes": []}
        changed = False
        cues = []
        for cue in p["cues"]:
            open_ = cue["review"] in open_states and not cue.get("manual") and not cue.get("retained_decision")
            if not open_:
                kept += 1
                cues.append(cue)
                detail["changes"].append({"role": cue["role"], "action": "keep", "before": cue,
                                          "after": cue, "anchor": cue_anchor(cue)})
                continue
            target = wanted.get(cue["role"])
            if target is None:
                removed += 1
                changed = True
                detail["changes"].append({"role": cue["role"], "action": "remove", "before": cue, "after": None})
                continue
            end = target[3] if len(target) > 3 else None
            anchor_changed = cue["role"] in {"B", "C", "D"} and cue_anchor(cue) != template["drop_anchor"]
            if abs(cue["time"] - target[2]) > 1e-6 or cue.get("end") != end or cue["name"] != target[1] or anchor_changed:
                previous = cue
                cue = {**cue, "time": target[2], "name": target[1], "end": end, "review": "proposed"}
                if cue["role"] in {"B", "C", "D"}:
                    cue["anchor"] = template["drop_anchor"]
                detail["changes"].append({"role": cue["role"], "action": "update", "before": previous, "after": cue})
                moved += 1
                changed = True
            cues.append(cue)
        present = {c["role"] for c in cues}
        for role, target in wanted.items():
            if role in present:
                continue
            cue = {"id": digest([track_id, p.get("revision"), role])[:24], "role": role, "name": target[1],
                         "time": target[2], "end": target[3] if len(target) > 3 else None, "review": "proposed",
                         "revision": p.get("revision"), "confidence": "unverified",
                         "source": p.get("analysis_source") or "native-v1"}
            if role in {"B", "C", "D"}:
                cue["anchor"] = template["drop_anchor"]
            cues.append(cue)
            detail["changes"].append({"role": role, "action": "add", "before": None, "after": cue})
            added += 1
            changed = True
        if changed:
            order = {r: i for i, r in enumerate(ROLES)}
            updates.append((track_id, sorted(cues, key=lambda c: order.get(c["role"], len(order)))))
            tracks += 1
        details.append(detail)
    summary = {"tracks": tracks, "moved": moved, "added": added, "removed": removed, "kept": kept}
    return {"id": digest({"template": template, "profiles": inputs}), "summary": summary, "details": details}, updates


def preview(store, track_ids, template):
    """Read-only exact proposal changes, including protected old anchors and unresolved payoffs."""
    return _changes(store, track_ids, template)[0]


def reapply(store, track_ids, template, preview_id=None):
    report, updates = _changes(store, track_ids, template)
    if preview_id is not None and preview_id != report["id"]:
        raise ValueError("Cues, evidence or template changed; preview the changes again")
    for track_id, cues in updates:
        before = store.get(track_id)
        after = {**before, "cues": cues, "review_state": "reviewing", "write_state": "stale"}
        if hasattr(store, "record_edit"):
            store.record_edit(before, after)
        else:
            store.save(after)
    return report["summary"]
