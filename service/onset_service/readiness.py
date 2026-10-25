"""Pre-gig readiness: what in a playlist or selection would let the DJ down at the gig.

Read-only. Every finding names the fix and where it is made; nothing here changes a cue,
a profile or rekordbox. Severities: "blocker" (the track is not gig-ready), "warning"
(check before the gig) and "info"."""
from __future__ import annotations
from pathlib import Path
import numpy as np
from .util import file_hash, utcnow

# Median distance between OnSet's and rekordbox's downbeats above which the grids disagree.
GRID_TOLERANCE_S = .03
APPROVED = {"approved", "delete-approved"}


def issue(code, severity, message, fix):
    return {"code": code, "severity": severity, "message": message, "fix": fix}


def grid_offset(ours, theirs):
    """Median distance from each of rekordbox's downbeats to OnSet's nearest one, over the
    stretch both cover; None when either grid is too short to compare."""
    ours, theirs = np.asarray(ours, dtype=float), np.asarray(theirs, dtype=float)
    if len(ours) < 2 or len(theirs) < 2:
        return None
    theirs = theirs[(theirs >= ours[0] - .5) & (theirs <= ours[-1] + .5)]
    if not len(theirs):
        return None
    index = np.clip(np.searchsorted(ours, theirs), 1, len(ours) - 1)
    nearest = np.minimum(abs(theirs - ours[index - 1]), abs(theirs - ours[index]))
    return float(np.median(nearest))


def current_cue(track, role):
    """The track's cue for a role at its current analysis revision, if any."""
    return next((c for c in track.get("cues", []) if c.get("role") == role
                 and c.get("revision") == track.get("revision")), None)


