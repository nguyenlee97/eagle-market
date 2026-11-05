"""
Eagle Wall Street Stock Exchange — Live In-Game Runtime Engine (Phase 2)
========================================================================
Synchronizes 1:1 with EagleCompanionEngine (35 Stocks/Commodities + 16 Crypto = 51 Assets,
48-bar OHLC candles, Futures positions, The Eagle Times headlines, Cash & Bank):
  1. Streams 5 live BGRA32 electronic boards into "Local\\EagleWallStreetSHM" for
     EagleWallStreet.asi -> RenderWare RwRasterLock/Unlock direct 3D rendering.
  2. Directs randomized, non-repeating choreography for the strict 18-female cast
     (8 Interactive Brokers 49448..49455 + 10 Ambient Floor NPCs 49456..49465),
     including multi-waypoint staircase traversal and 2-person face-to-face chats.
  3. Powers interactive Broker AI Consultation strictly via OpenAI `gpt-5-nano`
     plus direct Spot BUY/SELL, 10x Futures LONG/SHORT, Close Position, and live
     West/East 3D Candlestick Wall ticker pinning.
"""
from __future__ import annotations

import ctypes
import json
import math
import os
import random
import re
import struct
import textwrap
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

# ============================================================================
# SHARED MEMORY BINARY CONTRACT ("Local\\EagleWallStreetSHM")
# ============================================================================
SHM_NAME = "Local\\EagleWallStreetSHM"
SHM_MAGIC = 0x57535431       # 'WST1'
SHM_VERSION = 1
SHM_TOTAL_BYTES = 0x00902000  # 9,445,376 bytes

OFF_SLOTS_BASE   = 0x00000100  # 18 * 64B = 1152B (0x0100..0x057F)
OFF_TICKER_RING  = 0x00002000  # 2048 x 128 x 4 = 1,048,576 B
OFF_BOARD_MAIN   = 0x00102000  # 1024 x 512 x 4 = 2,097,152 B
OFF_BOARD_CH_A   = 0x00302000  # 1024 x 512 x 4 = 2,097,152 B
OFF_BOARD_CH_B   = 0x00502000  # 1024 x 512 x 4 = 2,097,152 B
OFF_POST_SCREEN  = 0x00702000  # 1024 x 512 x 4 = 2,097,152 B

PAGE_READWRITE = 0x04
FILE_MAP_ALL_ACCESS = 0x000F001F
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

INTERIOR_ORIGIN = (2200.0, -1650.0, 1650.0)
BROKER_AI_MODEL = "gpt-5-nano"  # Strictly gpt-5-nano per user directive (never gpt-6-luna)

CITY_PORTAL_META = [
    {
        "idx": 0,
        "city_en": "Los Santos — Pershing Square Financial Hall",
        "city_vi": "Los Santos — Toa Nha Tai Chinh Pershing Square",
        "door": (1481.0, -1770.5, 18.80),
        "return": (1481.0, -1768.0, 18.80, 0.0),
    },
    {
        "idx": 1,
        "city_en": "San Fierro — Financial District Tower",
        "city_vi": "San Fierro — Thap Tai Chinh Financial District",
        "door": (-1725.5, 789.8, 23.90),
        "return": (-1722.5, 789.8, 24.55, 270.0),
    },
    {
        "idx": 2,
        "city_en": "Downtown Chicago — LaSalle Stock Exchange",
        "city_vi": "Downtown Chicago — San Chung Khoan LaSalle",
        "door": (6256.2, 9257.5, 7.80),
        "return": (6252.8, 9257.5, 8.45, 90.0),
    },
    {
        "idx": 3,
        "city_en": "Liberty City — South Staunton Exchange",
        "city_vi": "Liberty City — Trung Tam Chung Khoan Staunton",
        "door": (14580.9, 7766.5, 21.52),
        "return": (14580.9, 7762.5, 22.15, 180.0),
    },
]

ORDER_SIZE_STEPS = [500, 1000, 2500, 10000, 25000, 100000]

# ============================================================================
# STRICT 18-FEMALE CAST (8 INTERACTIVE BROKERS + 10 AMBIENT FLOOR NPCS)
# ============================================================================
BROKERS_8 = [
    {
        "slot": 0,
        "ped_id": 49448,
        "stem": "ws_yanagi",
        "name": "Tsukishiro Yanagi",
        "origin": "Zenless Zone Zero",
        "desk_en": "Post 01 — AI, Semiconductors & Gaming",
        "desk_vi": "Quay 01 — AI, Ban Dan & Game Tech",
        "stationary": True,
        "local_pos": (-4.15, -5.20, 0.05),
        "default_hdg": 180.0,
        "persona": (
            "You are Tsukishiro Yanagi, calm, razor-sharp Chief Tech & Semiconductor Broker at Post 01 of the "
            "Eagle Wall Street Stock Exchange. You speak concisely with institutional precision, referencing moving "
            "averages, candle momentum, and risk discipline."
        ),
        "tickers": ["NVDA", "MSFT", "AAPL", "AMD", "AVGO", "TSM", "GOOG", "META", "SONY", "NTDOY"],
    },
    {
        "slot": 1,
        "ped_id": 49449,
        "stem": "ws_zani",
        "name": "Zani",
        "origin": "Wuthering Waves",
        "desk_en": "Post 02 — Gold, Oil & Macro Commodities",
        "desk_vi": "Quay 02 — Vang, Dau Tho & Hang Hoa Vimo",
        "stationary": True,
        "local_pos": (-4.15, 5.80, 0.05),
        "default_hdg": 180.0,
        "persona": (
            "You are Zani from Averardo Vault, now Senior Gold, Energy & Macro Commodities Broker at Post 02. "
            "Cool-headed, dry-witted, professional, focused on inflation hedges, safe-haven flows, and tight stops."
        ),
        "tickers": ["XAU", "XAG", "WTIOIL", "BRENT", "NATGAS", "COPPER", "JPM", "BRK.B", "XOM", "CVX"],
    },
    {
        "slot": 2,
        "ped_id": 49450,
        "stem": "ws_evelyn",
        "name": "Evelyn Chevalier",
        "origin": "Zenless Zone Zero",
        "desk_en": "Post 04 — VIP Institutional & Blue-Chips",
        "desk_vi": "Quay 04 — Quy Dinh Che VIP & Blue-Chip",
        "stationary": True,
        "local_pos": (4.15, 5.80, 0.05),
        "default_hdg": 180.0,
        "persona": (
            "You are Evelyn Chevalier, poised VIP Institutional & Blue-Chip Desk Lead at Post 04. "
            "Protective of client capital, tactical, decisive, favoring asymmetric reward-to-risk setups."
        ),
        "tickers": ["BRK.B", "JPM", "V", "MA", "COST", "WMT", "LLY", "UNH", "LMT", "AAPL"],
    },
    {
        "slot": 3,
        "ped_id": 49451,
        "stem": "ws_kazusa",
        "name": "Kyouyama Kazusa",
        "origin": "Blue Archive",
        "desk_en": "Floor Pit — Momentum & Swing Execution",
        "desk_vi": "San Giao Dich — Luot Song & Khop Lenh Nhanh",
        "stationary": False,
        "local_pos": (-1.80, 0.20, 0.05),
        "default_hdg": 90.0,
        "persona": (
            "You are Kyouyama Kazusa, pragmatic Roving Floor Execution Broker in the central pit. "
            "Down-to-earth, candid, allergic to hype, focused on clean breakout entries and quick profit-taking."
        ),
        "tickers": ["TSLA", "NFLX", "PLTR", "COIN", "UBER", "AMZN", "SOL", "DOGE", "NVDA"],
    },
    {
        "slot": 4,
        "ped_id": 49452,
        "stem": "ws_yaowg",
        "name": "Yao (Quant)",
        "origin": "Snowbreak",
        "desk_en": "West Chart — Quantitative & Mean-Reversion",
        "desk_vi": "Bang Nen Tay — Phan Tich Dinh Luong Quant",
        "stationary": False,
        "local_pos": (-8.80, -2.00, 0.05),
        "default_hdg": 90.0,
        "persona": (
            "You are Yao, laid-back low-energy quantitative analyst roving by the giant candlestick walls. "
            "Effortlessly sharp with numbers, MA7/MA20 spreads, overbought/oversold stretches, and minimal fuss."
        ),
        "tickers": ["AMD", "NVDA", "INTC", "ETH", "BTC", "LINK", "AVAX", "GOOG", "MSFT"],
    },
    {
        "slot": 5,
        "ped_id": 49453,
        "stem": "ws_karenina",
        "name": "Karenina: Ember",
        "origin": "Punishing: Gray Raven",
        "desk_en": "Post 03 — Crypto & 10x High-Beta Desk",
        "desk_vi": "Quay 03 — Crypto & Phai Sinh 10x Bien Dong Cao",
        "stationary": True,
        "local_pos": (4.15, -5.20, 0.05),
        "default_hdg": 180.0,
        "persona": (
            "You are Karenina: Ember, energetic and fiery Head of Crypto & High-Beta Derivatives at Post 03. "
            "Direct, confident, loves high-volatility momentum on BTC/SOL/ETH while warning bluntly about 10x liquidation."
        ),
        "tickers": ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "PEPE", "SUI", "TON", "ADA"],
    },
    {
        "slot": 6,
        "ped_id": 49454,
        "stem": "ws_himeko",
        "name": "Himeko",
        "origin": "Honkai: Star Rail",
        "desk_en": "Opening Bell Balcony — Senior Macro Partner",
        "desk_vi": "Ban Cong Chuong Khai Mac — Doi Tac Vimo Cap Cao",
        "stationary": True,
        "local_pos": (1.85, 16.55, 3.25),
        "default_hdg": 180.0,
        "persona": (
            "You are Himeko, elegant Senior Macro Partner presiding over the North Mezzanine Opening Bell podium. "
            "Warm, composed, visionary, connecting macro headlines and cross-sector capital rotation."
        ),
        "tickers": ["XAU", "BTC", "NVDA", "MSFT", "BRK.B", "JPM", "TSM", "ETH", "XOM"],
    },
    {
        "slot": 7,
        "ped_id": 49455,
        "stem": "ws_topaz",
        "name": "Topaz",
        "origin": "Honkai: Star Rail",
        "desk_en": "Floor Pit — IPC Strategic M&A & Turnarounds",
        "desk_vi": "San Giao Dich — Giam Doc Chien Luoc IPC",
        "stationary": False,
        "local_pos": (1.80, 0.20, 0.05),
        "default_hdg": 270.0,
        "persona": (
            "You are Topaz, upbeat and razor-savvy IPC Strategic Investment Director roving the trading floor. "
            "Enthusiastic about undervalued turnarounds, cash-flow Compounders, and disciplined portfolio sizing."
        ),
        "tickers": ["JPM", "GS", "BRK.B", "AAPL", "BTC", "SOL", "XAU", "DIS", "BA", "NKE"],
    },
]

AMBIENT_FEMALES_10 = [
    {"slot": 8,  "ped_id": 49456, "stem": "ws_hina",       "name": "Sorasaki Hina"},
    {"slot": 9,  "ped_id": 49457, "stem": "ws_griselle",   "name": "Griselle"},
    {"slot": 10, "ped_id": 49458, "stem": "ws_mcafe",      "name": "Manhattan Cafe"},
    {"slot": 11, "ped_id": 49459, "stem": "ws_goldcity",   "name": "Gold City"},
    {"slot": 12, "ped_id": 49460, "stem": "ws_bourbon",    "name": "Mihono Bourbon"},
    {"slot": 13, "ped_id": 49461, "stem": "ws_blackswan",  "name": "Black Swan"},
    {"slot": 14, "ped_id": 49462, "stem": "ws_lynette",    "name": "Lynette"},
    {"slot": 15, "ped_id": 49463, "stem": "ws_chevreuse",  "name": "Chevreuse"},
    {"slot": 16, "ped_id": 49464, "stem": "ws_clorinde",   "name": "Clorinde"},
    {"slot": 17, "ped_id": 49465, "stem": "ws_arlecchino", "name": "Arlecchino"},
]


