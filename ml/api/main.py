"""HTTP routes of the AmbiLiving backend (decision D16).

Interactive documentation is served at ``/docs`` while the server runs.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from har.data import DATASETS
from har.routine_live import routine_path

from . import live, sessions, simulate, store, stream

app = FastAPI(
    title="AmbiLiving API",
    version="0.1.0",
    description="Activity recognition, routine deviations and live replay for the "
                "AmbiLiving caregiver dashboard.",
)

# The Next.js dev server; override with a comma-separated AMBILIVING_CORS.
_origins = os.environ.get("AMBILIVING_CORS", "http://localhost:3000,http://127.0.0.1:3000")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in _origins.split(",")],
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])


@app.exception_handler(store.NotFound)
async def _not_found(_: Request, exc: store.NotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


# --------------------------------------------------------------------------- homes

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


@app.get("/health", tags=["service"])
def health():
    return {"status": "ok", "homes": list(DATASETS)}


@app.get("/homes", tags=["homes"])
def homes():
    """The homes the backend knows and whether their live model is available."""
    return [{"id": h, "model": live.model_info(h),
             "routine": {"available": routine_path(h).is_file()}} for h in DATASETS]


@app.get("/homes/{home}/day", tags=["homes"])
def dashboard_day(home: str):
    """The exported real day (sensor events + recognised activities) for the dashboard."""
    return store.dashboard_day(home)


@app.get("/homes/{home}/anomalies", tags=["homes"])
def anomalies(home: str):
    """Routine deviations found on the real monitoring days (nothing injected)."""
    return store.anomalies(home)


# --------------------------------------------------------------------------- live recognition

class SensorEvent(BaseModel):
    timestamp: datetime
    sensor: str = Field(examples=["M003"])
    state: str = Field(examples=["ON"], description="ON/OFF/OPEN/CLOSE or active/inactive/open/closed")


class RecogniseRequest(BaseModel):
    events: list[SensorEvent] = Field(min_length=1, max_length=200_000)
    every: int | None = Field(
        None, ge=1, le=10_000,
        description="Also recognise every N events back from the last one (the live "
                    "demo uses 10). Omit for the last event only.")
    top: int = Field(3, ge=1, le=20, description="How many alternative activities to return")


@app.post("/homes/{home}/recognise", tags=["live"])
def recognise(home: str, body: RecogniseRequest):
    """Recognise the current activity from the last 100 sensor events.

    Send at least 100 events (motion and door sensors). They are sorted by time
    first. Sensor/state pairs the model never saw are ignored and listed in
    ``unknownSensorStates``.
    """
    ev = body.events
    try:
        out, info = live.recognise(home, [e.timestamp for e in ev], [e.sensor for e in ev],
                                   [e.state for e in ev], body.every, body.top)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    wm = live.get_model(home)
    return {
        "home": home, "model": wm.name, "windowEvents": wm.size, **info,
        "current": _recognised(out[-1]),
        "history": [_recognised(r) for r in out] if body.every else None,
    }


def _recognised(r: live.Recognised) -> dict:
    return {"timestamp": r.timestamp.isoformat(), "eventIndex": r.end - 1,
            "activity": r.activity, "confidence": round(r.confidence, 4),
            "top": [{"activity": a, "confidence": round(c, 4)} for a, c in r.top]}


# --------------------------------------------------------------------------- live monitoring

@app.get("/homes/{home}/routine", tags=["live"])
def routine(home: str):
    """The saved routine model: observation period, stream rule, thresholds, usual day."""
    return sessions.routine_info(home)


class SessionRequest(BaseModel):
    monitorFrom: date | None = Field(
        None, description="First day to monitor (from midnight). Events before it only fill "
                          "the first recognition windows. Default: the day of the first event.")


@app.post("/homes/{home}/sessions", tags=["live"], status_code=201)
def create_session(home: str, body: SessionRequest | None = None):
    """Start live monitoring of a home: then push events to ``/sessions/{id}/events``."""
    s = sessions.create(home, body.monitorFrom if body else None)
    return sessions.state_json(s) | {"routine": sessions.routine_info(home)}


class PushRequest(BaseModel):
    events: list[SensorEvent] = Field(default_factory=list, max_length=200_000)
    now: datetime | None = Field(
        None, description="Current clock time, if later than the last event. Lets the "
                          "routine model notice silences while no events arrive.")


@app.post("/sessions/{session_id}/events", tags=["live"])
def push_events(session_id: str, body: PushRequest):
    """Add sensor events (in time order, none earlier than the session clock).

    Runs recognition every 10th event and the routine model every 2 minutes of the
    clock, as a deployed system would. Returns the new predictions, the IDs of newly
    raised alerts, the day's routed alerts so far, and any days that ended.
    """
    s = sessions.get(session_id)
    ev = body.events
    try:
        result = s.push([e.timestamp for e in ev], [e.sensor for e in ev],
                        [e.state for e in ev], body.now)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return sessions.push_json(s, result)


@app.get("/sessions/{session_id}", tags=["live"])
def session_state(session_id: str):
    """Current activity, today's episodes and routed alerts, and recently ended days."""
    return sessions.state_json(sessions.get(session_id))


