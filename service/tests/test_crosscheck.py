"""Cross-checks must retain contradictory evidence rather than pick a convenient vote."""
from itertools import permutations

from tools.crosscheck import gemini_for_track, judge_event, judge_tempo, seconds, sources


def test_competing_clusters_are_unresolved_in_any_source_order():
    votes = {"onset": 2, "spectral": 3, "allin1": 40, "gemini": 41}
    for order in permutations(votes):
        assert judge_event("drop", {k: votes[k] for k in order}, {})["status"] == "ambiguous"


def test_middle_vote_cannot_bridge_disagreeing_endpoints():
    assert judge_event("drop", {"onset": 10, "spectral": 12, "gemini": 14}, {})["status"] == "ambiguous"


def test_large_energy_step_does_not_settle_musical_meaning():
    result = judge_event("drop", {"spectral": 10, "gemini": 40}, {"step_db": {"drop": 20}})
    assert result["status"] == "ambiguous"


def test_consensus_against_stored_value_is_only_a_candidate():
    result = judge_event("groove", {"onset": 2, "spectral": 40, "gemini": 41}, {})
    assert result["status"] == "candidate"
    assert result["value"] == 40


def test_mixed_tempo_estimates_remain_unresolved():
    assert judge_tempo({"onset": 75, "allin1": 150, "gemini": 75})["status"] == "ambiguous"
    assert judge_tempo({"onset": 75, "allin1": 150, "gemini": 150})["value"] == 150


def test_exact_audio_path_wins_and_ambiguous_titles_do_not_match():
    p = {"title": "Follow", "path": r"C:\music\Follow.flac"}
    results = {"C:/music/Follow.flac": {"bpm": 127}, "C:/other/Follow remix.flac": {"bpm": 128}}
    assert gemini_for_track(p, results) == {"bpm": 127}
    p["path"] = "missing.flac"
    assert gemini_for_track(p, results) is None


def test_invalid_or_out_of_track_times_are_not_clamped_to_last_bar():
    assert seconds("1:70") is None
    assert seconds("1:02.5") == 62.5
    p = {"analysis": {"duration": 20, "downbeats": [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]}}
    spec = dict.fromkeys(("groove", "drop", "breakdown", "outro"))
    found = sources(p, spec, None, {"drop": "0:04", "main_drop": "3:00", "outro": "0:20"})
    assert found["groove"]["gemini"] == 2
    assert "gemini" not in found["drop"]
    assert "gemini" not in found["outro"]


def test_split_essentia_profiles_do_not_invent_a_majority():
    estimates = {"a": {"key": "C", "scale": "major"},
                 "b": {"key": "G", "scale": "major"},
                 "c": {"key": "D", "scale": "minor"}}
    p = {"analysis": {"duration": 20, "downbeats": [0, 2, 4],
                      "deep": {"models": {"essentia": {"data": estimates}}}}}
    spec = dict.fromkeys(("groove", "drop", "breakdown", "outro"))
    assert "essentia" not in sources(p, spec, None, None)["key"]
    estimates["c"] = estimates["a"]
    assert sources(p, spec, None, None)["key"]["essentia"] == "8B"
