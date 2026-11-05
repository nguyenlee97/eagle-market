# eagle-market

> **Project Eagle** | Financial Systems — Wall Street · Trading · News · Casino | v1.0

All in-game financial and media systems for Project Eagle: NYSE-style stock exchange, historical market data, newspaper, and online casino.

## Repository Contents

```
eagle_wallstreet_floor.py          ← Wall Street 3D exchange floor (live 60FPS displays)
eagle_historical_data.py           ← OHLCV historical data (35 stocks, 16 crypto, 2010-2025)
eagle_market_regimes_2010_2025.py  ← Market regime engine + live candle stepping
eagle_news_en.py                   ← Eagle Times content (5,844 days, 35,064 articles)
eagle_news_archive_2010_2025.py    ← Historical news archive 2010-2025
eagle_news_live_wire.py            ← Live journalism module (real-time market → news)
eagle_stake_casino.py              ← EagleStake casino engine
eagle_stake_games.py               ← 8 casino games (Sicbo, Slots, Crash, Mines, Plinko...)
```

## Eagle Wall Street (Phase 2)

NYSE 18 Broad Street-inspired interior (`36m × 44m × 16.8m`, Model ID 15100):

- **5 Live 3D Displays** via Shared Memory `Local\EagleWallStreetSHM` (9.4 MB):
  - `ws_ticker_ring` 2048×128 — LED ticker belt 360°, 148px/s
  - `ws_board_main` 1024×512 — Jumbotron EAGLE-51 index + heatmap
  - `ws_board_chart_a/b` 1024×512 — OHLCV candlestick walls + L2 order book
  - `ws_post_screen` 1024×512 — Counter screen + GPT-5-nano Broker Wire
- **18 Female NPCs** (ID 49448–49465): 8 interactive Brokers `[E]` + 10 Traders
- **AI advisory** via `gpt-5-nano` + live BUY/SELL/LONG/SHORT order placement
- **4 City Teleport Gates**: LS, SF, Chicago, Liberty City

## Historical Market Data

```python
from eagle_historical_data import get_historical_ohlcv_window
from eagle_market_regimes_2010_2025 import step_live_market_candle

# 35 stocks: Commodities, US Mega-Cap, AI/Semis, ACG/Gaming, GTA/Teyvat Lore
# 16 crypto: BTC, ETH, XMR, NMC, PPC + more (curves from 2010)
data = get_historical_ohlcv_window("NVDA", start="2020-01-01", days=90)
```

## The Eagle Times

- **5,844 days** of content (Jan 1, 2010 → Dec 31, 2025)
- **35,064 articles** across 6 sections
- 389 historical milestones + 1,152 monthly chronicles
- 24 dedicated reporters, live market integration via `eagle_news_live_wire.py`
- In-game scroll with red vertical scrollbar

## EagleStake Casino

8 Stake-Original games with `Provably Fair HMAC-SHA256`:

| Game | Type | RTP |
|------|------|-----|
| Sicbo MD5 + Pot | Dice | 97.2% |
| Neon Slots 3×5 | Slots + Free Spins | 96.5% |
| Crash | Multiplier (up to 1000x) | 97.0% |
| Diamond Mines 5×5 | Mine sweeper | 97.5% |
| Plinko 1000x | Ball drop | 96.0% |
| Stake Dice | HiLo | 99.0% |
| Xóc Đĩa | Vietnamese Dice | 97.8% |
| Blackjack 21 | Cards | 99.2% |

VIP Tiers: Bronze → Silver → Gold → Platinum → Diamond | Rakeback 1% | Progressive Mega Pot

Wallet sync: GTA SA cash `0x00B7CE50` — real in-game money.

## Jira
- [SCRUM-169](https://nguyennguyenle997.atlassian.net/browse/SCRUM-169) — Wall Street Phase 2
- [SCRUM-166](https://nguyennguyenle997.atlassian.net/browse/SCRUM-166) — Trading Historical Depth
- [SCRUM-167](https://nguyennguyenle997.atlassian.net/browse/SCRUM-167) — Eagle Times Expansion
- [SCRUM-168](https://nguyennguyenle997.atlassian.net/browse/SCRUM-168) — EagleStake Casino