def gta_heading_toward(sx: float, sy: float, tx: float, ty: float) -> float:
    """Exact GTA SA 0173 heading so ped at (sx, sy) faces (tx, ty)."""
    dx = tx - sx
    dy = ty - sy
    if abs(dx) < 1e-4 and abs(dy) < 1e-4:
        return 0.0
    return (math.degrees(math.atan2(-dx, dy)) + 360.0) % 360.0


def clean_cfont_ascii(text: str) -> str:
    """Sanitize any string to 100% GTA SA CFont-safe printable ASCII (zero ~ tags, zero non-ASCII)."""
    if not text:
        return ""
    vi_map = str.maketrans(
        "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
        "ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ",
        "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd"
        "AAAAAAAAAAAAAAAAAEEEEEEEEEEEIIIIIOOOOOOOOOOOOOOOOOUUUUUUUUUUUYYYYYD",
    )
    s = str(text).translate(vi_map)
    s = (
        s.replace("—", "-")
        .replace("–", "-")
        .replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("…", "...")
        .replace("~", "-")
    )
    s = re.sub(r"[^\x20-\x7E]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ============================================================================
# INTERIOR CHOREOGRAPHY WAYPOINTS & CONVERSATION PAIRS (LOCAL TO 2200,-1650,1650)
# ============================================================================
# Collision-free interior zones (avoiding Posts at (-6,±5.5), (+6,±5.5), Bull at (0,-14.2), Bell at (0,16.8,3.2))
SOLO_ANCHORS = [
    # Watching West Giant Candlestick Wall (X = -15.65, Y = 0.2)
    {"id": "west_wall_n",  "pos": (-10.4,  4.2, 0.05), "look": (-15.7,  2.2), "anims": [1, 2, 3]},
    {"id": "west_wall_c",  "pos": (-10.2,  0.2, 0.05), "look": (-15.7,  0.2), "anims": [1, 2, 3]},
    {"id": "west_wall_s",  "pos": (-10.4, -3.8, 0.05), "look": (-15.7, -1.8), "anims": [1, 2, 3]},
    {"id": "west_aisle_s", "pos": (-9.5,  -9.2, 0.05), "look": (-15.7, -1.5), "anims": [2, 3, 8]},
    # Watching East Giant Candlestick Wall (X = +15.65, Y = 0.2)
    {"id": "east_wall_n",  "pos": ( 10.4,  4.2, 0.05), "look": ( 15.7,  2.2), "anims": [1, 2, 3]},
    {"id": "east_wall_c",  "pos": ( 10.2,  0.2, 0.05), "look": ( 15.7,  0.2), "anims": [1, 2, 3]},
    {"id": "east_wall_s",  "pos": ( 10.4, -3.8, 0.05), "look": ( 15.7, -1.8), "anims": [1, 2, 3]},
    {"id": "east_aisle_s", "pos": (  9.5, -9.2, 0.05), "look": ( 15.7, -1.5), "anims": [2, 3, 8]},
    # Watching North EAGLE-51 Jumbotron (X = 0.0, Y = 21.6)
    {"id": "north_apron_w", "pos": (-3.6, 11.8, 0.05), "look": (-1.2, 21.6), "anims": [1, 2, 3]},
    {"id": "north_apron_c", "pos": ( 0.0, 12.2, 0.05), "look": ( 0.0, 21.6), "anims": [1, 3, 8]},
    {"id": "north_apron_e", "pos": ( 3.6, 11.8, 0.05), "look": ( 1.2, 21.6), "anims": [1, 2, 3]},
    # Central Pit Watching 360 Overhead Ticker Ring & Post Screens
    {"id": "pit_center_n",  "pos": ( 0.0,  6.4, 0.05), "look": ( 0.0, 21.6), "anims": [1, 2, 8]},
    {"id": "pit_center_m",  "pos": (-1.4,  0.6, 0.05), "look": (-6.0,  5.5), "anims": [2, 4, 8]},
    {"id": "pit_center_e",  "pos": ( 1.6, -1.2, 0.05), "look": ( 6.0, -5.5), "anims": [2, 4, 8]},
    {"id": "pit_south_w",   "pos": (-2.6, -9.4, 0.05), "look": (-6.0, -5.5), "anims": [3, 4, 2]},
    {"id": "pit_south_e",   "pos": ( 2.6, -9.4, 0.05), "look": ( 6.0, -5.5), "anims": [3, 4, 2]},
    # Checking Post Outer Monitors
    {"id": "post1_client",  "pos": (-8.3, -5.5, 0.05), "look": (-6.0, -5.5), "anims": [4, 2]},
    {"id": "post2_client",  "pos": (-8.3,  5.5, 0.05), "look": (-6.0,  5.5), "anims": [4, 2]},
    {"id": "post3_client",  "pos": ( 8.3, -5.5, 0.05), "look": ( 6.0, -5.5), "anims": [4, 2]},
    {"id": "post4_client",  "pos": ( 8.3,  5.5, 0.05), "look": ( 6.0,  5.5), "anims": [4, 2]},
    # Admiring Bronze Charging Bull in South Atrium
    {"id": "bull_view_w",   "pos": (-3.2, -13.6, 0.05), "look": (0.0, -14.2), "anims": [2, 3]},
    {"id": "bull_view_e",   "pos": ( 3.2, -13.6, 0.05), "look": (0.0, -14.2), "anims": [2, 3]},
    # Mezzanine Balcony Overlook (Z = 3.25 — routed via West/East marble stairs!)
    {"id": "balc_west_rail", "pos": (-6.8, 15.8, 3.25), "look": ( 0.0,  0.0), "anims": [1, 2, 3]},
    {"id": "balc_west_mid",  "pos": (-4.0, 16.2, 3.25), "look": (-8.0,  0.0), "anims": [2, 3, 8]},
    {"id": "balc_east_mid",  "pos": ( 4.4, 16.2, 3.25), "look": ( 8.0,  0.0), "anims": [2, 3, 8]},
    {"id": "balc_east_rail", "pos": ( 7.2, 15.8, 3.25), "look": ( 0.0,  0.0), "anims": [1, 2, 3]},
]

# Spontaneous 2-person face-to-face conversation zones
CHAT_PAIR_ZONES = [
    {"id": "chat_pit_north",  "a": (-0.65,  8.8, 0.05), "b": ( 0.65,  8.8, 0.05)},
    {"id": "chat_pit_south",  "a": (-0.65, -7.8, 0.05), "b": ( 0.65, -7.8, 0.05)},
    {"id": "chat_west_aisle", "a": (-9.8,   7.8, 0.05), "b": (-9.8,   9.1, 0.05)},
    {"id": "chat_east_aisle", "a": ( 9.8,   7.8, 0.05), "b": ( 9.8,   9.1, 0.05)},
    {"id": "chat_bull_foyer", "a": (-3.6, -16.2, 0.05), "b": (-2.3, -16.2, 0.05)},
    {"id": "chat_balcony_w",  "a": (-9.2,  17.4, 3.25), "b": (-7.9,  17.4, 3.25)},
]

STAIR_WEST_FLOOR = (-12.6,  8.5, 0.05)
STAIR_WEST_BALC  = (-12.6, 17.1, 3.25)
STAIR_EAST_FLOOR = ( 12.6,  8.5, 0.05)
STAIR_EAST_BALC  = ( 12.6, 17.1, 3.25)


# ============================================================================
# WIN32 SHARED MEMORY WRAPPER
# ============================================================================
class WallStreetShmClient:
    def __init__(self) -> None:
        self.handle = None
        self.base_addr: int = 0
        self._k32 = ctypes.windll.kernel32
        self._k32.CreateFileMappingW.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_wchar_p,
        ]
        self._k32.CreateFileMappingW.restype = ctypes.c_void_p
        self._k32.MapViewOfFile.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
            ctypes.c_uint32, ctypes.c_size_t,
        ]
        self._k32.MapViewOfFile.restype = ctypes.c_void_p
        self._k32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
        self._k32.UnmapViewOfFile.restype = ctypes.c_int
        self._k32.CloseHandle.argtypes = [ctypes.c_void_p]
        self._k32.CloseHandle.restype = ctypes.c_int

    def ensure_open(self) -> bool:
        if self.base_addr:
            return True
        h = self._k32.CreateFileMappingW(
            ctypes.c_void_p(INVALID_HANDLE_VALUE),
            None,
            PAGE_READWRITE,
            0,
            SHM_TOTAL_BYTES,
            SHM_NAME,
        )
        if not h:
            return False
        ptr = self._k32.MapViewOfFile(h, FILE_MAP_ALL_ACCESS, 0, 0, SHM_TOTAL_BYTES)
        if not ptr:
            self._k32.CloseHandle(h)
            return False
        self.handle = h
        self.base_addr = int(ptr)
        magic = self.read_u32(0x00)
        if magic != SHM_MAGIC:
            ctypes.memset(self.base_addr, 0, 0x2000)
            self.write_u32(0x00, SHM_MAGIC)
            self.write_u32(0x04, SHM_VERSION)
            self.write_i32(0x1C, -1)
            self.write_i32(0x20, -1)
            self.write_i32(0x2C, -1)
            self.write_i32(0xB0, -1)
            self.write_i32(0xBC, 148)
        return True

    def close(self) -> None:
        if self.base_addr:
            self._k32.UnmapViewOfFile(ctypes.c_void_p(self.base_addr))
            self.base_addr = 0
        if self.handle:
            self._k32.CloseHandle(ctypes.c_void_p(self.handle))
            self.handle = None

    def read_bytes(self, offset: int, size: int) -> bytes:
        if not self.ensure_open():
            return b"\x00" * size
        return ctypes.string_at(self.base_addr + offset, size)

    def write_bytes(self, offset: int, data: bytes) -> None:
        if not self.ensure_open():
            return
        ctypes.memmove(self.base_addr + offset, data, len(data))

    def read_u32(self, offset: int) -> int:
        return struct.unpack("<I", self.read_bytes(offset, 4))[0]

    def write_u32(self, offset: int, val: int) -> None:
        self.write_bytes(offset, struct.pack("<I", int(val) & 0xFFFFFFFF))

    def read_i32(self, offset: int) -> int:
        return struct.unpack("<i", self.read_bytes(offset, 4))[0]

    def write_i32(self, offset: int, val: int) -> None:
        self.write_bytes(offset, struct.pack("<i", int(val)))

    def read_f32(self, offset: int) -> float:
        return struct.unpack("<f", self.read_bytes(offset, 4))[0]

    def read_header_dict(self) -> dict[str, Any]:
        raw = self.read_bytes(0, 256)
        (
            magic, ver, asi_hb, cs_hb, py_hb,
            inside, entry_city, near_portal, near_broker, near_dist,
            consult_active, consult_broker, px, py, pz, p_area,
            spawned_mask, e_seq, py_cmd_seq, py_cmd_type, py_cmd_arg0, py_cmd_arg1,
            cs_cmd_ack, ped_density_locked,
        ) = struct.unpack_from("<5I4if2i3fi2I6i", raw, 0)
        b_py = struct.unpack_from("<5I", raw, 0x80)
        b_gpu = struct.unpack_from("<5I", raw, 0x94)
        scroll_px, gpu_frames, txd_slot, valid_mask, total_uploads, speed = struct.unpack_from(
            "<2Ii2Ii", raw, 0xA8
        )
        return {
            "magic": magic,
            "version": ver,
            "asi_heartbeat": asi_hb,
            "cs_heartbeat": cs_hb,
            "py_heartbeat": py_hb,
            "inside_exchange": inside,
            "entry_city_idx": entry_city,
            "near_portal_idx": near_portal,
            "near_broker_idx": near_broker,
            "near_broker_dist": round(near_dist, 2),
            "consult_active": consult_active,
            "consult_broker_idx": consult_broker,
            "player_pos": [round(px, 2), round(py, 2), round(pz, 2)],
            "player_area": p_area,
            "spawned_mask": spawned_mask,
            "spawned_count": int(bin(spawned_mask & 0x3FFFF).count("1")),
            "e_press_seq": e_seq,
            "py_cmd_seq": py_cmd_seq,
            "cs_cmd_ack": cs_cmd_ack,
            "ped_density_locked": ped_density_locked,
            "board_py_seq": list(b_py),
            "board_gpu_ack": list(b_gpu),
            "ticker_scroll_px": scroll_px,
            "ticker_gpu_frames": gpu_frames,
            "txd_slot_found": txd_slot,
            "rasters_valid_mask": valid_mask,
            "total_board_uploads": total_uploads,
            "ticker_speed_px_s": speed,
        }


