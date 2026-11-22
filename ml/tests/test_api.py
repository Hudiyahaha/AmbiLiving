"""Backend smoke tests. Run from ml/: ``py -m pytest tests -q``."""

from __future__ import annotations

import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from api import live
from api.main import app
from har.data import RAW_DIR

client = TestClient(app)


def _sse(text: str) -> list[tuple[str, dict]]:
    out = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_health_and_homes():
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/", follow_redirects=False).headers["location"] == "/docs"
    homes = {h["id"]: h for h in client.get("/homes").json()}
    assert set(homes) == {"aruba", "milan"}
    assert all(h["model"]["available"] for h in homes.values())


@pytest.mark.parametrize("home", ["aruba", "milan"])
def test_exported_data(home):
    day = client.get(f"/homes/{home}/day").json()
    assert day["home"] == home and day["events"]
    an = client.get(f"/homes/{home}/anomalies").json()
    assert an["anomalies"] and {"observed", "expected", "reason", "severity"} <= set(an["anomalies"][0])


def test_unknown_home_and_scenario():
    assert client.get("/homes/kasteren/day").status_code == 404
    assert client.get("/replay/aruba/../../package").status_code == 404
    r = client.get("/replay/aruba/nope")
    assert r.status_code == 404 and "normal" in r.json()["detail"]


def test_replay_scenario_matches_file():
    idx = client.get("/replay").json()
    ids = [s["id"] for s in idx["aruba"]["scenarios"]]
    assert "normal" in ids
    sc = client.get("/replay/aruba/normal").json()
    assert sc["home"] == "aruba" and sc["id"] == "normal" and sc["events"]


def test_stream_is_ordered_and_complete():
    sc = client.get("/replay/aruba/inactivity").json()
    r = client.get("/replay/aruba/inactivity/stream", params={"speed": 86400})
    assert r.headers["content-type"].startswith("text/event-stream")
    msgs = _sse(r.text)
    assert msgs[0][0] == "start" and msgs[-1][0] == "end"
    body = msgs[1:-1]
    ts = [m["t"] for _, m in body]
    assert ts == sorted(ts)
    kinds = [k for k, _ in body]
    assert kinds.count("event") == len(sc["events"])
    assert kinds.count("prediction") == len(sc["predictions"])
    assert kinds.count("alert") == len(sc["alerts"])
    assert kinds.count("clock") == 24 * 60  # one per minute of the day
    # An alert is sent at the second it was raised, never before.
    for k, m in body:
        if k == "alert":
            assert m["t"] == m["raisedAt"]


def test_stream_window_and_filter():
    r = client.get("/replay/milan/normal/stream",
                   params={"speed": 86400, "start": 6 * 3600, "end": 7 * 3600,
                           "only": ["prediction"]})
    body = _sse(r.text)[1:-1]
    assert body and all(k == "prediction" for k, _ in body)
    assert all(6 * 3600 <= m["t"] < 7 * 3600 for _, m in body)
    assert client.get("/replay/milan/normal/stream", params={"start": 10, "end": 5}).status_code == 422


def test_recognise_rejects_short_or_bad_input():
    ev = [{"timestamp": "2011-01-01T08:00:00", "sensor": "M003", "state": "ON"}] * 10
    r = client.post("/homes/aruba/recognise", json={"events": ev})
    assert r.status_code == 422 and "100" in r.json()["detail"]
    ev = [{"timestamp": "2011-01-01T08:00:00", "sensor": "M003", "state": "maybe"}] * 100
    assert client.post("/homes/aruba/recognise", json={"events": ev}).status_code == 422


def test_routine_and_session_basics():
    r = client.get("/homes/milan/routine").json()
    assert r["observation_days"] == 13 and r["stream"] == "win" and r["usual_day"]
    assert all(h["routine"]["available"] for h in client.get("/homes").json())

    s = client.post("/homes/aruba/sessions", json={"monitorFrom": "2011-05-05"})
    assert s.status_code == 201
    sid = s.json()["session"]
    assert s.json()["started"] is False and s.json()["routine"]["stream"] == "winc"
    ev = [{"timestamp": f"2011-05-05T08:00:{i:02d}", "sensor": "M003", "state": "ON"}
          for i in range(5)]
    r = client.post(f"/sessions/{sid}/events", json={"events": ev}).json()
    assert r["day"] == "2011-05-05" and r["predictions"] == []  # fewer than 100 events yet
    # Events must not go back in time.
    old = [{"timestamp": "2011-05-05T07:00:00", "sensor": "M003", "state": "ON"}]
    assert client.post(f"/sessions/{sid}/events", json={"events": old}).status_code == 422
    assert client.delete(f"/sessions/{sid}").status_code == 204
    assert client.get(f"/sessions/{sid}").status_code == 404


