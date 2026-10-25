"""Separate cue anchors without promoting an energy edge or model label to a main payoff.

Legacy sections.drop always means first sustained full groove. Main-payoff selection is
explicit evidence, never inferred from the first chorus, largest jump or candidate order.
This read-time adapter does not change stored analyses or invalidate expensive caches.
"""
import math

ANCHORS = ("main_payoff", "first_full_groove")


def anchor_event(analysis, kind):
    grid = analysis.get("downbeats") or []
    duration = analysis.get("duration")
    events = analysis.get("events") or []
    if not isinstance(events, list):
        events = []

    def align(event):
        time = event.get("time")
        if (not grid or not isinstance(time, (int, float)) or isinstance(time, bool)
                or not math.isfinite(time) or time < 0
                or duration is None or time >= duration):
            return None
        bar = min(range(len(grid)), key=lambda i: abs(grid[i] - time))
        if grid[bar] < 0 or grid[bar] >= duration:
            return None
        return {**event, "original_time": event.get("original_time", time),
                "aligned_bar": bar, "aligned_time": grid[bar]}

    if kind == "first_full_groove":
        bar = (analysis.get("sections") or {}).get("drop")
        if isinstance(bar, int) and not isinstance(bar, bool) and 0 <= bar < len(grid):
            event = align({"kind": kind, "state": "estimated", "time": grid[bar],
                           "source": "stored-first-groove", "confidence": "unverified"})
            if event:
                return event
        return {"kind": kind, "state": "unknown", "time": None, "aligned_bar": None}

    if kind != "main_payoff":
        raise ValueError("Unknown drop anchor")
    candidates = [e for e in events if isinstance(e, dict) and e.get("kind") in {"main_payoff", "major_payoff_candidate"}]
    selected = [e for e in candidates if e.get("kind") == kind and e.get("selected") is True]
    if len(selected) == 1:
        event = selected[0]
        if event.get("state") == "absent":
            return {**event, "time": None, "aligned_bar": None, "candidates": candidates}
        aligned = align(event)
        if event.get("state") in {"estimated", "present"} and event.get("source") and aligned:
            return {**aligned, "confidence": "unverified", "candidates": candidates}
    return {"kind": kind, "state": "ambiguous" if len(selected) > 1 else "unknown",
            "time": None, "aligned_bar": None, "confidence": "unverified", "candidates": candidates,
            "reason": "No single valid main payoff has been selected; first groove is separate evidence"}


def cue_anchor(cue):
    """Missing metadata identifies the old scheme; changing a template never relabels it."""
    return cue.get("anchor", "first_full_groove") if cue["role"] in {"B", "C", "D"} else None
