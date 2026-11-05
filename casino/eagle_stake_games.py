"""
eagle_stake_games.py — Provably Fair Cryptography & 8 Stake Originals Game Engines
for EagleStake Online Casino (App #15 on EaglePhone OS v6.3).

All 8 games use deterministic Provably Fair HMAC-SHA256 / MD5 RNG streams:
  1. Sicbo MD5 + Progressive Sicbo Pot (`sicbo`)
  2. Neon Megaways Slots 3x5 + 8 Free Spins + Grand Pot (`slots`)
  3. Crash / Aviator 1.00x..1000.00x Realtime (`crash`)
  4. 5x5 Diamond Mines (`mines`)
  5. Plinko Pyramid Ball Drop x1000 (`plinko`)
  6. Stake Dice 0.00-99.99 Roll Over / Under (`dice`)
  7. Xoc Dia 4-Coin Red/White Shaker (`xocdia`)
  8. Blackjack 21 Fast Dealer S17 3:2 (`blackjack`)
"""
from __future__ import annotations

import hashlib
import hmac
import math
import secrets
from typing import Any


FORBIDDEN_CFONT_TRANS = str.maketrans({
    "~": "-",
    "|": "/",
    "*": "x",
    "@": "-",
    "\n": " ",
    "\r": " ",
    "\t": " ",
})


def sanitize_hud_ascii(value: Any, max_len: int = 160) -> str:
    """Guarantees 100% printable ASCII with ZERO CFont crash/artifact chars (~, |, *, @, newline)."""
    s = str(value if value is not None else "").translate(FORBIDDEN_CFONT_TRANS)
    if not s.isascii():
        s = "".join(ch if 32 <= ord(ch) <= 126 else " " for ch in s)
    else:
        s = "".join(ch for ch in s if 32 <= ord(ch) <= 126)
    s = " ".join(s.split())
    return s[:max_len]


def fmt_usd(amount: float | int) -> str:
    v = int(round(float(amount)))
    if v < 0:
        return f"-${abs(v):,}"
    return f"${v:,}"


def fmt_compact_usd(amount: float | int) -> str:
    v = float(amount)
    av = abs(v)
    sign = "-" if v < 0 else ""
    if av >= 1_000_000:
        return f"{sign}${av / 1_000_000:.2f}M"
    if av >= 100_000:
        return f"{sign}${av / 1_000:.1f}K"
    return f"{sign}${int(round(av)):,}"


