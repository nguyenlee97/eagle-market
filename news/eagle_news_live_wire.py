"""
Live Data Journalism, Multi-Paragraph Editorial Engine & San Andreas Whale Wire
for The Eagle Times (`App 6` on EaglePhone OS v6.3 - Project Eagle Gameplay Lab).

Generates NYT / Bloomberg / Kotaku / The Athletic caliber multi-paragraph articles
across all 5,844 days (01/01/2010 -> 31/12/2025) and all 6 newspaper desks:
  0. world      (WORLD)   : Global Geopolitics, Big Science & Los Santos Maritime Desk
  1. life_net   (CULT)    : Internet Culture, Hardware, Vinewood & Santa Maria Life
  2. anime_game (ACG)     : Anime, Esports, Gaming History & Teyvat Traveler Chronicle
  3. finance    (MARKET)  : Live Wall Street Equities, Gold XAU, Oil WTI & Maze Bank Tape
  4. crypto     (CRYPTO)  : Live 24/7 On-Chain Order Books, Halving Cycles & Venture IOUs
  5. sports     (SPORT)   : Live Matchday Results, Tactical Chalkboard & Venturas Odds

100% RenderWare CFont-safe printable ASCII (zero ~, |, *, @, smart quotes, or em-dashes).
"""

from __future__ import annotations

import datetime
import re
import textwrap
import unicodedata
from typing import Dict, List, Optional, Tuple


MONTH_NAMES_EN = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

WEEKDAY_NAMES_EN = (
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
)

# Strictly <= 46 chars per byline so HUD left column never collides with right scroll indicator
BYLINE_ROSTER_EN: Dict[str, Tuple[str, ...]] = {
    "world": (
        "By Clara Vance - Diplomatic & Port Desk",
        "By Julian Mercer - Global Summit Wire",
        "By Elena Rostova - Science & Grid Desk",
        "By Arthur Pendelton - Foreign Chronicle",
    ),
    "life_net": (
        "By Maya Lin - Santa Maria & Web Trends",
        "By Leo Sterling - Vinewood & Tech Desk",
        "By Chloe Park - San Fierro Digital Beat",
        "By Noah Bennett - Culture & Radio Wire",
    ),
    "anime_game": (
        "By Kenji Sato - Akihabara & Mondstadt",
        "By Sora Takahashi - WIBU-01 & ACG Desk",
        "By Reina Mori - Esports & Teyvat Wire",
        "By Lucas Vance - Open-World & RPG Desk",
    ),
    "finance": (
        "By Evelyn Vance - Wall St & Maze Bank",
        "By Marcus Sterling - Macro & Gold Desk",
        "By Hannah Chen - Semis & Equity Tape",
        "By Victor Hale - Commodities & Yield",
    ),
    "crypto": (
        "By Alexei Volkov - 24/7 On-Chain Wire",
        "By Nadia Kwon - Digital Gold & Custody",
        "By Liam O'Connor - San Fierro Node Desk",
        "By Talia Brooks - Perp & Layer-1 Radar",
    ),
    "sports": (
        "By Mateo Silva - European Tactical Box",
        "By Declan Hughes - Matchday & Odds Wire",
        "By Gianni Moretti - Floodlight Press",
        "By Marcus Cole - Venturas Sportsbook",
    ),
}

BYLINE_ROSTER_VI: Dict[str, Tuple[str, ...]] = {
    "world": ("Ban Quoc Te & Cang Los Santos", "Ban Thoi Su & Khoa Hoc Toan Cau"),
    "life_net": ("Ban Doi Song So & Santa Maria", "Ban Van Hoa Mang & San Fierro"),
    "anime_game": ("Ban Akihabara WIBU-01 & Mondstadt", "Ban Esports & The Gioi Game"),
    "finance": ("Ban Kinh Te Pho Wall & Maze Bank", "Ban Vang XAU & Vi Mo Toan Cau"),
    "crypto": ("Ban Tai San So & On-Chain 24/7", "Ban Blockchain & San Fierro"),
    "sports": ("Ban The Thao Chau Au & NBA", "Ban Binh Luan & Keo Las Venturas"),
}

COMMODITY_SYMS = frozenset({"XAU", "XAG", "WTI", "NGAS", "COPPER", "DIAMOND"})

_CFONT_TRANS = str.maketrans({
    "đ": "d",
    "Đ": "D",
    "\u2013": "-",
    "\u2022": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": "'",
    "\u201d": "'",
    "|": "-",
    "*": "",
})
_RE_TILDE_NUM = re.compile(r"~(?=\$|\d)")
_RE_TILDE_WRAP = re.compile(r"~([^~]+)~")
_RE_WS = re.compile(r"\s+")
_RE_BRACKET_PREFIX = re.compile(r"^\[[^\]]+\]\s*")


def sanitize_cfont_en(text: str) -> str:
    """
    Converts any string into 100% printable RenderWare CFont-safe ASCII:
      - Replaces curly quotes with ' and em/en-dashes/bullets with -
      - Eliminates forbidden GTA SA CFont control characters: ~, |, *, @
      - Strips combining accents without dropping base Latin letters (including đ/Đ)
    """
    if not text:
        return ""
    s = str(text)
    # Ultra-fast path for already clean printable ASCII strings
    if (
        s.isascii()
        and "~" not in s
        and "|" not in s
        and "*" not in s
        and "@" not in s
        and "\n" not in s
        and "\r" not in s
        and "\t" not in s
        and "  " not in s
    ):
        return s.strip()

    if "\u2014" in s:
        s = s.replace("\u2014", " - ")
    if "\u2026" in s:
        s = s.replace("\u2026", "...")
    if "@" in s:
        s = s.replace("@", "at ")
    s = s.translate(_CFONT_TRANS)
    if "~" in s:
        s = _RE_TILDE_NUM.sub("about ", s)
        s = _RE_TILDE_WRAP.sub(r"'\1'", s)
        s = s.replace("~", "-")
    if not s.isascii():
        nfd = unicodedata.normalize("NFD", s)
        s = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn" and 32 <= ord(ch) < 127)
    else:
        s = "".join(ch for ch in s if 32 <= ord(ch) < 127)
    return _RE_WS.sub(" ", s).strip()


def fit_headline_cfont(title: str, width: int = 48, max_chars: int = 90) -> str:
    """Ensures headline is clean CFont ASCII and wraps into at most 2 lines at `width=48`."""
    t = sanitize_cfont_en(title)
    if len(t) <= max_chars and len(textwrap.wrap(t, width=width)) <= 2:
        return t
    compact_pairs = (
        (" & ", " and "),
        ("International", "Global"),
        ("Championship", "Crown"),
        ("Institutional", "Inst."),
        ("Infrastructure", "Infra"),
        ("Semiconductors", "Semis"),
        ("Cryptocurrency", "Crypto"),
    )
    for old_s, new_s in compact_pairs:
        if old_s in t:
            cand = sanitize_cfont_en(t.replace(old_s, new_s))
            if len(cand) <= max_chars and len(textwrap.wrap(cand, width=width)) <= 2:
                return cand
    words = t.split()
    while len(words) > 4:
        cand = " ".join(words).rstrip(",;:-")
        if len(cand) <= max_chars and len(textwrap.wrap(cand, width=width)) <= 2:
            return cand
        words.pop()
    return " ".join(words)[:max_chars].rstrip(",;:-")


def fmt_price(val: float) -> str:
    """Formats asset price cleanly across 6 orders of magnitude ($0.0002 -> $105,400)."""
    try:
        v = float(val)
    except Exception:
        return "$0.00"
    if v >= 1000.0:
        return f"${v:,.2f}" if v < 10000.0 else f"${v:,.0f}"
    if v >= 1.0:
        return f"${v:,.2f}"
    if v >= 0.01:
        return f"${v:.4f}"
    return f"${v:.5f}".rstrip("0").rstrip(".") if v > 0 else "$0.0001"


