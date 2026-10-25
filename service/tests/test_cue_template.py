"""The DJ's cue template: defaults, validation, placement, re-placement and the write slots."""
import pytest

from onset_service.cue_template import PAD_KIND, default, place, preview, reapply, validate, write_kind
from onset_service.cues import HOT_SLOT, derive_cues

BAR = 2.0                                   # 120 BPM: one bar every 2 s
DOWNBEATS = [i * BAR for i in range(120)]
SECTIONS = {"drop": 40, "breakdown": 72, "second_drop": None, "outro": 104}


def analysis():
    return {"sections": SECTIONS, "downbeats": DOWNBEATS, "duration": 240.0,
            "cues": derive_cues(SECTIONS, DOWNBEATS, second_drop=True, end_loop_bars=8, intro_loop_bars=8,
                                duration=240.0)}


def times(cues):
    return {c[0]: c[2] for c in cues}


def test_the_default_template_is_the_original_scheme():
    template = validate({})
    assert template == default()
    assert times(place(analysis(), template)) == times(analysis()["cues"])
    for role, kind in HOT_SLOT.items():
        assert write_kind(template, role, hot=True, loop=False) == kind
    assert write_kind(template, "I", hot=True, loop=True) is None        # the intro loop has no pad
    assert write_kind(template, "A", hot=False, loop=False) == 0
    assert write_kind(template, "L", hot=False, loop=True) == 4


def test_bars_before_the_drop_move_b_and_c():
    template = validate({"bars_before_drop": {"B": 16, "C": 8}})
    placed = times(place(analysis(), template))
    assert placed["B"] == (40 - 16) * BAR and placed["C"] == (40 - 8) * BAR and placed["D"] == 40 * BAR


def test_disabled_roles_are_not_proposed_or_written():
    template = validate({"roles": {"E": {"enabled": False}, "I": {"enabled": False}}})
    assert "E" not in times(place(analysis(), template)) and "I" not in times(place(analysis(), template))
    assert write_kind(template, "E", hot=False, loop=False) is None


def test_memory_and_hot_choices_and_pads():
    template = validate({"roles": {"A": {"memory": False}, "D": {"pad": "H"}, "L": {"hot": False}}})
    assert write_kind(template, "A", hot=False, loop=False) is None
    assert write_kind(template, "A", hot=True, loop=False) == PAD_KIND["A"]
    assert write_kind(template, "D", hot=True, loop=False) == PAD_KIND["H"]
    assert write_kind(template, "L", hot=True, loop=True) is None


@pytest.mark.parametrize("bad, message", [
    ({"roles": {"D": {"pad": "B"}}}, "share pad B"),
    ({"roles": {"I": {"hot": True}}}, "choose a pad"),
    ({"roles": {"A": {"pad": "Z"}}}, "A to H"),
    ({"roles": {"X": {}}}, "Unknown cue role"),
    ({"bars_before_drop": {"B": 0}}, "1 to 64"),
    ({"bars_before_drop": {"D": 4}}, "B and C only"),
    ({"roles": {"A": {"enabled": "yes"}}}, "true or false"),
])
def test_unusable_templates_are_refused(bad, message):
    with pytest.raises(ValueError, match=message):
        validate(bad)


def test_a_disabled_role_frees_its_pad():
    template = validate({"roles": {"A": {"enabled": False}, "B": {"pad": "A"}}})
    assert write_kind(template, "B", hot=True, loop=False) == PAD_KIND["A"]


class Store:
    def __init__(self, profiles):
        self.profiles = profiles

    def get(self, track_id):
        return {**self.profiles[track_id], "cues": [dict(c) for c in self.profiles[track_id]["cues"]]}

    def save(self, profile):
        self.profiles[profile["id"]] = profile


