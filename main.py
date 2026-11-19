"""Forecast GTA VI PS5 trophy earn rates on Exophase at a case's target.

Two regimes, chosen by what the case's history shows:

* Frozen page. Every read is identical and the tracked pool never moved:
  the page is a stale snapshot of a tiny early pool. Exophase refreshes
  such a page in jumps, and a broader pool dilutes almost every rate, so
  the forecast prices in a dilution drop (median = last rate x 0.22) with
  a wide logit spread instead of pretending the rate stands still.

* Moving page. Fit, per trophy, a weighted least-squares line of
  logit(rate) against ln(1 + hours since release) over the last 24 hours
  of reads (weights = time gaps, so dense read clusters do not dominate),
  then read the line at the target with the slope damped to 70% beyond
  the last read, because week-one trajectories bend as the player pool
  saturates. The spread combines the fit's residual scale with a
  slope-uncertainty term and a floor, all on the logit scale.

Deterministic: closed-form fits only, no randomness, no clock, no network.
"""

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]

# Frozen-page regime.
STALE_K = 0.22          # dilution factor priced into the median
STALE_S = 0.5           # logit spread at a 90-minute horizon
# Moving-page regime.
WINDOW_H = 24.0         # fit window before the checkpoint
DAMP = 0.7              # slope damping beyond the last read
CAP_MOVE = 2.6          # max |median logit move| away from the last rate
CD = 0.2                # slope-uncertainty weight in the spread
SFLOOR = 0.15           # spread floor, logit units
SMAX = 1.5              # spread cap, logit units


def clamp_pct(x):
    return min(99.99, max(0.01, x))


def logit(pct):
    p = clamp_pct(pct)
    return math.log(p / (100.0 - p))


def inv_logit(lg):
    return 100.0 / (1.0 + math.exp(-lg))


def round4(x):
    scaled = x * 10000.0
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1.0
    value = whole / 10000.0
    return int(value) if float(value).is_integer() else value


def hours(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() / 3600.0


def wlsq(xs, ys, ws):
    """Weighted least squares y ~ a + b*x; returns (a, b, residual sd)."""
    sw = sum(ws)
    if sw <= 0 or not xs:
        return 0.0, 0.0, 0.3
    if len(xs) == 1:
        return ys[0], 0.0, 0.3
    mx = sum(w * x for x, w in zip(xs, ws)) / sw
    my = sum(w * y for y, w in zip(ys, ws)) / sw
    sxx = sum(w * (x - mx) ** 2 for x, w in zip(xs, ws))
    sxy = sum(w * (x - mx) * (y - my) for x, y, w in zip(xs, ys, ws))
    b = sxy / sxx if sxx > 1e-12 else 0.0
    a = my - b * mx
    var = sum(w * (y - (a + b * x)) ** 2 for x, y, w in zip(xs, ys, ws)) / sw
    return a, b, math.sqrt(max(var, 1e-6))


def last_rates(hist, n):
    out = []
    for i in range(n):
        r = 0.0
        for h in reversed(hist):
            if h["rates"][i] is not None:
                r = h["rates"][i]
                break
        out.append(r)
    return out


def page_moved(hist, n):
    if len({h["players_tracked"] for h in hist}) > 1:
        return True
    for i in range(n):
        if len({h["rates"][i] for h in hist if h["rates"][i] is not None}) > 1:
            return True
    return False


def frozen_rows(case, lasts):
    horizon = case["horizon_minutes"]
    s = min(1.2, max(0.4, STALE_S * math.sqrt(horizon / 90.0)))
    rows = []
    for t, r in zip(case["trophies"], lasts):
        med = logit(99.9) if r >= 99.99 else logit(r * STALE_K)
        rows.append({"id": t["id"], "q": [round4(inv_logit(med + z * s)) for z in Z]})
    return rows


def release_anchor(case):
    """Hours (epoch) of the release day's 00:00 UTC: from the case's game
    block when it names a release date, else the first read's UTC date."""
    try:
        return hours(case["game"]["release_date"] + "T00:00:00Z")
    except Exception:
        first = hours(case["history"][0]["slot"])
        return math.floor(first / 24.0) * 24.0


def moving_rows(case, lasts):
    hist = case["history"]
    trophies = case["trophies"]
    n = len(trophies)
    anchor = release_anchor(case)
    times = [hours(h["slot"]) - anchor for h in hist]
    gaps = [1.0] + [max(0.02, times[j] - times[j - 1]) for j in range(1, len(times))]
    start = 0
    for j, t in enumerate(times):
        if t >= times[-1] - WINDOW_H:
            start = j
            break
    start = min(start, max(0, len(times) - 12))
    hist = hist[start:]
    times = times[start:]
    gaps = gaps[start:]
    xs_all = [math.log(1.0 + max(0.0, t)) for t in times]
    x_last = xs_all[-1]
    x_tgt = math.log(1.0 + max(0.0, hours(case["target"]) - anchor))
    fits = []
    for i in range(n):
        xs, ys, ws = [], [], []
        for j, h in enumerate(hist):
            r = h["rates"][i]
            if r is None:
                continue
            xs.append(xs_all[j])
            ys.append(logit(r))
            ws.append(gaps[j])
        fits.append(wlsq(xs, ys, ws))
    med_sd = sorted(f[2] for f in fits)[n // 2]
    rows = []
    for t, (a, b, sd), r in zip(trophies, fits, lasts):
        med = (a + b * x_last) + DAMP * b * (x_tgt - x_last)
        lg_last = logit(r)
        med = min(max(med, lg_last - CAP_MOVE), lg_last + CAP_MOVE)
        resid = max(sd, 0.35 * med_sd)
        spread = math.sqrt(resid ** 2 + (CD * abs(b) * (x_tgt - x_last)) ** 2 + SFLOOR ** 2)
        spread = min(SMAX, spread)
        if r >= 99.99:
            med, spread = logit(99.9), min(spread, 0.4)
        rows.append({"id": t["id"], "q": [round4(inv_logit(med + z * spread)) for z in Z]})
    return rows


def forecast_case(case):
    hist = case["history"]
    n = len(case["trophies"])
    lasts = last_rates(hist, n)
    if not hist or not page_moved(hist, n):
        return {"trophies": frozen_rows(case, lasts)}
    return {"trophies": moving_rows(case, lasts)}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        out = forecast_case(case)
        (OUTPUT_DIR / (path.stem + ".out")).write_text(
            json.dumps(out, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
