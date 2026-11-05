"""
eagle_stake_casino.py — App #15 `EagleStake` Online Casino Backend Manager
for Project Eagle (`EaglePhone OS v6.3`).

Implements `EagleStakeManager(base_dir: Path)` with:
  - Stake.com Originals Lobby (`2x4` game grid, VIP Bronze->Diamond, 1% Rakeback, Progressive Mega Pot)
  - 8 Provably Fair Casino Games (`Sicbo MD5`, `Neon Slots 3x5`, `Crash 1000x`, `Diamond Mines 5x5`,
    `Plinko x1000`, `Stake Dice`, `Xoc Dia`, `Blackjack 21`)
  - Live GTA SA `$` RAM wallet synchronization via `engine.cash` / `engine.modify_cash(...)`
  - Dedicated SQLite persistence at `data/project-eagle/stake_casino.sqlite3`
"""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

import eagle_stake_games as G

STAKE_HUD_VER = "2"

BET_LADDER = [
    50, 100, 250, 500, 1_000, 2_500, 5_000,
    10_000, 25_000, 50_000, 100_000, 250_000,
]
MIN_BET = 50
MAX_BET = 250_000

GAME_META: list[dict[str, Any]] = [
    {"id": 1, "slug": "sicbo",     "title": "SICBO MD5",    "sub": "MD5 + Pot",     "max_tag": "31x + POT"},
    {"id": 2, "slug": "slots",     "title": "NEON SLOTS",   "sub": "3x5 + FreeSpin","max_tag": "GRAND POT"},
    {"id": 3, "slug": "crash",     "title": "CRASH 1000X",  "sub": "Live Flight",   "max_tag": "Up to 1000x"},
    {"id": 4, "slug": "mines",     "title": "MINES 5X5",    "sub": "25 Gems Grid",  "max_tag": "99% RTP"},
    {"id": 5, "slug": "plinko",    "title": "PLINKO X1000", "sub": "Pyramid Drop",  "max_tag": "1000x Edge"},
    {"id": 6, "slug": "dice",      "title": "STAKE DICE",   "sub": "Over / Under",  "max_tag": "99.00x"},
    {"id": 7, "slug": "xocdia",    "title": "XOC DIA",      "sub": "4-Coin Shaker", "max_tag": "14.5x + Bonus"},
    {"id": 8, "slug": "blackjack", "title": "BLACKJACK 21", "sub": "3:2 Payout",    "max_tag": "Fast Dealer"},
]

VIP_TIERS: list[tuple[str, int]] = [
    ("Diamond",  1_000_000),
    ("Platinum",   250_000),
    ("Gold",        50_000),
    ("Silver",      10_000),
    ("Bronze",           0),
]


def compute_vip_tier(total_wagered: float) -> tuple[str, int]:
    """Returns (tier_name, progress_pct_0_to_100)."""
    w = max(0.0, float(total_wagered))
    if w >= 1_000_000:
        return ("Diamond", 100)
    if w >= 250_000:
        return ("Platinum", int(min(100, (w - 250_000) / 7_500.0)))
    if w >= 50_000:
        return ("Gold", int(min(100, (w - 50_000) / 2_000.0)))
    if w >= 10_000:
        return ("Silver", int(min(100, (w - 10_000) / 400.0)))
    return ("Bronze", int(min(100, w / 100.0)))