@pytest.mark.skipif(not (RAW_DIR / "milan.txt").exists(), reason="raw CASAS data not present")
def test_live_session_reproduces_replay_day():
    """Pushing a real day in 2-hour batches gives the replay's predictions and alerts."""
    import pandas as pd

    from har.data import load_home

    sc = client.get("/replay/milan/normal").json()
    day = pd.Timestamp(sc["day"]).normalize()
    home = load_home("milan")
    lo, hi = np.searchsorted(home.times, [day.to_datetime64(),
                                          (day + pd.Timedelta(days=1)).to_datetime64()])

    def events(a, b):
        return [{"timestamp": str(t), "sensor": s, "state": v}
                for t, s, v in zip(home.times[a:b], home.sensors[a:b], home.states[a:b])]

    sid = client.post("/homes/milan/sessions",
                      json={"monitorFrom": str(day.date())}).json()["session"]
    r = client.post(f"/sessions/{sid}/events", json={"events": events(lo - 150, lo)}).json()
    assert r["predictions"] == [] and r["alerts"] == []  # history only
    n_pred, raised = 0, set()
    for h in range(0, 24, 2):
        g, g2 = day + pd.Timedelta(hours=h), day + pd.Timedelta(hours=h + 2)
        a, b = np.searchsorted(home.times, [g.to_datetime64(), g2.to_datetime64()])
        r = client.post(f"/sessions/{sid}/events",
                        json={"events": events(a, b), "now": g2.isoformat()})
        assert r.status_code == 200, r.text
        r = r.json()
        n_pred += len(r["predictions"])
        raised |= set(r["newAlerts"])
    assert n_pred == len(sc["predictions"])
    assert [c["day"] for c in r["closed"]] == [str(day.date())]
    closed = r["closed"][0]["alerts"]
    assert {a["id"] for a in closed} == raised

    def key(a, sec):
        return (sec, a["kind"], a["activity"], a["tier"], a["delivered"])

    ours = sorted(key(a, int((pd.Timestamp(a["raisedAt"]) - day).total_seconds())) for a in closed)
    ref = sorted(key(a, a["raisedAt"]) for a in sc["alerts"])
    assert ours == ref
    assert r["day"] == str((day + pd.Timedelta(days=1)).date())  # moved on to the next day
    client.delete(f"/sessions/{sid}")


def test_simulation_plays_a_feed_live():
    """A recorded day played at 3600x through a simulation gives the replay's result,
    and the stream delivers a snapshot followed by ticks with spliceable deltas."""
    import time

    sc = client.get("/replay/milan/toilet-trips").json()
    feeds = {f["id"] for f in client.get("/homes/milan/feeds").json()}
    assert {"normal", "toilet-trips"} <= feeds
    with TestClient(app) as c:  # keeps the event loop alive for the background task
        r = c.post("/homes/milan/simulations",
                   json={"scenario": "toilet-trips", "speed": 3600, "startAt": 0})
        assert r.status_code == 201, r.text
        sim = r.json()["simulation"]

        # Follow the stream for a few messages.
        with c.stream("GET", f"/simulations/{sim}/stream") as s:
            msgs, buf = [], ""
            for chunk in s.iter_text():
                buf += chunk
                while "\n\n" in buf:
                    block, buf = buf.split("\n\n", 1)
                    if block.startswith(":"):
                        continue
                    lines = dict(line.split(": ", 1) for line in block.splitlines())
                    msgs.append((lines["event"], json.loads(lines["data"])))
                if sum(k == "tick" for k, _ in msgs) >= 3:
                    break
        kinds = [k for k, _ in msgs]
        assert "snapshot" in kinds and kinds.index("snapshot") < kinds.index("tick")
        snap = next(m for k, m in msgs if k == "snapshot")
        events = list(snap["events"])
        for k, m in msgs[kinds.index("snapshot") + 1:]:
            if k == "tick" and "events" in m:
                assert m["eventsFrom"] <= len(events)
                events = events[:m["eventsFrom"]] + m["events"]
        assert [e[0] for e in events] == sorted(e[0] for e in events)

        deadline = time.time() + 240
        while c.get(f"/simulations/{sim}").json()["status"] != "finished":
            assert time.time() < deadline, "simulation did not finish"
            time.sleep(1)
        full = c.get(f"/simulations/{sim}", params={"full": True}).json()
        c.delete(f"/simulations/{sim}")

    assert len(full["predictions"]) == len(sc["predictions"])
    labels = sc["labels"]
    assert [(int(t), a) for t, a, _ in full["predictions"]] == \
        [(t, labels[a]) for t, a, _ in sc["predictions"]]

    def key(a):
        return (a["raisedAt"], a["kind"], a["activity"], a["tier"], a["delivered"])

    assert sorted(key(a) for a in full["alerts"]) == sorted(key(a) for a in sc["alerts"])
    assert full["episodes"] and full["current"] is not None


