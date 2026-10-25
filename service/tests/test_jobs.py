import threading
import time
import pytest
from onset_service.service import Service


@pytest.mark.parametrize("shutdown", [True, False])
def test_shutdown_preserves_resumable_job_but_explicit_cancel_stays_cancelled(tmp_path, song, monkeypatch, shutdown):
    from onset_service import analysis
    started=threading.Event()
    def waiting_analysis(*args):
        checkpoint=args[3]
        started.set()
        while True:
            checkpoint("fixture", .25)
            time.sleep(.01)
    monkeypatch.setattr(analysis,"analyse",waiting_analysis)
    service=Service(tmp_path/"app")
    track=service.store.import_track(song)
    job=service.enqueue("analyze",{"track_ids":[track["id"]],"deep":False})
    assert started.wait(10)
    if shutdown:
        service.job_control(job["id"],"pause")
    else:
        service.job_control(job["id"],"cancel")
        deadline=time.monotonic()+5
        while service.store.jobs()[0]["state"]!="cancelled" and time.monotonic()<deadline:
            time.sleep(.01)
        assert service.store.jobs()[0]["state"]=="cancelled"
    service.close()
    reopened=Service(tmp_path/"app")
    try:
        saved=reopened.store.jobs()[0]
        assert saved["id"]==job["id"]
        assert saved["state"]==("paused" if shutdown else "cancelled")
        assert saved["params"]["track_ids"]==[track["id"]]
        if shutdown:assert "resume" in saved["error"]
    finally:reopened.close()


def test_queue_resume_does_not_claim_running_and_duplicate_requests_reuse_job(tmp_path,song,monkeypatch):
    import threading
    from onset_service import analysis
    entered=threading.Event();release=threading.Event()
    def blocked(*args):
        entered.set();release.wait(5);args[3]("fixture",.2)
        raise RuntimeError("fixture end")
    monkeypatch.setattr(analysis,"analyse",blocked)
    service=Service(tmp_path/"app");track=service.store.import_track(song)
    first=service.enqueue("analyze",{"track_ids":[track["id"]],"deep":True})
    assert entered.wait(5)
    params={"track_ids":[track["id"]],"deep":True,"experimental":["edmformer"]}
    queued=service.enqueue("analyze",params)
    assert service.enqueue("analyze",params)["id"]==queued["id"]
    assert service.job_control(queued["id"],"resume")["state"]=="queued"
    service.job_control(first["id"],"cancel")
    release.set();service.close()
    reopened=Service(tmp_path/"app")
    assert next(j for j in reopened.store.jobs() if j["id"]==first["id"])["state"]=="cancelled"
    reopened.close()


def test_checkpointed_paused_job_can_be_cancelled_without_restarting_work(tmp_path):
    service=Service(tmp_path/"app")
    service.store.job({"id":"paused","kind":"analyze","state":"paused","params":{},"completed":[]})
    assert service.job_control("paused","cancel")["state"]=="cancelled"
    assert not service.controls
    service.close()


def test_pause_between_checkpoints_is_not_overwritten_by_completed_track(tmp_path,song,monkeypatch):
    from onset_service import analysis
    entered=threading.Event();release=threading.Event()
    def finishing(*args):
        args[3]("fixture",.1)
        if not entered.is_set():entered.set();release.wait(5)
        return {"state":"complete"}
    monkeypatch.setattr(analysis,"analyse",finishing)
    service=Service(tmp_path/"app")
    monkeypatch.setattr(service.store,"apply_analysis",lambda tid,result:None)
    first=service.store.import_track(song)
    monkeypatch.setattr(service.store,"get",lambda tid:{"id":tid})
    job=service.enqueue("analyze",{"track_ids":[first["id"],"second"],"deep":False})
    assert entered.wait(5)
    service.job_control(job["id"],"pause")
    release.set()
    deadline=time.monotonic()+5
    while first["id"] not in service.store.jobs()[0]["completed"] and time.monotonic()<deadline:
        time.sleep(.01)
    saved=service.store.jobs()[0]
    assert saved["completed"]==[first["id"]] and saved["state"]=="paused"
    service.job_control(job["id"],"cancel");service.close()


