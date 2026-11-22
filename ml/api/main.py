"""HTTP routes of the AmbiLiving backend (decision D16).

Interactive documentation is served at ``/docs`` while the server runs.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from har.data import DATASETS

from . import live, store, stream

app = FastAPI(
    title="AmbiLiving API",
    version="0.1.0",
    description="Activity recognition, routine deviations and live replay for the "
                "AmbiLiving caregiver dashboard.",
)

# The Next.js dev server; override with a comma-separated AMBILIVING_CORS.
_origins = os.environ.get("AMBILIVING_CORS", "http://localhost:3000,http://127.0.0.1:3000")
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in _origins.split(",")],
                   allow_methods=["GET", "POST"], allow_headers=["*"])


@app.exception_handler(store.NotFound)
async def _not_found(_: Request, exc: store.NotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


# --------------------------------------------------------------------------- homes

@app.get("/health", tags=["service"])
def health():
    return {"status": "ok", "homes": list(DATASETS)}


@app.get("/homes", tags=["homes"])
def homes():
    """The homes the backend knows and whether their live model is available."""
    return [{"id": h, "model": live.model_info(h)} for h in DATASETS]


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