def test_simulation_week_runs_past_midnight():
    """The week feed carries on past midnight (D20): a new snapshot starts the next day,
    and the closed day's report equals the replay of the scenario played on it."""
    feeds = {f["id"]: f for f in client.get("/homes/milan/feeds").json()}
    assert feeds["week"]["days"] == 7
    sc = client.get("/replay/milan/inactivity").json()  # played on the week's first day
    with TestClient(app) as c:
        r = c.post("/homes/milan/simulations",
                   json={"scenario": "week", "speed": 3600, "startAt": 23 * 3600})
        assert r.status_code == 201, r.text
        sim = r.json()["simulation"]
        snaps = []
        with c.stream("GET", f"/simulations/{sim}/stream") as s:
            buf = ""
            for chunk in s.iter_text():
                buf += chunk
                while "\n\n" in buf:
                    block, buf = buf.split("\n\n", 1)
                    if block.startswith(":"):
                        continue
                    lines = dict(line.split(": ", 1) for line in block.splitlines())
                    if lines["event"] == "snapshot":
                        snaps.append(json.loads(lines["data"]))
                if len(snaps) >= 2:
                    break
        c.post(f"/simulations/{sim}/control", json={"action": "pause"})
        first, second = snaps[0], snaps[1]
        assert (first["day"], first["dayIndex"]) == ("2009-12-25", 0)
        assert (second["day"], second["dayIndex"]) == ("2009-12-26", 1)
        assert second["closedDays"][0]["day"] == "2009-12-25"
        assert all(e[0] < 86400 for e in second["events"])
        report = c.get(f"/simulations/{sim}/days/2009-12-25").json()
        missing = c.get(f"/simulations/{sim}/days/2009-12-28")
        c.delete(f"/simulations/{sim}")

    assert missing.status_code == 404
    labels = report["labels"]
    assert [(int(t), labels[a]) for t, a, _ in report["predictions"]] == \
        [(t, sc["labels"][a]) for t, a, _ in sc["predictions"]]

    def key(a):
        return (a["raisedAt"], a["kind"], a["activity"], a["tier"], a["delivered"])

    assert sorted(key(a) for a in report["alerts"]) == sorted(key(a) for a in sc["alerts"])
    assert report["episodes"] and report["daily"] and len(report["usual"]) == 48


@pytest.mark.skipif(not (RAW_DIR / "aruba.txt").exists(), reason="raw CASAS data not present")
def test_recognise_matches_saved_model():
    """The endpoint gives the same answer as the saved model on real Aruba events."""
    from har.data import load_home

    home = load_home("aruba")
    lo, hi = 500_000, 500_250
    events = [{"timestamp": str(t), "sensor": s, "state": v}
              for t, s, v in zip(home.times[lo:hi], home.sensors[lo:hi], home.states[lo:hi])]
    # Send them shuffled: the API must sort by time itself.
    rng = np.random.default_rng(0)
    shuffled = [events[i] for i in rng.permutation(len(events))]
    r = client.post("/homes/aruba/recognise", json={"events": shuffled, "every": 10})
    assert r.status_code == 200, r.text
    out = r.json()

    wm = live.get_model("aruba")
    part = live.to_home("aruba", home.times[lo:hi], home.sensors[lo:hi], home.states[lo:hi])
    ends = np.arange(250, 99, -10)[::-1]
    names, conf = wm.predict(part, ends)
    assert out["current"]["activity"] == names[-1]
    assert out["current"]["confidence"] == pytest.approx(float(conf[-1]), abs=1e-4)
    assert [h["activity"] for h in out["history"]] == names
    assert out["unknownSensorStates"] == []
