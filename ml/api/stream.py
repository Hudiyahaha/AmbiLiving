"""Replay a recorded day as a live feed (ROADMAP 4.2).

A D17 scenario (``har.replay``) is turned into one timeline: sensor events, the
live recogniser's predictions and alerts (at the minute they were raised, never
earlier), in timestamp order. It is sent as server-sent events, paced so that
``speed`` seconds of the day pass per real second.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

# Order of items that share a second: the clock, what was sensed, what was
# recognised, then what was raised from it.
_CLOCK, _EVENT, _PREDICTION, _ALERT = 0, 1, 2, 3


def timeline(sc: dict, start: int = 0, end: int = 86400,
             tick: int = 60) -> list[tuple[int, int, dict]]:
    """(second of day, order, payload) for every item with start <= second < end.

    With ``tick`` > 0 a ``clock`` item marks every ``tick`` seconds of the day, so a
    client sees time pass during a silence (when inactivity alerts happen).
    """
    sensors, states, labels = sc["sensors"], sc["states"], sc["labels"]
    items = [(t, _EVENT, {"type": "event", "t": t, "sensor": sensors[s], "state": states[v]})
             for t, s, v in sc["events"]]
    if tick > 0:
        first = -(-start // tick) * tick  # first multiple of tick at or after start
        items += [(t, _CLOCK, {"type": "clock", "t": t}) for t in range(first, end, tick)]
    items += [(t, _PREDICTION, {"type": "prediction", "t": t, "activity": labels[a],
                                "confidence": c})
              for t, a, c in sc["predictions"]]
    items += [(a["raisedAt"], _ALERT, {"type": "alert", "t": a["raisedAt"], **a})
              for a in sc["alerts"]]
    items = [it for it in items if start <= it[0] < end]
    items.sort(key=lambda it: (it[0], it[1]))
    return items


def meta(sc: dict, speed: float, start: int, end: int, n: int) -> dict:
    keep = ("home", "id", "title", "kind", "day", "injected", "typical", "summaryAt")
    return {"type": "start", **{k: sc.get(k) for k in keep},
            "speed": speed, "from": start, "to": end, "items": n}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


async def sse(sc: dict, speed: float, start: int = 0, end: int = 86400,
              tick: int = 60) -> AsyncIterator[str]:
    """Server-sent events for one scenario, paced by ``speed`` (day seconds per real second).

    The stream lasts (end - start) / speed real seconds: ``end`` is sent when the
    replayed clock reaches ``end``, even if nothing happened since the last item.
    """
    now = asyncio.get_running_loop().time
    items = timeline(sc, start, end, tick)
    yield _sse("start", meta(sc, speed, start, end, len(items)))
    t0 = now()

    async def until(t: int) -> None:
        wait = t0 + (t - start) / speed - now()
        if wait > 0:
            await asyncio.sleep(wait)

    for t, _, payload in items:
        await until(t)
        yield _sse(payload["type"], payload)
    await until(end)
    yield _sse("end", {"type": "end", "t": end, "items": len(items)})