def test_full_disk_pauses_job_and_resume_reenqueues(tmp_path,song,monkeypatch):
    import errno
    from onset_service import analysis
    calls=[]
    def full(*args):
        calls.append(1)
        raise OSError(errno.ENOSPC,"No space left on device")
    monkeypatch.setattr(analysis,"analyse",full)
    service=Service(tmp_path/"app")
    a=service.store.import_track(song)
    job=service.enqueue("analyze",{"track_ids":[a["id"],"never-reached"],"deep":False})
    deadline=time.monotonic()+5
    while service.store.jobs()[0]["state"] not in {"paused","failed","partial"} and time.monotonic()<deadline:
        time.sleep(.01)
    saved=service.store.jobs()[0]
    assert saved["state"]=="paused" and "full" in saved["error"] and saved["completed"]==[]
    assert len(calls)==1
    monkeypatch.setattr(analysis,"analyse",lambda *args:{"state":"complete"})
    monkeypatch.setattr(service.store,"apply_analysis",lambda tid,result:None)
    service.job_control(job["id"],"resume")
    deadline=time.monotonic()+5
    while service.store.jobs()[0]["state"] not in {"complete","partial","failed"} and time.monotonic()<deadline:
        time.sleep(.01)
    assert service.store.jobs()[0]["completed"]==[a["id"]]
    service.close()


def test_progress_is_saved_on_stage_changes_and_a_heartbeat_not_every_checkpoint():
    from onset_service.service import progress_due, PROGRESS_S, HEARTBEAT_S, STALL_S
    assert progress_due(None, "decode", 0, 0.)
    last = ("stems/models:demucs", .5, 100.)
    assert progress_due(last, "stems/models:essentia", .5, 100.1)
    assert not progress_due(last, "stems/models:demucs", .5, 100. + HEARTBEAT_S - .1)
    assert progress_due(last, "stems/models:demucs", .5, 100. + HEARTBEAT_S)
    assert not progress_due(last, "stems/models:demucs", .6, 100. + PROGRESS_S - .1)
    assert progress_due(last, "stems/models:demucs", .6, 100. + PROGRESS_S)
    assert HEARTBEAT_S * 4 < STALL_S


def test_a_busy_checkpoint_loop_saves_and_notifies_once_per_stage(tmp_path, song, monkeypatch):
    from onset_service import analysis
    service=Service(tmp_path/"app")
    track=service.store.import_track(song)
    def busy(profile,home,deep,checkpoint,*args):
        for stage in ("stems/models:demucs","stems/models:essentia"):
            for _ in range(200):
                checkpoint(stage,.5)
        return {"state":"complete"}
    monkeypatch.setattr(analysis,"analyse",busy)
    monkeypatch.setattr(service.store,"apply_analysis",lambda tid,result:None)
    saves,sent=[],[]
    real_job=service.store.job
    monkeypatch.setattr(service.store,"job",lambda record:(saves.append(record.get("stage")),real_job(record))[1])
    service.notify=lambda message:sent.append(message["params"]["stage"])
    job=service.enqueue("analyze",{"track_ids":[track["id"]],"deep":False})
    deadline=time.monotonic()+20
    while next(j for j in service.store.jobs() if j["id"]==job["id"])["state"] in {"queued","running"} and time.monotonic()<deadline:
        time.sleep(.02)
    assert next(j for j in service.store.jobs() if j["id"]==job["id"])["state"]=="complete"
    assert sent.count("stems/models:demucs")==1 and sent.count("stems/models:essentia")==1
    assert saves.count("stems/models:demucs")==1 and len(saves)<10
    service.close()


def test_a_resumed_job_saves_running_at_once(tmp_path, song, monkeypatch):
    from onset_service import analysis
    started,release=threading.Event(),threading.Event()
    def pausing(profile,home,deep,checkpoint,*args):
        checkpoint("fixture",.25);started.set()
        release.wait(10)
        checkpoint("fixture",.25)
        return {"state":"complete"}
    monkeypatch.setattr(analysis,"analyse",pausing)
    service=Service(tmp_path/"app")
    track=service.store.import_track(song)
    monkeypatch.setattr(service.store,"apply_analysis",lambda tid,result:None)
    sent=[];service.notify=lambda message:sent.append(message["params"]["state"])
    job=service.enqueue("analyze",{"track_ids":[track["id"]],"deep":False})
    assert started.wait(10)
    service.job_control(job["id"],"pause");release.set()
    time.sleep(.5)
    before=len(sent)
    service.job_control(job["id"],"resume")
    deadline=time.monotonic()+10
    while next(j for j in service.store.jobs() if j["id"]==job["id"])["state"]!="complete" and time.monotonic()<deadline:
        time.sleep(.02)
    assert "running" in sent[before:]
    service.close()