class EagleStakeManager:
    """App #15 plugin manager attached to `EagleCompanionEngine.stake_mgr`."""

    def __init__(self, base_dir: Path, db_path: Path | None = None) -> None:
        self.base_dir = Path(base_dir).resolve()
        if db_path is not None:
            self.db_path = Path(db_path).resolve()
        else:
            # Workspace root is two levels above `Project Eagle/gta sa gameplay-lab`
            ws_root = self.base_dir.parent.parent
            cand_dir = ws_root / "data" / "project-eagle"
            if not ws_root.exists() or not (ws_root / "Project Eagle").exists():
                cand_dir = self.base_dir / "data"
            self.db_path = cand_dir / "stake_casino.sqlite3"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_lock = threading.RLock()

        # Persistent profile & provably fair state
        self.server_seed: str = G.new_server_seed()
        self.client_seed: str = "AETHER-STAKE-V63"
        self.nonce: int = 0
        self.last_revealed_seed: str = ""

        self.total_bets: int = 0
        self.total_wagered: float = 0.0
        self.net_profit: float = 0.0
        self.biggest_win: float = 0.0
        self.biggest_mult: float = 0.0
        self.rakeback_unclaimed: float = 0.0
        self.mega_pot: float = 258_400.0
        self.sicbo_pot: float = 88_888.0

        self._init_db()
        self._load_profile()

        # Navigation & global bet controls
        self.view: str = "lobby"          # "lobby" or "game"
        self.lobby_sel: int = 0           # 0..7 in 2x4 grid
        self.active_game: int = 1         # 1..8
        self.bet_amount: int = 500
        self.hud_ver: str = STAKE_HUD_VER
        self.status_line: str = "Provably Fair Ready - Select a Game"
        self.last_win_amt: int = 0
        self.last_win_mult: float = 0.0

        # ---- Game #1: Sicbo MD5 + Pot ----
        self.sicbo_pick_idx: int = 1      # 0=XIU, 1=TAI, 2=ODD, 3=EVEN, 4=BAO
        self.sicbo_anim_ticks: int = 0
        self.sicbo_display_dice: list[int] = [5, 4, 3]
        self.sicbo_pending: dict[str, Any] | None = None
        self.sicbo_pending_bet: int = 0
        self.sicbo_pending_pick: str = "TAI"
        self.sicbo_next_round: dict[str, Any] = G.prepare_sicbo_round(
            self.server_seed, self.client_seed, self.nonce + 1
        )
        self.sicbo_last_plain: str = "Pre-Roll MD5 Committed Above"
        self.sicbo_last_res: str = "12 TAI (5-4-3)"
        self.sicbo_history: list[str] = [
            "T:12", "X:08", "T:14", "T:11", "X:07", "X:09",
            "B:18", "T:13", "X:06", "T:15", "X:10", "T:12",
        ]

        # ---- Game #2: Neon Slots 3x5 ----
        self.slots_grid_flat: list[str] = [
            "777", "CROWN", "GEM", "CROWN", "777",
            "WILD", "777", "SCAT", "777", "WILD",
            "GEM", "BELL", "CROWN", "BELL", "GEM",
        ]
        self.slots_win_mask: str = "0" * 15
        self.slots_anim_ticks: int = 0
        self.slots_pending: dict[str, Any] | None = None
        self.slots_pending_bet: int = 0
        self.slots_pending_was_fs: bool = False
        self.slots_fs_left: int = 0
        self.slots_fs_idx: int = 0
        self.slots_fs_bet: int = 500
        self.slots_fs_nonce: int = 0
        self.slots_status: str = "9 Paylines - 3+ SCAT = 8 Free Spins"

        # ---- Game #3: Crash 1000x ----
        self.crash_state: str = "IDLE"    # "IDLE", "FLYING", "CRASHED"
        self.crash_auto_idx: int = 2      # 0=OFF, 1=1.5x, 2=2.0x, 3=3.0x, 4=5.0x, 5=10x
        self.crash_bet: int = 0
        self.crash_point: float = 2.00
        self.crash_cur_mult: float = 1.00
        self.crash_cashed: bool = False
        self.crash_cash_mult: float = 0.0
        self.crash_cash_payout: int = 0
        self.crash_start_mono: float = 0.0
        self.crash_cash_mono: float = 0.0
        self.crash_history: list[float] = [1.84, 4.25, 1.12, 14.60, 2.31, 1.04, 6.80]
        self.crash_pts_csv: str = "0,12,26,42,60,80,100"

        # ---- Game #4: 5x5 Diamond Mines ----
        self.mines_preset_idx: int = 1    # [1, 3, 5, 10, 15] -> default 3 Mines
        self.mines_state: str = "IDLE"    # "IDLE", "ACTIVE", "BOOM", "CASHED"
        self.mines_cursor: int = 12       # 0..24 keyboard cursor
        self.mines_bet: int = 0
        self.mines_bombs: set[int] = set()
        self.mines_opened: set[int] = set()
        self.mines_boom_idx: int = -1
        self.mines_cur_mult: float = 1.00
        self.mines_status: str = "Pick Mines Count & Press START"

        # ---- Game #5: Plinko x1000 ----
        self.plinko_rows_idx: int = 2     # [8, 12, 16] -> default 16 rows
        self.plinko_risk_idx: int = 2     # ["LOW", "MED", "HIGH"] -> default HIGH (up to 1000x!)
        self.plinko_balls: list[dict[str, Any]] = []
        self.plinko_last_bucket: int = 8
        self.plinko_last_mult: float = 1.0
        self.plinko_recent: list[str] = ["2.0x", "0.2x", "9.0x", "26x", "4.0x"]

        # ---- Game #6: Stake Dice ----
        self.dice_target: int = 50        # 5..95
        self.dice_mode: str = "OVER"      # "OVER" or "UNDER"
        self.dice_last_roll: float = 64.28
        self.dice_last_won: bool = True
        self.dice_history: list[str] = ["W:64.2", "L:21.5", "W:82.9", "W:54.0", "L:12.4", "W:91.3"]

        # ---- Game #7: Xoc Dia ----
        self.xocdia_pick_idx: int = 0     # 0=EVEN, 1=ODD, 2=4R, 3=4W, 4=3R1W, 5=3W1R
        self.xocdia_coins: list[str] = ["R", "W", "R", "W"]
        self.xocdia_anim_ticks: int = 0
        self.xocdia_pending: dict[str, Any] | None = None
        self.xocdia_pending_bet: int = 0
        self.xocdia_last_lbl: str = "2R - 2W (CHAN)"
        self.xocdia_history: list[str] = [
            "C", "L", "C", "C", "4R", "L", "C", "L", "L", "C", "4W", "C"
        ]

        # ---- Game #8: Blackjack 21 ----
        self.bj_state: str = "IDLE"       # "IDLE", "PLAYER_TURN", "SETTLED"
        self.bj_shoe: list[str] = []
        self.bj_shoe_idx: int = 0
        self.bj_player: list[str] = ["AS", "KH"]
        self.bj_dealer: list[str] = ["10D", "9C"]
        self.bj_base_bet: int = 500
        self.bj_wager: int = 500
        self.bj_doubled: bool = False
        self.bj_result_txt: str = "Press DEAL HAND (3:2 Natural 21)"
        self.bj_btn_sel: int = 0          # 0=HIT, 1=STAND, 2=DOUBLE

    # ========================================================================
    # SQLITE PERSISTENCE (`data/project-eagle/stake_casino.sqlite3`)
    # ========================================================================
    def _init_db(self) -> None:
        with self._db_lock:
            con = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                con.execute("PRAGMA journal_mode=WAL;")
                con.execute(
                    """
                    CREATE TABLE IF NOT EXISTS stake_profile (
                        id INTEGER PRIMARY KEY CHECK (id = 1),
                        server_seed TEXT NOT NULL,
                        client_seed TEXT NOT NULL,
                        nonce INTEGER NOT NULL DEFAULT 0,
                        total_bets INTEGER NOT NULL DEFAULT 0,
                        total_wagered REAL NOT NULL DEFAULT 0.0,
                        net_profit REAL NOT NULL DEFAULT 0.0,
                        biggest_win REAL NOT NULL DEFAULT 0.0,
                        biggest_mult REAL NOT NULL DEFAULT 0.0,
                        rakeback_unclaimed REAL NOT NULL DEFAULT 0.0,
                        mega_pot REAL NOT NULL DEFAULT 258400.0,
                        sicbo_pot REAL NOT NULL DEFAULT 88888.0,
                        updated_at REAL NOT NULL DEFAULT 0.0
                    );
                    """
                )
                con.execute(
                    """
                    CREATE TABLE IF NOT EXISTS stake_bets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts REAL NOT NULL,
                        game TEXT NOT NULL,
                        nonce INTEGER NOT NULL,
                        wager REAL NOT NULL,
                        mult REAL NOT NULL,
                        payout REAL NOT NULL,
                        profit REAL NOT NULL,
                        detail TEXT NOT NULL
                    );
                    """
                )
                con.commit()
            finally:
                con.close()

    def _load_profile(self) -> None:
        with self._db_lock:
            con = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                row = con.execute(
                    """
                    SELECT server_seed, client_seed, nonce, total_bets, total_wagered,
                           net_profit, biggest_win, biggest_mult, rakeback_unclaimed,
                           mega_pot, sicbo_pot
                    FROM stake_profile WHERE id = 1
                    """
                ).fetchone()
                if row is None:
                    con.execute(
                        """
                        INSERT INTO stake_profile (
                            id, server_seed, client_seed, nonce, total_bets, total_wagered,
                            net_profit, biggest_win, biggest_mult, rakeback_unclaimed,
                            mega_pot, sicbo_pot, updated_at
                        ) VALUES (1, ?, ?, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, ?, ?, ?)
                        """,
                        (self.server_seed, self.client_seed, self.mega_pot, self.sicbo_pot, time.time()),
                    )
                    con.commit()
                else:
                    self.server_seed = str(row[0] or G.new_server_seed())
                    self.client_seed = str(row[1] or "AETHER-STAKE-V63")
                    self.nonce = int(row[2] or 0)
                    self.total_bets = int(row[3] or 0)
                    self.total_wagered = float(row[4] or 0.0)
                    self.net_profit = float(row[5] or 0.0)
                    self.biggest_win = float(row[6] or 0.0)
                    self.biggest_mult = float(row[7] or 0.0)
                    self.rakeback_unclaimed = float(row[8] or 0.0)
                    self.mega_pot = max(50_000.0, float(row[9] or 258_400.0))
                    self.sicbo_pot = max(25_000.0, float(row[10] or 88_888.0))
            finally:
                con.close()

    def _save_profile(self, bet_log: tuple[str, int, float, float, float, str] | None = None) -> None:
        with self._db_lock:
            con = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                now = time.time()
                con.execute(
                    """
                    UPDATE stake_profile
                    SET server_seed = ?, client_seed = ?, nonce = ?,
                        total_bets = ?, total_wagered = ?, net_profit = ?,
                        biggest_win = ?, biggest_mult = ?, rakeback_unclaimed = ?,
                        mega_pot = ?, sicbo_pot = ?, updated_at = ?
                    WHERE id = 1
                    """,
                    (
                        self.server_seed,
                        self.client_seed,
                        int(self.nonce),
                        int(self.total_bets),
                        float(self.total_wagered),
                        float(self.net_profit),
                        float(self.biggest_win),
                        float(self.biggest_mult),
                        float(self.rakeback_unclaimed),
                        float(self.mega_pot),
                        float(self.sicbo_pot),
                        now,
                    ),
                )
                if bet_log is not None:
                    game_slug, b_nonce, wager, mult, payout, detail = bet_log
                    con.execute(
                        """
                        INSERT INTO stake_bets (ts, game, nonce, wager, mult, payout, profit, detail)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            now,
                            game_slug,
                            int(b_nonce),
                            float(wager),
                            float(mult),
                            float(payout),
                            float(payout - wager),
                            G.sanitize_hud_ascii(detail, 120),
                        ),
                    )
                    # Keep history bounded for fast queries
                    con.execute(
                        "DELETE FROM stake_bets WHERE id NOT IN (SELECT id FROM stake_bets ORDER BY id DESC LIMIT 400)"
                    )
                con.commit()
            finally:
                con.close()

    # ========================================================================
    # WALLET, PROGRESSION & PROBABLY FAIR SEED HELPERS
    # ========================================================================
    def _next_nonce(self) -> int:
        self.nonce += 1
        return self.nonce

    def _has_active_round(self) -> bool:
        return (
            self.crash_state == "FLYING"
            or self.mines_state == "ACTIVE"
            or self.bj_state == "PLAYER_TURN"
            or len(self.plinko_balls) > 0
            or self.sicbo_anim_ticks > 0
            or self.slots_anim_ticks > 0
            or self.xocdia_anim_ticks > 0
        )

    def _toast(self, engine: Any, msg: str) -> None:
        clean = G.sanitize_hud_ascii(msg, 120)
        self.status_line = clean
        if engine is not None:
            engine.last_toast = clean

    def _debit_wager(self, engine: Any, amount: int) -> bool:
        amt = int(max(1, amount))
        if engine is not None:
            if int(getattr(engine, "cash", 0)) < amt:
                self._toast(engine, f"Insufficient Cash! Need {G.fmt_usd(amt)}")
                return False
            if not engine.modify_cash(-amt):
                self._toast(engine, f"Insufficient Cash! Need {G.fmt_usd(amt)}")
                return False
        self.total_wagered += amt
        self.rakeback_unclaimed += round(amt * 0.01, 2)
        self.mega_pot += round(amt * 0.008, 2)
        self.sicbo_pot += round(amt * 0.006, 2)
        return True

    def _settle_round(
        self,
        engine: Any,
        game_slug: str,
        round_nonce: int,
        wager: int,
        payout: int,
        detail: str,
        jackpot_hit: bool = False,
        count_bet: bool = True,
    ) -> None:
        pay = max(0, int(round(payout)))
        wag = max(0, int(round(wager)))
        if pay > 0 and engine is not None:
            engine.modify_cash(pay)

        if count_bet:
            self.total_bets += 1
        profit = pay - wag
        self.net_profit += profit
        eff_mult = round(pay / float(max(1, wag)), 2) if wag > 0 else 0.0
        self.last_win_amt = pay
        self.last_win_mult = eff_mult

        if pay > self.biggest_win:
            self.biggest_win = float(pay)
        if eff_mult > self.biggest_mult and pay > 0:
            self.biggest_mult = float(eff_mult)

        if engine is not None and pay > 0 and (jackpot_hit or eff_mult >= 5.0):
            title = "EAGLESTAKE JACKPOT!" if jackpot_hit else f"EAGLESTAKE BIG WIN ({eff_mult:.2f}x)!"
            sub = f"{game_slug.upper()} paid {G.fmt_usd(pay)} (+{G.fmt_usd(max(0, profit))} net)"
            try:
                engine.push_event_banner(
                    G.sanitize_hud_ascii(title, 64),
                    G.sanitize_hud_ascii(sub, 96),
                    kind="win",
                    duration=5.5,
                )
            except Exception:
                pass

        self._save_profile((game_slug, round_nonce, float(wag), eff_mult, float(pay), detail))

    def rotate_seeds(self, engine: Any) -> None:
        if self._has_active_round():
            self._toast(engine, "Finish current active round before rotating seeds!")
            return
        self.last_revealed_seed = self.server_seed[:20]
        self.server_seed = G.new_server_seed()
        self.client_seed = f"AETHER-{int(time.time()) % 100000:05d}"
        self.nonce = 0
        self.sicbo_next_round = G.prepare_sicbo_round(self.server_seed, self.client_seed, 1)
        self._save_profile()
        self._toast(engine, f"New Seed Active! Old Seed: {self.last_revealed_seed}...")

    def claim_rakeback(self, engine: Any) -> int:
        amt = int(self.rakeback_unclaimed)
        if amt < 1:
            self._toast(engine, "Rakeback < $1 - Wager to earn 1% instant VIP cashback!")
            return 0
        self.rakeback_unclaimed = max(0.0, round(self.rakeback_unclaimed - amt, 2))
        if engine is not None:
            engine.modify_cash(amt)
        self.net_profit += amt
        self._save_profile()
        self._toast(engine, f"Claimed 1% VIP Rakeback: +{G.fmt_usd(amt)} added to wallet!")
        return amt

    def _adjust_bet_step(self, engine: Any, delta: int) -> None:
        cur = self.bet_amount
        idx = 0
        for i, v in enumerate(BET_LADDER):
            if v <= cur:
                idx = i
        new_idx = max(0, min(len(BET_LADDER) - 1, idx + delta))
        cash_cap = max(MIN_BET, int(getattr(engine, "cash", MAX_BET))) if engine is not None else MAX_BET
        self.bet_amount = max(MIN_BET, min(MAX_BET, min(BET_LADDER[new_idx], cash_cap)))
        self._toast(engine, f"Bet Amount: {G.fmt_usd(self.bet_amount)}")

    def _scale_bet(self, engine: Any, mode: str) -> None:
        cash_cap = max(MIN_BET, min(MAX_BET, int(getattr(engine, "cash", MAX_BET)))) if engine is not None else MAX_BET
        if mode == "half":
            self.bet_amount = max(MIN_BET, self.bet_amount // 2)
        elif mode == "double":
            self.bet_amount = max(MIN_BET, min(cash_cap, self.bet_amount * 2))
        elif mode == "min":
            self.bet_amount = MIN_BET
        elif mode == "max":
            self.bet_amount = cash_cap
        self._toast(engine, f"Bet Set: {G.fmt_usd(self.bet_amount)}")

    # ========================================================================
    # 8 GAME ACTION HANDLERS
    # ========================================================================
    # ---- 1. SICBO MD5 + POT ----
    def _play_sicbo(self, engine: Any, instant: bool = False) -> None:
        if self.sicbo_anim_ticks > 0:
            return
        bet = self.bet_amount
        if not self._debit_wager(engine, bet):
            return
        n = self._next_nonce()
        # Use the exact pre-committed MD5 round if nonces match!
        if self.sicbo_next_round and int(self.sicbo_next_round.get("nonce", -1)) == n:
            rnd = self.sicbo_next_round
        else:
            rnd = G.prepare_sicbo_round(self.server_seed, self.client_seed, n)

        pick_code = G.SICBO_BETS[self.sicbo_pick_idx][0]
        self.sicbo_pending = rnd
        self.sicbo_pending_bet = bet
        self.sicbo_pending_pick = pick_code
        if instant:
            self._finish_sicbo_roll(engine)
        else:
            self.sicbo_anim_ticks = 8
            self._toast(engine, f"Shaking MD5 Dice ({pick_code} {G.fmt_usd(bet)})...")

    def _finish_sicbo_roll(self, engine: Any) -> None:
        rnd = self.sicbo_pending
        if rnd is None:
            self.sicbo_anim_ticks = 0
            return
        self.sicbo_pending = None
        self.sicbo_anim_ticks = 0
        bet = self.sicbo_pending_bet
        pick = self.sicbo_pending_pick
        ev = G.evaluate_sicbo_bet(rnd, pick, bet, self.sicbo_pot)
        if ev["pot_hit"]:
            self.sicbo_pot = max(50_000.0, self.sicbo_pot - ev["pot_bonus"])

        d1, d2, d3 = rnd["dice"]
        self.sicbo_display_dice = [d1, d2, d3]
        self.sicbo_last_plain = f"VERIFY: {rnd['plain']}"
        tag = "B" if rnd["is_triple"] else ("T" if rnd["kind"] == "TAI" else "X")
        self.sicbo_history.append(f"{tag}:{rnd['total']:02d}")
        self.sicbo_history = self.sicbo_history[-12:]
        self.sicbo_last_res = f"{rnd['total']} {rnd['kind']} ({d1}-{d2}-{d3})"

        # Prepare next round MD5 commitment BEFORE next bet!
        self.sicbo_next_round = G.prepare_sicbo_round(self.server_seed, self.client_seed, self.nonce + 1)

        self._settle_round(
            engine, "sicbo", rnd["nonce"], bet, ev["payout"],
            f"{pick} -> {d1}-{d2}-{d3} ({rnd['kind']})",
            jackpot_hit=ev["pot_hit"],
        )
        if ev["pot_hit"]:
            self._toast(engine, f"SICBO POT EXPLODED! +{G.fmt_usd(ev['payout'])} ({d1}-{d2}-{d3})!")
        elif ev["won"]:
            self._toast(engine, f"WIN +{G.fmt_usd(ev['payout'])}! Rolled {d1}-{d2}-{d3} = {rnd['total']} ({rnd['kind']})")
        else:
            self._toast(engine, f"Rolled {d1}-{d2}-{d3} = {rnd['total']} ({rnd['kind']}) - Try Next MD5 Hand")

    # ---- 2. NEON SLOTS 3x5 ----
    def _play_slots(self, engine: Any, instant: bool = False) -> None:
        if self.slots_anim_ticks > 0:
            return
        if self.slots_fs_left > 0:
            self.slots_fs_left -= 1
            self.slots_fs_idx += 1
            fs_m = G.free_spin_multiplier(self.slots_fs_idx)
            bet = self.slots_fs_bet
            n = self.slots_fs_nonce
            res = G.spin_slots_3x5(
                self.server_seed, self.client_seed, n, bet,
                fs_mult=fs_m, cursor_start=self.slots_fs_idx * 5,
            )
            self.slots_pending = res
            self.slots_pending_bet = 0
            self.slots_pending_was_fs = True
            if instant:
                self._finish_slots_spin(engine)
            else:
                self.slots_anim_ticks = 6
                self._toast(engine, f"FREE SPIN {self.slots_fs_idx}/8 (x{fs_m} Multiplier)!")
            return

        bet = self.bet_amount
        if not self._debit_wager(engine, bet):
            return
        n = self._next_nonce()
        res = G.spin_slots_3x5(self.server_seed, self.client_seed, n, bet, fs_mult=1, cursor_start=0)
        res["nonce"] = n
        self.slots_pending = res
        self.slots_pending_bet = bet
        self.slots_pending_was_fs = False
        if instant:
            self._finish_slots_spin(engine)
        else:
            self.slots_anim_ticks = 7
            self._toast(engine, f"Spinning Neon 3x5 Reels ({G.fmt_usd(bet)})...")

    def _finish_slots_spin(self, engine: Any) -> None:
        res = self.slots_pending
        if res is None:
            self.slots_anim_ticks = 0
            return
        self.slots_pending = None
        self.slots_anim_ticks = 0
        self.slots_grid_flat = list(res["flat"])
        self.slots_win_mask = str(res["win_mask"])
        payout = int(res["payout"])
        was_fs = self.slots_pending_was_fs
        wager = 0 if was_fs else self.slots_pending_bet
        ref_bet = self.slots_fs_bet if was_fs else max(1, wager)

        if res["grand_pot_hit"]:
            self.mega_pot = max(150_000.0, self.mega_pot - res["grand_bonus"])

        if res["triggered_fs"] > 0 and not was_fs:
            self.slots_fs_left = int(res["triggered_fs"])
            self.slots_fs_idx = 0
            self.slots_fs_bet = wager
            self.slots_fs_nonce = int(res.get("nonce", self.nonce))

        self._settle_round(
            engine, "slots", int(res.get("nonce", self.nonce)),
            wager, payout,
            f"Hits:{len(res['line_hits'])} Scat:{res['scatter_count']}",
            jackpot_hit=bool(res["grand_pot_hit"]),
            count_bet=(not was_fs),
        )
        # Keep display mult meaningful on free spins too
        if was_fs and payout > 0:
            self.last_win_mult = round(payout / float(max(1, ref_bet)), 2)

        if res["triggered_fs"] > 0 and not was_fs:
            self.slots_status = f"3+ SCATTER! 8 FREE SPINS UNLOCKED (x2->x5->x10)!"
        elif self.slots_fs_left > 0:
            nxt_m = G.free_spin_multiplier(self.slots_fs_idx + 1)
            self.slots_status = f"FREE SPINS LEFT: {self.slots_fs_left} (Next Mult x{nxt_m})  +{G.fmt_usd(payout)}"
        elif payout > 0:
            top_hit = res["line_hits"][0] if res["line_hits"] else (1, "SCAT", 3, res["mult"])
            self.slots_status = f"WIN +{G.fmt_usd(payout)} ({top_hit[2]}x {top_hit[1]} - {len(res['line_hits'])} Lines)"
        else:
            self.slots_status = "No Line Match - Spin Again for 777 / 3x SCAT!"
        self._toast(engine, self.slots_status)

    # ---- 3. CRASH / AVIATOR ----
    def _start_crash(self, engine: Any) -> None:
        if self.crash_state == "FLYING":
            self._cashout_crash(engine)
            return
        bet = self.bet_amount
        if not self._debit_wager(engine, bet):
            return
        n = self._next_nonce()
        cp = G.generate_crash_point(self.server_seed, self.client_seed, n)
        self.crash_bet = bet
        self.crash_point = cp
        self.crash_cashed = False
        self.crash_cash_mult = 0.0
        self.crash_cash_payout = 0
        self.crash_cur_mult = 1.00
        self.crash_start_mono = time.monotonic()
        self.crash_cash_mono = 0.0

        if cp <= 1.00:
            # Instant 1.00x house crash (1% probability)
            self.crash_state = "CRASHED"
            self.crash_pts_csv = "0,0"
            self.crash_history.append(1.00)
            self.crash_history = self.crash_history[-7:]
            self._settle_round(engine, "crash", n, bet, 0, "Instant Crash @ 1.00x")
            self._toast(engine, "INSTANT CRASH @ 1.00x!")
            return

        self.crash_state = "FLYING"
        self.crash_pts_csv = "0,4"
        auto_lbl, auto_val = G.CRASH_AUTO_PRESETS[self.crash_auto_idx]
        self._toast(
            engine,
            f"Rocket Launched ({G.fmt_usd(bet)}, Auto:{auto_lbl}) - Click CASHOUT NOW!",
        )

    def _cashout_crash(self, engine: Any, forced_mult: float | None = None) -> bool:
        if self.crash_state != "FLYING" or self.crash_cashed:
            return False
        m = forced_mult if forced_mult is not None else self.crash_cur_mult
        m = max(1.01, min(m, self.crash_point))
        payout = int(round(self.crash_bet * m))
        self.crash_cashed = True
        self.crash_cash_mult = round(m, 2)
        self.crash_cash_payout = payout
        self.crash_cash_mono = time.monotonic()
        self._settle_round(
            engine, "crash", self.nonce, self.crash_bet, payout,
            f"Cashed @ {self.crash_cash_mult:.2f}x (Crash {self.crash_point:.2f}x)",
        )
        self._toast(engine, f"CASHED OUT @ {self.crash_cash_mult:.2f}x -> +{G.fmt_usd(payout)}!")
        return True

    def _update_crash_curve_csv(self, cur_mult: float) -> None:
        # 12 normalized Y points in 0..100 depicting smooth upward curvature
        span = max(0.25, math.log(max(1.02, cur_mult))) if False else 1.0
        pts: list[str] = []
        for i in range(12):
            frac = i / 11.0
            # Convex rocket trajectory
            y_norm = int(round(min(100.0, (frac ** 1.65) * min(100.0, 22.0 + (cur_mult - 1.0) * 18.0))))
            pts.append(str(y_norm))
        self.crash_pts_csv = ",".join(pts)

    # ---- 4. 5x5 DIAMOND MINES ----
    def _start_mines(self, engine: Any) -> None:
        if self.mines_state == "ACTIVE":
            if len(self.mines_opened) >= 1:
                self._cashout_mines(engine)
            else:
                self._toast(engine, "Tap any tile on the 5x5 grid to reveal a Diamond first!")
            return
        bet = self.bet_amount
        if not self._debit_wager(engine, bet):
            return
        n = self._next_nonce()
        m_cnt = G.MINES_PRESETS[self.mines_preset_idx]
        self.mines_bombs = G.generate_mines_board(m_cnt, self.server_seed, self.client_seed, n)
        self.mines_opened = set()
        self.mines_boom_idx = -1
        self.mines_bet = bet
        self.mines_cur_mult = 1.00
        self.mines_state = "ACTIVE"
        self.mines_status = f"{m_cnt} Mines Hidden - Pick Gems or CASHOUT Anytime"
        self._toast(engine, self.mines_status)

    def _pick_mines_tile(self, engine: Any, idx_0based: int) -> bool:
        if self.mines_state != "ACTIVE":
            # Convenience: clicking a tile when idle starts a new board if cash suffices!
            self._toast(engine, "Press START MINES first to place bet on 5x5 board!")
            return False
        tile = max(0, min(24, int(idx_0based)))
        if tile in self.mines_opened:
            return False
        self.mines_cursor = tile
        m_cnt = G.MINES_PRESETS[self.mines_preset_idx]
        if tile in self.mines_bombs:
            self.mines_boom_idx = tile
            self.mines_state = "BOOM"
            self.mines_cur_mult = 0.0
            self._settle_round(
                engine, "mines", self.nonce, self.mines_bet, 0,
                f"Hit Mine @ tile #{tile + 1} ({m_cnt} mines)",
            )
            self.mines_status = f"BOOM! Hit Mine #{tile + 1} - Board Revealed"
            self._toast(engine, self.mines_status)
            return True

        self.mines_opened.add(tile)
        safe_total = 25 - m_cnt
        self.mines_cur_mult = round(G.mines_multiplier(m_cnt, len(self.mines_opened)), 2)
        if len(self.mines_opened) >= safe_total:
            # Cleared the entire board! Auto-cashout max multiplier!
            return self._cashout_mines(engine)
        pot_win = int(round(self.mines_bet * self.mines_cur_mult))
        self.mines_status = f"{len(self.mines_opened)} Gems ({self.mines_cur_mult:.2f}x) -> Cashout {G.fmt_usd(pot_win)}"
        self._toast(engine, self.mines_status)
        return True

    def _cashout_mines(self, engine: Any) -> bool:
        if self.mines_state != "ACTIVE" or len(self.mines_opened) < 1:
            return False
        # Atomic transition BEFORE payout prevents any double-cashout!
        self.mines_state = "CASHED"
        m_cnt = G.MINES_PRESETS[self.mines_preset_idx]
        exact_m = G.mines_multiplier(m_cnt, len(self.mines_opened))
        payout = int(round(self.mines_bet * exact_m))
        self.mines_cur_mult = round(exact_m, 2)
        self._settle_round(
            engine, "mines", self.nonce, self.mines_bet, payout,
            f"Cashed {len(self.mines_opened)} gems ({m_cnt} mines) @ {self.mines_cur_mult:.2f}x",
        )
        self.mines_status = f"CASHED OUT +{G.fmt_usd(payout)} ({self.mines_cur_mult:.2f}x)!"
        self._toast(engine, self.mines_status)
        return True

    # ---- 5. PLINKO x1000 ----
    def _drop_plinko_ball(self, engine: Any, instant: bool = False) -> None:
        if len(self.plinko_balls) >= 6 and not instant:
            self._toast(engine, "Max 6 balls in flight - watch them land!")
            return
        bet = self.bet_amount
        if not self._debit_wager(engine, bet):
            return
        n = self._next_nonce()
        rows = G.PLINKO_ROWS_OPTIONS[self.plinko_rows_idx]
        risk = G.PLINKO_RISK_OPTIONS[self.plinko_risk_idx]
        drop = G.generate_plinko_drop(rows, risk, self.server_seed, self.client_seed, n)
        ball = {
            "nonce": n,
            "bet": bet,
            "rows": rows,
            "risk": risk,
            "steps": drop["steps"],
            "bucket": drop["bucket"],
            "mult": drop["mult"],
            "row_f": 0.0,
            "col_f": 0.0,
        }
        if instant:
            self._land_plinko_ball(engine, ball)
        else:
            self.plinko_balls.append(ball)
            self._toast(engine, f"Dropped Ball #{n} ({rows} Rows {risk}) - In Flight: {len(self.plinko_balls)}")

    def _land_plinko_ball(self, engine: Any, ball: dict[str, Any]) -> None:
        mult = float(ball["mult"])
        bet = int(ball["bet"])
        payout = int(round(bet * mult))
        self.plinko_last_bucket = int(ball["bucket"])
        self.plinko_last_mult = mult
        lbl = f"{int(mult)}x" if mult >= 10.0 else f"{mult:.1f}x"
        self.plinko_recent.append(lbl)
        self.plinko_recent = self.plinko_recent[-6:]
        self._settle_round(
            engine, "plinko", int(ball["nonce"]), bet, payout,
            f"{ball['rows']}R {ball['risk']} -> Bucket #{ball['bucket']} ({lbl})",
            jackpot_hit=(mult >= 130.0),
        )
        self._toast(engine, f"Plinko Landed {lbl} -> +{G.fmt_usd(payout)}!")

    # ---- 6. STAKE DICE ----
    def _play_dice(self, engine: Any) -> None:
        bet = self.bet_amount
        if not self._debit_wager(engine, bet):
            return
        n = self._next_nonce()
        res = G.roll_stake_dice(
            self.dice_target, self.dice_mode, bet,
            self.server_seed, self.client_seed, n,
        )
        self.dice_last_roll = float(res["roll"])
        self.dice_last_won = bool(res["won"])
        tag = "W" if res["won"] else "L"
        self.dice_history.append(f"{tag}:{res['roll']:.2f}")
        self.dice_history = self.dice_history[-6:]

        self._settle_round(
            engine, "dice", n, bet, res["payout"],
            f"Roll {res['roll']:.2f} ({res['mode']} {res['target']})",
        )
        if res["won"]:
            self._toast(engine, f"DICE WIN! Rolled {res['roll']:.2f} -> +{G.fmt_usd(res['payout'])} ({res['mult']:.2f}x)")
        else:
            self._toast(engine, f"Rolled {res['roll']:.2f} (Need {self.dice_mode} {self.dice_target}.00)")

    # ---- 7. XOC DIA ----
    def _play_xocdia(self, engine: Any, instant: bool = False) -> None:
        if self.xocdia_anim_ticks > 0:
            return
        bet = self.bet_amount
        if not self._debit_wager(engine, bet):
            return
        n = self._next_nonce()
        pick_code = G.XOCDIA_BETS[self.xocdia_pick_idx][0]
        res = G.shake_xoc_dia(pick_code, bet, self.server_seed, self.client_seed, n)
        res["nonce"] = n
        res["pick"] = pick_code
        self.xocdia_pending = res
        self.xocdia_pending_bet = bet
        if instant:
            self._finish_xocdia(engine)
        else:
            self.xocdia_anim_ticks = 7
            self._toast(engine, f"Shaking 4-Coin Bowl ({pick_code} {G.fmt_usd(bet)})...")

    def _finish_xocdia(self, engine: Any) -> None:
        res = self.xocdia_pending
        if res is None:
            self.xocdia_anim_ticks = 0
            return
        self.xocdia_pending = None
        self.xocdia_anim_ticks = 0
        bet = self.xocdia_pending_bet
        self.xocdia_coins = list(res["coins"])
        self.xocdia_last_lbl = str(res["result_label"])
        self.xocdia_history.append(str(res["bead"]))
        self.xocdia_history = self.xocdia_history[-12:]
        self._settle_round(
            engine, "xocdia", int(res["nonce"]), bet, int(res["payout"]),
            f"{res['pick']} -> {res['result_label']}",
        )
        if res["won"]:
            self._toast(engine, f"XOC DIA WIN +{G.fmt_usd(res['payout'])}! {res['result_label']}")
        else:
            self._toast(engine, f"Opened Bowl: {res['result_label']}")

    # ---- 8. BLACKJACK 21 ----
    def _deal_blackjack(self, engine: Any) -> None:
        if self.bj_state == "PLAYER_TURN":
            self._bj_hit(engine)
            return
        bet = self.bet_amount
        if not self._debit_wager(engine, bet):
            return
        n = self._next_nonce()
        self.bj_shoe = G.build_provably_fair_shoe(self.server_seed, self.client_seed, n, decks=6, draw_count=20)
        self.bj_player = [self.bj_shoe[0], self.bj_shoe[2]]
        self.bj_dealer = [self.bj_shoe[1], self.bj_shoe[3]]
        self.bj_shoe_idx = 4
        self.bj_base_bet = bet
        self.bj_wager = bet
        self.bj_doubled = False
        self.bj_btn_sel = 0

        p_tot, _, p_bj = G.evaluate_bj_hand(self.bj_player)
        d_tot, _, d_bj = G.evaluate_bj_hand(self.bj_dealer)
        if p_bj and d_bj:
            self.bj_state = "SETTLED"
            self.bj_result_txt = f"PUSH 1.0x - Both Natural Blackjack 21 (+{G.fmt_usd(bet)})"
            self._settle_round(engine, "blackjack", n, bet, bet, "Push Both BJ")
            self._toast(engine, self.bj_result_txt)
            return
        if p_bj:
            payout = int(round(bet * 2.5))
            self.bj_state = "SETTLED"
            self.bj_result_txt = f"NATURAL BLACKJACK 3:2! +{G.fmt_usd(payout)} (2.50x)"
            self._settle_round(engine, "blackjack", n, bet, payout, "Natural Blackjack 3:2")
            self._toast(engine, self.bj_result_txt)
            return
        if d_bj:
            self.bj_state = "SETTLED"
            self.bj_result_txt = f"DEALER BLACKJACK 21 ({self.bj_dealer[0]} {self.bj_dealer[1]})"
            self._settle_round(engine, "blackjack", n, bet, 0, "Dealer Natural BJ")
            self._toast(engine, self.bj_result_txt)
            return

        self.bj_state = "PLAYER_TURN"
        hint = G.blackjack_basic_strategy_action(self.bj_player, self.bj_dealer[0], can_double=True)
        self.bj_result_txt = f"Your Turn ({p_tot}) - HIT / STAND / DOUBLE (Hint: {hint})"
        self._toast(engine, self.bj_result_txt)

    def _bj_draw_card(self) -> str:
        if self.bj_shoe_idx < len(self.bj_shoe):
            c = self.bj_shoe[self.bj_shoe_idx]
            self.bj_shoe_idx += 1
            return c
        return "10S"

    def _bj_hit(self, engine: Any) -> None:
        if self.bj_state != "PLAYER_TURN":
            return
        self.bj_player.append(self._bj_draw_card())
        p_tot, is_soft, _ = G.evaluate_bj_hand(self.bj_player)
        if p_tot > 21:
            self.bj_state = "SETTLED"
            self.bj_result_txt = f"BUST ({p_tot}) - Dealer Wins"
            self._settle_round(engine, "blackjack", self.nonce, self.bj_wager, 0, f"Player Bust {p_tot}")
            self._toast(engine, self.bj_result_txt)
            return
        if p_tot == 21:
            self._bj_stand_and_settle(engine)
            return
        soft_tag = f"Soft {p_tot}" if is_soft else str(p_tot)
        self.bj_result_txt = f"Hand: {soft_tag} - Choose HIT or STAND"
        self._toast(engine, self.bj_result_txt)

    def _bj_double(self, engine: Any) -> None:
        if self.bj_state != "PLAYER_TURN":
            return
        if len(self.bj_player) != 2:
            self._toast(engine, "Double Down only available on initial 2 cards!")
            return
        if not self._debit_wager(engine, self.bj_base_bet):
            return
        self.bj_wager += self.bj_base_bet
        self.bj_doubled = True
        self.bj_player.append(self._bj_draw_card())
        p_tot, _, _ = G.evaluate_bj_hand(self.bj_player)
        if p_tot > 21:
            self.bj_state = "SETTLED"
            self.bj_result_txt = f"DOUBLE BUST ({p_tot}) - Lost {G.fmt_usd(self.bj_wager)}"
            self._settle_round(engine, "blackjack", self.nonce, self.bj_wager, 0, f"Double Bust {p_tot}")
            self._toast(engine, self.bj_result_txt)
            return
        self._bj_stand_and_settle(engine)

    def _bj_stand_and_settle(self, engine: Any) -> None:
        if self.bj_state != "PLAYER_TURN":
            return
        while True:
            d_tot, d_soft, _ = G.evaluate_bj_hand(self.bj_dealer)
            if d_tot < 17 or (d_tot == 17 and d_soft):
                self.bj_dealer.append(self._bj_draw_card())
            else:
                break
        p_tot, _, _ = G.evaluate_bj_hand(self.bj_player)
        d_tot, _, _ = G.evaluate_bj_hand(self.bj_dealer)
        self.bj_state = "SETTLED"
        dbl_tag = "2x DOUBLE " if self.bj_doubled else ""

        if d_tot > 21:
            payout = self.bj_wager * 2
            self.bj_result_txt = f"{dbl_tag}WIN 2.0x! Dealer Bust {d_tot} (+{G.fmt_usd(payout)})"
            self._settle_round(engine, "blackjack", self.nonce, self.bj_wager, payout, f"Win vs Dealer Bust {d_tot}")
        elif p_tot > d_tot:
            payout = self.bj_wager * 2
            self.bj_result_txt = f"{dbl_tag}WIN 2.0x! {p_tot} beats {d_tot} (+{G.fmt_usd(payout)})"
            self._settle_round(engine, "blackjack", self.nonce, self.bj_wager, payout, f"Win {p_tot} vs {d_tot}")
        elif p_tot == d_tot:
            payout = self.bj_wager
            self.bj_result_txt = f"PUSH 1.0x ({p_tot} vs {d_tot}) - Returned {G.fmt_usd(payout)}"
            self._settle_round(engine, "blackjack", self.nonce, self.bj_wager, payout, f"Push {p_tot}")
        else:
            self.bj_result_txt = f"DEALER WINS ({d_tot} vs {p_tot})"
            self._settle_round(engine, "blackjack", self.nonce, self.bj_wager, 0, f"Lose {p_tot} vs {d_tot}")
        self._toast(engine, self.bj_result_txt)

    # ========================================================================
    # CORE HOOK CONTRACT FOR `EagleCompanion.py`
    # ========================================================================
    def on_open(self, engine: Any) -> None:
        if not self._has_active_round():
            self.view = "lobby"
        if engine is not None:
            cash = max(MIN_BET, int(getattr(engine, "cash", 500)))
            if self.bet_amount > cash:
                self.bet_amount = max(MIN_BET, min(500, cash))
        self._toast(engine, "EagleStake VIP Casino - Click Any Game or Press [1-8]")

    def on_back(self, engine: Any) -> bool:
        if self.view == "game":
            self.view = "lobby"
            self._toast(engine, "EagleStake Originals Lobby - Choose 1 of 8 Games")
            return True
        return False

    def tick(self, engine: Any) -> bool:
        dirty = False

        # 1. Sicbo MD5 shake animation
        if self.sicbo_anim_ticks > 0:
            self.sicbo_anim_ticks -= 1
            t = self.sicbo_anim_ticks
            self.sicbo_display_dice = [((t * 3 + 1) % 6) + 1, ((t * 5 + 2) % 6) + 1, ((t * 2 + 4) % 6) + 1]
            if self.sicbo_anim_ticks <= 0:
                self._finish_sicbo_roll(engine)
            dirty = True

        # 2. Slots 3x5 reel cascade animation
        if self.slots_anim_ticks > 0:
            self.slots_anim_ticks -= 1
            if self.slots_anim_ticks <= 0:
                self._finish_slots_spin(engine)
            else:
                # Cycle spinning symbols on unlocked right-hand columns
                locked_cols = max(0, 5 - self.slots_anim_ticks)
                target_flat = self.slots_pending["flat"] if self.slots_pending else self.slots_grid_flat
                syms = G.SLOT_SYMBOLS
                step_seed = self.slots_anim_ticks
                disp: list[str] = []
                for r in range(3):
                    for c in range(5):
                        if c < locked_cols:
                            disp.append(target_flat[r * 5 + c])
                        else:
                            disp.append(syms[(step_seed * 3 + r * 2 + c) % len(syms)])
                self.slots_grid_flat = disp
                self.slots_win_mask = "0" * 15
            dirty = True

        # 3. Crash 1000x realtime flight
        if self.crash_state == "FLYING":
            now = time.monotonic()
            if self.crash_cashed and self.crash_cash_mono > 0.0:
                # Accelerate post-cashout reveal so player sees true crash point quickly!
                base_el = self.crash_cash_mono - self.crash_start_mono
                post_el = (now - self.crash_cash_mono) * 8.5
                elapsed = base_el + post_el
            else:
                elapsed = now - self.crash_start_mono

            m = G.crash_mult_at_elapsed(elapsed)
            auto_val = G.CRASH_AUTO_PRESETS[self.crash_auto_idx][1]
            if (not self.crash_cashed) and auto_val > 1.0 and self.crash_point >= auto_val and m >= auto_val:
                self._cashout_crash(engine, forced_mult=auto_val)

            if m >= self.crash_point:
                self.crash_cur_mult = self.crash_point
                self.crash_state = "CRASHED"
                self._update_crash_curve_csv(self.crash_point)
                self.crash_history.append(self.crash_point)
                self.crash_history = self.crash_history[-7:]
                if not self.crash_cashed:
                    self._settle_round(
                        engine, "crash", self.nonce, self.crash_bet, 0,
                        f"Busted @ {self.crash_point:.2f}x",
                    )
                    self._toast(engine, f"CRASHED @ {self.crash_point:.2f}x!")
                else:
                    self._toast(
                        engine,
                        f"Cashed {self.crash_cash_mult:.2f}x (+{G.fmt_usd(self.crash_cash_payout)}) - Flew to {self.crash_point:.2f}x",
                    )
            else:
                self.crash_cur_mult = m
                self._update_crash_curve_csv(m)
            dirty = True

        # 4. Plinko multi-ball realtime bounce
        if self.plinko_balls:
            still_falling: list[dict[str, Any]] = []
            for b in self.plinko_balls:
                rows = int(b["rows"])
                speed = 0.95 if rows >= 16 else 0.72
                b["row_f"] = min(float(rows), float(b["row_f"]) + speed)
                r_idx = int(b["row_f"])
                # Cumulative deflection across completed peg rows
                steps = b["steps"]
                rights = sum(steps[:r_idx])
                # Centered offset in [-r_idx/2 .. +r_idx/2]
                b["col_f"] = rights - (r_idx * 0.5)
                if b["row_f"] >= float(rows):
                    self._land_plinko_ball(engine, b)
                else:
                    still_falling.append(b)
            self.plinko_balls = still_falling
            dirty = True

        # 5. Xoc Dia shaker animation
        if self.xocdia_anim_ticks > 0:
            self.xocdia_anim_ticks -= 1
            t = self.xocdia_anim_ticks
            self.xocdia_coins = ["R" if ((t + k) % 2 == 0) else "W" for k in range(4)]
            if self.xocdia_anim_ticks <= 0:
                self._finish_xocdia(engine)
            dirty = True

        return dirty

    def step_simulation(self, engine: Any) -> None:
        # Organic 2-second progressive jackpot drip
        inc = int(time.time()) % 7
        self.mega_pot = round(self.mega_pot + 18.0 + inc * 5.0, 2)
        self.sicbo_pot = round(self.sicbo_pot + 9.0 + inc * 3.0, 2)

    def poll_hotkeys(self, engine: Any) -> bool:
        if engine is None or getattr(engine, "bridge", None) is None:
            return False
        hit_vk = 0
        for vk in range(0x31, 0x39):  # Keys '1' .. '8'
            if engine.bridge.poll_hotkey_edge(vk):
                hit_vk = vk
                break
        if hit_vk == 0:
            return False

        num = hit_vk - 0x30  # 1..8
        lock = getattr(engine, "lock", None)
        if lock is not None:
            with lock:
                self._handle_number_hotkey(engine, num)
                if hasattr(engine, "_write_hud_dat"):
                    engine._write_hud_dat(force=True)
        else:
            self._handle_number_hotkey(engine, num)
        return True

    def _handle_number_hotkey(self, engine: Any, num: int) -> None:
        if self.view == "lobby":
            self._open_game(engine, num)
            return
        g = self.active_game
        if g == 1 and 1 <= num <= 5:
            self.sicbo_pick_idx = num - 1
            lbl = G.SICBO_BETS[self.sicbo_pick_idx][1]
            self._toast(engine, f"Selected Door: {lbl}")
        elif g == 3 and 1 <= num <= 6:
            self.crash_auto_idx = num - 1
            self._toast(engine, f"Auto Cashout: {G.CRASH_AUTO_PRESETS[self.crash_auto_idx][0]}")
        elif g == 4 and 1 <= num <= 5 and self.mines_state != "ACTIVE":
            self.mines_preset_idx = num - 1
            self._toast(engine, f"Mines Count: {G.MINES_PRESETS[self.mines_preset_idx]}")
        elif g == 5 and 1 <= num <= 3:
            self.plinko_risk_idx = num - 1
            self._toast(engine, f"Plinko Risk: {G.PLINKO_RISK_OPTIONS[self.plinko_risk_idx]}")
        elif g == 6 and num == 1:
            self.dice_mode = "UNDER" if self.dice_mode == "OVER" else "OVER"
            self._toast(engine, f"Dice Mode: ROLL {self.dice_mode}")
        elif g == 7 and 1 <= num <= 6:
            self.xocdia_pick_idx = num - 1
            self._toast(engine, f"Xoc Dia Door: {G.XOCDIA_BETS[self.xocdia_pick_idx][1]}")
        elif g == 8 and self.bj_state == "PLAYER_TURN":
            if num == 1:
                self._bj_hit(engine)
            elif num == 2:
                self._bj_stand_and_settle(engine)
            elif num == 3:
                self._bj_double(engine)

    def _open_game(self, engine: Any, game_id: int) -> None:
        gid = ((int(game_id) - 1) % 8) + 1
        self.active_game = gid
        self.lobby_sel = gid - 1
        self.view = "game"
        meta = GAME_META[gid - 1]
        self._toast(engine, f"{meta['title']} ({meta['sub']}) - Bet {G.fmt_usd(self.bet_amount)}")

    def move_vertical(self, engine: Any, delta: int) -> None:
        if self.view == "lobby":
            row = (self.lobby_sel // 2 + delta) % 4
            col = self.lobby_sel % 2
            self.lobby_sel = row * 2 + col
            return
        g = self.active_game
        if g == 4:
            r = (self.mines_cursor // 5 + delta) % 5
            c = self.mines_cursor % 5
            self.mines_cursor = r * 5 + c
        elif g == 5:
            self.plinko_rows_idx = (self.plinko_rows_idx - delta) % len(G.PLINKO_ROWS_OPTIONS)
        else:
            self._adjust_bet_step(engine, -delta)

    def adjust_horizontal(self, engine: Any, delta: int) -> None:
        if self.view == "lobby":
            row = self.lobby_sel // 2
            col = (self.lobby_sel % 2 + delta) % 2
            self.lobby_sel = row * 2 + col
            return
        g = self.active_game
        if g == 1:
            self.sicbo_pick_idx = (self.sicbo_pick_idx + delta) % len(G.SICBO_BETS)
        elif g == 3:
            self.crash_auto_idx = (self.crash_auto_idx + delta) % len(G.CRASH_AUTO_PRESETS)
        elif g == 4:
            if self.mines_state == "ACTIVE":
                r = self.mines_cursor // 5
                c = (self.mines_cursor % 5 + delta) % 5
                self.mines_cursor = r * 5 + c
            else:
                self.mines_preset_idx = (self.mines_preset_idx + delta) % len(G.MINES_PRESETS)
        elif g == 5:
            self.plinko_risk_idx = (self.plinko_risk_idx + delta) % len(G.PLINKO_RISK_OPTIONS)
        elif g == 6:
            self.dice_target = max(5, min(95, self.dice_target + delta))
        elif g == 7:
            self.xocdia_pick_idx = (self.xocdia_pick_idx + delta) % len(G.XOCDIA_BETS)
        elif g == 8 and self.bj_state == "PLAYER_TURN":
            max_btn = 3 if len(self.bj_player) == 2 else 2
            self.bj_btn_sel = (self.bj_btn_sel + delta) % max_btn
        else:
            self._adjust_bet_step(engine, delta)

    def execute_primary(self, engine: Any, secondary: bool = False) -> None:
        if self.view == "lobby":
            if secondary:
                self.claim_rakeback(engine)
            else:
                self._open_game(engine, self.lobby_sel + 1)
            return

        g = self.active_game
        if secondary:
            if g == 4 and self.mines_state == "ACTIVE":
                self._cashout_mines(engine)
            elif g == 6:
                self.dice_mode = "UNDER" if self.dice_mode == "OVER" else "OVER"
                self._toast(engine, f"Switched to ROLL {self.dice_mode}")
            elif g == 8 and self.bj_state == "PLAYER_TURN":
                self._bj_stand_and_settle(engine)
            else:
                self._scale_bet(engine, "double")
            return

        # Primary (`F9 / Enter / U` or Green Action Button)
        if g == 1:
            self._play_sicbo(engine)
        elif g == 2:
            self._play_slots(engine)
        elif g == 3:
            self._start_crash(engine)
        elif g == 4:
            if self.mines_state == "ACTIVE":
                self._pick_mines_tile(engine, self.mines_cursor)
            else:
                self._start_mines(engine)
        elif g == 5:
            self._drop_plinko_ball(engine)
        elif g == 6:
            self._play_dice(engine)
        elif g == 7:
            self._play_xocdia(engine)
        elif g == 8:
            if self.bj_state == "PLAYER_TURN":
                if self.bj_btn_sel == 0:
                    self._bj_hit(engine)
                elif self.bj_btn_sel == 1:
                    self._bj_stand_and_settle(engine)
                else:
                    self._bj_double(engine)
            else:
                self._deal_blackjack(engine)

    def on_wheel(self, engine: Any, step: int) -> None:
        # Note: step == -1 is Wheel Up, step == +1 is Wheel Down
        direction = -int(step)
        if self.view == "game" and self.active_game == 6:
            self.dice_target = max(5, min(95, self.dice_target + direction * 2))
            self._toast(engine, f"Dice Target: {self.dice_target}.00")
            return
        self._adjust_bet_step(engine, direction)

    def on_touch(self, engine: Any, code: int, arg: int) -> None:
        if code == 3:
            # Optional sub-mode tab strip support
            if self.view == "game" and self.active_game == 5 and 0 <= arg <= 2:
                self.plinko_risk_idx = arg
            return
        if code != 15:
            return

        # Lobby cards 1..8
        if 1 <= arg <= 8:
            self._open_game(engine, arg)
            return
        if arg == 10:
            self.claim_rakeback(engine)
            return
        if arg == 11:
            self.rotate_seeds(engine)
            return

        # Header Navigation inside Game View
        if arg == 900:
            self.view = "lobby"
            self._toast(engine, "EagleStake Originals Lobby")
            return
        if arg == 901:
            self._open_game(engine, ((self.active_game - 2) % 8) + 1)
            return
        if arg == 902:
            self._open_game(engine, (self.active_game % 8) + 1)
            return

        # Unified Bet Control Bar
        if arg == 21:
            self._adjust_bet_step(engine, -1)
            return
        if arg == 22:
            self._adjust_bet_step(engine, +1)
            return
        if arg == 23:
            self._scale_bet(engine, "half")
            return
        if arg == 24:
            self._scale_bet(engine, "double")
            return
        if arg == 25:
            self._scale_bet(engine, "min")
            return
        if arg == 26:
            self._scale_bet(engine, "max")
            return

        # Primary / Secondary / Tertiary Action Buttons
        if arg == 30:
            if self.active_game == 4 and self.mines_state == "ACTIVE":
                if len(self.mines_opened) >= 1:
                    self._cashout_mines(engine)
                else:
                    # Pick random unopened tile if user clicks green button before picking a tile
                    rem = [i for i in range(25) if i not in self.mines_opened]
                    if rem:
                        self._pick_mines_tile(engine, rem[int(time.time() * 1000) % len(rem)])
            elif self.active_game == 8 and self.bj_state == "PLAYER_TURN":
                self._bj_hit(engine)
            else:
                self.execute_primary(engine, secondary=False)
            return
        if arg == 31:
            if self.active_game == 4 and self.mines_state == "ACTIVE":
                rem = [i for i in range(25) if i not in self.mines_opened]
                if rem:
                    self._pick_mines_tile(engine, rem[(self.nonce + len(rem)) % len(rem)])
            elif self.active_game == 8 and self.bj_state == "PLAYER_TURN":
                self._bj_stand_and_settle(engine)
            return
        if arg == 32:
            if self.active_game == 8 and self.bj_state == "PLAYER_TURN":
                self._bj_double(engine)
            return

        # Game #1 Sicbo Doors (141..145)
        if 141 <= arg <= 145:
            self.sicbo_pick_idx = arg - 141
            lbl = G.SICBO_BETS[self.sicbo_pick_idx][1]
            self._toast(engine, f"Bet Door: {lbl}")
            return

        # Game #2 Slots Spin (201)
        if arg == 201:
            self._play_slots(engine)
            return

        # Game #3 Crash Auto Presets (301..306) & Cashout (310)
        if 301 <= arg <= 306:
            self.crash_auto_idx = arg - 301
            self._toast(engine, f"Auto Cashout: {G.CRASH_AUTO_PRESETS[self.crash_auto_idx][0]}")
            return
        if arg == 310:
            self._cashout_crash(engine)
            return

        # Game #4 Mines 5x5 Grid Tiles (101..125) & Mines Count Presets (401..405)
        if 101 <= arg <= 125:
            if self.mines_state != "ACTIVE":
                self._start_mines(engine)
            self._pick_mines_tile(engine, arg - 101)
            return
        if 401 <= arg <= 405:
            if self.mines_state == "ACTIVE":
                self._toast(engine, "Cashout current Mines board before changing difficulty!")
            else:
                self.mines_preset_idx = arg - 401
                self._toast(engine, f"Difficulty: {G.MINES_PRESETS[self.mines_preset_idx]} Mines")
            return

        # Game #5 Plinko Rows (501..503) & Risk (511..513)
        if 501 <= arg <= 503:
            self.plinko_rows_idx = arg - 501
            self._toast(engine, f"Plinko Pyramid: {G.PLINKO_ROWS_OPTIONS[self.plinko_rows_idx]} Rows")
            return
        if 511 <= arg <= 513:
            self.plinko_risk_idx = arg - 511
            self._toast(engine, f"Plinko Risk: {G.PLINKO_RISK_OPTIONS[self.plinko_risk_idx]}")
            return

        # Game #6 Stake Dice Target & Mode (601..610)
        if arg == 601:
            self.dice_target = max(5, self.dice_target - 5)
            return
        if arg == 602:
            self.dice_target = max(5, self.dice_target - 1)
            return
        if arg == 603:
            self.dice_target = min(95, self.dice_target + 1)
            return
        if arg == 604:
            self.dice_target = min(95, self.dice_target + 5)
            return
        if arg == 610:
            self.dice_mode = "UNDER" if self.dice_mode == "OVER" else "OVER"
            self._toast(engine, f"Dice Mode: ROLL {self.dice_mode} {self.dice_target}.00")
            return

        # Game #7 Xoc Dia 6 Doors (701..706)
        if 701 <= arg <= 706:
            self.xocdia_pick_idx = arg - 701
            self._toast(engine, f"Xoc Dia Door: {G.XOCDIA_BETS[self.xocdia_pick_idx][1]}")
            return

        # Game #8 Blackjack Actions (801..803)
        if arg == 801:
            if self.bj_state == "PLAYER_TURN":
                self._bj_hit(engine)
            else:
                self._deal_blackjack(engine)
            return
        if arg == 802:
            self._bj_stand_and_settle(engine)
            return
        if arg == 803:
            self._bj_double(engine)
            return

    def handle_action(self, engine: Any, payload: dict[str, Any]) -> None:
        act = str(payload.get("action", ""))
        if act == "stake_lobby":
            self.view = "lobby"
        elif act == "stake_open_game":
            self._open_game(engine, int(payload.get("game", 1)))
        elif act == "stake_set_bet":
            amt = max(MIN_BET, min(MAX_BET, int(payload.get("bet", 500))))
            self.bet_amount = amt
            self._toast(engine, f"Bet Set: {G.fmt_usd(amt)}")
        elif act == "stake_touch":
            self.on_touch(engine, int(payload.get("code", 15)), int(payload.get("arg", 0)))
        elif act == "stake_bet":
            instant = bool(payload.get("instant", False))
            g = self.active_game
            if g == 1:
                if "pick_idx" in payload:
                    self.sicbo_pick_idx = int(payload["pick_idx"]) % 5
                self._play_sicbo(engine, instant=instant)
            elif g == 2:
                self._play_slots(engine, instant=instant)
            elif g == 3:
                if "auto_idx" in payload:
                    self.crash_auto_idx = int(payload["auto_idx"]) % 6
                self._start_crash(engine)
            elif g == 4:
                if "preset_idx" in payload and self.mines_state != "ACTIVE":
                    self.mines_preset_idx = int(payload["preset_idx"]) % 5
                self._start_mines(engine)
            elif g == 5:
                if "rows_idx" in payload:
                    self.plinko_rows_idx = int(payload["rows_idx"]) % 3
                if "risk_idx" in payload:
                    self.plinko_risk_idx = int(payload["risk_idx"]) % 3
                self._drop_plinko_ball(engine, instant=instant)
            elif g == 6:
                if "target" in payload:
                    self.dice_target = max(5, min(95, int(payload["target"])))
                if "mode" in payload:
                    self.dice_mode = "UNDER" if str(payload["mode"]).upper() == "UNDER" else "OVER"
                self._play_dice(engine)
            elif g == 7:
                if "pick_idx" in payload:
                    self.xocdia_pick_idx = int(payload["pick_idx"]) % 6
                self._play_xocdia(engine, instant=instant)
            elif g == 8:
                self._deal_blackjack(engine)
        elif act == "stake_cashout":
            if self.active_game == 3:
                self._cashout_crash(engine)
            elif self.active_game == 4:
                self._cashout_mines(engine)
        elif act == "stake_mines_pick":
            self._pick_mines_tile(engine, int(payload.get("tile", 0)))
        elif act == "stake_bj_act":
            sub = str(payload.get("move", "HIT")).upper()
            if sub == "HIT":
                self._bj_hit(engine)
            elif sub == "STAND":
                self._bj_stand_and_settle(engine)
            elif sub == "DOUBLE":
                self._bj_double(engine)
        elif act == "stake_claim_rakeback":
            self.claim_rakeback(engine)
        elif act == "stake_rotate_seeds":
            self.rotate_seeds(engine)
        elif act == "stake_reload_hud":
            self.hud_ver = str(int(self.hud_ver) + 1)

    # ========================================================================
    # HUD KEY-VALUE PROJECTION (`EaglePhoneHUD.dat` — 100% CLEAN ASCII)
    # ========================================================================
    def build_hud_kv(self, engine: Any) -> dict[str, str]:
        cash = int(getattr(engine, "cash", 0)) if engine is not None else 0
        tier_name, tier_pct = compute_vip_tier(self.total_wagered)
        meta = GAME_META[self.active_game - 1]
        dice_chance, dice_mult = G.dice_stats(self.dice_target, self.dice_mode)

        # Mines 25-char board string: H=Hidden, D=Opened Diamond, B=Hit Bomb, d=Dim Diamond, b=Dim Bomb
        mn_chars: list[str] = []
        for idx in range(25):
            if self.mines_state == "ACTIVE":
                mn_chars.append("D" if idx in self.mines_opened else "H")
            elif self.mines_state in ("BOOM", "CASHED"):
                if idx == self.mines_boom_idx:
                    mn_chars.append("B")
                elif idx in self.mines_opened:
                    mn_chars.append("D")
                elif idx in self.mines_bombs:
                    mn_chars.append("b")
                else:
                    mn_chars.append("d")
            else:
                mn_chars.append("H")

        # Plinko active balls compact CSV: "rowF:colF;rowF:colF"
        pl_balls_str = ";".join(f"{b['row_f']:.2f}:{b['col_f']:.2f}" for b in self.plinko_balls[:6])
        pl_rows = G.PLINKO_ROWS_OPTIONS[self.plinko_rows_idx]
        pl_risk = G.PLINKO_RISK_OPTIONS[self.plinko_risk_idx]
        pl_table = G.PLINKO_PAYTABLES[(pl_rows, pl_risk)]
        pl_mults_csv = ",".join(
            (f"{int(m)}" if m >= 10.0 else f"{m:g}") for m in pl_table
        )

        # Blackjack dealer masking during PLAYER_TURN
        p_tot, p_soft, _ = G.evaluate_bj_hand(self.bj_player)
        p_pts_lbl = f"Soft {p_tot}" if (p_soft and p_tot <= 21 and self.bj_state == "PLAYER_TURN") else str(p_tot)
        if self.bj_state == "PLAYER_TURN" and len(self.bj_dealer) >= 2:
            d_cards_str = f"{self.bj_dealer[0]},??"
            d_pts_lbl = f"{G.card_rank_value(self.bj_dealer[0])} + ?"
        else:
            d_cards_str = ",".join(self.bj_dealer)
            d_tot, _, _ = G.evaluate_bj_hand(self.bj_dealer)
            d_pts_lbl = str(d_tot)

        raw: dict[str, Any] = {
            "stake_hud_ver": self.hud_ver,
            "stake_view": self.view,
            "stake_lobby_sel": str(self.lobby_sel),
            "stake_game": str(self.active_game),
            "stake_game_title": meta["title"],
            "stake_game_sub": meta["sub"],
            "stake_cash": G.fmt_usd(cash),
            "stake_bet": G.fmt_usd(self.bet_amount),
            "stake_vip": f"{tier_name.upper()} ({tier_pct}%)",
            "stake_rakeback": G.fmt_usd(int(self.rakeback_unclaimed)),
            "stake_mega_pot": G.fmt_usd(int(self.mega_pot)),
            "stake_sicbo_pot": G.fmt_usd(int(self.sicbo_pot)),
            "stake_seed_hash": G.sha256_hex(self.server_seed)[:16],
            "stake_client_seed": self.client_seed,
            "stake_nonce": str(self.nonce),
            "stake_status": self.status_line,
            "stake_last_win": G.fmt_usd(self.last_win_amt),

            # 1. Sicbo MD5
            "stake_sb_pick": str(self.sicbo_pick_idx),
            "stake_sb_anim": "1" if self.sicbo_anim_ticks > 0 else "0",
            "stake_sb_dice": ",".join(str(x) for x in self.sicbo_display_dice),
            "stake_sb_md5": self.sicbo_next_round["md5"],
            "stake_sb_plain": self.sicbo_last_plain,
            "stake_sb_res": self.sicbo_last_res,
            "stake_sb_hist": ",".join(self.sicbo_history),

            # 2. Neon Slots 3x5
            "stake_sl_grid": ",".join(self.slots_grid_flat),
            "stake_sl_mask": self.slots_win_mask,
            "stake_sl_anim": "1" if self.slots_anim_ticks > 0 else "0",
            "stake_sl_fs": str(self.slots_fs_left),
            "stake_sl_fsm": str(G.free_spin_multiplier(self.slots_fs_idx + 1) if self.slots_fs_left > 0 else 1),
            "stake_sl_msg": self.slots_status,

            # 3. Crash 1000x
            "stake_cr_state": self.crash_state,
            "stake_cr_mult": f"{self.crash_cur_mult:.2f}x",
            "stake_cr_auto": str(self.crash_auto_idx),
            "stake_cr_cashed": "1" if self.crash_cashed else "0",
            "stake_cr_cash_str": (
                f"CASHED {self.crash_cash_mult:.2f}x (+{G.fmt_usd(self.crash_cash_payout)})"
                if self.crash_cashed
                else ""
            ),
            "stake_cr_live_win": G.fmt_usd(int(round(self.crash_bet * self.crash_cur_mult))) if self.crash_state == "FLYING" else G.fmt_usd(self.bet_amount),
            "stake_cr_pts": self.crash_pts_csv,
            "stake_cr_hist": ",".join(f"{x:.2f}x" for x in self.crash_history),

            # 4. Mines 5x5
            "stake_mn_state": self.mines_state,
            "stake_mn_preset": str(self.mines_preset_idx),
            "stake_mn_cnt": str(G.MINES_PRESETS[self.mines_preset_idx]),
            "stake_mn_cur": str(self.mines_cursor),
            "stake_mn_board": "".join(mn_chars),
            "stake_mn_gems": str(len(self.mines_opened)),
            "stake_mn_mult": f"{self.mines_cur_mult:.2f}x",
            "stake_mn_cashout": G.fmt_usd(int(round(self.mines_bet * self.mines_cur_mult))),
            "stake_mn_msg": self.mines_status,

            # 5. Plinko x1000
            "stake_pl_ridx": str(self.plinko_rows_idx),
            "stake_pl_rows": str(pl_rows),
            "stake_pl_kidx": str(self.plinko_risk_idx),
            "stake_pl_risk": pl_risk,
            "stake_pl_mults": pl_mults_csv,
            "stake_pl_balls": pl_balls_str,
            "stake_pl_last_b": str(self.plinko_last_bucket),
            "stake_pl_hist": ",".join(self.plinko_recent),

            # 6. Stake Dice
            "stake_dc_target": str(self.dice_target),
            "stake_dc_mode": self.dice_mode,
            "stake_dc_roll": f"{self.dice_last_roll:.2f}",
            "stake_dc_won": "1" if self.dice_last_won else "0",
            "stake_dc_mult": f"{dice_mult:.2f}x",
            "stake_dc_chance": f"{dice_chance:.0f}%",
            "stake_dc_hist": ",".join(self.dice_history),

            # 7. Xoc Dia
            "stake_xd_pick": str(self.xocdia_pick_idx),
            "stake_xd_anim": "1" if self.xocdia_anim_ticks > 0 else "0",
            "stake_xd_coins": ",".join(self.xocdia_coins),
            "stake_xd_res": self.xocdia_last_lbl,
            "stake_xd_hist": ",".join(self.xocdia_history),

            # 8. Blackjack 21
            "stake_bj_state": self.bj_state,
            "stake_bj_pcards": ",".join(self.bj_player),
            "stake_bj_dcards": d_cards_str,
            "stake_bj_ppts": p_pts_lbl,
            "stake_bj_dpts": d_pts_lbl,
            "stake_bj_can_dbl": "1" if (self.bj_state == "PLAYER_TURN" and len(self.bj_player) == 2) else "0",
            "stake_bj_sel": str(self.bj_btn_sel),
            "stake_bj_msg": self.bj_result_txt,
        }
        return {k: G.sanitize_hud_ascii(v, 180) for k, v in raw.items()}

    def get_summary_stats(self) -> dict[str, Any]:
        tier_name, _ = compute_vip_tier(self.total_wagered)
        return {
            "total_bets": int(self.total_bets),
            "total_wagered": round(self.total_wagered, 2),
            "net_profit": round(self.net_profit, 2),
            "biggest_win": round(self.biggest_win, 2),
            "biggest_mult": round(self.biggest_mult, 2),
            "vip_tier": tier_name,
            "mega_pot": round(self.mega_pot, 2),
            "sicbo_pot": round(self.sicbo_pot, 2),
        }

    def build_web_projection(self, engine: Any) -> dict[str, Any]:
        stats = self.get_summary_stats()
        stats.update({
            "installed": True,
            "view": self.view,
            "active_game": self.active_game,
            "game_title": GAME_META[self.active_game - 1]["title"],
            "bet_amount": self.bet_amount,
            "rakeback_unclaimed": round(self.rakeback_unclaimed, 2),
            "server_seed_sha256": G.sha256_hex(self.server_seed),
            "client_seed": self.client_seed,
            "nonce": self.nonce,
            "status_line": self.status_line,
            "games": GAME_META,
        })
        return stats