# ============================================================================
# LIVE TELEMETRY ANALYZERS (STOCKS, CRYPTO, SPORTS & EXTRA_CONTEXT WHALE WIRE)
# ============================================================================
def _analyze_stocks_board(stocks_market: Optional[dict]) -> dict:
    sm = stocks_market or {}
    all_items = [v for v in sm.values() if isinstance(v, dict) and "symbol" in v]
    equities = [x for x in all_items if x["symbol"] not in COMMODITY_SYMS]
    if not equities:
        equities = all_items or [
            {"symbol": "AAPL", "name": "Apple Inc.", "price": 10.5, "delta_pct": 1.25, "category": "Mega Tech"},
            {"symbol": "NVDA", "name": "NVIDIA Corp", "price": 12.4, "delta_pct": -0.65, "category": "AI Tech"},
        ]

    by_gain = sorted(equities, key=lambda x: (float(x.get("delta_pct", 0.0)), x["symbol"]), reverse=True)
    by_loss = sorted(equities, key=lambda x: (float(x.get("delta_pct", 0.0)), x["symbol"]))
    by_abs = sorted(all_items or equities, key=lambda x: (abs(float(x.get("delta_pct", 0.0))), x["symbol"]), reverse=True)

    adv = sum(1 for x in all_items if float(x.get("delta_pct", 0.0)) > 0.02)
    dec = sum(1 for x in all_items if float(x.get("delta_pct", 0.0)) < -0.02)
    avg_eq_delta = sum(float(x.get("delta_pct", 0.0)) for x in equities) / max(1, len(equities))

    def _get_sym(sym: str, default_px: float) -> dict:
        obj = sm.get(sym)
        if isinstance(obj, dict):
            return obj
        return {"symbol": sym, "name": sym, "price": default_px, "delta_pct": 0.15}

    return {
        "top_gainer": by_gain[0],
        "sec_gainer": by_gain[1] if len(by_gain) > 1 else by_gain[0],
        "top_loser": by_loss[0],
        "sec_loser": by_loss[1] if len(by_loss) > 1 else by_loss[0],
        "top_abs": by_abs[0],
        "sec_abs": by_abs[1] if len(by_abs) > 1 else by_abs[0],
        "adv": adv,
        "dec": dec,
        "total": max(1, len(all_items)),
        "avg_delta": avg_eq_delta,
        "xau": _get_sym("XAU", 1250.0),
        "xag": _get_sym("XAG", 20.5),
        "wti": _get_sym("WTI", 72.0),
        "diamond": _get_sym("DIAMOND", 6400.0),
        "copper": _get_sym("COPPER", 3.45),
        "maze": sm.get("MAZE") if isinstance(sm.get("MAZE"), dict) else None,
        "dawn": sm.get("DAWN") if isinstance(sm.get("DAWN"), dict) else None,
    }


def _analyze_crypto_board(crypto_market: Optional[dict], year: int) -> dict:
    cm = crypto_market or {}
    all_coins = [v for v in cm.values() if isinstance(v, dict) and "symbol" in v]
    if not all_coins:
        all_coins = [
            {"symbol": "BTC", "name": "Bitcoin", "price": 0.10, "delta_pct": 1.5, "category": "Layer-1"},
            {"symbol": "LTC", "name": "Litecoin", "price": 0.05, "delta_pct": 0.4, "category": "Layer-1"},
        ]

    btc = cm.get("BTC") if isinstance(cm.get("BTC"), dict) else all_coins[0]
    eth = cm.get("ETH") if isinstance(cm.get("ETH"), dict) else btc
    sol = cm.get("SOL") if isinstance(cm.get("SOL"), dict) else eth
    doge = cm.get("DOGE") if isinstance(cm.get("DOGE"), dict) else btc
    bnb = cm.get("BNB") if isinstance(cm.get("BNB"), dict) else eth
    ltc = cm.get("LTC") if isinstance(cm.get("LTC"), dict) else btc

    alts = [c for c in all_coins if c["symbol"] != "BTC"] or [btc]
    by_gain = sorted(alts, key=lambda x: (float(x.get("delta_pct", 0.0)), x["symbol"]), reverse=True)
    by_loss = sorted(alts, key=lambda x: (float(x.get("delta_pct", 0.0)), x["symbol"]))

    adv = sum(1 for x in all_coins if float(x.get("delta_pct", 0.0)) > 0.02)
    dec = sum(1 for x in all_coins if float(x.get("delta_pct", 0.0)) < -0.02)

    def _coin_tag(c: dict) -> str:
        cat_s = str(c.get("category") or "")
        nm_s = str(c.get("name") or "")
        if "IOU" in cat_s or "IOU" in nm_s:
            return f"{c['symbol']} (OTC Venture IOU)"
        return str(c["symbol"])

    return {
        "btc": btc,
        "eth": eth,
        "sol": sol,
        "doge": doge,
        "bnb": bnb,
        "ltc": ltc,
        "eth_is_iou": ("IOU" in str(eth.get("category", "")) or "IOU" in str(eth.get("name", "")) or year < 2015),
        "sol_is_iou": ("IOU" in str(sol.get("category", "")) or "IOU" in str(sol.get("name", "")) or year < 2020),
        "hot_alt": by_gain[0],
        "hot_alt_lbl": _coin_tag(by_gain[0]),
        "lag_alt": by_loss[0],
        "lag_alt_lbl": _coin_tag(by_loss[0]),
        "adv": adv,
        "dec": dec,
        "total": len(all_coins),
    }