# ============================================================================
# 5-BOARD HIGH-CONTRAST BGRA32 FINANCIAL RENDERER (1:1 EAGLECOMPANION SYNC)
# ============================================================================
class WallStreetBoardRenderer:
    def __init__(self) -> None:
        self._fonts: dict[tuple[str, int], Any] = {}

    def _font(self, size: int, bold: bool = True):
        key = ("b" if bold else "r", size)
        if key in self._fonts:
            return self._fonts[key]
        candidates = (
            ["consolab.ttf", "arialbd.ttf", "segoeuib.ttf"]
            if bold
            else ["consola.ttf", "arial.ttf", "segoeui.ttf"]
        )
        win_fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for c in candidates:
            fp = win_fonts / c
            if fp.exists():
                try:
                    f = ImageFont.truetype(str(fp), size)
                    self._fonts[key] = f
                    return f
                except Exception:
                    pass
        f = ImageFont.load_default()
        self._fonts[key] = f
        return f

    @staticmethod
    def _fmt_price(p: float) -> str:
        if p >= 1000.0:
            return f"{p:,.1f}"
        if p >= 10.0:
            return f"{p:.2f}"
        if p >= 0.1:
            return f"{p:.4f}"
        return f"{p:.6f}"

    def render_all_5_bgra(self, snap: dict[str, Any]) -> dict[int, bytes]:
        """Render all 5 electronic boards from an EagleCompanion market snapshot into raw BGRA32 bytes."""
        return {
            0: self._render_ticker_ring(snap).tobytes("raw", "BGRA"),
            1: self._render_main_jumbotron(snap).tobytes("raw", "BGRA"),
            2: self._render_candlestick_wall(snap, snap["west_sym"], "WEST WALL [T]").tobytes("raw", "BGRA"),
            3: self._render_candlestick_wall(snap, snap["east_sym"], "EAST WALL [Y]").tobytes("raw", "BGRA"),
            4: self._render_post_monitors(snap).tobytes("raw", "BGRA"),
        }

    def _render_ticker_ring(self, snap: dict[str, Any]) -> Image.Image:
        W, H = 2048, 128
        img = Image.new("RGBA", (W, H), (6, 10, 18, 255))
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, W, 6), fill=(245, 190, 55, 255))
        d.rectangle((0, H - 6, W, H), fill=(245, 190, 55, 255))

        f_sym = self._font(32, True)
        f_prc = self._font(28, True)
        assets = snap["ordered_ticker_tape"]
        x = 18
        idx = 0
        while x < W - 40 and assets:
            a = assets[idx % len(assets)]
            idx += 1
            sym = a["symbol"][:7]
            dp = float(a["delta_pct"])
            up = dp >= 0.0
            col = (16, 235, 135, 255) if up else (255, 72, 88, 255)
            sign = "+" if up else ""
            p_txt = f"${self._fmt_price(a['price'])} {sign}{dp:.2f}%"

            d.rounded_rectangle((x, 18, x + 318, H - 18), radius=8, fill=(13, 22, 38, 255), outline=(32, 52, 82, 255), width=2)
            d.text((x + 12, 24), sym, font=f_sym, fill=(250, 208, 76, 255))
            d.text((x + 12, 64), p_txt, font=f_prc, fill=col)
            x += 336
        return img

    def _render_main_jumbotron(self, snap: dict[str, Any]) -> Image.Image:
        W, H = 1024, 512
        img = Image.new("RGBA", (W, H), (7, 12, 22, 255))
        d = ImageDraw.Draw(img)

        # Gold institutional header bar
        d.rectangle((0, 0, W, 56), fill=(15, 25, 45, 255))
        d.rectangle((0, 54, W, 58), fill=(245, 190, 55, 255))
        d.text((18, 12), "EAGLE WALL STREET EXCHANGE  |  LIVE MARKET COMPOSITE", font=self._font(24, True), fill=(250, 208, 76, 255))
        d.text((740, 15), f"{snap['date_str']}  {snap['clock_str']}", font=self._font(21, True), fill=(186, 230, 253, 255))

        # Left Panel: EAGLE-51 Index + Sentiment + Sector Breadth
        d.rounded_rectangle((14, 70, 356, 434), radius=10, fill=(12, 20, 35, 255), outline=(38, 64, 98, 255), width=2)
        idx_val = snap["index_value"]
        idx_dp = snap["index_delta_pct"]
        idx_col = (16, 235, 135, 255) if idx_dp >= 0 else (255, 72, 88, 255)
        d.text((28, 82), "EAGLE-51 INDEX (LIVE)", font=self._font(18, True), fill=(148, 163, 184, 255))
        d.text((28, 108), f"{idx_val:,.2f}", font=self._font(36, True), fill=(248, 250, 252, 255))
        d.text((228, 118), f"{idx_dp:+.2f}%", font=self._font(24, True), fill=idx_col)

        fg_score = snap["sentiment_score"]
        fg_label = snap["sentiment_label"]
        fg_col = (16, 235, 135, 255) if fg_score >= 55 else ((250, 204, 21, 255) if fg_score >= 42 else (255, 72, 88, 255))
        d.text((28, 158), f"SENTIMENT: {fg_label} ({fg_score}/100)", font=self._font(16, True), fill=fg_col)
        d.rectangle((28, 182, 340, 196), fill=(26, 38, 58, 255))
        d.rectangle((28, 182, 28 + int(3.12 * max(4, min(100, fg_score))), 196), fill=fg_col)

        d.text((28, 212), "SECTOR PERFORMANCE", font=self._font(16, True), fill=(250, 208, 76, 255))
        sy = 238
        for sec_name, sec_dp in snap["sectors"][:6]:
            scol = (16, 235, 135, 255) if sec_dp >= 0 else (255, 72, 88, 255)
            d.text((28, sy), f"{sec_name:<12}", font=self._font(16, True), fill=(226, 232, 240, 255))
            bar_w = min(92, max(6, int(abs(sec_dp) * 18.0)))
            if sec_dp >= 0:
                d.rectangle((205, sy + 3, 205 + bar_w, sy + 17), fill=scol)
            else:
                d.rectangle((205 - bar_w, sy + 3, 205, sy + 17), fill=scol)
            d.text((272, sy), f"{sec_dp:+.2f}%", font=self._font(15, True), fill=scol)
            sy += 30

        # Right Panel: 12-Tile Live Finviz Heatmap (4x3)
        d.rounded_rectangle((370, 70, 1010, 434), radius=10, fill=(12, 20, 35, 255), outline=(38, 64, 98, 255), width=2)
        d.text((386, 80), "LIVE S&P / CRYPTO HEATMAP (SYNCED WITH EAGLEPHONE)", font=self._font(17, True), fill=(250, 208, 76, 255))
        tiles = snap["heatmap_12"]
        tw, th = 148, 102
        for idx, t in enumerate(tiles[:12]):
            col_i = idx % 4
            row_i = idx // 4
            tx = 384 + col_i * (tw + 8)
            ty = 108 + row_i * (th + 8)
            dp = float(t["delta_pct"])
            if dp >= 2.0:
                bg = (12, 132, 74, 255)
            elif dp >= 0.0:
                bg = (16, 88, 56, 255)
            elif dp > -2.0:
                bg = (112, 26, 38, 255)
            else:
                bg = (165, 24, 42, 255)
            d.rounded_rectangle((tx, ty, tx + tw, ty + th), radius=7, fill=bg, outline=(255, 255, 255, 65), width=1)
            d.text((tx + 10, ty + 8), t["symbol"][:7], font=self._font(24, True), fill=(255, 255, 255, 255))
            d.text((tx + 10, ty + 40), f"${self._fmt_price(t['price'])}", font=self._font(18, True), fill=(241, 245, 249, 255))
            d.text((tx + 10, ty + 68), f"{dp:+.2f}%", font=self._font(20, True), fill=(254, 249, 195, 255) if dp >= 0 else (254, 202, 202, 255))

        # Bottom Wire: The Eagle Times Live Headline + Player Net Worth
        d.rounded_rectangle((14, 444, 1010, 502), radius=8, fill=(16, 28, 48, 255), outline=(245, 190, 55, 220), width=2)
        wire = clean_cfont_ascii(snap["headline"])[:78]
        d.text((28, 452), f"EAGLE TIMES WIRE: {wire}", font=self._font(17, True), fill=(253, 224, 71, 255))
        nw_line = (
            f"AETHER WALLET: CASH ${snap['cash']:,}  |  BANK ${snap['bank']:,}  |  "
            f"SPOT ${snap['spot_total']:,.0f}  |  ACTIVE FUTURES: {snap['futures_count']} ({snap['futures_pnl']:+.0f}$)"
        )
        d.text((28, 476), nw_line[:96], font=self._font(15, True), fill=(167, 243, 208, 255))
        return img

    def _render_candlestick_wall(self, snap: dict[str, Any], sym: str, wall_tag: str) -> Image.Image:
        W, H = 1024, 512
        img = Image.new("RGBA", (W, H), (6, 11, 20, 255))
        d = ImageDraw.Draw(img)

        asset = snap["assets_by_sym"].get(sym) or next(iter(snap["assets_by_sym"].values()))
        sym = asset["symbol"]
        price = float(asset["price"])
        dp = float(asset["delta_pct"])
        up = dp >= 0.0
        p_col = (16, 235, 135, 255) if up else (255, 72, 88, 255)
        candles = list(asset.get("candles") or [])[-48:]

        # Header
        d.rectangle((0, 0, W, 68), fill=(14, 24, 42, 255))
        d.rectangle((0, 66, W, 70), fill=p_col)
        d.text((18, 10), f"{sym}  -  {clean_cfont_ascii(asset.get('name', sym))[:28]}", font=self._font(26, True), fill=(255, 255, 255, 255))
        d.text((18, 41), f"{wall_tag}  |  48-BAR LIVE OHLCV  |  MA7 (GOLD) / MA20 (CYAN)", font=self._font(15, True), fill=(148, 163, 184, 255))
        d.text((610, 8), f"${self._fmt_price(price)}", font=self._font(32, True), fill=p_col)
        d.text((855, 14), f"{dp:+.2f}%", font=self._font(26, True), fill=p_col)

        # Position badge on header right
        pos_txt = f"YOUR SPOT: {asset.get('spot_qty', 0.0):.4f} (${asset.get('spot_val', 0.0):,.0f})"
        d.text((610, 44), pos_txt[:44], font=self._font(15, True), fill=(253, 224, 71, 255))

        # Chart Canvas (Left 740px)
        cx0, cy0, cx1, cy1 = 18, 82, 748, 418
        vy0, vy1 = 424, 496
        d.rounded_rectangle((cx0, cy0, cx1, vy1), radius=8, fill=(10, 17, 30, 255), outline=(32, 52, 82, 255), width=2)

        if candles:
            hi_all = max(float(c["h"]) for c in candles)
            lo_all = min(float(c["l"]) for c in candles)
            span = max(1e-6, (hi_all - lo_all) * 1.08)
            p_top = hi_all + span * 0.04
            p_bot = max(0.0, lo_all - span * 0.04)
            p_rng = max(1e-6, p_top - p_bot)

            def py_of(val: float) -> int:
                t = (val - p_bot) / p_rng
                return int(cy1 - 12 - t * (cy1 - cy0 - 24))

            # Horizontal price gridlines
            for g_i in range(5):
                gv = p_bot + (p_rng * g_i / 4.0)
                gy = py_of(gv)
                d.line((cx0 + 8, gy, cx1 - 88, gy), fill=(24, 38, 62, 255), width=1)
                d.text((cx1 - 84, gy - 8), self._fmt_price(gv)[:9], font=self._font(13, True), fill=(148, 163, 184, 255))

            n = len(candles)
            plot_w = (cx1 - 96) - (cx0 + 14)
            step_x = plot_w / max(1, n)
            body_w = max(4, int(step_x * 0.62))

            closes = [float(c["c"]) for c in candles]
            ma7_pts = []
            ma20_pts = []

            for i, c in enumerate(candles):
                o_v, h_v, l_v, c_v = float(c["o"]), float(c["h"]), float(c["l"]), float(c["c"])
                mid_x = int(cx0 + 14 + (i + 0.5) * step_x)
                c_up = c_v >= o_v
                ccol = (16, 235, 135, 255) if c_up else (255, 72, 88, 255)
                wy0, wy1 = py_of(h_v), py_of(l_v)
                by0, by1 = py_of(max(o_v, c_v)), py_of(min(o_v, c_v))
                if by1 - by0 < 3:
                    by1 = by0 + 3
                d.line((mid_x, wy0, mid_x, wy1), fill=ccol, width=2)
                d.rectangle((mid_x - body_w // 2, by0, mid_x + body_w // 2, by1), fill=ccol)

                # Synthetic volume bar proportional to candle range
                v_ratio = min(1.0, max(0.12, (h_v - l_v) / max(1e-6, span * 0.28)))
                vh = int((vy1 - vy0 - 10) * v_ratio)
                vcol = (16, 185, 129, 175) if c_up else (239, 68, 68, 175)
                d.rectangle((mid_x - body_w // 2, vy1 - 4 - vh, mid_x + body_w // 2, vy1 - 4), fill=vcol)

                w7 = closes[max(0, i - 6): i + 1]
                w20 = closes[max(0, i - 19): i + 1]
                ma7_pts.append((mid_x, py_of(sum(w7) / len(w7))))
                ma20_pts.append((mid_x, py_of(sum(w20) / len(w20))))

            if len(ma20_pts) >= 2:
                d.line(ma20_pts, fill=(56, 189, 248, 235), width=2)
            if len(ma7_pts) >= 2:
                d.line(ma7_pts, fill=(250, 204, 21, 245), width=2)

        # Right Panel: Live L2 Orderbook & Key Metrics
        ox0, ox1 = 760, 1008
        d.rounded_rectangle((ox0, cy0, ox1, vy1), radius=8, fill=(10, 17, 30, 255), outline=(32, 52, 82, 255), width=2)
        d.text((ox0 + 12, cy0 + 10), "L2 ORDER BOOK", font=self._font(18, True), fill=(250, 208, 76, 255))

        # Asks (top 6)
        ay = cy0 + 40
        d.text((ox0 + 12, ay), "ASK PRICE       SIZE", font=self._font(14, True), fill=(148, 163, 184, 255))
        ay += 22
        for lvl in range(6, 0, -1):
            ask_p = price * (1.0 + 0.0012 * lvl)
            sz = ((hash((sym, lvl, int(price * 100))) & 0xFF) + 40) * 0.15
            bw = min(220, int(sz * 3.8))
            d.rectangle((ox1 - 10 - bw, ay, ox1 - 10, ay + 19), fill=(120, 22, 36, 160))
            d.text((ox0 + 12, ay + 1), self._fmt_price(ask_p)[:10], font=self._font(15, True), fill=(255, 95, 108, 255))
            d.text((ox0 + 150, ay + 1), f"{sz:5.1f}K", font=self._font(15, True), fill=(226, 232, 240, 255))
            ay += 23

        # Spread divider
        d.rectangle((ox0 + 10, ay + 4, ox1 - 10, ay + 32), fill=(20, 34, 58, 255))
        d.text((ox0 + 16, ay + 8), f"LAST: ${self._fmt_price(price)}", font=self._font(16, True), fill=p_col)
        ay += 40

        # Bids (bottom 6)
        for lvl in range(1, 7):
            bid_p = price * (1.0 - 0.0012 * lvl)
            sz = ((hash((sym, -lvl, int(price * 100))) & 0xFF) + 45) * 0.16
            bw = min(220, int(sz * 3.8))
            d.rectangle((ox1 - 10 - bw, ay, ox1 - 10, ay + 19), fill=(14, 98, 62, 160))
            d.text((ox0 + 12, ay + 1), self._fmt_price(bid_p)[:10], font=self._font(15, True), fill=(34, 238, 145, 255))
            d.text((ox0 + 150, ay + 1), f"{sz:5.1f}K", font=self._font(15, True), fill=(226, 232, 240, 255))
            ay += 23
        return img

    def _render_post_monitors(self, snap: dict[str, Any]) -> Image.Image:
        """3-Monitor Horizontal Atlas (1024x512 = 3 x 341px screens for every Horseshoe Trading Post)."""
        W, H = 1024, 512
        img = Image.new("RGBA", (W, H), (8, 13, 24, 255))
        d = ImageDraw.Draw(img)

        # Screen 1 (0..338): Top Movers Watchlist
        d.rounded_rectangle((6, 8, 336, 504), radius=8, fill=(12, 20, 36, 255), outline=(45, 76, 115, 255), width=2)
        d.rectangle((6, 8, 336, 46), fill=(18, 32, 56, 255))
        d.text((16, 16), "TOP MOVERS WATCHLIST", font=self._font(18, True), fill=(250, 208, 76, 255))
        wy = 58
        for a in snap["top_movers"][:11]:
            dp = float(a["delta_pct"])
            col = (16, 235, 135, 255) if dp >= 0 else (255, 72, 88, 255)
            d.text((16, wy), f"{a['symbol']:<6}", font=self._font(18, True), fill=(248, 250, 252, 255))
            d.text((104, wy), f"${self._fmt_price(a['price']):>9}", font=self._font(17, True), fill=(203, 213, 225, 255))
            d.text((236, wy), f"{dp:+6.2f}%", font=self._font(17, True), fill=col)
            d.line((14, wy + 29, 328, wy + 29), fill=(24, 38, 62, 255), width=1)
            wy += 39

        # Screen 2 (344..680): Player Live Wallet & Positions
        d.rounded_rectangle((344, 8, 680, 504), radius=8, fill=(12, 20, 36, 255), outline=(45, 76, 115, 255), width=2)
        d.rectangle((344, 8, 680, 46), fill=(18, 32, 56, 255))
        d.text((356, 16), "CLIENT PORTFOLIO DESK", font=self._font(18, True), fill=(56, 189, 248, 255))
        d.text((356, 58), f"CASH:  ${snap['cash']:,}", font=self._font(19, True), fill=(16, 235, 135, 255))
        d.text((356, 86), f"BANK:  ${snap['bank']:,}", font=self._font(19, True), fill=(186, 230, 253, 255))
        d.text((356, 114), f"SPOT:  ${snap['spot_total']:,.0f}", font=self._font(19, True), fill=(250, 208, 76, 255))
        d.line((354, 144, 670, 144), fill=(45, 76, 115, 255), width=2)
        d.text((356, 154), "ACTIVE HOLDINGS & FUTURES:", font=self._font(15, True), fill=(148, 163, 184, 255))
        py = 182
        pos_lines = snap["position_lines"] or ["No open positions yet.", "Approach any Broker [E]", "to trade Spot or 10x!"]
        for pl in pos_lines[:8]:
            pcol = (255, 92, 104, 255) if " -" in pl else (167, 243, 208, 255)
            d.text((356, py), clean_cfont_ascii(pl)[:30], font=self._font(16, True), fill=pcol)
            py += 36

        # Screen 3 (688..1018): GPT-5-NANO Institutional Research Feed
        d.rounded_rectangle((688, 8, 1018, 504), radius=8, fill=(12, 20, 36, 255), outline=(245, 190, 55, 220), width=2)
        d.rectangle((688, 8, 1018, 46), fill=(36, 28, 14, 255))
        d.text((700, 16), "GPT-5-NANO BROKER WIRE", font=self._font(18, True), fill=(250, 208, 76, 255))
        d.text((700, 58), f"SPEAKER: {snap['ai_broker_name'][:20]}", font=self._font(16, True), fill=(125, 211, 252, 255))
        d.text((700, 84), f"FOCUS: {snap['ai_focus_sym']}  |  WALLS: {snap['west_sym']}/{snap['east_sym']}", font=self._font(15, True), fill=(167, 243, 208, 255))
        d.line((698, 112, 1008, 112), fill=(65, 85, 115, 255), width=1)
        ay = 126
        for ln in textwrap.wrap(clean_cfont_ascii(snap["ai_wire_note"]), width=31)[:10]:
            d.text((700, ay), ln, font=self._font(16, False), fill=(241, 245, 249, 255))
            ay += 28
        d.text((700, 468), "PRESS [E] AT ANY BROKER", font=self._font(16, True), fill=(250, 208, 76, 255))
        return img


# ============================================================================
# 18-FEMALE RANDOMIZED NON-REPEATING CHOREOGRAPHY DIRECTOR
# ============================================================================
class FloorChoreographyDirector:
    def __init__(self) -> None:
        self.rng = random.Random()
        self.visit_epoch = 0
        self.slots: dict[int, dict[str, Any]] = {}
        for s in range(18):
            self.slots[s] = {
                "task_seq": 0,
                "mode": 0,
                "waypoints": [],  # list of (lx, ly, lz, hdg, anim_code, is_walk)
                "wp_idx": 0,
                "next_change_ts": 0.0,
                "taboo": [],
                "pair_id": None,
                "cur_anchor_id": "",
                "last_z": 3.25 if s in (6, 14, 15) else 0.05,
            }

    @staticmethod
    def _to_world(lx: float, ly: float, lz: float) -> tuple[float, float, float]:
        ox, oy, oz = INTERIOR_ORIGIN
        return (ox + lx, oy + ly, oz + lz)

    def _build_stair_route(
        self, start_x: float, start_z: float, dst_pos: tuple[float, float, float], dst_hdg: float, dst_anim: int
    ) -> list[tuple[float, float, float, float, int, int]]:
        dx, dy, dz = dst_pos
        on_balc_now = start_z > 1.6
        on_balc_dst = dz > 1.6
        if on_balc_now == on_balc_dst:
            return [(dx, dy, dz, dst_hdg, dst_anim, 1)]
        # Pick nearer marble staircase (West X=-12.6 vs East X=+12.6)
        use_west = (start_x + dx) <= 0.0
        sf = STAIR_WEST_FLOOR if use_west else STAIR_EAST_FLOOR
        sb = STAIR_WEST_BALC if use_west else STAIR_EAST_BALC
        if not on_balc_now and on_balc_dst:
            h1 = gta_heading_toward(sf[0], sf[1], sb[0], sb[1])
            h2 = gta_heading_toward(sb[0], sb[1], dx, dy)
            return [
                (sf[0], sf[1], sf[2], h1, 0, 1),
                (sb[0], sb[1], sb[2], h2, 0, 1),
                (dx, dy, dz, dst_hdg, dst_anim, 1),
            ]
        else:
            h1 = gta_heading_toward(sb[0], sb[1], sf[0], sf[1])
            h2 = gta_heading_toward(sf[0], sf[1], dx, dy)
            return [
                (sb[0], sb[1], sb[2], h1, 0, 1),
                (sf[0], sf[1], sf[2], h2, 0, 1),
                (dx, dy, dz, dst_hdg, dst_anim, 1),
            ]

    def roll_fresh_visit(self, shm: WallStreetShmClient, now: float) -> None:
        """Roll a brand-new randomized floor & balcony layout across all 18 female characters."""
        self.visit_epoch += 1
        self.rng.seed(int(time.time() * 1000) ^ (self.visit_epoch * 7919))

        # 1. Stationary Desk/Podium Brokers (0, 1, 2, 5, 6)
        desk_anims = [7, 4, 2, 3, 1]
        for b in BROKERS_8:
            if not b["stationary"]:
                continue
            s = b["slot"]
            lx, ly, lz = b["local_pos"]
            anim = self.rng.choice(desk_anims)
            hdg = (b["default_hdg"] + self.rng.uniform(-14.0, 14.0)) % 360.0
            st = self.slots[s]
            st["cur_anchor_id"] = f"desk_{s}"
            st["pair_id"] = None
            st["last_z"] = lz
            st["waypoints"] = [(lx, ly, lz, hdg, anim, 0)]
            st["wp_idx"] = 0
            st["next_change_ts"] = now + self.rng.uniform(14.0, 26.0)
            self._emit_current_waypoint(shm, s, snap_immediately=True)

        # 2. Dynamic Movers: 3 Roving Brokers (3, 4, 7) + 10 Ambient Females (8..17) = 13 movers
        movers = [3, 4, 7] + list(range(8, 18))
        self.rng.shuffle(movers)

        # Form 2 or 3 spontaneous 2-person face-to-face conversations right on entry!
        num_pairs = self.rng.choice([2, 3])
        pair_zones = list(CHAT_PAIR_ZONES)
        self.rng.shuffle(pair_zones)

        used_solo_ids: set[str] = set()
        idx_m = 0
        for p_i in range(num_pairs):
            if idx_m + 1 >= len(movers) or p_i >= len(pair_zones):
                break
            s_a = movers[idx_m]
            s_b = movers[idx_m + 1]
            idx_m += 2
            pz = pair_zones[p_i]
            ax, ay, az = pz["a"]
            bx, by, bz = pz["b"]
            hdg_a = gta_heading_toward(ax, ay, bx, by)
            hdg_b = gta_heading_toward(bx, by, ax, ay)
            dur = self.rng.uniform(16.0, 28.0)
            for s_slot, pos_t, hdg_t, a_code in (
                (s_a, (ax, ay, az), hdg_a, 5),
                (s_b, (bx, by, bz), hdg_b, 6),
            ):
                st = self.slots[s_slot]
                st["cur_anchor_id"] = pz["id"]
                st["pair_id"] = pz["id"]
                st["last_z"] = pos_t[2]
                st["waypoints"] = [(pos_t[0], pos_t[1], pos_t[2], hdg_t, a_code, 0)]
                st["wp_idx"] = 0
                st["next_change_ts"] = now + dur
                st["taboo"] = (st["taboo"] + [pz["id"]])[-4:]
                self._emit_current_waypoint(shm, s_slot, snap_immediately=True)

        # Assign remaining movers to distinct solo anchors (watching boards, thinking, balcony, etc.)
        solo_pool = list(SOLO_ANCHORS)
        self.rng.shuffle(solo_pool)
        for s_slot in movers[idx_m:]:
            chosen = None
            for cand in solo_pool:
                if cand["id"] not in used_solo_ids and cand["id"] not in self.slots[s_slot]["taboo"]:
                    chosen = cand
                    break
            if chosen is None:
                chosen = next((c for c in solo_pool if c["id"] not in used_solo_ids), solo_pool[0])
            used_solo_ids.add(chosen["id"])
            px, py, pz = chosen["pos"]
            lkx, lky = chosen["look"]
            hdg = gta_heading_toward(px, py, lkx, lky)
            anim = self.rng.choice(chosen["anims"])
            st = self.slots[s_slot]
            st["cur_anchor_id"] = chosen["id"]
            st["pair_id"] = None
            st["last_z"] = pz
            st["waypoints"] = [(px, py, pz, hdg, anim, 0)]
            st["wp_idx"] = 0
            st["next_change_ts"] = now + self.rng.uniform(12.0, 27.0)
            st["taboo"] = (st["taboo"] + [chosen["id"]])[-4:]
            self._emit_current_waypoint(shm, s_slot, snap_immediately=True)

    def tick(self, shm: WallStreetShmClient, now: float, consult_slot: int) -> None:
        """Advance multi-waypoint stair routes & schedule continuous non-repeating transitions."""
        occupied_anchors = {st["cur_anchor_id"] for st in self.slots.values() if st["cur_anchor_id"]}

        # 1. Check multi-waypoint progress (stair climbing/descending) via CLEO slot_state == 2
        for s, st in self.slots.items():
            if s == consult_slot:
                continue
            wps = st["waypoints"]
            if st["wp_idx"] + 1 < len(wps):
                slot_off = OFF_SLOTS_BASE + s * 64
                slot_state = shm.read_i32(slot_off + 0x34)
                cs_ack = shm.read_u32(slot_off + 0x1C)
                if cs_ack == st["task_seq"] and slot_state == 2:
                    st["wp_idx"] += 1
                    st["last_z"] = wps[st["wp_idx"]][2]
                    self._emit_current_waypoint(shm, s, snap_immediately=False)

        # 2. Transition Stationary Brokers' desk animations naturally
        for b in BROKERS_8:
            if not b["stationary"]:
                continue
            s = b["slot"]
            if s == consult_slot:
                continue
            st = self.slots[s]
            if now >= st["next_change_ts"]:
                lx, ly, lz = b["local_pos"]
                # Occasionally face their Trading Post monitors vs facing outward/toward boards
                face_monitors = self.rng.random() < 0.42
                if s in (0, 1):
                    hdg = 270.0 if face_monitors else self.rng.choice([90.0, 165.0, 195.0])
                elif s in (2, 5):
                    hdg = 90.0 if face_monitors else self.rng.choice([270.0, 165.0, 195.0])
                else:
                    hdg = self.rng.choice([180.0, 155.0, 205.0, 0.0])
                anim = 4 if face_monitors else self.rng.choice([7, 2, 3, 1])
                st["waypoints"] = [(lx, ly, lz, hdg, anim, 0)]
                st["wp_idx"] = 0
                st["next_change_ts"] = now + self.rng.uniform(15.0, 28.0)
                self._emit_current_waypoint(shm, s, snap_immediately=False)

        # 3. Transition Roving Brokers & Ambient Floor NPCs
        movers = [s for s in ([3, 4, 7] + list(range(8, 18))) if s != consult_slot]
        due = [s for s in movers if now >= self.slots[s]["next_change_ts"] and self.slots[s]["wp_idx"] + 1 >= len(self.slots[s]["waypoints"])]
        if not due:
            return
        self.rng.shuffle(due)

        # If >= 2 NPCs finish around the same moment, 38% chance they meet up for a spontaneous 2-person chat!
        if len(due) >= 2 and self.rng.random() < 0.38:
            free_pairs = [pz for pz in CHAT_PAIR_ZONES if pz["id"] not in occupied_anchors]
            if free_pairs:
                pz = self.rng.choice(free_pairs)
                s_a, s_b = due[0], due[1]
                due = due[2:]
                occupied_anchors.add(pz["id"])
                ax, ay, az = pz["a"]
                bx, by, bz = pz["b"]
                hdg_a = gta_heading_toward(ax, ay, bx, by)
                hdg_b = gta_heading_toward(bx, by, ax, ay)
                dur = self.rng.uniform(18.0, 30.0)
                for s_slot, dst_p, hdg_t, a_code in (
                    (s_a, (ax, ay, az), hdg_a, 5),
                    (s_b, (bx, by, bz), hdg_b, 6),
                ):
                    st = self.slots[s_slot]
                    cur_wx = shm.read_f32(OFF_SLOTS_BASE + s_slot * 64 + 0x28)
                    cur_lx = (cur_wx - INTERIOR_ORIGIN[0]) if abs(cur_wx) > 100.0 else 0.0
                    route = self._build_stair_route(cur_lx, st["last_z"], dst_p, hdg_t, a_code)
                    st["cur_anchor_id"] = pz["id"]
                    st["pair_id"] = pz["id"]
                    st["waypoints"] = route
                    st["wp_idx"] = 0
                    st["last_z"] = route[0][2]
                    st["next_change_ts"] = now + dur
                    st["taboo"] = (st["taboo"] + [pz["id"]])[-4:]
                    self._emit_current_waypoint(shm, s_slot, snap_immediately=False)

        # Remaining due movers walk to fresh solo anchors (including climbing up/down Mezzanine stairs!)
        for s_slot in due:
            st = self.slots[s_slot]
            cands = [
                a for a in SOLO_ANCHORS
                if a["id"] not in occupied_anchors and a["id"] not in st["taboo"]
            ]
            if not cands:
                cands = [a for a in SOLO_ANCHORS if a["id"] not in occupied_anchors] or list(SOLO_ANCHORS)
            chosen = self.rng.choice(cands)
            occupied_anchors.add(chosen["id"])
            px, py, pz = chosen["pos"]
            lkx, lky = chosen["look"]
            hdg = gta_heading_toward(px, py, lkx, lky)
            anim = self.rng.choice(chosen["anims"])

            cur_wx = shm.read_f32(OFF_SLOTS_BASE + s_slot * 64 + 0x28)
            cur_lx = (cur_wx - INTERIOR_ORIGIN[0]) if abs(cur_wx) > 100.0 else 0.0
            route = self._build_stair_route(cur_lx, st["last_z"], (px, py, pz), hdg, anim)

            st["cur_anchor_id"] = chosen["id"]
            st["pair_id"] = None
            st["waypoints"] = route
            st["wp_idx"] = 0
            st["last_z"] = route[0][2]
            st["next_change_ts"] = now + self.rng.uniform(15.0, 31.0)
            st["taboo"] = (st["taboo"] + [chosen["id"]])[-4:]
            self._emit_current_waypoint(shm, s_slot, snap_immediately=False)

    def _emit_current_waypoint(self, shm: WallStreetShmClient, slot: int, snap_immediately: bool) -> None:
        st = self.slots[slot]
        lx, ly, lz, hdg, anim, is_walk = st["waypoints"][st["wp_idx"]]
        wx, wy, wz = self._to_world(lx, ly, lz)
        st["task_seq"] = (st["task_seq"] + 1) & 0x7FFFFFFF
        if st["task_seq"] == 0:
            st["task_seq"] = 1
        mode = 0 if snap_immediately else (1 if is_walk else 0)
        slot_off = OFF_SLOTS_BASE + slot * 64
        packed = struct.pack("<Ii4fi", st["task_seq"], mode, wx, wy, wz, float(hdg), int(anim))
        shm.write_bytes(slot_off, packed)


# ============================================================================
# MAIN WALL STREET FLOOR MANAGER (PLUGGED INTO EAGLECOMPANION)
# ============================================================================
class WallStreetExchangeManager:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.project_root = self.base_dir.parent.parent
        self.shm = WallStreetShmClient()
        self.renderer = WallStreetBoardRenderer()
        self.director = FloorChoreographyDirector()

        self.west_wall_sym = "NVDA"
        self.east_wall_sym = "BTC"
        self.order_size_idx = 2  # default $2,500

        self.inside_exchange = False
        self.near_portal_idx = -1
        self.near_broker_idx = -1
        self.entry_city_idx = 0

        self.active_consult: dict[str, Any] | None = None
        self.ai_broker_name = "Tsukishiro Yanagi"
        self.ai_focus_sym = "NVDA"
        self.ai_wire_note = (
            "Welcome to the Eagle Wall Street Exchange. All 5 LED boards stream 100% real-time "
            "data synced with EaglePhone. Approach any of our 8 Brokers [E] for gpt-5-nano analysis."
        )

        self._last_e_seq = 0
        self._py_cmd_seq = 0
        self._py_hb = 0
        self._board_seq = [0, 0, 0, 0, 0]
        self._last_board_render_ts = 0.0
        self._boards_dirty = True
        self._render_busy = False
        self._ai_busy = False
        self._api_cfg_cache: dict[str, str] | None = None

    def _load_openai_nano_config(self) -> tuple[str, str]:
        if self._api_cfg_cache is None:
            conn_path = self.project_root / "data" / "project-eagle" / "character-chat" / "connection.json"
            base_url = "https://api.openai.com/v1"
            env_name = "EAGLE_CHARACTER_OPENAI_API_KEY"
            if conn_path.exists():
                try:
                    cfg = json.loads(conn_path.read_text(encoding="utf-8"))
                    base_url = str(cfg.get("base_url") or base_url).rstrip("/")
                    env_name = str(cfg.get("api_key_env") or env_name)
                except Exception:
                    pass
            self._api_cfg_cache = {"base_url": base_url, "env_name": env_name}
        key = os.environ.get(self._api_cfg_cache["env_name"], "").strip() or os.environ.get("OPENAI_API_KEY", "").strip()
        return self._api_cfg_cache["base_url"], key

    def send_cleo_cmd(self, cmd_type: int, arg0: int = 0, arg1: int = 0) -> int:
        if not self.shm.ensure_open():
            return 0
        self._py_cmd_seq += 1
        self.shm.write_i32(0x4C, int(cmd_type))
        self.shm.write_i32(0x50, int(arg0))
        self.shm.write_i32(0x54, int(arg1))
        self.shm.write_i32(0x48, int(self._py_cmd_seq))
        return self._py_cmd_seq

    def _build_market_snapshot(self, engine: Any) -> dict[str, Any]:
        """Extract a thread-safe snapshot of all 51 assets, candles, positions & headlines from EagleCompanion."""
        assets_by_sym: dict[str, dict[str, Any]] = {}
        all_assets: list[dict[str, Any]] = []
        for sym, a in list(engine.stocks_market.items()) + list(engine.crypto_market.items()):
            cp = {
                "symbol": sym,
                "name": str(a.get("name", sym)),
                "category": str(a.get("category", a.get("sector", "Market"))),
                "market_group": str(a.get("market_group", "stocks")),
                "price": float(a.get("price", 1.0)),
                "delta_pct": float(a.get("delta_pct", 0.0)),
                "decimals": int(a.get("decimals", 2)),
                "spot_qty": float(a.get("spot_qty", 0.0)),
                "spot_val": float(a.get("spot_val", 0.0)),
                "spot_pnl": float(a.get("spot_pnl", 0.0)),
                "candles": list(a.get("candles") or [])[-48:],
            }
            assets_by_sym[sym] = cp
            all_assets.append(cp)

        if not all_assets:
            dummy = {
                "symbol": "NVDA", "name": "NVIDIA", "category": "Tech", "market_group": "stocks",
                "price": 140.0, "delta_pct": 1.25, "decimals": 2, "spot_qty": 0.0, "spot_val": 0.0,
                "spot_pnl": 0.0, "candles": [{"o": 138, "h": 141, "l": 137, "c": 140}],
            }
            assets_by_sym["NVDA"] = dummy
            all_assets = [dummy]

        avg_dp = sum(a["delta_pct"] for a in all_assets) / len(all_assets)
        index_val = 5100.0 * (1.0 + avg_dp / 100.0)
        advancers = sum(1 for a in all_assets if a["delta_pct"] >= 0.0)
        fg_score = int(round((advancers / len(all_assets)) * 100))
        if fg_score >= 68:
            fg_lbl = "EXTREME GREED"
        elif fg_score >= 54:
            fg_lbl = "BULLISH"
        elif fg_score >= 44:
            fg_lbl = "NEUTRAL"
        else:
            fg_lbl = "RISK-OFF FEAR"

        sector_buckets = [
            ("AI & SEMI", ("NVDA", "AMD", "AVGO", "TSM", "INTC", "PLTR")),
            ("BIG TECH", ("AAPL", "MSFT", "GOOG", "META", "AMZN", "NFLX")),
            ("CRYPTO", ("BTC", "ETH", "SOL", "BNB", "XRP", "DOGE")),
            ("COMMODITIES", ("XAU", "XAG", "WTIOIL", "BRENT", "NATGAS")),
            ("FINANCE", ("JPM", "BRK.B", "GS", "V", "MA", "COIN")),
            ("CONSUMER", ("TSLA", "COST", "WMT", "NKE", "DIS", "SONY")),
        ]
        sectors_out = []
        for s_lbl, syms in sector_buckets:
            vals = [assets_by_sym[s]["delta_pct"] for s in syms if s in assets_by_sym]
            sectors_out.append((s_lbl, sum(vals) / len(vals) if vals else 0.0))

        bellwethers = ["NVDA", "BTC", "AAPL", "MSFT", "ETH", "XAU", "TSLA", "SOL", "META", "AMZN", "GOOG", "WTIOIL"]
        heatmap_12 = [assets_by_sym[s] for s in bellwethers if s in assets_by_sym]
        if len(heatmap_12) < 12:
            for a in all_assets:
                if a not in heatmap_12:
                    heatmap_12.append(a)
                if len(heatmap_12) >= 12:
                    break

        top_movers = sorted(all_assets, key=lambda x: abs(x["delta_pct"]), reverse=True)
        tape = []
        for s in (self.west_wall_sym, self.east_wall_sym, "NVDA", "BTC", "XAU", "ETH", "SOL", "TSLA", "AAPL", "MSFT"):
            if s in assets_by_sym and assets_by_sym[s] not in tape:
                tape.append(assets_by_sym[s])

        spot_total = sum(a["spot_val"] for a in all_assets)
        futs = list(getattr(engine, "futures", []) or [])
        fut_pnl = sum(float(f.get("pnl", 0.0)) for f in futs)

        pos_lines: list[str] = []
        for f in futs[:4]:
            pos_lines.append(
                f"{f.get('side','LONG')} {f.get('leverage',10)}x {f.get('symbol','')} {float(f.get('pnl',0.0)):+.0f}$"
            )
        for a in sorted(all_assets, key=lambda x: x["spot_val"], reverse=True):
            if a["spot_val"] >= 1.0 and len(pos_lines) < 8:
                pos_lines.append(f"SPOT {a['symbol']} ${a['spot_val']:,.0f} ({a['spot_pnl']:+.0f}$)")

        headline = "Markets trade actively across Los Santos, San Fierro, Chicago & Liberty City."
        np_obj = getattr(engine, "newspaper", None)
        if isinstance(np_obj, dict):
            stories = np_obj.get("stories") or np_obj.get("articles") or []
            if stories and isinstance(stories[0], dict):
                headline = str(stories[0].get("headline") or stories[0].get("title") or headline)
            elif np_obj.get("lead_headline"):
                headline = str(np_obj["lead_headline"])

        cur_dt = getattr(engine, "current_date", None)
        date_str = cur_dt.strftime("%Y-%m-%d") if hasattr(cur_dt, "strftime") else str(cur_dt or "2026-11-05")
        h_clk = int(getattr(engine, "last_clock_h", 12) or 12)
        m_clk = int(getattr(engine, "last_clock_m", 0) or 0)

        return {
            "assets_by_sym": assets_by_sym,
            "all_assets": all_assets,
            "ordered_ticker_tape": tape,
            "heatmap_12": heatmap_12,
            "top_movers": top_movers,
            "sectors": sectors_out,
            "index_value": round(index_val, 2),
            "index_delta_pct": round(avg_dp, 2),
            "sentiment_score": fg_score,
            "sentiment_label": fg_lbl,
            "west_sym": self.west_wall_sym if self.west_wall_sym in assets_by_sym else all_assets[0]["symbol"],
            "east_sym": self.east_wall_sym if self.east_wall_sym in assets_by_sym else all_assets[-1]["symbol"],
            "cash": int(getattr(engine, "cash", 0) or 0),
            "bank": int(getattr(engine, "bank_balance", getattr(engine, "bank", 0)) or 0),
            "spot_total": spot_total,
            "futures_count": len(futs),
            "futures_pnl": fut_pnl,
            "position_lines": pos_lines,
            "headline": headline,
            "date_str": date_str,
            "clock_str": f"{h_clk:02d}:{m_clk:02d}",
            "ai_broker_name": self.ai_broker_name,
            "ai_focus_sym": self.ai_focus_sym,
            "ai_wire_note": self.ai_wire_note,
        }

    def _schedule_board_refresh(self, engine: Any, force_now: bool = False) -> None:
        if self._render_busy:
            if force_now:
                self._boards_dirty = True
            return
        now = time.time()
        if not force_now and not self._boards_dirty and (now - self._last_board_render_ts) < 2.0:
            return
        self._boards_dirty = False
        self._last_board_render_ts = now
        snap = self._build_market_snapshot(engine)
        self._render_busy = True

        def _worker() -> None:
            try:
                bgra_map = self.renderer.render_all_5_bgra(snap)
                offsets = {
                    0: OFF_TICKER_RING,
                    1: OFF_BOARD_MAIN,
                    2: OFF_BOARD_CH_A,
                    3: OFF_BOARD_CH_B,
                    4: OFF_POST_SCREEN,
                }
                for b_idx, raw_bytes in bgra_map.items():
                    self.shm.write_bytes(offsets[b_idx], raw_bytes)
                    self._board_seq[b_idx] = (self._board_seq[b_idx] + 1) & 0x7FFFFFFF or 1
                    self.shm.write_u32(0x80 + b_idx * 4, self._board_seq[b_idx])
            finally:
                self._render_busy = False

        threading.Thread(target=_worker, daemon=True).start()

    def _get_broker_ticker_list(self, engine: Any, broker_idx: int) -> list[str]:
        b = BROKERS_8[broker_idx % len(BROKERS_8)]
        all_syms = list(engine.stocks_market.keys()) + list(engine.crypto_market.keys())
        ordered = [s for s in b["tickers"] if s in all_syms]
        for s in all_syms:
            if s not in ordered:
                ordered.append(s)
        return ordered or ["NVDA"]

    def open_broker_consultation(self, engine: Any, broker_idx: int) -> None:
        broker_idx = max(0, min(7, int(broker_idx)))
        b = BROKERS_8[broker_idx]
        syms = self._get_broker_ticker_list(engine, broker_idx)
        sym0 = syms[0]
        is_vi = getattr(engine, "lang", "en") == "vi"
        greeting = (
            f"Chao Aether! Toi la {b['name']} ({b['desk_vi']}). Ban muon phan tich ma {sym0} bang AI gpt-5-nano hay dat lenh truc tiep?"
            if is_vi
            else f"Welcome Aether! {b['name']} here ({b['desk_en']}). Ready for a live gpt-5-nano read on {sym0} or instant floor execution."
        )
        self.active_consult = {
            "broker_idx": broker_idx,
            "syms": syms,
            "sym_idx": 0,
            "reply": clean_cfont_ascii(greeting),
            "pending": False,
            "last_model": BROKER_AI_MODEL,
            "opened_at": time.time(),
        }
        try:
            if hasattr(engine, "bridge") and hasattr(engine.bridge, "clear_hotkey_states"):
                engine.bridge.clear_hotkey_states()
        except Exception:
            pass
        self.shm.write_i32(0x28, 1)
        self.shm.write_i32(0x2C, broker_idx)
        self.send_cleo_cmd(3, broker_idx, 0)
        self.request_broker_ai_advice(engine, custom_question=None)

    def close_broker_consultation(self, engine: Any) -> None:
        b_idx = int(self.active_consult["broker_idx"]) if self.active_consult else -1
        self.active_consult = None
        self.shm.write_i32(0x28, 0)
        self.shm.write_i32(0x2C, -1)
        self.send_cleo_cmd(4, max(0, b_idx), 0)

    def cycle_consult_ticker(self, engine: Any, delta: int) -> None:
        if not self.active_consult:
            return
        syms = self.active_consult["syms"]
        self.active_consult["sym_idx"] = (int(self.active_consult["sym_idx"]) + delta) % len(syms)

    def cycle_order_size(self, delta: int) -> None:
        self.order_size_idx = (self.order_size_idx + delta) % len(ORDER_SIZE_STEPS)

    def pin_consult_ticker_to_wall(self, engine: Any, wall: str) -> None:
        if not self.active_consult:
            return
        sym = self.active_consult["syms"][self.active_consult["sym_idx"]]
        if wall == "west":
            self.west_wall_sym = sym
            msg = f"Pinned {sym} live candlestick chart onto the West 3D Wall!"
        else:
            self.east_wall_sym = sym
            msg = f"Pinned {sym} live candlestick chart onto the East 3D Wall!"
        self.active_consult["reply"] = clean_cfont_ascii(msg)
        engine.last_toast = msg
        self._schedule_board_refresh(engine, force_now=True)

    def execute_floor_trade(self, engine: Any, mode: str) -> None:
        if not self.active_consult:
            return
        sym = self.active_consult["syms"][self.active_consult["sym_idx"]]
        grp = "crypto" if sym in engine.crypto_market else "stocks"
        usd = ORDER_SIZE_STEPS[self.order_size_idx % len(ORDER_SIZE_STEPS)]
        b_idx = int(self.active_consult["broker_idx"])

        if mode == "close_fut":
            fut = next((f for f in engine.futures if f.get("symbol") == sym), None)
            if fut:
                engine.handle_action({"action": "close_future", "id": fut["id"]})
            else:
                engine.last_toast = f"No open futures position on {sym} to close."
        else:
            engine.handle_action(
                {
                    "action": "trade_order",
                    "market_group": grp,
                    "symbol": sym,
                    "mode": mode,
                    "usd": usd,
                    "leverage": 10,
                }
            )
        self.active_consult["reply"] = clean_cfont_ascii(f"[EXECUTION DESK] {engine.last_toast}")
        self.send_cleo_cmd(5, b_idx, 0)
        self._schedule_board_refresh(engine, force_now=True)

    def request_broker_ai_advice(self, engine: Any, custom_question: str | None = None) -> None:
        if not self.active_consult or self._ai_busy:
            return
        c = self.active_consult
        b_idx = int(c["broker_idx"])
        b = BROKERS_8[b_idx]
        sym = c["syms"][c["sym_idx"]]
        asset = engine.crypto_market.get(sym) or engine.stocks_market.get(sym)
        if not asset:
            return

        price = float(asset.get("price", 1.0))
        dp = float(asset.get("delta_pct", 0.0))
        candles = list(asset.get("candles") or [])[-20:]
        closes = [float(x["c"]) for x in candles] if candles else [price]
        ma7 = sum(closes[-7:]) / min(7, len(closes))
        ma20 = sum(closes) / len(closes)
        hi20 = max(float(x["h"]) for x in candles) if candles else price
        lo20 = min(float(x["l"]) for x in candles) if candles else price
        spot_val = float(asset.get("spot_val", 0.0))
        spot_pnl = float(asset.get("spot_pnl", 0.0))
        fut_match = [f for f in engine.futures if f.get("symbol") == sym]
        fut_desc = (
            f"{fut_match[0]['side']} {fut_match[0]['leverage']}x PnL ${fut_match[0]['pnl']:+.0f}"
            if fut_match
            else "None"
        )
        cash_now = int(getattr(engine, "cash", 0) or 0)
        is_vi = getattr(engine, "lang", "en") == "vi"

        c["pending"] = True
        c["reply"] = (
            f"{b['name']} dang phan tich du lieu nen {sym} qua {BROKER_AI_MODEL}..."
            if is_vi
            else f"{b['name']} is analyzing live {sym} orderflow via {BROKER_AI_MODEL}..."
        )
        self._ai_busy = True

        lang_rule = (
            "Reply in concise Vietnamese WITHOUT diacritics (plain ASCII Vietnamese) in 2 short complete sentences (strictly under 240 characters)."
            if is_vi
            else "Reply in crisp institutional English in 2 short complete sentences (strictly under 240 characters)."
        )
        user_q = (
            clean_cfont_ascii(custom_question)
            if custom_question
            else f"Give me your live floor call, key level, and action plan on {sym} right now."
        )
        sys_prompt = (
            f"{b['persona']} {lang_rule} "
            "Ground every number strictly in the live Eagle Exchange snapshot provided. Never use markdown bullets or emojis."
        )
        mkt_ctx = (
            f"Ticker: {sym} ({asset.get('name', sym)}) | Live Price: ${price} ({dp:+.2f}%) | "
            f"MA7: ${ma7:.2f} | MA20: ${ma20:.2f} | 20-bar Range: ${lo20:.2f}-${hi20:.2f} | "
            f"Client Cash: ${cash_now:,} | Client {sym} Spot: ${spot_val:,.0f} (PnL ${spot_pnl:+.0f}) | "
            f"Client {sym} Futures: {fut_desc}. Client asks: {user_q}"
        )

        def _call_nano() -> None:
            reply_txt = ""
            try:
                base_url, api_key = self._load_openai_nano_config()
                if api_key:
                    payload = json.dumps(
                        {
                            "model": BROKER_AI_MODEL,
                            "reasoning_effort": "minimal",
                            "max_completion_tokens": 450,
                            "messages": [
                                {"role": "system", "content": sys_prompt},
                                {"role": "user", "content": mkt_ctx},
                            ],
                        }
                    ).encode("utf-8")
                    req = urllib.request.Request(
                        f"{base_url}/chat/completions",
                        data=payload,
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=12.0) as resp:
                        body = json.loads(resp.read().decode("utf-8"))
                        reply_txt = str(body["choices"][0]["message"].get("content") or "").strip()
            except Exception:
                reply_txt = ""

            if not reply_txt:
                bias = "BULLISH above MA7" if price >= ma7 else "PULLBACK below MA7"
                reply_txt = (
                    f"{sym} is trading at ${price:.2f} ({dp:+.2f}%), {bias} (${ma7:.2f}) with 20-bar support at ${lo20:.2f} "
                    f"and resistance near ${hi20:.2f}. Size Spot entries prudently from your ${cash_now:,} cash reserve."
                )

            clean_rep = clean_cfont_ascii(reply_txt)
            if len(clean_rep) > 345:
                cut = clean_rep[:345]
                last_dot = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "), cut.rfind("."))
                clean_rep = cut[: last_dot + 1] if last_dot > 140 else (cut.rsplit(" ", 1)[0] + ".")
            with engine.lock:
                self.ai_broker_name = b["name"]
                self.ai_focus_sym = sym
                self.ai_wire_note = clean_rep
                if self.active_consult and int(self.active_consult["broker_idx"]) == b_idx:
                    self.active_consult["reply"] = clean_rep
                    self.active_consult["pending"] = False
                self.send_cleo_cmd(5, b_idx, 0)
                self._schedule_board_refresh(engine, force_now=True)
                engine._write_hud_dat(force=True)
            self._ai_busy = False

        threading.Thread(target=_call_nano, daemon=True).start()

    def tick(self, engine: Any) -> bool:
        """Called ~20Hz from EagleCompanion.poll_ingame_hotkeys under engine.lock."""
        if not self.shm.ensure_open():
            return False
        now = time.time()
        self._py_hb = (self._py_hb + 1) & 0x7FFFFFFF or 1
        self.shm.write_u32(0x10, self._py_hb)

        # Ensure initial board pixels exist in SHM even before first entry so entry has 0ms blank frame!
        if self._board_seq[0] == 0 and not self._render_busy:
            self._schedule_board_refresh(engine, force_now=True)

        inside_now = self.shm.read_i32(0x14) == 1
        near_portal = self.shm.read_i32(0x1C)
        near_broker = self.shm.read_i32(0x20)
        entry_city = max(0, min(3, self.shm.read_i32(0x18)))
        e_seq = self.shm.read_u32(0x44)
        if self._last_e_seq == 0 and e_seq > 0 and not inside_now:
            self._last_e_seq = e_seq

        ui_changed = (
            inside_now != self.inside_exchange
            or near_portal != self.near_portal_idx
            or near_broker != self.near_broker_idx
            or entry_city != self.entry_city_idx
        )

        # Transition: Outside -> Inside Stock Exchange!
        if inside_now and not self.inside_exchange:
            self.inside_exchange = True
            self.entry_city_idx = entry_city
            self.director.roll_fresh_visit(self.shm, now)
            self._schedule_board_refresh(engine, force_now=True)
            city_lbl = CITY_PORTAL_META[entry_city]["city_vi" if getattr(engine, "lang", "en") == "vi" else "city_en"]
            engine.push_event_banner(
                "EAGLE WALL STREET EXCHANGE",
                f"Live 51-Asset Trading Floor | Entered via {city_lbl}",
                kind="money",
                duration=5.5,
            )
            ui_changed = True
        elif not inside_now and self.inside_exchange:
            self.inside_exchange = False
            if self.active_consult is not None:
                self.active_consult = None
                self.shm.write_i32(0x28, 0)
                self.shm.write_i32(0x2C, -1)
            ui_changed = True

        self.near_portal_idx = near_portal
        self.near_broker_idx = near_broker
        self.entry_city_idx = entry_city

        # Handle rising-edge [E] near one of the 8 Brokers (both CLEO 0AB0 e_seq & Win32 LSB latch)
        win_e_edge = False
        try:
            if (
                self.active_consult is None
                and hasattr(engine, "bridge")
                and engine.bridge.is_game_active_and_unpaused()
                and engine.bridge.poll_hotkey_edge(0x45)
            ):
                win_e_edge = True
        except Exception:
            win_e_edge = False

        if self.inside_exchange:
            consult_slot = int(self.active_consult["broker_idx"]) if self.active_consult else -1
            self.director.tick(self.shm, now, consult_slot)
            self._schedule_board_refresh(engine, force_now=False)

            if e_seq != self._last_e_seq or win_e_edge:
                self._last_e_seq = e_seq
                if self.active_consult is None and 0 <= near_broker <= 7:
                    self.open_broker_consultation(engine, near_broker)
                    ui_changed = True
        else:
            self._last_e_seq = e_seq
            if win_e_edge and 0 <= near_portal <= 3:
                self.send_cleo_cmd(1, near_portal, 0)

        return ui_changed

    def on_market_step(self, engine: Any) -> None:
        """Mark boards dirty whenever EagleCompanion updates live stock/crypto candle prices."""
        self._boards_dirty = True
        if self.inside_exchange:
            self._schedule_board_refresh(engine, force_now=True)

    def handle_consult_hotkeys(self, engine: Any) -> bool:
        """Process interactive Broker Trading & gpt-5-nano hotkeys when active_consult is open."""
        if self.active_consult is None:
            return False
        br = engine.bridge
        if (time.time() - float(self.active_consult.get("opened_at", 0.0))) < 0.38:
            br.clear_hotkey_states()
            return True
        if engine.wl_typing_active:
            engine._poll_waifulink_typing_keys(target_mode="ws_broker")
            return True

        # F6: Live custom question to Broker
        if not self.active_consult.get("pending") and br.poll_hotkey_edge(0x75):
            with engine.lock:
                engine._typing_event_queue.clear()
                engine._wl_typing_started_at = time.time()
                engine.wl_typing_active = True
                engine.wl_typing_buf = ""
                br.clear_hotkey_states()
                b_nm = BROKERS_8[self.active_consult["broker_idx"]]["name"]
                engine.last_toast = f"Ask {b_nm} ({BROKER_AI_MODEL}) — Enter: Send | F6: Cancel"
                engine._write_hud_dat(force=True)
            return True

        # [Q] (0x51) or [J] (0x4A): Prev Ticker | [R] (0x52) or [L] (0x4C): Next Ticker
        if br.poll_hotkey_edge(0x51) or br.poll_hotkey_edge(0x4A):
            with engine.lock:
                self.cycle_consult_ticker(engine, -1)
                engine._write_hud_dat(force=True)
            return True
        if br.poll_hotkey_edge(0x52) or br.poll_hotkey_edge(0x4C):
            with engine.lock:
                self.cycle_consult_ticker(engine, +1)
                engine._write_hud_dat(force=True)
            return True

        # [Z] (0x5A) or [K] (0x4B): Smaller Order | [C] (0x43) or [I] (0x49): Larger Order
        if br.poll_hotkey_edge(0x5A) or br.poll_hotkey_edge(0x4B):
            with engine.lock:
                self.cycle_order_size(-1)
                engine._write_hud_dat(force=True)
            return True
        if br.poll_hotkey_edge(0x43) or br.poll_hotkey_edge(0x49):
            with engine.lock:
                self.cycle_order_size(+1)
                engine._write_hud_dat(force=True)
            return True

        # [T] (0x54): Pin to West 3D Wall | [Y] (0x59): Pin to East 3D Wall
        if br.poll_hotkey_edge(0x54):
            with engine.lock:
                self.pin_consult_ticker_to_wall(engine, "west")
                engine._write_hud_dat(force=True)
            return True
        if br.poll_hotkey_edge(0x59):
            with engine.lock:
                self.pin_consult_ticker_to_wall(engine, "east")
                engine._write_hud_dat(force=True)
            return True

        # [1]: Ask gpt-5-nano | [2]: Spot BUY | [3]: Spot SELL | [4]: LONG 10x | [5]: SHORT 10x | [6]: Close Future
        if br.poll_hotkey_edge(0x31) or br.poll_hotkey_edge(0x61):
            with engine.lock:
                self.request_broker_ai_advice(engine, custom_question=None)
                engine._write_hud_dat(force=True)
            return True
        for key_vk, num_vk, t_mode in (
            (0x32, 0x62, "spot_buy"),
            (0x33, 0x63, "spot_sell"),
            (0x34, 0x64, "fut_long"),
            (0x35, 0x65, "fut_short"),
            (0x36, 0x66, "close_fut"),
        ):
            if br.poll_hotkey_edge(key_vk) or br.poll_hotkey_edge(num_vk):
                with engine.lock:
                    self.execute_floor_trade(engine, t_mode)
                    engine._write_hud_dat(force=True)
                return True

        # [Backspace] (0x08) or [F8] (0x77): Close Broker Consultation
        if br.poll_hotkey_edge(0x08) or br.poll_hotkey_edge(0x77):
            with engine.lock:
                engine.wl_typing_active = False
                self.close_broker_consultation(engine)
                br.clear_hotkey_states()
                engine._write_hud_dat(force=True)
            return True

        return True

    def build_hud_kv(self, engine: Any) -> dict[str, str]:
        """Export CFont-safe keys into EaglePhoneState for cleo/EagleWallStreetHud.lua."""
        is_vi = getattr(engine, "lang", "en") == "vi"
        show_any = self.inside_exchange or (0 <= self.near_portal_idx <= 4)
        if not show_any and self.active_consult is None:
            return {
                "ws_ver": "3",
                "ws_show": "0",
                "ws_inside": "0",
                "ws_consult": "0",
                "ws_prompt": "",
            }

        prompt = ""
        if 0 <= self.near_portal_idx <= 3 and not self.inside_exchange:
            cm = CITY_PORTAL_META[self.near_portal_idx]
            lbl = cm["city_vi"] if is_vi else cm["city_en"]
            prompt = (
                f"[E] Vao San Chung Khoan Eagle Wall Street ({lbl})"
                if is_vi
                else f"[E] Enter Eagle Wall Street Stock Exchange ({lbl})"
            )
        elif self.near_portal_idx == 4 and self.inside_exchange and self.active_consult is None:
            cm = CITY_PORTAL_META[self.entry_city_idx % 4]
            lbl = cm["city_vi"] if is_vi else cm["city_en"]
            prompt = f"[E] Roi San -> Tro ve {lbl}" if is_vi else f"[E] Exit Trading Floor -> Return to {lbl}"
        elif self.inside_exchange and self.active_consult is None and 0 <= self.near_broker_idx <= 7:
            b = BROKERS_8[self.near_broker_idx]
            d_lbl = b["desk_vi"] if is_vi else b["desk_en"]
            prompt = (
                f"[E] Tu Van Broker {b['name']} ({d_lbl}) — AI {BROKER_AI_MODEL}"
                if is_vi
                else f"[E] Consult Broker {b['name']} ({d_lbl}) — AI {BROKER_AI_MODEL}"
            )

        kv = {
            "ws_ver": "3",
            "ws_show": "1",
            "ws_inside": "1" if self.inside_exchange else "0",
            "ws_consult": "1" if self.active_consult is not None else "0",
            "ws_prompt": clean_cfont_ascii(prompt)[:92],
            "ws_floor_bar": clean_cfont_ascii(
                f"WALL STREET LIVE  |  WEST [T]: {self.west_wall_sym}  |  EAST [Y]: {self.east_wall_sym}  |  18 TRADERS ACTIVE"
            ),
        }

        if self.active_consult is not None:
            c = self.active_consult
            b = BROKERS_8[int(c["broker_idx"])]
            sym = c["syms"][c["sym_idx"]]
            asset = engine.crypto_market.get(sym) or engine.stocks_market.get(sym) or {}
            price = float(asset.get("price", 0.0))
            dp = float(asset.get("delta_pct", 0.0))
            spot_val = float(asset.get("spot_val", 0.0))
            spot_pnl = float(asset.get("spot_pnl", 0.0))
            fut = next((f for f in engine.futures if f.get("symbol") == sym), None)
            fut_str = (
                f"{fut['side']} {fut['leverage']}x (${fut['margin']:,} | PnL {fut['pnl']:+.0f}$)"
                if fut
                else "NONE"
            )
            usd = ORDER_SIZE_STEPS[self.order_size_idx % len(ORDER_SIZE_STEPS)]
            wrapped = textwrap.wrap(clean_cfont_ascii(c.get("reply", "")), width=92)[:4]
            while len(wrapped) < 4:
                wrapped.append("")

            kv.update(
                {
                    "ws_broker_name": clean_cfont_ascii(f"{b['name']}  ({b['origin']})"),
                    "ws_broker_desk": clean_cfont_ascii(b["desk_vi"] if is_vi else b["desk_en"]),
                    "ws_ai_badge": f"AI: {BROKER_AI_MODEL.upper()}",
                    "ws_sym": sym,
                    "ws_sym_name": clean_cfont_ascii(str(asset.get("name", sym)))[:28],
                    "ws_price": f"${WallStreetBoardRenderer._fmt_price(price)}",
                    "ws_delta": f"{dp:+.2f}%",
                    "ws_is_up": "1" if dp >= 0 else "0",
                    "ws_order_usd": f"${usd:,}",
                    "ws_cash": f"${int(getattr(engine, 'cash', 0) or 0):,}",
                    "ws_pos_info": clean_cfont_ascii(
                        f"SPOT: ${spot_val:,.0f} ({spot_pnl:+.0f}$)  |  FUTURES: {fut_str}  |  WALLS: W={self.west_wall_sym} / E={self.east_wall_sym}"
                    )[:96],
                    "ws_r1": wrapped[0],
                    "ws_r2": wrapped[1],
                    "ws_r3": wrapped[2],
                    "ws_r4": wrapped[3],
                    "ws_typing": "1" if engine.wl_typing_active else "0",
                    "ws_typing_buf": clean_cfont_ascii(getattr(engine, "wl_typing_buf", ""))[:84],
                }
            )
        return kv

    def build_debug_projection(self, engine: Any) -> dict[str, Any]:
        """Full live diagnostic state for HTTP /api/wallstreet & automated E2E QA."""
        hdr = self.shm.read_header_dict()
        slots_out = []
        for s in range(18):
            raw = self.shm.read_bytes(OFF_SLOTS_BASE + s * 64, 64)
            t_seq, t_mode, tx, ty, tz, thdg, anim, ack, handle, ptr, cx, cy, cz, s_state, ref_ms, _ = struct.unpack(
                "<Ii4fiI2I3f3i", raw
            )
            meta = BROKERS_8[s] if s < 8 else AMBIENT_FEMALES_10[s - 8]
            slots_out.append(
                {
                    "slot": s,
                    "ped_id": meta["ped_id"],
                    "stem": meta["stem"],
                    "name": meta["name"],
                    "role": "broker" if s < 8 else "floor_npc",
                    "ped_handle": handle,
                    "ped_ptr": hex(ptr) if ptr else "0x0",
                    "task_seq": t_seq,
                    "cs_task_ack": ack,
                    "task_mode": t_mode,
                    "slot_state": s_state,
                    "anim_code": anim,
                    "anchor": self.director.slots[s]["cur_anchor_id"],
                    "target_pos": [round(tx, 2), round(ty, 2), round(tz, 2)],
                    "cur_pos": [round(cx, 2), round(cy, 2), round(cz, 2)],
                }
            )
        return {
            "shm_header": hdr,
            "inside_exchange": self.inside_exchange,
            "entry_city_idx": self.entry_city_idx,
            "west_wall_sym": self.west_wall_sym,
            "east_wall_sym": self.east_wall_sym,
            "broker_ai_model": BROKER_AI_MODEL,
            "active_consult": self.active_consult,
            "ai_broker_name": self.ai_broker_name,
            "ai_focus_sym": self.ai_focus_sym,
            "ai_wire_note": self.ai_wire_note,
            "npcs_18": slots_out,
        }
