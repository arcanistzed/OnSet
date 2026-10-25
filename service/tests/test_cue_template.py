"""The DJ's cue template: defaults, validation, placement, re-placement and the write slots."""
import pytest

from onset_service.cue_template import PAD_KIND, default, place, reapply, validate, write_kind
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