def _analyze_sports_board(sport_history: Optional[list], fixtures: Optional[list], day_index: int) -> dict:
    hist = [sanitize_cfont_en(str(x)) for x in (sport_history or []) if str(x).strip()]
    latest_res = hist[0] if hist else "Matchweek opening whistles echo across Europe and North America."
    second_res = hist[1] if len(hist) > 1 else ""

    fix_list = [f for f in (fixtures or []) if isinstance(f, dict) and f.get("home") and f.get("away")]
    if not fix_list:
        marquee = {
            "home": "Real Madrid",
            "away": "Barcelona",
            "league_name": "UEFA Champions League",
            "league": "UCL",
            "round_label_en": f"Season 1 - Matchday {max(1, day_index % 38)}",
            "kickoff": "20:45",
            "odds": [2.15, 3.40, 3.10],
            "hcap": "-0.25",
            "ou_line": 2.5,
            "active_bet": None,
        }
        co_feature = {
            "home": "LA Lakers",
            "away": "Boston Celtics",
            "league_name": "NBA Basketball",
            "league": "NBA",
            "kickoff": "22:00",
            "odds": [1.90, 14.0, 2.05],
            "hcap": "-1.5",
            "ou_line": 210.5,
            "active_bet": None,
        }
    else:
        # Rotate league spotlight across days so EPL, La Liga, UCL, Serie A/Bund, and NBA all headline!
        by_lg: Dict[str, List[dict]] = {}
        for fx in fix_list:
            by_lg.setdefault(str(fx.get("league") or "EPL"), []).append(fx)
        lg_keys = sorted(by_lg.keys())
        pri_lg = lg_keys[day_index % len(lg_keys)]
        sec_lg = lg_keys[(day_index + 2) % len(lg_keys)]
        pri_pool = by_lg[pri_lg]
        sec_pool = by_lg[sec_lg]
        # Prefer any match with an active player bet if one exists!
        bet_matches = [fx for fx in fix_list if fx.get("active_bet")]
        marquee = bet_matches[0] if bet_matches else pri_pool[(day_index // len(lg_keys)) % len(pri_pool)]
        co_feature = sec_pool[(day_index + 1) % len(sec_pool)]
        if co_feature.get("id") == marquee.get("id") and len(fix_list) > 1:
            co_feature = fix_list[(day_index + 3) % len(fix_list)]

    odds = list(marquee.get("odds") or [2.10, 3.30, 3.20])
    while len(odds) < 3:
        odds.append(3.00)
    o1, ox, o2 = float(odds[0]), float(odds[1]), float(odds[2])
    is_bball = ("NBA" in str(marquee.get("league", ""))) or ("Basketball" in str(marquee.get("league_name", "")))
    fav_name = marquee["home"] if o1 <= o2 else marquee["away"]
    fav_odd = min(o1, o2)
    dog_name = marquee["away"] if o1 <= o2 else marquee["home"]
    dog_odd = max(o1, o2)

    return {
        "latest_res": latest_res,
        "second_res": second_res,
        "marquee": marquee,
        "co_feature": co_feature,
        "o1": o1,
        "ox": ox,
        "o2": o2,
        "is_bball": is_bball,
        "fav_name": sanitize_cfont_en(str(fav_name)),
        "fav_odd": fav_odd,
        "dog_name": sanitize_cfont_en(str(dog_name)),
        "dog_odd": dog_odd,
        "total_fixtures": len(fix_list) or 25,
        "active_bets_count": sum(1 for fx in fix_list if fx.get("active_bet")),
    }


def _build_whale_commentary(
    extra_context: Optional[dict],
    stocks_market: Optional[dict],
    crypto_market: Optional[dict],
) -> Dict[str, str]:
    """
    Inspects optional `extra_context` (`portfolio_stats`, `futures`, `lottery`, `cash`,
    `bank`, `stake_stats`) and produces subtle, witty anonymous 'San Andreas Whale'
    sentences tailored to Finance, Crypto, Sports, and Culture desks!
    """
    notes = {"finance": "", "crypto": "", "sports": "", "life_net": ""}
    if not isinstance(extra_context, dict) or not extra_context:
        return notes

    pstats = extra_context.get("portfolio_stats") or {}
    futs = extra_context.get("futures") or []
    lotto = extra_context.get("lottery") or {}
    stake = extra_context.get("stake_stats") or {}
    try:
        liquid = int(extra_context.get("cash") or 0) + int(extra_context.get("bank") or 0)
    except Exception:
        liquid = 0

    sm = stocks_market or {}
    cm = crypto_market or {}

    # 1. Inspect open futures positions & mark-to-market PnL
    best_stock_fut: Optional[Tuple[float, dict]] = None
    best_crypto_fut: Optional[Tuple[float, dict]] = None
    for f in futs:
        if not isinstance(f, dict):
            continue
        sym = str(f.get("symbol") or "")
        side = str(f.get("side") or "LONG").upper()
        lev = int(f.get("leverage") or 1)
        margin = float(f.get("margin") or 0.0)
        entry = float(f.get("entry_price") or 0.0)
        mkt_obj = cm.get(sym) if sym in cm else sm.get(sym)
        mark = float(mkt_obj.get("price", entry)) if isinstance(mkt_obj, dict) else entry
        pnl = 0.0
        if entry > 0 and margin > 0:
            pct = ((mark - entry) / entry) if "LONG" in side else ((entry - mark) / entry)
            pnl = margin * lev * pct
        tup = (abs(pnl) + margin * 0.25, {
            "sym": sym, "side": side, "lev": lev, "margin": margin, "pnl": pnl,
        })
        if sym in cm:
            if best_crypto_fut is None or tup[0] > best_crypto_fut[0]:
                best_crypto_fut = tup
        else:
            if best_stock_fut is None or tup[0] > best_stock_fut[0]:
                best_stock_fut = tup

    realized_mkt = float(pstats.get("realized_market_pnl") or 0.0)
    lotto_won = float(pstats.get("lotto_won") or 0.0)
    bet_won = float(pstats.get("bet_won") or 0.0)
    bet_net = float(pstats.get("bet_net_pnl") or 0.0)
    bet_cnt = int(pstats.get("bet_won_count") or 0)

    # Defensively inspect EagleStake casino stats (App #15)
    stake_big = 0.0
    stake_net = 0.0
    stake_rounds = 0
    if isinstance(stake, dict) and stake:
        for k in ("biggest_win", "max_win", "best_win", "last_win", "total_won", "total_payout"):
            try:
                stake_big = max(stake_big, float(stake.get(k) or 0.0))
            except Exception:
                pass
        for k in ("net_pnl", "net_profit", "profit"):
            if k in stake:
                try:
                    stake_net = float(stake.get(k) or 0.0)
                    break
                except Exception:
                    pass
        for k in ("rounds_played", "total_rounds", "games_played", "spins"):
            try:
                stake_rounds = max(stake_rounds, int(stake.get(k) or 0))
            except Exception:
                pass

    # Finance whale note
    fin_bits: List[str] = []
    if best_stock_fut is not None:
        bf = best_stock_fut[1]
        if bf["pnl"] >= 500:
            fin_bits.append(
                f"Floor chatter at Maze Bank Tower also tracks a mysterious San Andreas whale riding a "
                f"{bf['lev']}x {bf['side']} futures ticket on {bf['sym']} sitting on +${bf['pnl']:,.0f} in unrealized gains."
            )
        elif bf["margin"] >= 1000 or bf["lev"] >= 10:
            fin_bits.append(
                f"Derivatives clerks at Maze Bank note bold local flow after an anonymous San Andreas account opened a "
                f"{bf['lev']}x {bf['side']} position on {bf['sym']} backed by ${bf['margin']:,.0f} margin."
            )
    if realized_mkt >= 2500:
        fin_bits.append(
            f"Private-wealth desks in Los Santos report a solitary EaglePhone terminal has already locked in "
            f"+${realized_mkt:,.0f} in realized market profits."
        )
    elif liquid >= 500000 and not fin_bits:
        fin_bits.append(
            f"Overnight clearing logs at Maze Bank show a quiet high-net-worth resident holding ${liquid:,.0f} "
            f"in liquid cash and demand deposits ready to pounce on volatility."
        )
    if fin_bits:
        notes["finance"] = sanitize_cfont_en(" ".join(fin_bits[:2]))

    # Crypto whale note
    cry_bits: List[str] = []
    if best_crypto_fut is not None:
        cf = best_crypto_fut[1]
        if cf["pnl"] >= 500:
            cry_bits.append(
                f"On-chain perpetual trackers flagged an unnamed Santa Maria whale holding a {cf['lev']}x "
                f"{cf['side']} {cf['sym']} contract currently printing +${cf['pnl']:,.0f} in open profit."
            )
        elif cf["margin"] >= 500 or cf["lev"] >= 10:
            cry_bits.append(
                f"Order-book watchers spotted a daring {cf['lev']}x {cf['side']} {cf['sym']} perpetual block "
                f"(${cf['margin']:,.0f} margin) routed from a private San Andreas mobile key."
            )
    if stake_big >= 1000 or stake_net >= 1000:
        win_v = max(stake_big, stake_net)
        cry_bits.append(
            f"Meanwhile, EagleStake VIP telemetry lit up after a local high-roller hit +${win_v:,.0f} at the "
            f"provably-fair tables before rotating fresh chips toward digital assets."
        )
    elif realized_mkt >= 10000 and not cry_bits:
        cry_bits.append(
            f"San Fierro OTC brokers say a quiet San Andreas whale with +${realized_mkt:,.0f} in booked trading "
            f"gains continues to accumulate spot liquidity on dips."
        )
    if cry_bits:
        notes["crypto"] = sanitize_cfont_en(" ".join(cry_bits[:2]))

    # Sports & Casino whale note
    spt_bits: List[str] = []
    if bet_won >= 1000 or bet_net >= 500:
        spt_bits.append(
            f"Las Venturas oddsmakers are whispering about a sharp San Andreas bettor who has already cashed "
            f"{max(1, bet_cnt)} winning slips worth ${bet_won:,.0f} (net {bet_net:+,.0f} USD)."
        )
    if stake_big >= 500 or stake_rounds >= 3:
        if stake_big >= 500:
            spt_bits.append(
                f"Across the Strip at EagleStake's digital pit, a mystery VIP pocketed a ${stake_big:,.0f} payout "
                f"between matchday kickoffs."
            )
        else:
            spt_bits.append(
                f"Late-night action on EagleStake also logged {stake_rounds} brisk casino rounds from a Los Santos VIP line."
            )
    if spt_bits:
        notes["sports"] = sanitize_cfont_en(" ".join(spt_bits[:2]))

    # Culture / Lottery / High-roller street buzz
    life_bits: List[str] = []
    scratch_msg = sanitize_cfont_en(str(lotto.get("last_scratch_msg") or ""))
    if lotto_won >= 500 or ("WON" in scratch_msg.upper()) or ("JACKPOT" in scratch_msg.upper()):
        if lotto_won >= 500:
            life_bits.append(
                f"Local cafe chatter along Santa Maria Pier is buzzing over an anonymous San Andreas resident who has "
                f"quietly collected ${lotto_won:,.0f} in EagleLotto prize payouts."
            )
        else:
            life_bits.append(
                f"Convenience kiosks near Verona Beach report fresh excitement after a local EagleLotto player "
                f"scratched a winning ticket ({scratch_msg[:48]})."
            )
    elif stake_big >= 2000:
        life_bits.append(
            f"Nightlife blogs from Vinewood to Las Venturas are trading rumors of an anonymous EaglePhone player "
            f"who struck a ${stake_big:,.0f} hot streak inside EagleStake."
        )
    if life_bits:
        notes["life_net"] = sanitize_cfont_en(" ".join(life_bits[:1]))

    return notes


# ============================================================================
# 24 ROTATING DAILY BEAT ANGLES PER DESK (ZERO CONSECUTIVE-DAY REPETITION!)
# ============================================================================
WORLD_BEATS: Tuple[Tuple[str, str, str], ...] = (
    ("Global Summit Wire", "Cabinet envoys align trade, currency, and infrastructure priorities", "Los Santos Port"),
    ("Maritime Freight Pulse", "Container megaships and trans-Pacific cranes run at high tempo", "Ocean Docks"),
    ("Science & Orbital Brief", "Research labs and orbital telemetry hit fresh technical milestones", "Green Palms Lab"),
    ("Central Bank Corridor", "Sovereign bond desks weigh inflation targets against growth policy", "Maze Bank Plaza"),
    ("Energy & Grid Dispatch", "Power interconnectors and fuel terminals balance seasonal demand", "Easter Basin"),
    ("Aviation & Rail Beat", "High-speed transit corridors and international hubs expand capacity", "Los Santos Intl"),
    ("Pacific Trade Notebook", "Supply-chain planners diversify semiconductor and industrial routes", "San Fierro Bay"),
    ("Diplomatic Press Room", "Multilateral communiques spotlight security and telecom standards", "Verdant Bluffs"),
    ("Urban Skyline Report", "Supertall engineering and metro upgrades reshape major capitals", "Downtown LS"),
    ("Telecom & Fiber Wire", "Subsea cables and low-latency wireless backbones scale bandwidth", "Missionary Hill"),
    ("Industrial PMI Watch", "Factory automation orders and precision tooling pace global output", "Blueberry Acres"),
    ("Climate & Clean Grid", "Utility-scale solar, wind, and battery storage trim peak grid costs", "Sherman Dam"),
    ("Aerospace Engineering", "Reusable propulsion and satellite constellations redraw spaceflight", "Verdant Meadows"),
    ("Sovereign Fiscal Check", "Treasury auctions draw steady institutional demand across G20 hubs", "Commerce Hall"),
    ("Biotech & Lab Chronicle", "Genomic sequencing and clinical diagnostics accelerate medical care", "San Fierro Med"),
    ("Port Customs & Cargo", "Intermodal rail yards clear brisk import manifests ahead of schedule", "Docks Terminal 4"),
    ("Global University Desk", "STEM research consortia publish open benchmarks in computing and physics", "Bayside Campus"),
    ("Strategic Metals Brief", "Copper, lithium, and rare-earth logistics anchor industrial planning", "Hunter Quarry"),
    ("Civic Architecture", "Waterfront revitalization and public transit hubs draw urban planners", "Verona Pier"),
    ("Cyber & Cloud Treaty", "Cross-border encryption and data-center resilience top policy agendas", "Financial District"),
    ("Agri-Trade & Weather", "Grain shipping lanes and reservoir levels remain steady across regions", "Flint County"),
    ("Deep-Sea & Polar Watch", "Oceanographic vessels map currents and subsea mineral ridges", "Palomino Coast"),
    ("Parliamentary Question", "Legislators debate digital competition, infrastructure, and tax reform", "City Hall"),
    ("Evening Foreign Ledger", "Overnight cables from Tokyo, London, and Frankfurt set tomorrow's tone", "Mulholland Overlook"),
)

LIFE_BEATS: Tuple[Tuple[str, str, str], ...] = (
    ("Boardwalk Pulse", "Sunset crowds along Santa Maria Pier swap playlists and mobile snaps", "Santa Maria Pier"),
    ("Viral Timeline Watch", "A single late-night meme thread snowballs across millions of screens", "Vinewood Hills"),
    ("San Fierro Bench", "Teardown blogs test battery life, display PPI, and silicon thermals", "Garcia Tech Row"),
    ("Cafe Wi-Fi Notebook", "Espresso bars hum with laptops, headphones, and indie creative pitches", "Queens Cafe"),
    ("Midnight Radio FM", "Coastal highway drivers dial in synth, pop, and nostalgic rock sets", "Great Ocean Hwy"),
    ("Creator Economy Beat", "Independent video essayists and livestreamers rival legacy TV ratings", "Rodeo Studios"),
    ("Mechanical Key Cult", "Custom keycaps, high-refresh monitors, and cozy desk lamps trend online", "WIBU-01 Arcade"),
    ("Cinema & Box Office", "Packed Friday-night screenings turn post-credits scenes into events", "Cathay Theater"),
    ("Streetwear & Sneaker", "Limited weekend drops draw early-morning queues and resale chatter", "Market Station"),
    ("Audio & Vinyl Revival", "Hi-res headphones and warm analog pressings win back music purists", "Idlewood Records"),
    ("Campus Forum Digest", "Dorm-room group chats debate rankings, study beats, and weekend plans", "Greenglass College"),
    ("Mobile Camera Test", "Low-light night-mode street shots turn every pocket phone into a DSLR", "Chinatown Neon"),
    ("Retro Nostalgia Wave", "Throwback ringtones, classic forums, and childhood OSTs spark warm threads", "East Beach"),
    ("Weekend Food & Boba", "Late-night ramen counters and bubble-tea spots pack post-game crowds", "Little Tokyo LS"),
    ("Smart Living & Apps", "One-tap ride hailing, instant wallets, and clean dark-mode UIs shine", "Downtown San Fierro"),
    ("Fitness & Run Club", "Sunrise coastal joggers track splits and share coffee at the pier", "Verona Boardwalk"),
    ("Forum Mystery Thread", "Internet sleuths decode Easter eggs and ARG clues inside hours", "Palisades Lounge"),
    ("Festival Stage Lights", "Open-air summer sets and crowd sing-alongs flood short-video feeds", "Glen Park Amphitheater"),
    ("Setup Showcase", "Ultrawide dual-monitor battlestations inspire clean cable-management envy", "Juniper Hollow"),
    ("Podcast & Longform", "Two-hour commuter conversations unpack tech history and pop mysteries", "Mulholland Drive"),
    ("Collectible & Figure", "Display shelves gleaming with limited figures and artbooks top hobby subs", "WIBU-01 Mall"),
    ("Cloud Storage & Sync", "Seamless cross-device photo libraries rescue years of digital memories", "Calton Heights"),
    ("Indie Web Zine", "Minimalist blogs and curated newsletters push back against noisy feeds", "Hashbury Books"),
    ("Late-Night Lo-Fi", "Rainy-window beats keep coders and night owls company past 2 AM", "Pier 69 Overlook"),
)

ACG_BEATS: Tuple[Tuple[str, str, str], ...] = (
    ("Akihabara Broadcast", "Late-night TV anime animation cuts dominate sakuga breakdowns", "WIBU-01 Electric Town"),
    ("Esports Arena Wire", "Draft-phase mind games and frame-perfect teamfights electrify ranked fans", "San Fierro Coliseum"),
    ("Teyvat & Fantasy Lore", "World-building theories and character build guides pack community wikis", "Mondstadt Bridge"),
    ("Open-World Craft", "Seamless horizons and emergent physics reward curious off-road detours", "Mount Chiliad Ridge"),
    ("Soundtrack & Oricon", "Opening-theme guitar riffs and orchestral boss scores top streaming", "Starlight Hall"),
    ("Ranked Ladder Meta", "Patch-note balance tweaks shake up high-ELO pick-and-ban priorities", "PC Bang Row"),
    ("Studio Sakuga Focus", "Key animators hand-draw breathtaking swordplay and emotional close-ups", "Akiba Studio 3"),
    ("JRPG Turn-Based Art", "Party synergies, elemental reactions, and 80-hour scripts earn devotion", "Cathedral Plaza"),
    ("PC Frame-Rate Lab", "GPU drivers, shader caches, and 120Hz responsiveness get put to the test", "Silicon Alley"),
    ("Speedrun & Challenge", "Frame-perfect skips and no-hit boss clears leave livestream chats stunned", "Arcade Basement"),
    ("Manga Chapter Drop", "Midweek cliffhangers send translation discussion threads past 20,000 replies", "Kanda Bookshop"),
    ("Voice Actor Spotlight", "Iconic seiyuu performances bring unforgettable warmth and grit to scenes", "Tokyo Recording Booth"),
    ("Co-Op Raid Evening", "Four-player friend squads coordinate elemental bursts and boss mechanics", "Starfell Camp"),
    ("Indie Pixel Gem", "A tiny two-person dev team captivates Steam with pure gameplay soul", "Harbor Loft"),
    ("Figure & Gunpla Craft", "Hand-painted scale statues and weathered mecha kits fill showcase cases", "WIBU-01 Hobby Tower"),
    ("Visual Novel Chronicle", "Branching routes and solo piano epilogues linger with readers for weeks", "Rainy Cafe Booth"),
    ("Fighting Game Footsies", "Last-pixel parries in losers-bracket finals bring entire halls to their feet", "Las Venturas Expo"),
    ("Modding & Shader Scene", "Community texture packs and lighting overhauls breathe life into classics", "Gameplay Lab Garage"),
    ("Gacha Banner Math", "Pity-counter spreadsheets and saved primogem stashes face temptation", "Wangshu Balcony"),
    ("Convention Cosplay", "Hand-stitched armor props and glowing weapons turn plazas into Teyvat", "Convention Center"),
    ("Director Interview", "Veteran creators share storyboards showing how cut mechanics evolved", "Kyoto Tea Room"),
    ("Retro Console Vault", "CRT scanlines and timeless 16-bit/PS2 design lessons inspire modern hits", "Retro Corner"),
    ("Seasonal Cour Poll", "Weekly episode rankings crown a surprise dark-horse studio favorite", "Otaku Bulletin"),
    ("Midnight Patch Countdown", "Pre-load bars hit 100% as servers prepare to open a new region", "Celestia Lookout"),
)

FINANCE_BEATS: Tuple[str, ...] = (
    "Closing Bell Tape",
    "Bullion & Macro Watch",
    "Institutional Flow",
    "Sector Rotation Desk",
    "Semis & Cloud Pulse",
    "Crude & Commodity Wire",
    "Maze Bank Morning Note",
    "Volatility & Yield Curve",
    "Earnings Multiples Check",
    "Hard-Asset Barbell",
    "Cross-Asset Correlations",
    "Retail & Momentum Radar",
    "Quant Order-Book Brief",
    "Global Reserve Ledger",
    "Blue-Chip Cash Flows",
    "High-Beta Breakout Scan",
    "Treasury & Real Rates",
    "Consumer & Tech Margin",
    "Pacific Opening Cross",
    "Commodity Supercycle",
    "Options Gamma Pin",
    "Sovereign Wealth Bid",
    "Midday Reversal Study",
    "Wall Street After-Hours",
)

CRYPTO_BEATS: Tuple[str, ...] = (
    "24/7 Order-Book Wire",
    "Halving-Cycle Metrics",
    "On-Chain Liquidity",
    "Cold-Storage & Custody",
    "Altcoin Dispersion",
    "Hashrate & Node Pulse",
    "Perpetual Basis Check",
    "Digital Gold Thesis",
    "San Fierro Dev Commit",
    "Whale Wallet Radar",
    "Spot vs Leverage Tape",
    "Cross-Border Settlement",
    "Cryptographic Scarcity",
    "Weekend Volatility Desk",
    "Protocol Fee & Burn",
    "OTC Desk Briefing",
    "Self-Custody Ledger",
    "Layer-1 Throughput",
    "Asian Session Breakout",
    "Miner Reserve Watch",
    "Market-Maker Spreads",
    "Venture & Seed Book",
    "Macro-Crypto Beta",
    "Midnight Block Close",
)

SPORTS_BEATS: Tuple[str, ...] = (
    "Matchday Press Box",
    "Venturas Odds Report",
    "Tactical Chalkboard",
    "Floodlight Six-Pointer",
    "xG & Pressing Breakdown",
    "Transatlantic Slate",
    "Sharp Money Movement",
    "Title-Race Permutations",
    "Touchline Notebook",
    "Hardwood & Pitch Wire",
    "Stoppage-Time Pulse",
    "Underdog Value Radar",
    "Midfield Chess Study",
    "Continental Clash Preview",
    "Squad Rotation Brief",
    "Set-Piece & Pace Lab",
    "Championship Run-In",
    "Late-Kickoff Spotlight",
    "Derby Atmosphere Desk",
    "Golden Boot & MVP Tracker",
    "High-Line Counter Study",
    "Bookmaker Liability Note",
    "Bench Impact Analysis",
    "Final Whistle Verdict",
)


def _get_teyvat_acg_era_note(year: int, month: int, beat_idx: int) -> str:
    """Chronologically accurate ACG + Los Santos/Teyvat flavor (never leaks future Genshin patches!)."""
    if year <= 2012:
        notes = (
            "In WIBU-01's neon arcades and late-night LAN cafes, players debate whether future open-world anime RPGs could ever render seamless cel-shaded continents in real time.",
            "Across Akihabara hobby shops and San Andreas dorms, mechanical keyboards click through ranked MOBA queues while anime club projectors loop Blu-ray openings.",
            "From Ochanomizu guitar stores to Verona Beach skateparks, anime soundtracks and classic console RPGs bridge Eastern and Western youth culture.",
        )
    elif year <= 2016:
        notes = (
            "Since GTA V brought Los Santos to HD glory alongside open-world titans like The Witcher 3, studio engineers in Shanghai and Tokyo are quietly prototyping cross-platform anime worlds.",
            "Inside WIBU-01 figure towers and Discord voice rooms, ranked esports watch-parties run side by side with seasonal anime simulcast countdowns.",
            "Modders in San Fierro and illustrators on Pixiv trade shaders and character sketches, pushing stylized real-time rendering closer to hand-drawn film.",
        )
    elif year <= 2019:
        notes = (
            "Following Breath of the Wild's open-air physics and NieR:Automata's combat grace, buzz builds around miHoYo's ambitious open-world project 'Genshin Impact' in closed beta.",
            "PC rigs glowing with tempered-glass RGB and 144Hz monitors pack every block from San Fierro to Akihabara during global esports broadcasts.",
            "Seasonal anime production values reach theatrical heights as digital compositing and hand-drawn sakuga unite millions of weekly viewers.",
        )
    elif year == 2020 and month < 9:
        notes = (
            "Closed-beta footage of Traveler Aether gliding over Mondstadt's windmills has RPG forums counting down the weeks to September 28's global launch.",
            "With home gaming setups running twelve hours a day in 2020, co-op lobbies and anime simulcasts anchor friendships across every time zone.",
        )
    elif year == 2020:
        notes = (
            "Ever since Traveler Aether woke on Starfell Beach in late September, Mondstadt's Gothic windmills and Liyue's golden peaks have become a nightly second home for millions.",
            "Players cruising from Santa Maria Pier over to Mondstadt's bridge compare Spiral Abyss team rotations and Dragonspine frost strategies.",
        )
    elif year == 2021:
        notes = (
            "Across Teyvat and Project Eagle's WIBU-01 district, Hu Tao's Wangshu Inn mischief and Raiden Shogun's violet Inazuma lightning dominate fan art and Spiral Abyss clears.",
            "Co-op domains in Inazuma and ranked Valorant/LoL five-stacks keep Discord channels lively well past midnight.",
        )
    elif year == 2022:
        notes = (
            "Between Tarnished expeditions across Limgrave and Traveler Aether's Dendro journey through Sumeru's rainforests with Nahida, 2022 spoils open-world fans rotten.",
            "In WIBU-01 record stalls, Edgerunners synth tracks and Bocchi the Rock! guitar albums sell out within hours of restock.",
        )
    elif year == 2023:
        notes = (
            "From diving beneath Fontaine's crystal waters alongside Furina and Neuvillette to watching Frieren's quiet magic on Friday nights, ACG storytelling stands at an emotional peak.",
            "Meanwhile, Rockstar's December GTA VI trailer and Faker's fourth Worlds trophy have every San Andreas gamer counting frames and memories.",
        )
    elif year == 2024:
        notes = (
            "Traveler Aether's Saurian-riding trek into blazing Natlan alongside Mavuika, Citlali, and Xilonen shares top billing with Black Myth: Wukong and Shadow of the Erdtree.",
            "Walking from Los Santos's sunlit piers to WIBU-01 billboards, anime openings by Creepy Nuts and YOASOBI echo from passing custom radios.",
        )
    else:
        notes = (
            "In 2025, Pyro Aether's triumph beside Mavuika in Natlan flows directly into Mondstadt's Paralogism reunion, Skirk's abyssal lessons, and Columbina's moonlit Nod-Krai horizon.",
            "Inside Project Eagle's gameplay-lab, cruising past Santa Maria Pier with custom radio tracks and Teyvat companions brings sixteen years of gaming culture full circle.",
        )
    return notes[beat_idx % len(notes)]


# ============================================================================
# CORE ARTICLE BUILDER (EXACT-DATE MILESTONES + 24-BEAT LIVE DAILY EDITIONS)
# ============================================================================
def build_enriched_article_en(
    *,
    cat: str,
    raw: dict,
    current_date: datetime.date,
    day_index: int,
    era_info: dict,
    year_arc_pair: Tuple[str, str],
    month_lens_pair: Tuple[str, str],
    recent_milestone_note: str,
    stk: dict,
    cry: dict,
    spt: dict,
    whale_notes: Dict[str, str],
) -> dict:
    y = max(2010, min(2025, current_date.year))
    m = current_date.month
    d = current_date.day
    m_name = MONTH_NAMES_EN[m - 1]
    w_name = WEEKDAY_NAMES_EN[current_date.weekday()]
    pretty_dt = f"{m_name} {d}, {y}"

    cat_offsets = {"world": 0, "life_net": 5, "anime_game": 11, "finance": 17, "crypto": 7, "sports": 13}
    beat_idx = (current_date.toordinal() + cat_offsets.get(cat, 0)) % 24
    roster = BYLINE_ROSTER_EN.get(cat, BYLINE_ROSTER_EN["world"])
    byline = roster[(current_date.toordinal() + cat_offsets.get(cat, 0)) % len(roster)]

    is_exact = bool(raw.get("is_exact_date", False))
    arc_head, arc_body = year_arc_pair
    lens_head, lens_tmpl = month_lens_pair
    lens_sentence = lens_tmpl.format(year=y)

    # Live market snippets reusable across Finance & Crypto
    g1 = stk["top_gainer"]
    l1 = stk["top_loser"]
    xau = stk["xau"]
    xag = stk["xag"]
    wti = stk["wti"]
    dia = stk["diamond"]

    fin_tape_para = (
        f"On the live {pretty_dt} electronic board ({stk['adv']} advancing vs {stk['dec']} declining across "
        f"{stk['total']} tracked tickers), {g1['symbol']} paces gainers at {fmt_price(g1['price'])} "
        f"({g1.get('delta_pct', 0.0):+.2f}%), while {l1['symbol']} lags at {fmt_price(l1['price'])} "
        f"({l1.get('delta_pct', 0.0):+.2f}%). In hard commodities, spot Gold XAU trades at "
        f"{fmt_price(xau['price'])}/oz ({xau.get('delta_pct', 0.0):+.2f}%), Silver XAG prints "
        f"{fmt_price(xag['price'])}/oz, WTI Crude stands at {fmt_price(wti['price'])}/bbl "
        f"({wti.get('delta_pct', 0.0):+.2f}%), and 1ct GIA Diamond holds {fmt_price(dia['price'])}."
    )
    if stk["maze"] and stk["dawn"] and (beat_idx % 2 == 0):
        mz, dw = stk["maze"], stk["dawn"]
        fin_local_line = (
            f"Regional San Andreas & Teyvat bellwethers also draw brisk volume, with Maze Bank (MAZE) at "
            f"{fmt_price(mz['price'])} ({mz.get('delta_pct', 0.0):+.2f}%) and Dawn Winery (DAWN) at "
            f"{fmt_price(dw['price'])} ({dw.get('delta_pct', 0.0):+.2f}%)."
        )
    else:
        fin_local_line = (
            f"Portfolio strategists between Wall Street and Maze Bank Plaza note average equity dispersion "
            f"sitting near {stk['avg_delta']:+.2f}% heading into the afternoon bell."
        )

    btc = cry["btc"]
    eth = cry["eth"]
    sol = cry["sol"]
    doge = cry["doge"]
    hot_c = cry["hot_alt"]
    lag_c = cry["lag_alt"]

    if y < 2015:
        cry_tape_para = (
            f"Across 24/7 digital order books on {pretty_dt} ({cry['adv']} green vs {cry['dec']} red across "
            f"{cry['total']} pairs), flagship Bitcoin (BTC) trades at {fmt_price(btc['price'])} "
            f"({btc.get('delta_pct', 0.0):+.2f}%), while Scrypt peer Litecoin (LTC) prints "
            f"{fmt_price(cry['ltc']['price'])}. In high-beta & OTC Venture IOU books, {cry['hot_alt_lbl']} "
            f"leads at {fmt_price(hot_c['price'])} ({hot_c.get('delta_pct', 0.0):+.2f}%) while "
            f"{cry['lag_alt_lbl']} cools to {fmt_price(lag_c['price'])} ({lag_c.get('delta_pct', 0.0):+.2f}%)."
        )
    else:
        sol_lbl = "SOL (Venture IOU)" if cry["sol_is_iou"] else "SOL"
        cry_tape_para = (
            f"Live 24/7 on-chain & exchange feeds for {pretty_dt} ({cry['adv']} advancing vs {cry['dec']} "
            f"pulling back) peg Bitcoin (BTC) at {fmt_price(btc['price'])} ({btc.get('delta_pct', 0.0):+.2f}%) "
            f"and Ethereum (ETH) at {fmt_price(eth['price'])} ({eth.get('delta_pct', 0.0):+.2f}%). "
            f"Elsewhere, {sol_lbl} trades at {fmt_price(sol['price'])}, DOGE prints {fmt_price(doge['price'])}, "
            f"top mover {cry['hot_alt_lbl']} clocks {hot_c.get('delta_pct', 0.0):+.2f}%, and "
            f"{cry['lag_alt_lbl']} slips {lag_c.get('delta_pct', 0.0):+.2f}%."
        )

    mq = spt["marquee"]
    cf = spt["co_feature"]
    if spt["is_bball"]:
        odds_phrase = (
            f"moneyline {spt['o1']:.2f} on {mq['home']} vs {spt['o2']:.2f} on {mq['away']} "
            f"(spread {mq.get('hcap', '-1.5')}, Over/Under {mq.get('ou_line', 210.5)} pts)"
        )
    else:
        odds_phrase = (
            f"1X2 odds at {spt['o1']:.2f} (Home) - {spt['ox']:.2f} (Draw) - {spt['o2']:.2f} (Away), "
            f"Asian handicap {mq.get('hcap', '-0.25')}, and goal line {mq.get('ou_line', 2.5)}"
        )

    spt_live_recap = (
        f"From the latest final whistle on the EagleSports wire: {spt['latest_res']}"
        + (f" Meanwhile, {spt['second_res']}" if spt["second_res"] else "")
    )
    spt_live_preview = (
        f"Looking ahead to today's {spt['total_fixtures']}-match card across five major leagues, all eyes turn "
        f"to {mq['league_name']} ({mq.get('kickoff', '20:45')}) as {mq['home']} faces {mq['away']} with "
        f"{odds_phrase}. Across the slate in {cf.get('league_name', 'action')}, {cf['home']} meets "
        f"{cf['away']} ({cf.get('kickoff', '22:00')}), keeping Las Venturas ticket windows busy."
    )

    # ------------------------------------------------------------------------
    # CASE A: EXACT-DATE HISTORICAL MILESTONE (BESPOKE 4-PARAGRAPH FEATURE)
    # ------------------------------------------------------------------------
    if is_exact:
        title = fit_headline_cfont(raw.get("title", "Historic Dispatch"))
        subhead = sanitize_cfont_en(
            raw.get("subhead")
            or f"Special {pretty_dt} chronicle from our {cat.upper()} bureau."
        )
        p1 = sanitize_cfont_en(raw.get("summary", ""))
        p2_base = sanitize_cfont_en(raw.get("detail", ""))
        if not p2_base:
            p2_base = sanitize_cfont_en(f"Context across {m_name} {y}: {lens_sentence} {arc_body}")
        else:
            p2_base = sanitize_cfont_en(f"{p2_base} Across the broader {y} landscape, {lens_sentence.lower()}")

        if cat == "finance":
            p3 = sanitize_cfont_en(f"{fin_tape_para} {fin_local_line}")
            p4_core = (
                f"Risk managers note that landmark macro sessions like {pretty_dt} often anchor multi-month "
                f"positioning across equities, Treasury duration, and physical bullion vaults."
            )
        elif cat == "crypto":
            p3 = sanitize_cfont_en(cry_tape_para)
            p4_core = (
                f"From cypherpunk node operators in San Fierro to global liquidity desks, {pretty_dt} enters "
                f"the permanent ledger as a defining inflection point for borderless digital value."
            )
        elif cat == "sports":
            p3 = sanitize_cfont_en(f"{spt_live_recap} {spt_live_preview}")
            p4_core = (
                f"Whether replayed in neighborhood sports bars or studied on tactical chalkboards, iconic "
                f"nights like {pretty_dt} remind supporters why unscripted drama rules global sport."
            )
        elif cat == "anime_game":
            p3 = sanitize_cfont_en(_get_teyvat_acg_era_note(y, m, beat_idx))
            p4_core = (
                f"Years from now, players and anime fans looking back on {pretty_dt} will remember the exact "
                f"opening chords, late-night voice chats, and shared sense of wonder."
            )
        elif cat == "life_net":
            p3 = sanitize_cfont_en(
                f"From Santa Maria Pier boardwalk cafes to San Fierro's tech row and Vinewood screens, "
                f"reaction to today's milestone dominates {w_name} timelines and FM radio call-ins."
            )
            p4_core = (
                f"Cultural historians tracking {y} note how rapidly hardware, music, and online humor weave "
                f"single-day breakthroughs into everyday memory."
            )
        else:
            p3 = sanitize_cfont_en(
                f"Monitoring dispatches from Los Santos Port authorities, Maze Bank macro analysts, and "
                f"overseas capitals, observers underscore the lasting ripple effects across {y} policy."
            )
            p4_core = (
                f"As diplomatic and scientific calendars turn past {pretty_dt}, ministers and engineers alike "
                f"face a transformed strategic baseline for the remainder of {m_name} {y}."
            )

        w_extra = whale_notes.get(cat, "")
        p4 = sanitize_cfont_en(f"{p4_core} {w_extra}".strip())
        vibe = sanitize_cfont_en(raw.get("vibe") or era_info.get("vibe", ""))
        paras = [p for p in (p1, p2_base, p3, p4) if p]
        return {
            "title": title,
            "subhead": subhead,
            "byline": byline,
            "paragraphs": paras,
            "body": "\n\n".join(paras),
            "vibe": vibe,
            "summary": sanitize_cfont_en(f"{p1} {p3[:180]}"),
        }

    # ------------------------------------------------------------------------
    # CASE B: ROTATING DAILY BEAT ENGINE (24 DISTINCT ANGLES PER DESK)
    # ------------------------------------------------------------------------
    short_arc = arc_head.split(",")[0].strip()

    if cat == "world":
        b_tag, b_hook, b_loc = WORLD_BEATS[beat_idx]
        title_templates = (
            f"{b_tag}: {short_arc} Shapes {m_name} {d} Diplomacy",
            f"{m_name} {d} Dispatch: {b_hook}",
            f"Capitals to {b_loc} ({m_name} {d}): {b_tag}",
            f"{b_tag} ({w_name}, {m_name} {d}): {lens_head}",
        )
        title = fit_headline_cfont(title_templates[beat_idx % len(title_templates)])
        subhead = sanitize_cfont_en(
            f"{b_hook} on {w_name}, {pretty_dt}, as {lens_head.lower()} steers international agendas."
        )
        p1 = sanitize_cfont_en(
            f"International correspondents filing on {w_name}, {pretty_dt}, report steady momentum around "
            f"{arc_head.lower()}, with {b_hook.lower()} setting the pace across morning cabinet and trade briefings."
        )
        p2 = sanitize_cfont_en(
            f"{lens_sentence} {arc_body}"
            + (f" Earlier on the chronicle wire, {recent_milestone_note}" if recent_milestone_note else "")
        )
        p3 = sanitize_cfont_en(
            f"Closer to home at {b_loc} and Los Santos International, freight forwarders and civic planners "
            f"note how global shifts in energy, shipping, and telecommunications translate directly into "
            f"harbor crane schedules, WTI fuel costs ({fmt_price(wti['price'])}/bbl), and West Coast commerce."
        )
        p4 = sanitize_cfont_en(
            f"Looking through the second half of {m_name} {y}, diplomatic desks expect sovereign bond stability, "
            f"Gold reserves ({fmt_price(xau['price'])}/oz), and cross-border tech standards to anchor multilateral talks."
        )

    elif cat == "life_net":
        b_tag, b_hook, b_loc = LIFE_BEATS[beat_idx]
        title_templates = (
            f"{b_tag} ({m_name} {d}): {short_arc} Lights Up {w_name} Feeds",
            f"Inside {b_loc} ({m_name} {d}): {b_hook}",
            f"{b_tag} at {b_loc} ({m_name} {d}): {lens_head}",
            f"{w_name} Culture ({m_name} {d}): {b_tag} & {b_loc}",
        )
        title = fit_headline_cfont(title_templates[beat_idx % len(title_templates)])
        subhead = sanitize_cfont_en(
            f"{b_hook} this {w_name} ({pretty_dt}), capturing the unmistakable mood of {m_name} {y}."
        )
        p1 = sanitize_cfont_en(
            f"Spend an evening near {b_loc} on {pretty_dt} and the signature rhythm of {y} is impossible to "
            f"miss: {b_hook.lower()}, blending pocket-screen convenience with coastal San Andreas warmth."
        )
        p2 = sanitize_cfont_en(
            f"{lens_sentence} {arc_body}"
            + (f" Readers still talk about how {recent_milestone_note}" if recent_milestone_note else "")
        )
        p3 = sanitize_cfont_en(
            f"Hardware reviewers in San Fierro and radio DJs overlooking Vinewood Boulevard point out how "
            f"quickly everyday habits are evolving - from how friends share music and photos to how night "
            f"owls unwind after midnight drives down the Great Ocean Highway."
        )
        w_life = whale_notes.get("life_net", "")
        p4 = sanitize_cfont_en(
            f"Whether queuing up favorite {y} tracks or meeting friends by the pier lights, {pretty_dt} "
            f"captures a slice of internet history worth bookmarking. {w_life}".strip()
        )

    elif cat == "anime_game":
        b_tag, b_hook, b_loc = ACG_BEATS[beat_idx]
        title_templates = (
            f"{b_tag}: {short_arc} Energizes {m_name} {d} Nights",
            f"From {b_loc} ({m_name} {d}): {b_hook}",
            f"{b_tag} ({w_name}, {m_name} {d}): {lens_head}",
            f"{b_loc} Dispatch ({m_name} {d}): {short_arc}",
        )
        title = fit_headline_cfont(title_templates[beat_idx % len(title_templates)])
        subhead = sanitize_cfont_en(
            f"{b_hook} on {pretty_dt} as {y}'s anime broadcasts and gaming meta hit full stride."
        )
        p1 = sanitize_cfont_en(
            f"Reporting from {b_loc} on {w_name}, {pretty_dt}: {b_hook.lower()}, keeping hobbyists, ranked "
            f"grinders, and late-night simulcast viewers glued to their screens across {m_name} {y}."
        )
        p2 = sanitize_cfont_en(
            f"{lens_sentence} {arc_body}"
            + (f" Community threads are also buzzing after {recent_milestone_note}" if recent_milestone_note else "")
        )
        p3 = sanitize_cfont_en(_get_teyvat_acg_era_note(y, m, beat_idx))
        p4 = sanitize_cfont_en(
            f"As studios polish upcoming patches and seasonal finales for {y}, veterans say the marriage of "
            f"expressive hand-crafted art, unforgettable soundtracks, and responsive combat has never felt stronger."
        )

    elif cat == "finance":
        b_tag = FINANCE_BEATS[beat_idx]
        g_delta = float(g1.get("delta_pct", 0.0))
        l_delta = float(l1.get("delta_pct", 0.0))
        xau_delta = float(xau.get("delta_pct", 0.0))
        if beat_idx % 4 == 0:
            raw_t = f"{b_tag}: {g1['symbol']} ({g_delta:+.1f}%) Leads Tape; Gold XAU at {fmt_price(xau['price'])}"
        elif beat_idx % 4 == 1:
            raw_t = f"Wall St {m_name} {d}: {g1['symbol']} & {stk['sec_gainer']['symbol']} Pace {stk['adv']}-Ticker Advance"
        elif beat_idx % 4 == 2:
            raw_t = f"{b_tag}: Gold {fmt_price(xau['price'])} & WTI {fmt_price(wti['price'])} Steer {w_name} Flows"
        else:
            raw_t = f"{m_name} {d} Market Bell: {g1['symbol']} Rallies While {l1['symbol']} ({l_delta:+.1f}%) Lags"
        title = fit_headline_cfont(raw_t)
        subhead = sanitize_cfont_en(
            f"{g1['symbol']} ({g_delta:+.2f}%) tops {pretty_dt} movers against {l1['symbol']} ({l_delta:+.2f}%), "
            f"with Gold XAU at {fmt_price(xau['price'])}/oz ({xau_delta:+.2f}%)."
        )
        p1 = sanitize_cfont_en(fin_tape_para)
        p2 = sanitize_cfont_en(
            f"Behind today's {w_name} numbers sits the defining macro backdrop of {m_name} {y}: {lens_sentence} "
            f"{arc_body}"
        )
        p3 = sanitize_cfont_en(
            f"{fin_local_line} Secondary volume clusters around {stk['sec_gainer']['symbol']} "
            f"({fmt_price(stk['sec_gainer']['price'])}, {stk['sec_gainer'].get('delta_pct', 0.0):+.2f}%) on "
            f"the bid side and {stk['sec_loser']['symbol']} ({fmt_price(stk['sec_loser']['price'])}, "
            f"{stk['sec_loser'].get('delta_pct', 0.0):+.2f}%) on profit-taking, while industrial Copper prints "
            f"{fmt_price(stk['copper']['price'])}/lb."
        )
        w_fin = whale_notes.get("finance", "")
        p4_base = (
            f"Heading into tomorrow's opening cross, Maze Bank institutional desks advise watching real yields "
            f"and whether {g1['symbol']} holds intraday support alongside physical XAU bullion."
        )
        p4 = sanitize_cfont_en(f"{p4_base} {w_fin}".strip())

    elif cat == "crypto":
        b_tag = CRYPTO_BEATS[beat_idx]
        b_delta = float(btc.get("delta_pct", 0.0))
        h_delta = float(hot_c.get("delta_pct", 0.0))
        if beat_idx % 4 == 0:
            raw_t = f"{b_tag}: BTC Trades at {fmt_price(btc['price'])} ({b_delta:+.1f}%) as {hot_c['symbol']} Moves {h_delta:+.1f}%"
        elif beat_idx % 4 == 1:
            raw_t = f"On-Chain {m_name} {d}: Bitcoin {fmt_price(btc['price'])} Anchors {cry['adv']}-Coin Advance"
        elif beat_idx % 4 == 2:
            raw_t = f"{b_tag} ({m_name} {d}): {hot_c['symbol']} Leads Alt Dispersion Around {fmt_price(btc['price'])} BTC"
        else:
            raw_t = f"{w_name} Crypto Wire: BTC {fmt_price(btc['price'])} & {eth['symbol']} {fmt_price(eth['price'])} Test Depth"
        title = fit_headline_cfont(raw_t)
        subhead = sanitize_cfont_en(
            f"Bitcoin prints {fmt_price(btc['price'])} ({b_delta:+.2f}%) on {pretty_dt} while "
            f"{cry['hot_alt_lbl']} ({h_delta:+.2f}%) paces high-beta order books."
        )
        p1 = sanitize_cfont_en(cry_tape_para)
        p2 = sanitize_cfont_en(
            f"Structurally, {m_name} {y} marks a pivotal chapter in blockchain history: {lens_sentence} {arc_body}"
        )
        if y < 2015:
            p3 = sanitize_cfont_en(
                f"San Fierro cryptography circles note that while peer-to-peer mainnet pioneers like BTC and "
                f"LTC settle real blocks around the clock, speculative OTC Venture IOUs let bold desks price "
                f"next-generation protocol concepts years ahead of public genesis."
            )
        else:
            p3 = sanitize_cfont_en(
                f"Liquidity heatmaps from Tokyo to San Fierro show tight bid-ask depth on BTC and ETH alongside "
                f"brisk rotation in BNB ({fmt_price(cry['bnb']['price'])}), LTC ({fmt_price(cry['ltc']['price'])}), "
                f"and perp funding spreads."
            )
        w_cry = whale_notes.get("crypto", "")
        p4_base = (
            f"With blockchain ledgers never sleeping on nights or weekends, desk quants flag {fmt_price(btc['price'])} "
            f"on BTC as the key pivot governing altcoin beta over the next 24 hours."
        )
        p4 = sanitize_cfont_en(f"{p4_base} {w_cry}".strip())

    else:  # sports
        b_tag = SPORTS_BEATS[beat_idx]
        if beat_idx % 4 == 0:
            raw_t = f"{b_tag}: {mq['home']} vs {mq['away']} Headlines {m_name} {d} {mq['league']} Card"
        elif beat_idx % 4 == 1:
            raw_t = f"Floodlight Preview ({m_name} {d}): {spt['fav_name']} ({spt['fav_odd']:.2f}) Tested by {spt['dog_name']}"
        elif beat_idx % 4 == 2:
            raw_t = f"{b_tag}: Fresh Results In as {mq['home']} Hosts {mq['away']} ({mq.get('kickoff', '20:45')})"
        else:
            raw_t = f"{w_name} Sports & Odds: {mq['home']}-{mq['away']} & {cf['home']}-{cf['away']} Lead Slate"
        title = fit_headline_cfont(raw_t)
        subhead = sanitize_cfont_en(
            f"Oddsmakers install {spt['fav_name']} at {spt['fav_odd']:.2f} ahead of {mq['kickoff']} kickoff "
            f"after a dramatic slate of settled scores across our 5-league chronicle."
        )
        p1 = sanitize_cfont_en(spt_live_recap)
        p2 = sanitize_cfont_en(spt_live_preview)
        p3 = sanitize_cfont_en(
            f"Tactically, {m_name} {y} carries unmistakable weight: {lens_sentence} {arc_body} Analysts "
            f"studying {mq['home']} versus {mq['away']} point to transition pace and midfield press resistance "
            f"as the decisive edge behind that {mq.get('hcap', '-0.25')} handicap line."
        )
        w_spt = whale_notes.get("sports", "")
        p4_base = (
            f"Inside Las Venturas sportsbooks, sharp two-way action is splitting between favorite {spt['fav_name']} "
            f"({spt['fav_odd']:.2f}) and value hunters backing {spt['dog_name']} at {spt['dog_odd']:.2f} before "
            f"lineups lock."
        )
        p4 = sanitize_cfont_en(f"{p4_base} {w_spt}".strip())

    vibe_raw = f"{pretty_dt} ({lens_head}) - {era_info.get('vibe', '')}"
    vibe = sanitize_cfont_en(vibe_raw)
    paras = [p for p in (p1, p2, p3, p4) if p]
    return {
        "title": title,
        "subhead": subhead,
        "byline": byline,
        "paragraphs": paras,
        "body": "\n\n".join(paras),
        "vibe": vibe,
        "summary": sanitize_cfont_en(f"{p1} {p2[:160]}"),
    }


def build_enriched_article_vi(
    *,
    cat: str,
    raw: dict,
    current_date: datetime.date,
    day_index: int,
    live_fin_ticker: str,
    live_cry_ticker: str,
    live_spt_ticker: str,
) -> dict:
    """Provides clean 3-paragraph scrollable structure when Vietnamese (`lang='vi'`) is selected."""
    roster = BYLINE_ROSTER_VI.get(cat, BYLINE_ROSTER_VI["world"])
    byline = roster[(current_date.toordinal() + day_index) % len(roster)]
    title_vi = str(raw.get("title") or "")
    sum_vi = str(raw.get("summary") or "")
    vibe_vi = str(raw.get("vibe") or "")
    date_str = current_date.strftime("%d/%m/%Y")

    subhead = f"Ban tin chuyen sau ngay {date_str} tren The Eagle Times."
    p1 = sum_vi
    if cat == "finance":
        p2 = live_fin_ticker
    elif cat == "crypto":
        p2 = live_cry_ticker
    elif cat == "sports":
        p2 = live_spt_ticker
    else:
        p2 = f"Ghi nhan tu Los Santos, San Fierro den Akihabara va Mondstadt trong ngay {date_str}."
    p3 = vibe_vi or f"Bien nien su Project Eagle ngay {date_str}."
    paras_clean = [sanitize_cfont_en(x) for x in (p1, p2, p3) if str(x).strip()]
    return {
        "title": fit_headline_cfont(title_vi),
        "title_vi": title_vi,
        "subhead": sanitize_cfont_en(subhead),
        "byline": sanitize_cfont_en(byline),
        "paragraphs": paras_clean,
        "body": "\n\n".join(paras_clean),
        "vibe": sanitize_cfont_en(vibe_vi),
        "summary": sanitize_cfont_en(f"{p1} {p2}"),
        "summary_raw": f"{p1} {p2}",
    }


def enrich_newspaper_articles(
    *,
    raw_items: List[Tuple[str, dict]],
    current_date: datetime.date,
    day_index: int,
    era_info: dict,
    cmeta_dict: dict,
    stocks_market: Optional[dict],
    crypto_market: Optional[dict],
    sport_history: Optional[list],
    fixtures: Optional[list],
    extra_context: Optional[dict],
    year_arc_en: dict,
    monthly_lenses_en: dict,
    month_exact_index_en: dict,
    is_vi: bool,
    live_fin_ticker: str,
    live_cry_ticker: str,
    live_spt_ticker: str,
    format_5_lines_fn,
) -> List[dict]:
    """Builds the full list of enriched v6.3 `articles` dicts (with `subhead`, `byline`, `paragraphs`)."""
    y = max(2010, min(2025, current_date.year))
    m = current_date.month
    d = current_date.day
    date_str = current_date.strftime("%d/%m/%Y")

    stk = _analyze_stocks_board(stocks_market)
    cry = _analyze_crypto_board(crypto_market, y)
    spt = _analyze_sports_board(sport_history, fixtures, day_index)
    whale_notes = _build_whale_commentary(extra_context, stocks_market, crypto_market)

    articles: List[dict] = []
    for idx, (cat, raw) in enumerate(raw_items, start=1):
        cmeta = cmeta_dict.get(cat, cmeta_dict["world"])
        badge = sanitize_cfont_en(str(raw.get("badge") or cmeta["badge"]))

        if is_vi:
            enr = build_enriched_article_vi(
                cat=cat,
                raw=raw,
                current_date=current_date,
                day_index=day_index,
                live_fin_ticker=live_fin_ticker,
                live_cry_ticker=live_cry_ticker,
                live_spt_ticker=live_spt_ticker,
            )
            title_vi_out = enr["title_vi"]
            sum_vi_out = enr["summary_raw"]
            vibe_vi_out = str(raw.get("vibe") or "")
        else:
            arc_pair = (year_arc_en.get(y) or {}).get(
                cat,
                ("Global Chronicle & Market Shift", "Key developments shape the year across capitals and markets."),
            )
            lens_list = monthly_lenses_en.get(cat) or [("Monthly Dispatch", "Key updates across {year}.")]
            lens_pair = lens_list[(m - 1) % len(lens_list)]

            # Find most recent exact-date milestone earlier this month (strictly ed < d, never future!)
            past_m = [
                (ed_v, m_art)
                for ed_v, m_art in month_exact_index_en.get((y, m, cat), ())
                if ed_v < d
            ]
            recent_note = ""
            if past_m:
                past_m.sort(key=lambda x: x[0], reverse=True)
                ed_last, art_last = past_m[0]
                clean_t = re.sub(r"^\[[^\]]+\]\s*", "", str(art_last.get("title", "")))
                recent_note = f"{MONTH_NAMES_EN[m - 1]} {ed_last} brought '{clean_t}'."

            enr = build_enriched_article_en(
                cat=cat,
                raw=raw,
                current_date=current_date,
                day_index=day_index,
                era_info=era_info,
                year_arc_pair=arc_pair,
                month_lens_pair=lens_pair,
                recent_milestone_note=recent_note,
                stk=stk,
                cry=cry,
                spt=spt,
                whale_notes=whale_notes,
            )
            title_vi_out = enr["title"]
            sum_vi_out = enr["summary"]
            vibe_vi_out = enr["vibe"]

        art_lines = format_5_lines_fn(
            badge,
            date_str,
            enr["title"],
            enr["summary"],
            enr["vibe"],
            width=58,
            is_vi=is_vi,
        )

        articles.append({
            "id": f"D{day_index}_{idx}_{cat.upper()}",
            "category": cat,
            "category_name": sanitize_cfont_en(cmeta["name"]),
            "category_name_vi": cmeta["name_vi"],
            "badge": badge,
            "banner_tex": cmeta["banner_tex"],
            "is_exact_date": bool(raw.get("is_exact_date", False)),
            "title": enr["title"],
            "title_vi": title_vi_out,
            "subhead": enr["subhead"],
            "byline": enr["byline"],
            "paragraphs": enr["paragraphs"],
            "body": enr["body"],
            "summary": enr["summary"],
            "summary_vi": sum_vi_out,
            "vibe": enr["vibe"],
            "vibe_vi": vibe_vi_out,
            "lines": art_lines,
        })

    return articles