def profile(reviews, manual=()):
    cues = []
    for role, name, start, end in analysis()["cues"]:
        cues.append({"id": role, "role": role, "name": name, "time": start, "end": end,
                     "review": reviews.get(role, "proposed"), "revision": "r1", **({"manual": True} if role in manual else {})})
    return {"id": "t", "revision": "r1", "analysis": analysis(), "cues": cues}


def test_reapply_moves_only_open_proposals():
    store = Store({"t": profile({"B": "approved", "C": "rejected"}, manual={"E"})})
    template = validate({"bars_before_drop": {"B": 16, "C": 8}, "roles": {"F": {"enabled": False}}})
    report = reapply(store, ["t"], template)
    cues = {c["role"]: c for c in store.profiles["t"]["cues"]}
    assert cues["B"]["time"] == (40 - 32) * BAR and cues["B"]["review"] == "approved"      # decided: kept
    assert cues["C"]["time"] == (40 - 16) * BAR and cues["C"]["review"] == "rejected"
    assert "F" not in cues                                                                   # open and disabled
    assert cues["E"]["time"] == 72 * BAR                                                     # hand-moved: kept
    assert report == {"tracks": 1, "moved": 0, "added": 0, "removed": 1, "kept": 3}


def test_reapply_places_new_and_moved_proposals():
    store = Store({"t": profile({})})
    report = reapply(store, ["t"], validate({"bars_before_drop": {"B": 16}}))
    cues = {c["role"]: c for c in store.profiles["t"]["cues"]}
    assert cues["B"]["time"] == (40 - 16) * BAR and cues["B"]["review"] == "proposed"
    assert report["moved"] == 1 and report["tracks"] == 1
    assert reapply(store, ["t"], validate({"bars_before_drop": {"B": 16}}))["tracks"] == 0   # nothing left to change


def test_reapply_skips_tracks_without_cues():
    store = Store({"t": {"id": "t", "revision": "r1", "analysis": {"cues": []}, "cues": []}})
    assert reapply(store, ["t"], validate({}))["tracks"] == 0


def test_legacy_template_keeps_groove_and_main_payoff_is_explicit():
    assert validate({"schema_version": 1})["drop_anchor"] == "first_full_groove"
    with pytest.raises(ValueError, match="main payoff"):
        validate({"drop_anchor": "largest_energy_jump"})
    template = validate({"drop_anchor": "main_payoff"})
    # Legacy drop and arbitrary strongest boundaries cannot silently become a payoff.
    result = analysis()
    result["events"] = [{"kind": "major_payoff_candidate", "time": 120, "source": "multifeature-v1"}]
    assert not {"B", "C", "D"} & times(place(result, template)).keys()
    assert result["sections"]["drop"] == 40


def test_selected_payoff_moves_only_bcd_and_keeps_original_timing():
    from onset_service.payoff import anchor_event
    result = analysis()
    result["events"] = [{"kind": "main_payoff", "time": 120.6, "state": "estimated",
                         "selected": True, "source": "user-selection"}]
    template = validate({"drop_anchor": "main_payoff"})
    placed = times(place(result, template))
    assert (placed["B"], placed["C"], placed["D"]) == (56, 88, 120)
    assert {r: t for r, t in placed.items() if r not in "BCD"} == {
        r: t for r, t in times(analysis()["cues"]).items() if r not in "BCD"}
    event = anchor_event(result, "main_payoff")
    assert event["original_time"] == 120.6 and event["aligned_time"] == 120
    assert event["confidence"] == "unverified"


@pytest.mark.parametrize("time", [-1, 240, float("nan"), True])
def test_invalid_payoff_cannot_be_clamped_to_grid(time):
    event = {"kind": "main_payoff", "time": time, "state": "present", "selected": True, "source": "user-selection"}
    assert "D" not in times(place(analysis(), validate({"drop_anchor": "main_payoff"}), event))


