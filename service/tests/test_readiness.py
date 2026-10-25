import shutil
import numpy as np
import pytest
import soundfile as sf
from onset_service.store import Store
from onset_service.readiness import check, check_track, grid_offset
from conftest import analysis


def codes(row):
    return {i["code"] for i in row["issues"]}


def prepared(store, song, approve=("A", "D")):
    """An analysed track linked to rekordbox with matching grids and the given roles approved."""
    p = store.import_track(song)
    p = store.apply_analysis(p["id"], analysis(song))
    for cue in p["cues"]:
        if cue["role"] in approve:
            p = store.review_cue(p["id"], cue["id"], "approved")
    p["rekordbox_id"] = "42"
    p["rekordbox_observation"] = {"downbeats": list(np.arange(0, 24, 2.)), "grid_source": "rekordbox"}
    p["key"] = "8A"
    store.save(p)
    return store.get(p["id"])


def test_an_approved_linked_track_is_ready(tmp_path, song):
    store = Store(tmp_path / "app")
    row = check_track(prepared(store, song))
    assert row["status"] == "ready"
    assert codes(row) == {"not-written"}
    store.close()


def test_unapproved_cues_need_checking(tmp_path, song):
    store = Store(tmp_path / "app")
    row = check_track(prepared(store, song, approve=()))
    assert row["status"] == "check"
    assert {"first-beat-unapproved", "drop-unapproved"} <= codes(row)
    fix = next(i["fix"] for i in row["issues"] if i["code"] == "drop-unapproved")
    assert fix["action"] == "review-cues" and fix["cue_id"]
    store.close()


def test_missing_cues_and_rejected_drop(tmp_path, song):
    store = Store(tmp_path / "app")
    p = prepared(store, song)
    p["cues"] = [c for c in p["cues"] if c["role"] != "A"]
    for c in p["cues"]:
        if c["role"] == "D":
            c["review"] = "rejected"
    row = check_track(p)
    assert row["status"] == "blocked"
    assert {"no-first-beat-cue", "drop-rejected"} <= codes(row)
    p["cues"] = [c for c in p["cues"] if c["role"] != "D"]
    assert "no-drop-cue" in codes(check_track(p))
    store.close()


def test_missing_and_moved_audio(tmp_path, song):
    store = Store(tmp_path / "app")
    p = prepared(store, song)
    copy = tmp_path / "copy.wav"
    shutil.copyfile(song, copy)
    p = store.import_track(copy)
    p["path"] = str(tmp_path / "gone.wav")
    row = check_track(p)
    moved = next(i for i in row["issues"] if i["code"] == "moved-file")
    assert row["status"] == "blocked" and moved["fix"]["action"] == "relocate"
    assert moved["fix"]["path"] in p["locations"]
    p["locations"] = [p["path"]]
    assert "missing-file" in codes(check_track(p))
    store.close()


def test_changed_audio_only_when_verifying(tmp_path, song):
    store = Store(tmp_path / "app")
    p = prepared(store, song)
    y, sr = sf.read(song)
    sf.write(song, y * .5, sr)
    assert "changed-file" not in codes(check_track(p))
    assert "changed-file" in codes(check_track(p, verify_audio=True))
    store.close()


def test_grid_conflicts_with_rekordbox(tmp_path, song):
    store = Store(tmp_path / "app")
    p = prepared(store, song)
    p["rekordbox_observation"]["downbeats"] = list(np.arange(.5, 24, 2.))
    row = check_track(p)
    assert row["status"] == "blocked" and "grid-conflict" in codes(row)
    p["rekordbox_observation"]["downbeats"] = list(np.arange(0, 24, 2.) + .01)
    assert "grid-conflict" not in codes(check_track(p))
    p["overrides"]["grid"] = list(np.arange(0, 24, 2.))
    assert "grid-edited" in codes(check_track(p))
    p["overrides"]["accept_rekordbox_grid_conflict"] = True
    assert not {"grid-edited", "grid-conflict"} & codes(check_track(p))
    store.close()


def test_grid_offset_ignores_what_only_one_grid_covers():
    assert grid_offset([0, 2, 4], [0, 2, 4, 6, 8, 10]) == pytest.approx(0)
    assert grid_offset([0], [0, 2]) is None
    assert grid_offset([0, 2, 4], [1, 3]) == pytest.approx(1)


def test_reanalysis_makes_approvals_stale(tmp_path, song):
    store = Store(tmp_path / "app")
    p = prepared(store, song)
    changed = analysis(song)
    changed["bpm"] = 122
    p = store.apply_analysis(p["id"], changed)
    row = check_track(p)
    assert "stale-approvals" in codes(row) and "first-beat-unapproved" in codes(row)
    store.close()


def test_missing_key_bpm_and_rekordbox_link(tmp_path, song):
    store = Store(tmp_path / "app")
    p = store.import_track(song)
    row = check_track(p)
    assert {"not-analysed", "not-in-rekordbox", "no-key", "no-bpm"} <= codes(row)
    assert not {"no-first-beat-cue", "no-drop-cue"} & codes(row)
    p["key"] = {"name": "A minor", "state": "unknown"}
    assert "no-key" in codes(check_track(p))
    store.close()


def test_selection_by_ids_playlist_and_set(tmp_path, song):
    store = Store(tmp_path / "app")
    p = prepared(store, song)
    p["rekordbox_playlists"] = ["Friday"]
    store.save(p)
    other = tmp_path / "other.wav"
    y, sr = sf.read(song)
    sf.write(other, y * .9, sr)
    q = store.import_track(other)
    tracks = store.tracks()
    assert [r["track_id"] for r in check(tracks, playlist="Friday")["tracks"]] == [p["id"]]
    result = check(tracks, set_plan={"id": "s1", "track_ids": [q["id"], p["id"], q["id"]]})
    assert [r["track_id"] for r in result["tracks"]] == [q["id"], p["id"]]
    assert result["scope"] == {"set_id": "s1"} and result["summary"]["total"] == 2
    with pytest.raises(ValueError):
        check(tracks, track_ids=["nope"])
    with pytest.raises(ValueError):
        check(tracks)
    store.close()


def test_service_check_changes_nothing(tmp_path, song):
    from onset_service.service import Service
    service = Service(tmp_path / "app", warm=False)
    p = prepared(service.store, song, approve=())
    p["rekordbox_playlists"] = ["Friday"]
    service.store.save(p)
    tables = ("tracks", "aliases", "revisions", "edits", "jobs", "artifacts", "settings")
    before = {t: service.store.db.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall() for t in tables}
    result = service.dispatch("gig-readiness", {"playlist": "Friday", "verify_audio": True})
    assert result["summary"] == {"ready": 0, "check": 1, "blocked": 0, "total": 1}
    assert service.dispatch("gig-readiness", {"track_ids": [p["id"]]})["tracks"][0]["status"] == "check"
    with pytest.raises(ValueError):
        service.dispatch("gig-readiness", {"set_id": "missing"})
    with pytest.raises(ValueError):
        service.dispatch("gig-readiness", {"track_ids": p["id"]})
    after = {t: service.store.db.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall() for t in tables}
    assert before == after
    service.close()