@app.delete("/sessions/{session_id}", tags=["live"], status_code=204)
def delete_session(session_id: str):
    sessions.delete(session_id)


# --------------------------------------------------------------------------- simulated live homes

@app.get("/homes/{home}/feeds", tags=["simulation"])
def feeds(home: str):
    """Recorded days that can be played as a live sensor feed (``har.feeds``)."""
    return simulate.scenarios(home)


class SimulationRequest(BaseModel):
    scenario: str = Field("week", description="Recorded feed to play: a week of consecutive "
                                              "days, or one day (see /homes/{home}/feeds)")
    speed: float = Field(60, gt=0, le=3600, description="Simulated seconds per real second")
    startAt: int = Field(6 * 3600, ge=0, lt=86_400,
                         description="Second of the first day to start at; everything before "
                                     "it is processed at once")


@app.post("/homes/{home}/simulations", tags=["simulation"], status_code=201)
async def create_simulation(home: str, body: SimulationRequest | None = None):
    """Play a recorded day into a live session, as if its sensors were sending events now.

    Recognition, the routine model and alert routing run live on the feed. Follow it
    with ``GET /simulations/{id}/stream``.
    """
    body = body or SimulationRequest()
    sim = await simulate.create(home, body.scenario, body.speed, body.startAt)
    return sim.meta()


@app.get("/simulations/{sim_id}", tags=["simulation"])
def simulation(sim_id: str, full: bool = Query(False, description="Include the day so far")):
    """The simulation's status; with ``full=true`` also everything so far (as the stream's
    first message)."""
    sim = simulate.get(sim_id)
    return sim.snapshot() if full and sim.status != "starting" else sim.meta()


@app.get("/simulations/{sim_id}/stream", tags=["simulation"])
def simulation_stream(sim_id: str):
    """Server-sent events: ``snapshot`` (the day so far, and again when a new day starts
    at midnight), then a ``tick`` about every half second with new events and predictions (spliced in at ``eventsFrom`` /
    ``predictionsFrom``), the current episodes, routed alerts and newly raised alert IDs."""
    sim = simulate.get(sim_id)
    return StreamingResponse(simulate.events(sim), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class ControlRequest(BaseModel):
    action: Literal["pause", "resume", "speed"]
    speed: float | None = Field(None, gt=0, le=3600)


@app.get("/simulations/{sim_id}/days/{day}", tags=["simulation"])
def simulation_day(sim_id: str, day: date):
    """A day that has ended in the simulation, as a day report (the shape of a replay
    scenario): events, predictions, episodes, the routed alerts and the usual day."""
    return simulate.closed_day(sim_id, f"{day:%Y-%m-%d}")


@app.post("/simulations/{sim_id}/control", tags=["simulation"])
def control_simulation(sim_id: str, body: ControlRequest):
    sim = simulate.get(sim_id)
    if body.action == "pause":
        sim.pause()
    elif body.action == "resume":
        sim.resume()
    else:
        if body.speed is None:
            raise HTTPException(status_code=422, detail="speed is required")
        sim.set_speed(body.speed)
    return sim.meta()


@app.delete("/simulations/{sim_id}", tags=["simulation"], status_code=204)
def delete_simulation(sim_id: str):
    simulate.stop(sim_id)


# --------------------------------------------------------------------------- replay

@app.get("/replay", tags=["replay"])
def replay_index():
    """Replay scenarios per home, with the overall rates of the live pipeline."""
    return store.replay_index()


@app.get("/replay/{home}/{scenario}", tags=["replay"])
def replay_scenario(home: str, scenario: str):
    """One whole scenario: events, predictions, episodes and alerts (as ``/live`` uses it)."""
    return store.scenario(home, scenario)


@app.get("/replay/{home}/{scenario}/stream", tags=["replay"])
def replay_stream(
    home: str, scenario: str,
    speed: float = Query(60.0, gt=0, le=86_400,
                         description="Seconds of the day per real second (60 = a minute per second)"),
    start: int = Query(0, ge=0, lt=86_400, description="Start at this second of the day"),
    end: int = Query(86_400, gt=0, le=86_400, description="Stop before this second of the day"),
    only: list[Literal["clock", "event", "prediction", "alert"]] | None = Query(
        None, description="Only send these item types (default: all)"),
    tick: int = Query(60, ge=0, le=3600,
                      description="Send a clock item every this many seconds of the day (0 = off)"),
):
    """Stream a recorded day as server-sent events, in timestamp order.

    Event types: ``start`` (scenario details), then ``clock`` (every ``tick`` seconds),
    ``event`` (sensor), ``prediction`` (recognised activity) and ``alert`` (at the
    second it was raised), then ``end`` once the replayed clock reaches ``end``.
    """
    if end <= start:
        raise HTTPException(status_code=422, detail="end must be after start")
    sc = store.scenario(home, scenario)
    if only:
        keep = set(only)
        sc = {**sc,
              "events": sc["events"] if "event" in keep else [],
              "predictions": sc["predictions"] if "prediction" in keep else [],
              "alerts": sc["alerts"] if "alert" in keep else []}
        tick = tick if "clock" in keep else 0
    return StreamingResponse(stream.sse(sc, speed, start, end, tick),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
