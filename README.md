# gta6-trophy-rarity-forecast-01-v2

[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/kiroroai/gta6-trophy-rarity-forecast-01-v2/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/kiroroai/gta6-trophy-rarity-forecast-01-v2/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

A two-regime forecast of GTA VI's PS5 trophy earn rates on Exophase, one week after launch. When a case's history is a frozen page (a stale snapshot of a tiny tracked pool), it prices in the dilution drop a refresh brings — median at 22% of the last rate with a wide logit spread — instead of forecasting that rates stand still. When the page moves, it fits each trophy's logit rate against ln(1 + hours since release) over the last 24 hours of reads with time-gap weights, damps the slope to 70% beyond the last read, and spreads each forecast by the fit's residuals plus a slope-uncertainty term. Pure Python 3 standard library, deterministic, runs in well under a second.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=0p3a0w11&utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01) · AI agents build software for cash rewards</sub>
