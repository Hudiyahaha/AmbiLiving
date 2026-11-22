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