def test_unknown_absent_and_multiple_selected_payoffs_stay_distinct():
    from onset_service.payoff import anchor_event
    result = analysis()
    assert anchor_event(result, "main_payoff")["state"] == "unknown"
    result["events"] = [{"kind": "main_payoff", "state": "absent", "selected": True}]
    assert anchor_event(result, "main_payoff")["state"] == "absent"
    result["events"].append({"kind": "main_payoff", "state": "present", "time": 120, "selected": True})
    assert anchor_event(result, "main_payoff")["state"] == "ambiguous"


def test_malformed_imported_event_elements_do_not_break_preview():
    store = Store({"t": profile({})})
    store.profiles["t"]["analysis"]["events"] = [None, "bad", 42]
    assert preview(store, ["t"], default())["details"][0]["main_payoff"]["state"] == "unknown"
    event = {"kind": "main_payoff", "state": "present", "time": 80, "selected": True, "source": "user-selection"}
    assert times(place(store.profiles["t"]["analysis"], validate({"drop_anchor": "main_payoff"}), event))["D"] == 80


def test_preview_is_read_only_preserves_decisions_and_refuses_stale_apply():
    import copy
    store = Store({"t": profile({"D": "approved", "B": "rejected", "F": "delete-approved"}, manual={"C"})})
    before = copy.deepcopy(store.profiles)
    template = validate({"drop_anchor": "main_payoff"})
    report = preview(store, ["t"], template)
    assert store.profiles == before
    assert report["details"][0]["main_payoff"]["state"] == "unknown"
    kept = {c["role"]: c for c in report["details"][0]["changes"] if c["action"] == "keep"}
    assert kept["D"]["anchor"] == "first_full_groove"
    reapply(store, ["t"], template, report["id"])
    assert store.profiles == before
    # Even an approval, evidence selection or template change after preview invalidates it.
    store.profiles["t"]["cues"][0]["review"] = "approved"
    changed = copy.deepcopy(store.profiles)
    with pytest.raises(ValueError, match="preview"):
        reapply(store, ["t"], template, report["id"])
    assert store.profiles == changed


def test_anchor_change_at_identical_time_is_shown_and_proposed():
    store = Store({"t": profile({})})
    store.profiles["t"]["main_payoff"] = {"kind": "main_payoff", "state": "present", "time": 80,
                                         "selected": True, "source": "user-selection"}
    template = validate({"drop_anchor": "main_payoff"})
    report = preview(store, ["t"], template)
    assert report["summary"]["moved"] == 3
    reapply(store, ["t"], template, report["id"])
    cue = next(c for c in store.profiles["t"]["cues"] if c["role"] == "D")
    assert cue["time"] == 80 and cue["name"] == "D main payoff"
    assert cue["anchor"] == "main_payoff" and cue["review"] == "proposed"
    assert preview(store, ["t"], template)["summary"]["tracks"] == 0


