"""Routine-deviation detection on an activity stream (decisions D12-D14).

The goal is not generic anomaly detection. We learn *this resident's own routine*
from their observation days and report how a day departs from it, as observed vs
expected for this person. ``RoutineModel`` models these aspects of the routine:

=================  =====================================================  ==============
aspect             score                                                  deviation
=================  =====================================================  ==============
daily activities   -log P(not yet happened by now)  (first-occurrence      missed
                   survival over the observation days)
duration           robust z of log duration                               prolonged
time of day        surprise under a smoothed 48-bin time density          unusual_time
daily count        running count z-score                                  frequency
order              -log P(activity | previous activity)                   unusual_order
day timeline       occupancy surprise over 2-hour blocks, minus its        timeline
                   expected value
quiet spells       silence / usual long silence for the current activity  inactivity
evolution          rolling 7-day mean of first-occurrence time / count     drift
                   vs the observation period (``RoutineDrift``)
=================  =====================================================  ==============

``GenericAD`` is the generic anomaly-detection **baseline**: an MLP autoencoder that
flags episodes it reconstructs poorly (after Fahad & Tahir, 2020). It has no notion
of absence, order, day structure or drift.

Thresholds are calibrated on the observation period to a budget of alerts per
normal day. Every alert carries a caregiver-readable record in the dashboard's
``AnomalyRecord`` shape (title / observed / expected / reason / severity).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.neural_network import MLPRegressor

AWAY = {"Leave_Home"}
BATHROOM = {"Bed_to_Toilet", "Master_Bathroom", "Guest_Bathroom"}
MEDS = {"Morning_Meds", "Eve_Meds"}
NONE = "No_recognised_activity"
BINS = 48  # half-hour time-of-day bins
BLOCK = 4  # bins per timeline block (2 h)
MIN_EPISODES = 8
DAILY = 0.5  # activities present on at least this share of days are tracked for missed/drift
GAP_MIN = 10.0  # minutes; shorter silences are never inactivity candidates
DAY_HOURS = (7.0, 20.0)  # inactivity is only checked for silences starting in this range
GRID = np.arange(0, 24 * 12 + 1) / 12  # 5-minute grid for first-occurrence survival
DAILY_KINDS = ["missed", "prolonged", "unusual_time", "frequency", "unusual_order", "timeline",
               "inactivity"]


@dataclass
class DayData:
    key: int  # variant id for monitoring days, negative for observation days
    day: pd.Timestamp
    times: np.ndarray  # datetime64[ns] sensor events of the day (real time)
    eps: pd.DataFrame  # activity, start, end (real time), sorted by start


@dataclass
class Alert:
    key: int
    kind: str
    activity: str
    time: pd.Timestamp  # when a live system would raise it
    score: float
    record: dict = field(default_factory=dict)


def _minutes(td) -> np.ndarray:
    return np.asarray(td, dtype="timedelta64[ns]").astype(np.float64) / 60e9


def _hour(ts) -> np.ndarray:
    ts = pd.DatetimeIndex(ts)
    return (ts.hour + ts.minute / 60 + ts.second / 3600).to_numpy(dtype=float)


def nice(act: str) -> str:
    return act.replace("_", " ").replace("Rm", "room").lower()


def _clock(h: float) -> str:
    m = int(round(h * 60)) % (24 * 60)
    return f"{m // 60:02d}:{m % 60:02d}"


def _fmt_min(m: float) -> str:
    return f"{m / 60:.1f} h" if m >= 90 else f"{max(m, 1):.0f} min"


def _states(eps: pd.DataFrame, day: pd.Timestamp) -> list[str]:
    """Activity going on at the middle of each half-hour bin (latest started wins)."""
    st = eps["start"].to_numpy()
    en = eps["end"].to_numpy()
    acts = eps["activity"].to_numpy()
    out = []
    for b in range(BINS):
        t = (day + pd.Timedelta(minutes=30 * b + 15)).to_datetime64()
        j = int(np.searchsorted(st, t, side="right")) - 1
        state = NONE
        for k in range(j, max(j - 6, -1), -1):
            if en[k] >= t:
                state = acts[k]
                break
        out.append(state)
    return out


# --------------------------------------------------------------------------- routine model

class RoutineModel:
    """This resident's routine, learned from the observation days of one stream."""

    name = "routine"

    def fit(self, days: list[DayData]) -> "RoutineModel":
        n = len(days)
        self.n = n
        eps = pd.concat([d.eps for d in days], ignore_index=True)
        dur = np.log(_minutes(eps["end"] - eps["start"]) + 0.1)
        hrs = _hour(eps["start"])
        acts = eps["activity"].to_numpy()

        # duration and time of day
        self.dur, self.dens, self.span = {}, {}, {}
        k = np.exp(-0.5 * (np.arange(-6, 7) / 2.0) ** 2)
        for act in np.unique(acts):
            m = acts == act
            if m.sum() < MIN_EPISODES:
                continue
            med = float(np.median(dur[m]))
            self.dur[act] = (med, 1.4826 * float(np.median(np.abs(dur[m] - med))) + 0.25)
            h = np.bincount((hrs[m] * BINS / 24).astype(int) % BINS, minlength=BINS).astype(float)
            sm = sum(np.roll(h, s) * w for s, w in zip(range(-6, 7), k))
            self.dens[act] = (sm + 0.05) / (sm + 0.05).sum()
            self.span[act] = (float(np.quantile(hrs[m], 0.1)), float(np.quantile(hrs[m], 0.9)))

        # daily counts and first occurrences
        counts, first = {}, {}
        for i, d in enumerate(days):
            for act, grp in d.eps.groupby("activity"):
                counts[act] = counts.get(act, 0) + len(grp)
                first.setdefault(act, np.full(n, np.inf))[i] = _hour(grp["start"].iloc[:1])[0]
        self.mu = {a: c / n for a, c in counts.items()}
        self.p_day = {a: float(np.isfinite(f).mean()) for a, f in first.items()}
        self.first = {a: f for a, f in first.items() if self.p_day[a] >= DAILY}
        # S(h) = P(first occurrence later than h, or none): a smoothed skip probability plus
        # a normal curve over the usual first-occurrence time. A parametric tail keeps the
        # score continuous, so "a little later than ever seen" and "hours later / not at
        # all" get different scores even with few observation days.
        self.surv = {}
        for a, f in self.first.items():
            ff = f[np.isfinite(f)]
            p_skip = ((~np.isfinite(f)).sum() + 0.5) / (n + 1)
            mu, sd = float(ff.mean()), max(float(ff.std()), 0.25)
            self.surv[a] = p_skip + (1 - p_skip) * norm.sf((GRID - mu) / sd)

        # order: first-order transitions between consecutive different activities
        self.trans: dict[str, dict[str, int]] = {}
        for d in days:
            seq = d.eps["activity"].tolist()
            for a, b in zip(seq, seq[1:]):
                if a != b:
                    row = self.trans.setdefault(a, {})
                    row[b] = row.get(b, 0) + 1
        self.n_acts = max(len(set(acts)), 2)

        # day timeline: occupancy of each state in each half-hour bin
        occ: dict[str, np.ndarray] = {}
        for d in days:
            for b, s in enumerate(_states(d.eps, d.day)):
                occ.setdefault(s, np.zeros(BINS))[b] += 1
        self.states = sorted(occ)
        M = np.array([occ[s] for s in self.states]) + 0.2
        self.occ = M / M.sum(0, keepdims=True)
        self.entropy = -(self.occ * np.log(self.occ)).sum(0)  # expected surprise per bin
        self.unseen = float(-np.log(0.2 / (n + 0.2 * (len(self.states) + 1))))

        # quiet spells relative to the current activity
        gaps: dict[str, list[float]] = {}
        for d in days:
            for _, m_, cur in self._gaps(d):
                gaps.setdefault(cur, []).append(m_)
        every = [x for v in gaps.values() for x in v]
        self.gap_global = float(np.quantile(every, 0.95)) if every else 60.0
        self.gap_scale = {a: float(np.quantile(v, 0.95)) if len(v) >= 15 else self.gap_global
                          for a, v in gaps.items()}
        return self

    # ---- helpers
    @staticmethod
    def _gaps(d: DayData):
        """(start, minutes, current activity) for at-home daytime silences >= GAP_MIN."""
        t = d.times
        if len(t) < 2:
            return []
        g = _minutes(np.diff(t))
        starts = d.eps["start"].to_numpy()
        out = []
        for i in np.where(g >= GAP_MIN)[0]:
            s = pd.Timestamp(t[i])
            if not DAY_HOURS[0] <= s.hour + s.minute / 60 < DAY_HOURS[1]:
                continue
            j = int(np.searchsorted(starts, t[i], side="right")) - 1
            cur = d.eps["activity"].iloc[j] if j >= 0 else NONE
            if cur not in AWAY:
                out.append((s, float(g[i]), cur))
        return out

    def _p_next(self, a: str, b: str) -> float:
        row = self.trans.get(a, {})
        return (row.get(b, 0) + 0.1) / (sum(row.values()) + 0.1 * self.n_acts)

    def _expected_states(self, bins) -> list[str]:
        p = self.occ[:, bins].mean(1)
        top = np.argsort(p)[::-1][:2]
        return [self.states[i] for i in top if p[i] >= 0.15] or [self.states[top[0]]]

    # ---- scores
    def candidates(self, d: DayData) -> list[dict]:
        out = []
        running: dict[str, int] = {}
        prev = None
        for _, e in d.eps.iterrows():
            act, start = e["activity"], pd.Timestamp(e["start"])
            running[act] = running.get(act, 0) + 1
            if act in self.dur:
                med, sc = self.dur[act]
                z = (np.log(_minutes(e["end"] - e["start"]) + 0.1) - med) / sc
                out.append(dict(kind="prolonged", act=act, score=float(z), e=e))
                b = int(_hour([start])[0] * BINS / 24) % BINS
                out.append(dict(kind="unusual_time", act=act, e=e,
                                score=float(-np.log(self.dens[act][b] * BINS))))
            mu = self.mu.get(act, 0.0)
            out.append(dict(kind="frequency", act=act, e=e, n=running[act],
                            score=float((running[act] - mu) / np.sqrt(mu + 1))))
            if (prev is not None and prev != act
                    and sum(self.trans.get(prev, {}).values()) >= MIN_EPISODES):
                out.append(dict(kind="unusual_order", act=act, prev=prev, e=e,
                                score=float(-np.log(self._p_next(prev, act)))))
            prev = act
        # missed: surprise that a daily activity has still not happened
        for act, S in self.surv.items():
            st = d.eps.loc[d.eps["activity"] == act, "start"]
            h_obs = _hour(st.iloc[:1])[0] if len(st) else 24.0
            before = GRID < h_obs
            score = float(-np.log(S[before].min())) if before.any() else 0.0
            out.append(dict(kind="missed", act=act, score=score, h_obs=h_obs, S=S))
        # timeline: 2-hour blocks that look unlike the usual day at that time
        states = _states(d.eps, d.day)
        sidx = {s: i for i, s in enumerate(self.states)}
        for j in range(BINS // BLOCK):
            bins = range(j * BLOCK, (j + 1) * BLOCK)
            obs = [states[b] for b in bins]
            sur = [(-np.log(self.occ[sidx[states[b]], b]) if states[b] in sidx else self.unseen)
                   - self.entropy[b] for b in bins]
            out.append(dict(kind="timeline", act=max(set(obs), key=obs.count),
                            score=float(np.mean(sur)), block=j, obs=obs,
                            time=d.day + pd.Timedelta(hours=2 * (j + 1))))
        # inactivity
        for s, m, cur in self._gaps(d):
            out.append(dict(kind="inactivity", act=cur, start=s, minutes=m,
                            score=m / self.gap_scale.get(cur, self.gap_global)))
        return out

    @staticmethod
    def calib_items(cands) -> dict[str, list[float]]:
        """Scores that count towards the budget (missed/frequency: one per activity-day)."""
        items: dict[str, list[float]] = {k: [] for k in DAILY_KINDS}
        best: dict[tuple, float] = {}
        for c in cands:
            if c["kind"] in ("missed", "frequency"):
                key = (c["kind"], c["act"])
                best[key] = max(best.get(key, -np.inf), c["score"])
            else:
                items[c["kind"]].append(c["score"])
        for (kind, _), s in best.items():
            items[kind].append(s)
        return items

    # ---- alerts
    def alerts(self, d: DayData, theta: dict[str, float]) -> list[Alert]:
        out, fired = [], set()
        last_block = -2
        for c in self.candidates(d):
            kind, act, s = c["kind"], c["act"], c["score"]
            if s <= theta[kind]:
                continue
            if kind == "missed":
                h = GRID[(GRID < c["h_obs"]) & (-np.log(c["S"]) > theta[kind])]
                if not len(h):
                    continue
                f = self.first[act]
                usual = float(np.median(f[np.isfinite(f)]))
                out.append(Alert(d.key, kind, act, d.day + pd.Timedelta(hours=float(h[0])), s, dict(
                    title=f"No {nice(act)} yet today",
                    observed=f"No {nice(act)} by {_clock(h[0])}",
                    expected=f"Happens on {self.p_day[act]:.0%} of days, usually first around "
                             f"{_clock(usual)}",
                    reason="A daily part of the routine has not happened by the time it "
                           "nearly always has.",
                    severity="high" if act in MEDS else "medium")))
            elif kind == "timeline":
                merged = c["block"] == last_block + 1  # one alert per run of unusual blocks
                last_block = c["block"]
                if merged:
                    continue
                bins = list(range(c["block"] * BLOCK, (c["block"] + 1) * BLOCK))
                obs = sorted(set(c["obs"]), key=c["obs"].count, reverse=True)[:2]
                exp = self._expected_states(bins)
                a0 = 2 * c["block"]
                out.append(Alert(d.key, kind, act, c["time"], s, dict(
                    title="Part of the day looks different from usual",
                    observed=f"{_clock(a0)}–{_clock(a0 + 2)}: mostly "
                             + " and ".join(nice(x) for x in obs),
                    expected="Usually " + " or ".join(nice(x) for x in exp) + " at this time",
                    reason="The pattern of activities in this part of the day does not match "
                           "the resident's usual day.",
                    severity="low")))
            elif kind == "inactivity":
                scale = self.gap_scale.get(act, self.gap_global)
                out.append(Alert(d.key, kind, act,
                                 c["start"] + pd.Timedelta(minutes=theta[kind] * scale), s, dict(
                    title="Quiet for much longer than usual",
                    observed=f"No sensor activity for {_fmt_min(c['minutes'])} from "
                             f"{c['start']:%H:%M} (last activity: {nice(act)})",
                    expected=f"Quiet spells during {nice(act)} usually last under "
                             f"{_fmt_min(scale)}",
                    reason="A long silence while the resident is at home can mean a fall or "
                           "illness.",
                    severity="high")))
            else:
                out += self._episode_alert(d, c, theta, fired)
        return out

    def _episode_alert(self, d, c, theta, fired) -> list[Alert]:
        kind, act, s, e = c["kind"], c["act"], c["score"], c["e"]
        start = pd.Timestamp(e["start"])
        if kind == "prolonged":
            med, sc = self.dur[act]
            lim = float(np.exp(med + theta[kind] * sc) - 0.1)
            m = float(_minutes(e["end"] - e["start"]))
            lo, hi = np.exp(med - sc) - 0.1, np.exp(med + sc) - 0.1
            return [Alert(d.key, kind, act, start + pd.Timedelta(minutes=lim), s, dict(
                title=f"{nice(act).capitalize()} is taking much longer than usual",
                observed=f"{_fmt_min(m)}, started {start:%H:%M}",
                expected=(f"Usually {_fmt_min(max(lo, 0.5))} to {_fmt_min(hi)}" if hi >= 2
                          else "Usually under 2 min"),
                reason=f"Much longer than this resident's usual {nice(act)}; could indicate "
                       "a fall or illness.",
                severity="high" if act in BATHROOM else "medium"))]
        if kind == "unusual_time":
            a, b = self.span[act]
            night = start.hour < 5
            return [Alert(d.key, kind, act, start, s, dict(
                title=f"{nice(act).capitalize()} at an unusual time",
                observed=f"{nice(act).capitalize()} at {start:%H:%M}",
                expected=f"Usually between {_clock(a)} and {_clock(b)}",
                reason="This resident rarely does this at this hour"
                       + (" — night-time activity can be a sign of confusion." if night else "."),
                severity="high" if night and act in AWAY else "medium"))]
        if kind == "frequency":
            if act in fired:
                return []
            fired.add(act)
            return [Alert(d.key, kind, act, start, s, dict(
                title=f"More {nice(act)} than usual",
                observed=f"{nice(act).capitalize()} {c['n']} times today (by {start:%H:%M})",
                expected=f"Usually about {self.mu.get(act, 0):.1f} per day",
                reason="A sudden change in how often something happens"
                       + (" (such as night-time toilet trips) can signal infection or "
                          "restlessness." if act in BATHROOM else " can signal a change in health."),
                severity="medium" if act in BATHROOM else "low"))]
        row = self.trans.get(c["prev"], {})
        top = sorted(row, key=row.get, reverse=True)[:2]
        return [Alert(d.key, "unusual_order", act, start, s, dict(
            title="Unusual order of activities",
            observed=f"{nice(act).capitalize()} right after {nice(c['prev'])} ({start:%H:%M})",
            expected=f"After {nice(c['prev'])}, usually " + " or ".join(nice(x) for x in top),
            reason="The resident does not normally go from one to the other.",
            severity="low"))]


class RoutineDrift:
    """Multi-day drift: rolling-window mean of first-occurrence time and daily count."""

    def fit(self, days: list[DayData]) -> "RoutineDrift":
        n = len(days)
        first, counts = {}, {}
        for i, d in enumerate(days):
            for act, grp in d.eps.groupby("activity"):
                first.setdefault(act, np.full(n, np.nan))[i] = _hour(grp["start"].iloc[:1])[0]
                counts.setdefault(act, np.zeros(n))[i] = len(grp)
        self.stats = {}
        for act, f in first.items():
            if np.isfinite(f).mean() < DAILY:
                continue
            ff = f[np.isfinite(f)]
            self.stats[act] = (float(ff.mean()), max(float(ff.std()), 0.25),
                               float(counts[act].mean()), max(float(counts[act].std()), 0.5))
        return self

    def scores(self, window: list[DayData]) -> list[tuple]:
        out = []
        for act, (mt, st, mc, sc) in self.stats.items():
            f = [_hour(d.eps.loc[d.eps["activity"] == act, "start"].iloc[:1])[0]
                 for d in window if (d.eps["activity"] == act).any()]
            c = [int((d.eps["activity"] == act).sum()) for d in window]
            if len(f) >= 3:
                out.append((act, "time", (np.mean(f) - mt) / (st / np.sqrt(len(f))),
                            float(np.mean(f)), mt, len(f)))
            out.append((act, "count", (np.mean(c) - mc) / (sc / np.sqrt(len(c))),
                        float(np.mean(c)), mc, len(c)))
        return out

    def alerts(self, window: list[DayData], theta: float) -> list[Alert]:
        last = window[-1]
        out = []
        for act, what, z, now, usual, k in self.scores(window):
            if abs(z) <= theta:
                continue
            if what == "time":
                rec = dict(title=f"{nice(act).capitalize()} has been happening "
                                 f"{'later' if z > 0 else 'earlier'} than usual",
                           observed=f"First {nice(act)} around {_clock(now)} on average over "
                                    f"the last {k} days",
                           expected=f"Usually first around {_clock(usual)}",
                           reason="A gradual shift in the daily routine; worth checking how the "
                                  "resident is sleeping and eating.",
                           severity="medium")
            else:
                rec = dict(title=f"{'More' if z > 0 else 'Less'} {nice(act)} than usual "
                                 "this week",
                           observed=f"{now:.1f} times a day over the last {k} days",
                           expected=f"Usually {usual:.1f} times a day",
                           reason="A gradual change in how often part of the routine happens.",
                           severity="medium" if act in BATHROOM | MEDS else "low")
            out.append(Alert(last.key, "drift", act,
                             last.day + pd.Timedelta(hours=23, minutes=59), float(abs(z)),
                             rec | {"what": what}))
        return out


def calibrate_drift(days: list[DayData], size: int) -> tuple[list[float], int]:
    """Leave-one-week-out drift scores on the observation period (one window per day)."""
    pool, n_win = [], 0
    for j in range(0, max(len(days) - size + 1, 0)):
        rest = days[:j] + days[j + size:]
        if len(rest) < 3:
            continue
        dr = RoutineDrift().fit(rest)
        best: dict[tuple, float] = {}
        for act, what, z, *_ in dr.scores(days[j:j + size]):
            best[(act, what)] = max(best.get((act, what), 0.0), abs(z))
        pool += list(best.values())
        n_win += 1
    return pool, n_win


# --------------------------------------------------------------------------- generic baseline

class GenericAD:
    """Generic anomaly-detection baseline: MLP autoencoder over episode features."""

    name = "generic"

    def __init__(self, classes: list[str], seed: int = 0):
        self.classes = classes
        self.cidx = {c: i for i, c in enumerate(classes)}
        self.seed = seed

    def _features(self, d: DayData) -> tuple[np.ndarray, list]:
        rows, eps = [], []
        last_end: dict[str, pd.Timestamp] = {}
        count: dict[str, int] = {}
        for _, e in d.eps.iterrows():
            act = e["activity"]
            count[act] = count.get(act, 0) + 1
            since = (e["start"] - last_end.get(act, d.day)).total_seconds() / 3600
            h = _hour([e["start"]])[0]
            one = np.zeros(len(self.classes))
            one[self.cidx[act]] = 1
            rows.append(np.concatenate([one, [np.sin(2 * np.pi * h / 24), np.cos(2 * np.pi * h / 24),
                                              np.log(_minutes(e["end"] - e["start"]) + 0.1),
                                              np.log1p(count[act]), np.log1p(max(since, 0))]]))
            last_end[act] = e["end"]
            eps.append(e)
        X = np.array(rows) if rows else np.zeros((0, len(self.classes) + 5))
        return X, eps

    def _fit_model(self, X):
        k = len(self.classes)
        mu, sd = X[:, k:].mean(0), X[:, k:].std(0) + 1e-6
        Z = X.copy()
        Z[:, k:] = (Z[:, k:] - mu) / sd
        net = MLPRegressor(hidden_layer_sizes=(32, 8, 32), alpha=1e-3, max_iter=600,
                           random_state=self.seed)
        net.fit(Z, Z)
        return net, mu, sd

    def _score(self, model, X):
        net, mu, sd = model
        k = len(self.classes)
        Z = X.copy()
        Z[:, k:] = (Z[:, k:] - mu) / sd
        return ((net.predict(Z) - Z) ** 2).mean(1)

    def fit(self, days: list[DayData]) -> "GenericAD":
        self.model = self._fit_model(np.vstack([self._features(d)[0] for d in days]))
        return self

    def oof_scores(self, days: list[DayData], folds: int = 5) -> list[float]:
        out = []
        groups = np.arange(len(days)) % folds
        for f in range(folds):
            tr = [d for d, g in zip(days, groups) if g != f]
            m = self._fit_model(np.vstack([self._features(d)[0] for d in tr]))
            for d, g in zip(days, groups):
                if g == f:
                    X, _ = self._features(d)
                    if len(X):
                        out += list(self._score(m, X))
        return out

    def alerts(self, d: DayData, theta: float) -> list[Alert]:
        X, eps = self._features(d)
        if not len(X):
            return []
        s = self._score(self.model, X)
        out = []
        for i in np.where(s > theta)[0]:
            e = eps[i]
            act = e["activity"]
            st = pd.Timestamp(e["start"])
            out.append(Alert(d.key, "outlier", act, pd.Timestamp(e["end"]), float(s[i]), dict(
                title=f"Unusual {nice(act)}",
                observed=f"{nice(act).capitalize()} at {st:%H:%M} "
                         f"({_fmt_min(float(_minutes(e['end'] - e['start'])))})",
                expected="(none: generic outlier score)",
                reason=f"Reconstruction error {s[i]:.2f} above the threshold.",
                severity="low")))
        return out


# --------------------------------------------------------------------------- calibration

def budget_threshold(scores: list[float], n_days: int, per_day: float) -> float:
    """Threshold so that ``scores`` above it average ``per_day`` alerts per day."""
    if not scores:
        return np.inf
    s = np.sort(np.asarray(scores))[::-1]
    k = int(np.floor(per_day * n_days))
    return float(s[k]) if k < len(s) else float(s[-1]) - 1e-9


def calibrate_routine(days: list[DayData]) -> dict[str, list[float]]:
    """Leave-one-day-out scores on the observation period, per routine aspect."""
    pool: dict[str, list[float]] = {k: [] for k in DAILY_KINDS}
    for i, d in enumerate(days):
        m = RoutineModel().fit(days[:i] + days[i + 1:])
        for k, v in RoutineModel.calib_items(m.candidates(d)).items():
            pool[k] += v
    return pool


# --------------------------------------------------------------------------- evaluation

def match(alerts: list[Alert], kind: str, target: str, a_start, a_end) -> Alert | None:
    """First alert that explains an injected single-day deviation (D13 matching rule)."""
    lo, hi = a_start - pd.Timedelta(minutes=30), a_end + pd.Timedelta(minutes=60)
    for a in sorted(alerts, key=lambda a: a.time):
        if kind == "missed":
            if a.kind == "missed" and a.activity == target:
                return a
        elif lo <= a.time <= hi:
            return a
    return None