def check_track(track, verify_audio=False):
    issues = []
    path = Path(track.get("path") or "")
    if not path.is_file():
        elsewhere = next((p for p in track.get("locations", []) if p != str(path) and Path(p).is_file()), None)
        if elsewhere:
            issues.append(issue("moved-file", "blocker", f"Audio is no longer at {path}; a copy exists at {elsewhere}",
                                {"action": "relocate", "path": elsewhere, "label": "Relocate to the copy"}))
        else:
            issues.append(issue("missing-file", "blocker", f"Audio file is missing: {path}",
                                {"action": "relocate", "label": "Locate the audio file"}))
    elif verify_audio and track.get("fingerprint") and not str(track["fingerprint"]).startswith("unverified:") \
            and file_hash(path) != track["fingerprint"]:
        issues.append(issue("changed-file", "blocker", "Audio changed since it was analysed; cues may no longer line up",
                            {"action": "reimport", "label": "Reimport and reanalyse"}))

    analysis = track.get("analysis") or {}
    if not track.get("revision"):
        issues.append(issue("not-analysed", "warning", "Not analysed by OnSet yet; no cues proposed",
                            {"action": "analyze", "label": "Analyse"}))
    if not track.get("rekordbox_id"):
        issues.append(issue("not-in-rekordbox", "warning", "Not linked to a rekordbox track; cues cannot be written",
                            {"action": "rekordbox-import", "label": "Import from rekordbox"}))

    rb = track.get("rekordbox_observation") or {}
    overrides = track.get("overrides", {})
    if track.get("grid_error"):
        issues.append(issue("grid-unreadable", "warning", "rekordbox's beat grid could not be read: " + str(track["grid_error"]),
                            {"action": "grid", "label": "Check the grid in rekordbox"}))
    if overrides.get("grid") and not overrides.get("accept_rekordbox_grid_conflict"):
        issues.append(issue("grid-edited", "blocker", "OnSet's grid was edited and no longer matches rekordbox's; writes are refused until resolved",
                            {"action": "grid", "label": "Resolve the grid conflict"}))
    elif rb.get("downbeats") and track.get("revision"):
        offset = grid_offset(overrides.get("grid") or analysis.get("downbeats", []), rb["downbeats"])
        if offset is not None and offset > GRID_TOLERANCE_S:
            issues.append(issue("grid-conflict", "blocker",
                                f"OnSet's downbeats sit {offset * 1000:.0f} ms from rekordbox's; cues would land off the grid",
                                {"action": "grid", "label": "Compare the grids"}))
    if (analysis.get("grid_observation") or {}).get("downbeat_offset_seconds", 0) > .05:
        issues.append(issue("grid-doubt", "warning", "Independent beat tracking disagrees with the grid's downbeats",
                            {"action": "grid", "label": "Check the grid"}))

    if track.get("revision"):
        first, drop = current_cue(track, "A"), current_cue(track, "D")
        if first is None:
            issues.append(issue("no-first-beat-cue", "blocker", "No first-beat cue (A)",
                                {"action": "review-cues", "label": "Add cue A"}))
        elif first.get("review") not in APPROVED:
            issues.append(issue("first-beat-unapproved", "warning", "First-beat cue (A) is not approved",
                                {"action": "review-cues", "cue_id": first["id"], "label": "Review cue A"}))
        if drop is None:
            issues.append(issue("no-drop-cue", "warning", "No drop cue (D)",
                                {"action": "review-cues", "label": "Place cue D"}))
        elif drop.get("review") == "rejected":
            issues.append(issue("drop-rejected", "info", "Drop cue (D) was rejected; place your own in rekordbox if you want one",
                                {"action": "review-cues", "cue_id": drop["id"], "label": "Review cue D"}))
        elif drop.get("review") not in APPROVED:
            issues.append(issue("drop-unapproved", "warning", "Drop cue (D) is not approved",
                                {"action": "review-cues", "cue_id": drop["id"], "label": "Review cue D"}))
        stale = [c for c in track.get("cues", []) if c.get("review") == "stale"]
        if stale or track.get("review_state") == "stale":
            issues.append(issue("stale-approvals", "warning",
                                "Re-analysis or a grid change reset earlier approvals; review the cues again",
                                {"action": "review-cues", "label": "Review again"}))
        approved = [c for c in track.get("cues", []) if c.get("review") in APPROVED and c.get("revision") == track.get("revision")]
        if approved and track.get("write_state") != "written":
            issues.append(issue("not-written", "info", f"{len(approved)} approved cue(s) not yet written to rekordbox",
                                {"action": "rekordbox-write", "label": "Preview the write"}))

    key = track.get("key")
    if isinstance(key, dict):
        key = key.get("name") if key.get("state") not in {"unknown"} else None
    if not key:
        issues.append(issue("no-key", "warning", "Key is missing", {"action": "edit", "label": "Set the key"}))
    if not track.get("bpm"):
        issues.append(issue("no-bpm", "warning", "BPM is missing", {"action": "edit", "label": "Set the BPM"}))

    severities = {i["severity"] for i in issues}
    status = "blocked" if "blocker" in severities else "check" if "warning" in severities else "ready"
    return {"track_id": track["id"], "title": track.get("title"), "artist": track.get("artist"),
            "status": status, "issues": issues}


def select(tracks, track_ids=None, playlist=None, set_plan=None):
    """Tracks in the order the DJ will meet them: the set's order, the given IDs' order, or title order."""
    by_id = {t["id"]: t for t in tracks}
    if set_plan is not None:
        ids = list(set_plan.get("track_ids", []))
    elif track_ids is not None:
        ids = list(track_ids)
    elif playlist is not None:
        ids = [t["id"] for t in sorted(tracks, key=lambda t: (str(t.get("title") or ""), t["id"]))
               if playlist in (t.get("rekordbox_playlists") or [])]
    else:
        raise ValueError("Choose tracks, a rekordbox playlist or a saved set to check")
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        raise ValueError("Unknown track IDs: " + ", ".join(unknown))
    return [by_id[i] for i in dict.fromkeys(ids)]


def check(tracks, track_ids=None, playlist=None, set_plan=None, verify_audio=False):
    rows = [check_track(t, verify_audio) for t in select(tracks, track_ids, playlist, set_plan)]
    summary = {s: sum(r["status"] == s for r in rows) for s in ("ready", "check", "blocked")}
    scope = ({"set_id": set_plan.get("id")} if set_plan is not None else {"playlist": playlist} if playlist is not None
             else {"track_ids": len(rows)})
    return {"schema_version": 1, "checked_at": utcnow(), "scope": scope, "verify_audio": bool(verify_audio),
            "summary": {**summary, "total": len(rows)}, "tracks": rows}