def test_candidate_edit_preview_apply_undo_on_isolated_store(tmp_path, song):
    from onset_service.store import Store as RealStore
    from conftest import analysis as fixture_analysis
    store = RealStore(tmp_path / "payoff-workspace")
    try:
        p = store.import_track(song)
        p = store.apply_analysis(p["id"], fixture_analysis(song))
        original_cues = p["cues"]
        p = store.edit(p["id"], {"main_payoff": {"state": "present", "time": 16.2}})
        assert p["cues"] == original_cues and p["overrides"]["main_payoff"]["time"] == 16.2
        template = validate({"drop_anchor": "main_payoff"})
        # Exercise the real RPC handlers without starting Service, audio imports,
        # worker threads or a real library lifecycle.
        from onset_service.service import Service
        service = Service.__new__(Service)
        service.store = store
        service.cue_template({"template": template})
        with pytest.raises(ValueError, match="Preview"):
            service.apply_cue_template({"track_ids": [p["id"]]})
        report = service.preview_cue_template({"track_ids": [p["id"]]})
        service.apply_cue_template({"track_ids": [p["id"]], "preview_id": report["id"]})
        updated = store.get(p["id"])
        d = next(c for c in updated["cues"] if c["role"] == "D")
        assert d["time"] == 16 and d["review"] == "proposed" and d["anchor"] == "main_payoff"
        assert updated["analysis"]["sections"]["drop"] == 2
        assert store.undo(p["id"])["cues"] == original_cues
        changed_analysis = fixture_analysis(song)
        changed_analysis["bpm"] = 121
        assert store.apply_analysis(p["id"], changed_analysis)["main_payoff"]["time"] == 16.2
        current = store.get(p["id"])
        d = next(c for c in current["cues"] if c["role"] == "D")
        store.review_cue(p["id"], d["id"], "approved", position=6)
        unknown = fixture_analysis(song)
        unknown["cues"] = [c for c in unknown["cues"] if c[0] != "D"]
        unknown["cue_anchor"] = "main_payoff"
        refreshed = store.apply_analysis(p["id"], unknown)
        retained = next(c for c in refreshed["cues"] if c["role"] == "D")
        assert retained["time"] == 6 and retained["manual"] and retained["review"] == "stale"
        assert retained["anchor"] == "first_full_groove"
        known = fixture_analysis(song)
        known["cues"] = place(known, template, refreshed["main_payoff"])
        known["cue_anchor"] = "main_payoff"
        refreshed = store.apply_analysis(p["id"], known)
        retained = next(c for c in refreshed["cues"] if c["role"] == "D")
        assert retained["time"] == 6 and retained["anchor"] == "first_full_groove" and retained["name"] == "D drop"
        for value in (-1, 24, float("inf"), True):
            with pytest.raises(ValueError, match="within the audio"):
                store.edit(p["id"], {"main_payoff": {"state": "present", "time": value}})
    finally:
        store.close()


@pytest.mark.parametrize("review", ["approved", "rejected", "delete-approved"])
@pytest.mark.parametrize("manual", [False, True])
def test_reanalysis_cannot_replace_decided_groove_with_payoff(tmp_path, song, review, manual):
    from onset_service.store import Store as RealStore
    from conftest import analysis as fixture_analysis
    store = RealStore(tmp_path / "decided-anchor")
    try:
        p = store.import_track(song)
        p = store.apply_analysis(p["id"], fixture_analysis(song))
        d = next(c for c in p["cues"] if c["role"] == "D")
        store.review_cue(p["id"], d["id"], review, position=4 if manual else None)
        result = fixture_analysis(song)
        result["cues"] = [("A", "A intro", 0, None), ("D", "D main payoff", 16, None)]
        result["cue_anchor"] = "main_payoff"
        updated = store.apply_analysis(p["id"], result)
        kept = next(c for c in updated["cues"] if c["role"] == "D")
        assert kept["time"] == 4 and kept["name"] == "D drop" and kept["anchor"] == "first_full_groove"
        assert kept["review"] == ("rejected" if review == "rejected" else "stale")
        # A second changed analysis still cannot discard the now-stale decision.
        result["bpm"] = 121
        result["cues"] = [("A", "A intro", 0, None)]
        updated = store.apply_analysis(p["id"], result)
        kept = next(c for c in updated["cues"] if c["role"] == "D")
        assert kept["time"] == 4 and kept["retained_decision"] == review
        template = validate({"drop_anchor": "main_payoff"})
        store.edit(p["id"], {"main_payoff": {"state": "present", "time": 16}})
        report = preview(store, [p["id"]], template)
        d_change = next(c for c in report["details"][0]["changes"] if c["role"] == "D")
        assert d_change["action"] == "keep"
        reapply(store, [p["id"]], template, report["id"])
        assert next(c for c in store.get(p["id"])["cues"] if c["role"] == "D")["time"] == 4
        # Reset is an explicit DJ decision allowing the new preset to replace it.
        store.review_cue(p["id"], kept["id"], "proposed")
        report = preview(store, [p["id"]], template)
        assert next(c for c in report["details"][0]["changes"] if c["role"] == "D")["action"] == ("keep" if manual else "update")
    finally:
        store.close()