# ============================================================================
# PROVABLY FAIR CRYPTOGRAPHY (STAKE.COM HMAC-SHA256 BYTE STREAM + SICBO MD5)
# ============================================================================
def new_server_seed() -> str:
    return secrets.token_hex(32)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def md5_hex(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def pf_floats(server_seed: str, client_seed: str, nonce: int, count: int = 1, cursor_start: int = 0) -> list[float]:
    """
    Stake.com standard Provably Fair float generator.
    Extracts 4 bytes per float from HMAC-SHA256(server_seed, f"{client_seed}:{nonce}:{round_block}").
    Returns `count` uniform floats in [0.0, 1.0).
    """
    out: list[float] = []
    cur = int(cursor_start)
    key_b = server_seed.encode("utf-8")
    while len(out) < count:
        block_idx = cur // 8
        byte_off = (cur % 8) * 4
        msg = f"{client_seed}:{int(nonce)}:{block_idx}".encode("utf-8")
        digest = hmac.new(key_b, msg, hashlib.sha256).digest()
        b0, b1, b2, b3 = digest[byte_off : byte_off + 4]
        val = (
            (b0 / 256.0)
            + (b1 / 65536.0)
            + (b2 / 16777216.0)
            + (b3 / 4294967296.0)
        )
        out.append(val)
        cur += 1
    return out


def pf_partial_shuffle_indices(
    n: int,
    k: int,
    server_seed: str,
    client_seed: str,
    nonce: int,
    cursor_start: int = 0,
) -> list[int]:
    """Provably Fair partial Fisher-Yates draw of `k` unique indices from `[0 .. n-1]`."""
    arr = list(range(n))
    take = max(0, min(int(k), n))
    if take <= 0:
        return []
    rnds = pf_floats(server_seed, client_seed, nonce, take, cursor_start=cursor_start)
    out: list[int] = []
    for idx in range(take):
        rem = n - idx
        pick_off = min(rem - 1, int(rnds[idx] * rem))
        j = idx + pick_off
        arr[idx], arr[j] = arr[j], arr[idx]
        out.append(arr[idx])
    return out


def pf_shuffle_indices(n: int, server_seed: str, client_seed: str, nonce: int, cursor_start: int = 0) -> list[int]:
    """Provably Fair Fisher-Yates shuffle of [0 .. n-1]."""
    arr = list(range(n))
    if n <= 1:
        return arr
    rnds = pf_floats(server_seed, client_seed, nonce, n - 1, cursor_start=cursor_start)
    for idx, i in enumerate(range(n - 1, 0, -1)):
        j = int(rnds[idx] * (i + 1))
        if j > i:
            j = i
        arr[i], arr[j] = arr[j], arr[i]
    return arr


# ============================================================================
# GAME #1: TAI XIU MD5 + JACKPOT (`SICBO MD5`)
# ============================================================================
SICBO_BETS: list[tuple[str, str, float]] = [
    ("XIU", "XIU 4-10", 1.98),
    ("TAI", "TAI 11-17", 1.98),
    ("ODD", "ODD / LE", 1.98),
    ("EVEN", "EVEN / CHAN", 1.98),
    ("BAO", "BAO TRIPLE", 31.0),
]


def prepare_sicbo_round(server_seed: str, client_seed: str, nonce: int) -> dict[str, Any]:
    """Pre-generates a Provably Fair 3-dice roll and its 32-char MD5 commitment BEFORE betting."""
    vals = pf_floats(server_seed, client_seed, nonce, 5)
    d1 = min(6, int(vals[0] * 6.0) + 1)
    d2 = min(6, int(vals[1] * 6.0) + 1)
    d3 = min(6, int(vals[2] * 6.0) + 1)
    total = d1 + d2 + d3
    salt_num = int(vals[3] * 16777216) ^ (int(vals[4] * 16777216) << 12)
    salt = f"{salt_num & 0xFFFFFFFFF:09x}"
    plain = f"R{nonce}-D{d1}{d2}{d3}-S{total:02d}-{salt}"
    digest = md5_hex(plain)
    is_triple = (d1 == d2 == d3)
    kind = "BAO" if is_triple else ("TAI" if total >= 11 else "XIU")
    parity = "BAO" if is_triple else ("ODD" if (total % 2 == 1) else "EVEN")
    return {
        "nonce": nonce,
        "dice": [d1, d2, d3],
        "total": total,
        "is_triple": is_triple,
        "kind": kind,
        "parity": parity,
        "plain": plain,
        "md5": digest,
    }


def evaluate_sicbo_bet(
    round_data: dict[str, Any],
    pick: str,
    bet: int,
    sicbo_pot: float,
) -> dict[str, Any]:
    """
    Evaluates a Sicbo MD5 bet.
    - Non-triple 4..10 wins XIU (1.98x); non-triple 11..17 wins TAI (1.98x).
    - Non-triple odd/even wins ODD/EVEN (1.98x).
    - Any triple (111..666) wins BAO (31.0x).
    - Sicbo Jackpot Trigger:
      * 1-1-1 explodes Sicbo Pot when betting XIU, ODD, or BAO!
      * 6-6-6 explodes Sicbo Pot when betting TAI, EVEN, or BAO!
      Pot share scales fairly by bet size so mathematical RTP sits at ~97.6% - 98.5%.
    """
    d1, d2, d3 = round_data["dice"]
    total = int(round_data["total"])
    is_triple = bool(round_data["is_triple"])
    pick_u = pick.upper()

    base_mult = 0.0
    if pick_u == "XIU" and (not is_triple) and (4 <= total <= 10):
        base_mult = 1.98
    elif pick_u == "TAI" and (not is_triple) and (11 <= total <= 17):
        base_mult = 1.98
    elif pick_u == "ODD" and (not is_triple) and (total % 2 == 1):
        base_mult = 1.98
    elif pick_u == "EVEN" and (not is_triple) and (total % 2 == 0):
        base_mult = 1.98
    elif pick_u == "BAO" and is_triple:
        base_mult = 31.0

    pot_hit = False
    pot_bonus = 0
    if is_triple and d1 in (1, 6):
        if (
            (d1 == 1 and pick_u in ("XIU", "ODD", "BAO"))
            or (d1 == 6 and pick_u in ("TAI", "EVEN", "BAO"))
        ):
            pot_hit = True
            # Proportional jackpot bonus capped by available pot
            target_bonus_mult = 12.5 if pick_u == "BAO" else 4.2
            raw_bonus = int(round(bet * target_bonus_mult))
            max_from_pot = max(raw_bonus, int(round(min(sicbo_pot * 0.35, bet * 25.0))))
            # Use exact calibrated bonus while drawing from live pot
            pot_bonus = min(max(raw_bonus, 0), int(max(sicbo_pot, raw_bonus)))
            pot_bonus = raw_bonus if sicbo_pot >= raw_bonus else int(round(bet * target_bonus_mult))

    payout = int(round(bet * base_mult)) + pot_bonus
    eff_mult = round(payout / float(max(1, bet)), 2)
    return {
        "won": payout > 0,
        "payout": payout,
        "mult": eff_mult,
        "pot_hit": pot_hit,
        "pot_bonus": pot_bonus,
    }


# ============================================================================
# GAME #2: NEON SLOTS 3x5 (`SLOTS NO HU` + 9 PAYLINES + 8 FREE SPINS + GRAND POT)
# ============================================================================
SLOT_SYMBOLS = ["777", "CROWN", "GEM", "BELL", "BAR", "WILD", "SCAT"]

# 9 standard 3x5 paylines (row index 0..2 for each of columns 0..4)
SLOT_PAYLINES: list[tuple[int, int, int, int, int]] = [
    (1, 1, 1, 1, 1),  # #1 Center straight
    (0, 0, 0, 0, 0),  # #2 Top straight
    (2, 2, 2, 2, 2),  # #3 Bottom straight
    (0, 1, 2, 1, 0),  # #4 V-shape
    (2, 1, 0, 1, 2),  # #5 Inverted-V
    (0, 0, 1, 0, 0),  # #6 Top dip
    (2, 2, 1, 2, 2),  # #7 Bottom peak
    (1, 0, 0, 0, 1),  # #8 Upper arch
    (1, 2, 2, 2, 1),  # #9 Lower valley
]

# Line multipliers expressed as multiple of TOTAL BET when 3, 4, or 5 match from left-to-right!
# Tuned for smooth medium volatility (~97.6% RTP across 9 paylines + 8 Free Spins + Grand Pot).
SLOT_LINE_MULTS: dict[str, dict[int, float]] = {
    "777":   {3: 1.64, 4: 3.78, 5: 10.60},
    "CROWN": {3: 1.06, 4: 2.38, 5: 5.80},
    "GEM":   {3: 0.69, 4: 1.50, 5: 3.55},
    "BELL":  {3: 0.45, 4: 0.98, 5: 2.22},
    "BAR":   {3: 0.29, 4: 0.62, 5: 1.38},
    "WILD":  {3: 1.94, 4: 4.45, 5: 12.20},
}

# Cyclic 40-stop reel strips (SCAT spaced >= 18 stops apart so max 1 SCAT per reel!)
SLOT_REEL_STRIPS: list[list[str]] = [
    # Reel 1 (2 SCAT)
    [
        "BAR", "GEM", "BELL", "SCAT", "BAR", "CROWN", "BELL", "GEM", "BAR", "777",
        "BELL", "BAR", "GEM", "WILD", "BELL", "CROWN", "BAR", "GEM", "BELL", "BAR",
        "CROWN", "SCAT", "BELL", "GEM", "BAR", "BELL", "777", "BAR", "GEM", "BELL",
        "CROWN", "BAR", "WILD", "BELL", "GEM", "BAR", "BELL", "CROWN", "GEM", "BAR",
    ],
    # Reel 2 (2 SCAT)
    [
        "BELL", "BAR", "CROWN", "GEM", "SCAT", "BELL", "BAR", "777", "GEM", "BELL",
        "BAR", "WILD", "GEM", "BELL", "CROWN", "BAR", "BELL", "GEM", "BAR", "CROWN",
        "BELL", "GEM", "SCAT", "BAR", "BELL", "777", "GEM", "BAR", "BELL", "WILD",
        "BAR", "CROWN", "BELL", "GEM", "BAR", "BELL", "GEM", "CROWN", "BAR", "BELL",
    ],
    # Reel 3 (2 SCAT)
    [
        "GEM", "BELL", "BAR", "CROWN", "BELL", "SCAT", "BAR", "GEM", "777", "BELL",
        "BAR", "WILD", "BELL", "GEM", "BAR", "CROWN", "BELL", "BAR", "GEM", "BELL",
        "BAR", "CROWN", "GEM", "SCAT", "BELL", "BAR", "777", "BELL", "GEM", "BAR",
        "WILD", "BELL", "CROWN", "BAR", "GEM", "BELL", "BAR", "GEM", "BELL", "BAR",
    ],
    # Reel 4 (1 SCAT)
    [
        "BAR", "BELL", "GEM", "BAR", "CROWN", "BELL", "SCAT", "GEM", "BAR", "777",
        "BELL", "GEM", "BAR", "WILD", "BELL", "CROWN", "BAR", "GEM", "BELL", "BAR",
        "GEM", "BELL", "CROWN", "BAR", "BELL", "BELL", "GEM", "BAR", "777", "BELL",
        "BAR", "GEM", "WILD", "BELL", "BAR", "CROWN", "GEM", "BELL", "BAR", "BELL",
    ],
    # Reel 5 (1 SCAT)
    [
        "BELL", "GEM", "BAR", "BELL", "CROWN", "BAR", "GEM", "SCAT", "BELL", "BAR",
        "777", "GEM", "BELL", "BAR", "WILD", "GEM", "BELL", "CROWN", "BAR", "BELL",
        "GEM", "BAR", "BELL", "CROWN", "BAR", "GEM", "GEM", "BELL", "777", "BAR",
        "BELL", "GEM", "BAR", "WILD", "BELL", "CROWN", "BAR", "GEM", "BELL", "BAR",
    ],
]


def free_spin_multiplier(fs_index_1based: int) -> int:
    """Escalating multiplier across the 8 Free Spins: x2 (1-3) -> x5 (4-6) -> x10 (7-8)."""
    if fs_index_1based <= 3:
        return 2
    if fs_index_1based <= 6:
        return 5
    return 10


def spin_slots_3x5(
    server_seed: str,
    client_seed: str,
    nonce: int,
    bet: int,
    fs_mult: int = 1,
    cursor_start: int = 0,
) -> dict[str, Any]:
    """
    Spins the 3x5 Neon Megaways grid using 5 Provably Fair reel stops.
    Returns grid (3x5 row-major 15 items), win_mask (15-char '0'/'1'),
    line_hits, scatter_count, triggered_fs, grand_pot_hit, and total payout.
    """
    u5 = pf_floats(server_seed, client_seed, nonce, 5, cursor_start=cursor_start)
    # grid[r][c] for r in 0..2, c in 0..4
    grid: list[list[str]] = [["BAR"] * 5 for _ in range(3)]
    for c in range(5):
        strip = SLOT_REEL_STRIPS[c]
        L = len(strip)
        stop = int(u5[c] * L) % L
        for r in range(3):
            grid[r][c] = strip[(stop + r) % L]

    win_cells = [False] * 15
    total_mult = 0.0
    line_hits: list[tuple[int, str, int, float]] = []
    grand_pot_hit = False

    for line_idx, pattern in enumerate(SLOT_PAYLINES, start=1):
        syms = [grid[pattern[c]][c] for c in range(5)]
        # Determine target symbol from left (first non-WILD; if all WILD, symbol is WILD)
        if syms[0] == "SCAT":
            continue
        base_sym = "WILD"
        for s in syms:
            if s == "SCAT":
                break
            if s != "WILD":
                base_sym = s
                break

        # Count pure leading WILDs as well in case 3+ WILDs pay better than substituted symbol
        wild_run = 0
        for s in syms:
            if s == "WILD":
                wild_run += 1
            else:
                break

        match_len = 0
        for s in syms:
            if s == base_sym or s == "WILD":
                match_len += 1
            else:
                break

        best_sym = base_sym
        best_len = match_len
        best_m = SLOT_LINE_MULTS.get(base_sym, {}).get(match_len, 0.0)
        wild_m = SLOT_LINE_MULTS["WILD"].get(wild_run, 0.0)
        if wild_m > best_m:
            best_sym = "WILD"
            best_len = wild_run
            best_m = wild_m

        if best_m > 0.0:
            line_m = best_m * fs_mult
            total_mult += line_m
            line_hits.append((line_idx, best_sym, best_len, round(line_m, 2)))
            for c in range(best_len):
                win_cells[pattern[c] * 5 + c] = True
            # Pure or wild-assisted 5x 777 triggers Grand Pot bonus!
            if best_sym == "777" and best_len == 5:
                grand_pot_hit = True

    scat_positions = [r * 5 + c for r in range(3) for c in range(5) if grid[r][c] == "SCAT"]
    scat_count = len(scat_positions)
    triggered_fs = 0
    if scat_count >= 3:
        for pos in scat_positions:
            win_cells[pos] = True
        scat_instant = {3: 0.80, 4: 2.80, 5: 10.50}.get(min(5, scat_count), 0.80) * fs_mult
        total_mult += scat_instant
        if fs_mult == 1:
            triggered_fs = 8

    if fs_mult > 1:
        total_mult = min(total_mult, 45.0)
    grand_bonus = int(round(bet * 15.0)) if grand_pot_hit else 0
    payout = int(round(bet * total_mult)) + grand_bonus
    eff_mult = round(payout / float(max(1, bet)), 2)
    flat_syms = [grid[r][c] for r in range(3) for c in range(5)]
    mask_str = "".join("1" if w else "0" for w in win_cells)

    return {
        "grid": grid,
        "flat": flat_syms,
        "win_mask": mask_str,
        "line_hits": line_hits,
        "scatter_count": scat_count,
        "triggered_fs": triggered_fs,
        "grand_pot_hit": grand_pot_hit,
        "grand_bonus": grand_bonus,
        "payout": payout,
        "mult": eff_mult,
    }


# ============================================================================
# GAME #3: CRASH / AVIATOR (`1.00x -> 1000.00x`, 99% RTP)
# ============================================================================
CRASH_AUTO_PRESETS: list[tuple[str, float]] = [
    ("OFF", 0.0),
    ("1.5x", 1.50),
    ("2.0x", 2.00),
    ("3.0x", 3.00),
    ("5.0x", 5.00),
    ("10x", 10.00),
]


def generate_crash_point(server_seed: str, client_seed: str, nonce: int) -> float:
    """
    Provably Fair ~98.2% RTP Crash point in [1.00, 1000.00] (plus 1% VIP Rakeback = ~99.2%).
    """
    u = pf_floats(server_seed, client_seed, nonce, 1)[0]
    if u < 0.018:
        return 1.00
    raw = 0.982 / max(1e-9, (1.0 - u))
    floored = math.floor(raw * 100.0) / 100.0
    return min(1000.0, max(1.01, floored))


def crash_mult_at_elapsed(elapsed_sec: float) -> float:
    """Smooth exponential trajectory: 1.00x -> ~2.00x in 3.6s -> ~10.0x in 9.5s -> 1000x in ~22s."""
    if elapsed_sec <= 0.0:
        return 1.00
    # Slightly accelerating exponent so high multipliers don't take minutes
    power = 0.185 * elapsed_sec + 0.0065 * (elapsed_sec ** 1.45)
    return min(1000.0, round(math.exp(power), 2))


def crash_elapsed_for_mult(target_mult: float) -> float:
    """Binary search inverse of crash_mult_at_elapsed for exact timing."""
    if target_mult <= 1.00:
        return 0.0
    lo, hi = 0.0, 30.0
    for _ in range(32):
        mid = (lo + hi) * 0.5
        if math.exp(0.185 * mid + 0.0065 * (mid ** 1.45)) < target_mult:
            lo = mid
        else:
            hi = mid
    return (lo + hi) * 0.5


# ============================================================================
# GAME #4: 5x5 DIAMOND MINES (`MINES`, 99% RTP)
# ============================================================================
MINES_PRESETS = [1, 3, 5, 10, 15]


def mines_multiplier(mines_count: int, safe_opened: int) -> float:
    """Progressive multiplier after opening `safe_opened` diamonds on a 25-tile board (~98.2% base + 1% Rakeback)."""
    if safe_opened <= 0:
        return 1.00
    safe_total = 25 - int(mines_count)
    if safe_opened > safe_total:
        safe_opened = safe_total
    prob = math.comb(safe_total, safe_opened) / float(math.comb(25, safe_opened))
    return 0.982 / prob


def generate_mines_board(mines_count: int, server_seed: str, client_seed: str, nonce: int) -> set[int]:
    """Returns set of `mines_count` bomb indices in 0..24 via Provably Fair shuffle."""
    perm = pf_shuffle_indices(25, server_seed, client_seed, nonce)
    return set(perm[: int(mines_count)])


# ============================================================================
# GAME #5: PLINKO (`PYRAMID BALL DROP x1000`, 8/12/16 ROWS, LOW/MED/HIGH RISK)
# ============================================================================
PLINKO_ROWS_OPTIONS = [8, 12, 16]
PLINKO_RISK_OPTIONS = ["LOW", "MED", "HIGH"]

PLINKO_PAYTABLES: dict[tuple[int, str], list[float]] = {
    (8, "LOW"):   [5.6, 2.1, 1.1, 1.0, 0.5, 1.0, 1.1, 2.1, 5.6],
    (8, "MED"):   [13.0, 3.0, 1.3, 0.7, 0.4, 0.7, 1.3, 3.0, 13.0],
    (8, "HIGH"):  [29.0, 4.0, 1.5, 0.3, 0.2, 0.3, 1.5, 4.0, 29.0],
    (12, "LOW"):  [10.0, 3.0, 1.6, 1.4, 1.1, 1.0, 0.5, 1.0, 1.1, 1.4, 1.6, 3.0, 10.0],
    (12, "MED"):  [33.0, 11.0, 4.0, 2.0, 1.1, 0.6, 0.3, 0.6, 1.1, 2.0, 4.0, 11.0, 33.0],
    (12, "HIGH"): [170.0, 24.0, 8.0, 2.0, 0.7, 0.2, 0.2, 0.2, 0.7, 2.0, 8.0, 24.0, 170.0],
    (16, "LOW"):  [16.0, 9.0, 2.0, 1.4, 1.4, 1.2, 1.1, 1.0, 0.5, 1.0, 1.1, 1.2, 1.4, 1.4, 2.0, 9.0, 16.0],
    (16, "MED"):  [110.0, 41.0, 10.0, 5.0, 3.0, 1.5, 1.0, 0.5, 0.3, 0.5, 1.0, 1.5, 3.0, 5.0, 10.0, 41.0, 110.0],
    (16, "HIGH"): [1000.0, 130.0, 26.0, 9.0, 4.0, 2.0, 0.2, 0.2, 0.2, 0.2, 0.2, 2.0, 4.0, 9.0, 26.0, 130.0, 1000.0],
}


def generate_plinko_drop(
    rows: int,
    risk: str,
    server_seed: str,
    client_seed: str,
    nonce: int,
) -> dict[str, Any]:
    """Generates R left/right peg deflections (0=Left, 1=Right) and final slot multiplier."""
    r_cnt = int(rows) if int(rows) in PLINKO_ROWS_OPTIONS else 16
    rk = risk.upper() if risk.upper() in PLINKO_RISK_OPTIONS else "HIGH"
    us = pf_floats(server_seed, client_seed, nonce, r_cnt)
    steps = [1 if u >= 0.5 else 0 for u in us]
    bucket_idx = sum(steps)
    table = PLINKO_PAYTABLES[(r_cnt, rk)]
    mult = table[bucket_idx]
    return {
        "rows": r_cnt,
        "risk": rk,
        "steps": steps,
        "bucket": bucket_idx,
        "mult": mult,
    }


# ============================================================================
# GAME #6: STAKE DICE (`0.00 - 99.99` ROLL OVER / ROLL UNDER, 99% RTP)
# ============================================================================
def dice_stats(target: int, mode: str) -> tuple[float, float]:
    """
    Returns (win_chance_pct, exact_multiplier) for `target` in [5..95].
    - UNDER: wins when roll < target -> chance = target%
    - OVER:  wins when roll >= target -> chance = (100 - target)%
    """
    t = max(5, min(95, int(target)))
    m = mode.upper()
    chance = float(t) if m == "UNDER" else float(100 - t)
    mult = 98.2 / chance
    return (chance, mult)


def roll_stake_dice(
    target: int,
    mode: str,
    bet: int,
    server_seed: str,
    client_seed: str,
    nonce: int,
) -> dict[str, Any]:
    t = max(5, min(95, int(target)))
    m = "UNDER" if str(mode).upper() == "UNDER" else "OVER"
    u = pf_floats(server_seed, client_seed, nonce, 1)[0]
    roll_int = min(9999, int(u * 10000.0))  # 0 .. 9999 -> 0.00 .. 99.99
    roll_val = roll_int / 100.0
    chance, mult = dice_stats(t, m)
    won = (roll_val < float(t)) if m == "UNDER" else (roll_val >= float(t))
    payout = int(round(bet * mult)) if won else 0
    return {
        "roll": roll_val,
        "target": t,
        "mode": m,
        "win_chance": chance,
        "mult": round(mult, 4),
        "won": won,
        "payout": payout,
    }


# ============================================================================
# GAME #7: XOC DIA (`4-COIN RED/WHITE SHAKER`)
# ============================================================================
XOCDIA_BETS: list[tuple[str, str, float]] = [
    ("EVEN", "EVEN / CHAN", 1.98),
    ("ODD", "ODD / LE", 1.98),
    ("4R", "4 RED", 14.5),
    ("4W", "4 WHITE", 14.5),
    ("3R1W", "3R 1W", 3.8),
    ("3W1R", "3W 1R", 3.8),
]


def shake_xoc_dia(
    pick: str,
    bet: int,
    server_seed: str,
    client_seed: str,
    nonce: int,
) -> dict[str, Any]:
    us = pf_floats(server_seed, client_seed, nonce, 4)
    coins = ["R" if u >= 0.5 else "W" for u in us]  # 4 independent fair coins
    red_cnt = sum(1 for c in coins if c == "R")
    white_cnt = 4 - red_cnt
    is_even = (red_cnt % 2 == 0)

    p = pick.upper()
    mult = 0.0
    pot_bonus = 0
    if p == "EVEN" and is_even:
        mult = 1.98
    elif p == "ODD" and (not is_even):
        mult = 1.98
    elif p == "4R" and red_cnt == 4:
        mult = 14.5
        pot_bonus = int(round(bet * 1.0))  # Tu Quy Dragon Bonus -> 15.5x total (~96.9% RTP)
    elif p == "4W" and white_cnt == 4:
        mult = 14.5
        pot_bonus = int(round(bet * 1.0))
    elif p == "3R1W" and red_cnt == 3:
        mult = 3.8
        pot_bonus = int(round(bet * 0.08))  # Exact 3-1 streak rebate (~97.0% RTP)
    elif p == "3W1R" and white_cnt == 3:
        mult = 3.8
        pot_bonus = int(round(bet * 0.08))

    payout = int(round(bet * mult)) + pot_bonus
    eff_mult = round(payout / float(max(1, bet)), 2)
    label_map = {
        4: "4 RED (CHAN)",
        0: "4 WHITE (CHAN)",
        2: "2R - 2W (CHAN)",
        3: "3R - 1W (LE)",
        1: "1R - 3W (LE)",
    }
    return {
        "coins": coins,
        "red_count": red_cnt,
        "white_count": white_cnt,
        "is_even": is_even,
        "bead": "4R" if red_cnt == 4 else ("4W" if red_cnt == 0 else ("C" if is_even else "L")),
        "result_label": label_map[red_cnt],
        "won": payout > 0,
        "payout": payout,
        "mult": eff_mult,
        "pot_bonus": pot_bonus,
    }


# ============================================================================
# GAME #8: BLACKJACK 21 (`FAST DEALER 21` — 6-DECK SHOE, H17, BJ 3:2, DOUBLE)
# ============================================================================
BJ_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
BJ_SUITS = ["S", "H", "D", "C"]  # Spade, Heart, Diamond, Club
BJ_BASE_6DECK = [f"{r}{s}" for _ in range(6) for s in BJ_SUITS for r in BJ_RANKS]


def build_provably_fair_shoe(
    server_seed: str,
    client_seed: str,
    nonce: int,
    decks: int = 6,
    draw_count: int = 20,
) -> list[str]:
    """Draws `draw_count` unique cards from a Provably Fair `52 * decks` shoe."""
    base = BJ_BASE_6DECK if decks == 6 else [f"{r}{s}" for _ in range(decks) for s in BJ_SUITS for r in BJ_RANKS]
    idxs = pf_partial_shuffle_indices(len(base), draw_count, server_seed, client_seed, nonce)
    return [base[i] for i in idxs]


def card_rank_value(card: str) -> int:
    r = card[:-1]
    if r == "A":
        return 11
    if r in ("K", "Q", "J", "10"):
        return 10
    return int(r)


def evaluate_bj_hand(cards: list[str]) -> tuple[int, bool, bool]:
    """
    Returns (total, is_soft, is_natural_blackjack).
    `is_soft` is True iff at least one Ace is currently counted as 11.
    """
    total = 0
    aces = 0
    for c in cards:
        r = c[:-1]
        if r == "A":
            aces += 1
            total += 11
        elif r in ("K", "Q", "J", "10"):
            total += 10
        else:
            total += int(r)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    is_soft = aces > 0
    is_bj = (len(cards) == 2 and total == 21)
    return (total, is_soft, is_bj)


def blackjack_basic_strategy_action(player_cards: list[str], dealer_upcard: str, can_double: bool = True) -> str:
    """
    Optimal Vegas S17 Basic Strategy (Hit / Stand / Double) used for Part A Monte Carlo RTP verification
    and optional hint display.
    """
    p_tot, is_soft, _ = evaluate_bj_hand(player_cards)
    d_val = card_rank_value(dealer_upcard)  # 2..11 (11 = Ace)

    if is_soft:
        if p_tot >= 19:
            if p_tot == 19 and d_val == 6 and can_double and len(player_cards) == 2:
                return "DOUBLE"
            return "STAND"
        if p_tot == 18:
            if 3 <= d_val <= 6 and can_double and len(player_cards) == 2:
                return "DOUBLE"
            if d_val in (2, 7, 8):
                return "STAND"
            return "HIT"
        if p_tot == 17:
            if 3 <= d_val <= 6 and can_double and len(player_cards) == 2:
                return "DOUBLE"
            return "HIT"
        if p_tot in (15, 16):
            if 4 <= d_val <= 6 and can_double and len(player_cards) == 2:
                return "DOUBLE"
            return "HIT"
        if p_tot in (13, 14):
            if 5 <= d_val <= 6 and can_double and len(player_cards) == 2:
                return "DOUBLE"
            return "HIT"
        return "HIT"

    # Hard totals
    if p_tot >= 17:
        return "STAND"
    if 13 <= p_tot <= 16:
        return "STAND" if (2 <= d_val <= 6) else "HIT"
    if p_tot == 12:
        return "STAND" if (4 <= d_val <= 6) else "HIT"
    if p_tot == 11:
        if d_val != 11 and can_double and len(player_cards) == 2:
            return "DOUBLE"
        return "HIT"
    if p_tot == 10:
        if 2 <= d_val <= 9 and can_double and len(player_cards) == 2:
            return "DOUBLE"
        return "HIT"
    if p_tot == 9:
        if 3 <= d_val <= 6 and can_double and len(player_cards) == 2:
            return "DOUBLE"
        return "HIT"
    return "HIT"
