"""
Chronological Historical Datasets (01/01/2010 -> 31/12/2025, 5,844 Days)
for EaglePhone OS v6.3 (Project Eagle Gameplay Lab).
Supports English ('en', default) and Vietnamese ('vi') localization.

Upgraded Market Depth (v6.3):
1. 35 Stocks, Commodities & Lore Equities (`STOCK_AND_COMMODITY_ASSETS`) with monthly/catalyst waypoints.
2. 16 Cryptocurrencies (`CRYPTO_ASSETS`) with full 2010-2014 pioneer cycles & Pre-Mainnet OTC Venture IOUs.
3. Deterministic 48-candle OHLCV window (`get_historical_ohlcv_window`) & 2s intraday engine (`step_live_market_candle`).
4. Chronological Multi-League Sportsbook, EagleTimes fallback chronicle, and 4-in-1 Lottery tables.
"""

import datetime
import hashlib
import importlib.util as _importlib_util
import math
from pathlib import Path as _Path
import random
import sys as _sys

try:
    from eagle_market_regimes_2010_2025 import (
        CRYPTO_ASSETS,
        CRYPTO_WAYPOINTS,
        MARKET_REGIME_WINDOWS,
        START_DATE,
        STOCK_AND_COMMODITY_ASSETS,
        STOCK_WAYPOINTS,
        ensure_market_catalog_migrated,
        get_chronological_target_price,
        get_historical_ohlcv_window,
        get_market_regime,
        step_live_market_candle,
    )
except ModuleNotFoundError:
    _reg_path = _Path(__file__).resolve().with_name('eagle_market_regimes_2010_2025.py')
    _reg_spec = _importlib_util.spec_from_file_location('eagle_market_regimes_2010_2025', _reg_path)
    _reg_mod = _importlib_util.module_from_spec(_reg_spec)
    _sys.modules['eagle_market_regimes_2010_2025'] = _reg_mod
    _reg_spec.loader.exec_module(_reg_mod)
    CRYPTO_ASSETS = _reg_mod.CRYPTO_ASSETS
    CRYPTO_WAYPOINTS = _reg_mod.CRYPTO_WAYPOINTS
    MARKET_REGIME_WINDOWS = _reg_mod.MARKET_REGIME_WINDOWS
    START_DATE = _reg_mod.START_DATE
    STOCK_AND_COMMODITY_ASSETS = _reg_mod.STOCK_AND_COMMODITY_ASSETS
    STOCK_WAYPOINTS = _reg_mod.STOCK_WAYPOINTS
    ensure_market_catalog_migrated = _reg_mod.ensure_market_catalog_migrated
    get_chronological_target_price = _reg_mod.get_chronological_target_price
    get_historical_ohlcv_window = _reg_mod.get_historical_ohlcv_window
    get_market_regime = _reg_mod.get_market_regime
    step_live_market_candle = _reg_mod.step_live_market_candle

# ============================================================================
# 3. CHRONOLOGICAL SPORTSBOOK (SEASON-BY-SEASON, DAY 1 -> DAY 5844, NO YEAR SHOWN)
# ============================================================================
LEAGUES = [
    {"id": "EPL", "name": "Premier League", "sport": "Football", "ou_line": 2.5},
    {"id": "LALIGA", "name": "La Liga", "sport": "Football", "ou_line": 2.5},
    {"id": "SERIE_BUND", "name": "Serie A & Bundesliga", "sport": "Football", "ou_line": 2.5},
    {"id": "UCL", "name": "UEFA Champions League", "sport": "Football", "ou_line": 2.5},
    {"id": "NBA", "name": "NBA Basketball", "sport": "Basketball", "ou_line": 210.5},
]

LEAGUE_TEAMS = {
    "EPL": [
        ("Man United", 88), ("Chelsea", 87), ("Man City", 89), ("Arsenal", 84),
        ("Liverpool", 86), ("Tottenham", 82), ("Leicester City", 79), ("Everton", 77),
        ("Newcastle", 76), ("Aston Villa", 75), ("West Ham", 74), ("Southampton", 73),
    ],
    "LALIGA": [
        ("Barcelona", 92), ("Real Madrid", 91), ("Atletico Madrid", 86), ("Sevilla", 81),
        ("Valencia", 80), ("Villarreal", 79), ("Athletic Bilbao", 78), ("Real Sociedad", 77),
        ("Real Betis", 75), ("Malaga", 74), ("Celta Vigo", 73), ("Espanyol", 72),
    ],
    "SERIE_BUND": [
        ("Bayern Munich", 91), ("Dortmund", 86), ("Juventus", 88), ("AC Milan", 83),
        ("Inter Milan", 84), ("Napoli", 83), ("AS Roma", 81), ("Bayer Leverkusen", 80),
        ("Schalke 04", 77), ("Lazio", 78), ("Fiorentina", 76), ("Wolfsburg", 76),
    ],
    "UCL": [
        ("Real Madrid", 92), ("Barcelona", 92), ("Bayern Munich", 91), ("Man City", 89),
        ("Juventus", 87), ("PSG", 87), ("Liverpool", 87), ("Chelsea", 86),
        ("Atletico Madrid", 86), ("Dortmund", 85), ("Inter Milan", 84), ("Ajax", 82),
    ],
    "NBA": [
        ("GS Warriors", 91), ("Cleveland Cavs", 89), ("Miami Heat", 89), ("San Antonio Spurs", 88),
        ("LA Lakers", 86), ("Boston Celtics", 86), ("OKC Thunder", 85), ("Houston Rockets", 84),
        ("Dallas Mavericks", 84), ("Toronto Raptors", 84), ("Chicago Bulls", 82), ("LA Clippers", 82),
    ],
}

KICKOFF_SLOTS = ["15:00", "17:30", "19:45", "20:45", "22:00", "23:30"]


def to_clean_viet_ascii(text: str) -> str:
    """Converts Vietnamese text with diacritics into 100% readable unaccented ASCII without dropping letters."""
    import unicodedata
    if not text:
        return ""
    s = str(text).replace("đ", "d").replace("Đ", "D").replace("—", "-").replace("•", "-").replace("–", "-")
    nfd = unicodedata.normalize("NFD", s)
    out = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    return out.encode("ascii", errors="ignore").decode("ascii").strip()


def wrap_hud_lines(text: str, width: int = 58, max_lines: int = 4) -> list:
    """Word-wraps clean ASCII text into up to `max_lines` lines of `width` chars without `...` truncation."""
    import textwrap
    clean = to_clean_viet_ascii(text)
    lines = textwrap.wrap(clean, width=width)
    while len(lines) < max_lines:
        lines.append("")
    return lines[:max_lines]


def generate_daily_fixtures(day_index: int, lang: str = "en") -> list:
    """
    Generates 5 matches per league across all 5 leagues (25 matches/day total)
    for `day_index` (Day 1 = Season 1, Week 1, Day 1).
    Does NOT display the historical year so the player cannot cheat!
    """
    season_num = ((day_index - 1) // 266) + 1
    day_in_season = ((day_index - 1) % 266) + 1
    week_num = ((day_in_season - 1) // 7) + 1
    day_in_week = ((day_in_season - 1) % 7) + 1

    rng = random.Random(day_index * 9973 + 2010)
    fixtures = []
    is_vi = (lang == "vi")

    for idx, lg in enumerate(LEAGUES):
        lid = lg["id"]
        teams = list(LEAGUE_TEAMS[lid])
        n = len(teams)
        rot_step = (week_num * 5 + day_in_week * 2 + idx) % (n - 1)
        moving = teams[1:]
        moving = moving[rot_step:] + moving[:rot_step]
        ordered = [teams[0]] + moving

        for m_idx in range(5):  # 5 matches per league = 25 matches per day!
            home_name, home_str = ordered[m_idx]
            away_name, away_str = ordered[n - 1 - m_idx]
            if (week_num + day_in_week + m_idx) % 2 == 1:
                home_name, away_name = away_name, home_name
                home_str, away_str = away_str, home_str

            diff = (home_str + 3) - away_str
            odd_home = round(max(1.22, min(4.80, 2.35 - diff * 0.055)), 2)
            odd_draw = 14.0 if lg["sport"] == "Basketball" else round(max(2.95, min(4.60, 3.30 + abs(diff) * 0.04)), 2)
            odd_away = round(max(1.25, min(6.50, 2.65 + diff * 0.065)), 2)

            if lg["sport"] == "Basketball":
                hcap_val = -round(diff * 0.6, 1)
                hcap_str = f"{hcap_val:+.1f}"
                h_base = int(102 + diff * 0.45 + rng.randint(-5, 5))
                a_base = int(100 - diff * 0.45 + rng.randint(-5, 5))
            else:
                hcap_val = -round(diff * 0.08 * 4) / 4.0
                hcap_str = f"{hcap_val:+.2f}"
                h_base = max(0, int(round(1.45 + diff * 0.06 + rng.gauss(0, 0.9))))
                a_base = max(0, int(round(1.15 - diff * 0.05 + rng.gauss(0, 0.85))))

            kickoff = KICKOFF_SLOTS[(idx + m_idx + day_in_week) % len(KICKOFF_SLOTS)]
            round_label_en = f"Season {season_num} - Week {week_num} (Day {day_in_week}/7)"
            round_label_vi = f"Mua {season_num} - Tuan {week_num} (Ngay {day_in_week}/7)"
            headline_en = f"Matchweek {week_num} {lg['name']}: {home_name} vs {away_name} ({kickoff})."
            headline_vi = f"Vong {week_num} {lg['name']}: {home_name} vs {away_name} ({kickoff})."

            fixtures.append({
                "id": f"D{day_index}_{lid}_{m_idx+1}",
                "league": lid,
                "league_id": lid,
                "league_name": lg["name"],
                "round_label": round_label_vi if is_vi else round_label_en,
                "round_label_en": round_label_en,
                "round_label_vi": round_label_vi,
                "home": home_name,
                "away": away_name,
                "h_base": h_base,
                "a_base": a_base,
                "odds": [odd_home, odd_draw, odd_away],
                "hcap": hcap_str,
                "ou_line": lg["ou_line"],
                "kickoff": kickoff,
                "headline": headline_vi if is_vi else headline_en,
                "headline_en": headline_en,
                "headline_vi": headline_vi,
                "active_bet": None,
            })

    return fixtures


# ============================================================================
# 4. DAILY NEWSPAPER CHRONICLE (`EAGLETIMES` 01/01/2010 -> 31/12/2025)
# ============================================================================
EXACT_DATE_EVENTS = {
    (2010, 1, 1): "Chao don thap ky moi 2010s! Khu vuc dong Euro ky niem 11 nam thanh lap giua nhung canh bao no cong Hy Lap.",
    (2010, 1, 4): "Khanh thanh thap Burj Khalifa cao 828m tai Dubai — toa nha cao nhat hanh tinh!",
    (2010, 1, 12): "Tran dong dat manh 7.0 do Richter rung chuyen thu do Port-au-Prince cua Haiti, quoc te khan cap cuu tro.",
    (2010, 1, 27): "Steve Jobs chinh thuc gioi thieu chiec Apple iPad dau tien tai San Francisco, mo ra ky nguyen may tinh bang.",
    (2010, 5, 22): "Lich su Crypto: Lap trinh vien Laszlo Hanyecz dung 10,000 BTC de mua 2 chiec banh Pizza Papa John's!",
    (2010, 6, 11): "Khai mac World Cup 2010 tai Nam Phi voi giai dieu Waka Waka va tieng ken Vuvuzela vang doi.",
    (2010, 6, 29): "Tesla Motors chinh thuc IPO tren san NASDAQ voi ma TSLA o muc gia $17.00/co phieu!",
    (2011, 2, 9): "Bitcoin lần đầu tiên chạm mốc tỷ giá 1 BTC = 1 USD trên sàn Mt.Gox!",
    (2011, 3, 11): "Động đất và sóng thần Tōhoku tại Nhật Bản gây sự cố tại nhà máy điện hạt nhân Fukushima.",
    (2011, 5, 2): "Tổng thống Mỹ Barack Obama công bố chiến dịch đặc nhiệm tại Abbottabad.",
    (2011, 10, 5): "Huyền thoại sáng lập Apple Steve Jobs qua đời ở tuổi 56, để lại di sản công nghệ vĩ đại.",
    (2012, 5, 18): "Facebook thực hiện thương vụ IPO công nghệ lịch sử trên sàn NASDAQ với định giá 104 tỷ USD.",
    (2012, 11, 28): "Sự kiện Bitcoin Halving đầu tiên trong lịch sử: Phần thưởng khối giảm từ 50 BTC xuống 25 BTC!",
    (2013, 11, 29): "Giá Bitcoin lần đầu tiên trong lịch sử vượt mốc $1,000 USD, ngang ngửa giá 1 ounce Vàng!",
    (2014, 7, 13): "Đức đánh bại Argentina 1-0 nhờ bàn thắng hiệp phụ của Mario Gotze để vô địch World Cup 2014!",
    (2015, 7, 30): "Mạng lưới Ethereum (ETH) chính thức khởi chạy khối Genesis (Frontier), mở ra kỷ nguyên hợp đồng thông minh!",
    (2016, 6, 23): "Cử tri Vương quốc Anh bỏ phiếu thông qua Brexit, gây chấn động thị trường tài chính toàn cầu.",
    (2016, 7, 9): "Bitcoin Halving lần thứ 2: Phần thưởng khối giảm từ 25 BTC xuống 12.5 BTC.",
    (2017, 12, 17): "Cơn sốt Crypto 2017 đạt đỉnh: Bitcoin chạm mốc $19,800 sau khi CME triển khai hợp đồng tương lai BTC.",
    (2018, 7, 15): "Tuyển Pháp đánh bại Croatia 4-2 tại Moscow để nâng cao chức vô địch World Cup 2018.",
    (2020, 3, 11): "WHO chính thức công bố đại dịch toàn cầu COVID-19; các ngân hàng trung ương hạ lãi suất về 0%.",
    (2020, 5, 11): "Bitcoin Halving lần thứ 3 diễn ra thành công, khởi đầu chu kỳ tăng trưởng 2020-2021.",
    (2021, 11, 10): "Tổng vốn hóa thị trường Crypto vượt 3,000 tỷ USD khi Bitcoin lập đỉnh mới trên $68,000!",
    (2022, 11, 30): "OpenAI ra mắt ChatGPT, châm ngòi cho cuộc chạy đua Trí Tuệ Nhân Tạo (AI) và cổ phiếu bán dẫn NVDA.",
    (2024, 1, 10): "SEC Mỹ chính thức phê duyệt các quỹ Spot Bitcoin ETF của BlackRock và Fidelity!",
    (2024, 4, 20): "Bitcoin Halving lần thứ 4 hoàn tất, phần thưởng khối giảm xuống 3.125 BTC.",
    (2025, 1, 1): "Thế giới bước vào năm 2025 với sự bùng nổ của AI Agent, Vàng lập đỉnh mới trên $2,700/oz và BTC hướng tới $100,000.",
}

EXACT_DATE_EVENTS_EN = {
    (2010, 1, 1): "Welcome to the 2010s! The Eurozone marks its 11th anniversary amid sovereign debt warnings in Greece.",
    (2010, 1, 4): "Dubai officially inaugurates the 828m Burj Khalifa — the tallest skyscraper on Earth!",
    (2010, 1, 12): "A devastating 7.0-magnitude earthquake strikes Port-au-Prince, Haiti, prompting global emergency relief.",
    (2010, 1, 27): "Steve Jobs unveils the original Apple iPad in San Francisco, ushering in the modern tablet era.",
    (2010, 5, 22): "Crypto History: Programmer Laszlo Hanyecz pays 10,000 BTC for two Papa John's pizzas!",
    (2010, 6, 11): "The 2010 FIFA World Cup kicks off in South Africa to the sound of Waka Waka and roaring Vuvuzelas.",
    (2010, 6, 29): "Tesla Motors officially goes public on NASDAQ under ticker TSLA at $17.00 per share!",
    (2011, 2, 9): "Bitcoin reaches parity with the US Dollar (1 BTC = $1.00) for the first time on Mt.Gox!",
    (2011, 3, 11): "The Tohoku earthquake and tsunami strike Japan, triggering the Fukushima nuclear crisis.",
    (2011, 5, 2): "US President Barack Obama announces the special forces operation in Abbottabad.",
    (2011, 10, 5): "Apple co-founder Steve Jobs passes away at 56, leaving behind an extraordinary technological legacy.",
    (2012, 5, 18): "Facebook completes its historic tech IPO on NASDAQ at a $104 billion valuation.",
    (2012, 11, 28): "First Bitcoin Halving in history: Block reward drops from 50 BTC to 25 BTC!",
    (2013, 11, 29): "Bitcoin price surges past $1,000 USD for the first time, reaching parity with 1 oz of Gold!",
    (2014, 7, 13): "Germany defeats Argentina 1-0 on Mario Gotze's extra-time goal to win the 2014 World Cup in Brazil!",
    (2015, 7, 30): "The Ethereum (ETH) network officially launches its Frontier Genesis block, starting the Smart Contract era!",
    (2016, 6, 23): "UK voters approve Brexit in a historic referendum, sending shockwaves across global markets.",
    (2016, 7, 9): "Second Bitcoin Halving completed: Block reward drops from 25 BTC to 12.5 BTC.",
    (2017, 12, 17): "The 2017 Crypto boom peaks as Bitcoin touches $19,800 following CME's BTC futures launch.",
    (2018, 7, 15): "France defeats Croatia 4-2 in Moscow to lift the 2018 FIFA World Cup trophy.",
    (2020, 3, 11): "WHO declares COVID-19 a global pandemic; central banks slash interest rates to 0%.",
    (2020, 5, 11): "Third Bitcoin Halving completes successfully, igniting the 2020-2021 bull cycle.",
    (2021, 11, 10): "Total Crypto market cap surpasses $3 trillion as Bitcoin sets a new all-time high above $68,000!",
    (2022, 11, 30): "OpenAI launches ChatGPT, igniting the global Generative AI race and semiconductor rally led by NVDA.",
    (2024, 1, 10): "The US SEC officially approves Spot Bitcoin ETFs from BlackRock and Fidelity!",
    (2024, 4, 20): "Fourth Bitcoin Halving completes at block 840,000, reducing block rewards to 3.125 BTC.",
    (2025, 1, 1): "The world enters 2025 with the rise of AI Agents, Gold above $2,700/oz, and BTC charging toward $100,000.",
}

YEARLY_POLITICAL_THEMES = {
    2010: [
        "Hoi nghi thuong dinh G20 ban goi kich thich kinh te hau khung hoang tai chinh toan cau.",
        "Lien minh chau Au (EU) va IMF hop khan tai Brussels ve goi cuu tro no cong khu vuc Eurozone.",
        "My thong qua Dao luat cai cach tai chinh Dodd-Frank nham siet chat quan ly ngan hang Pho Wall.",
        "Cac cuoc dam phan thuong mai tu do chau A - Thai Binh Duong mo rong quy mo hop tac khu vuc.",
        "Ngan hang Trung uong My (FED) duoi thoi Ben Bernanke kich hoat goi noi long dinh luong QE2.",
    ],
    2011: [
        "Phong trao Mua Xuan A Rap lan rong tai Trung Dong - Bac Phi, day gia dau tho WTI va Vang tang vot.",
        "Hang dinh gia S&P lan dau tien ha bac tin nhiem no cong My tu AAA xuong AA+, Vang lap dinh lich su.",
        "Nhat Ban tai thiet manh me chuoi cung ung cong nghe va ban dan sau tham hoa kep thang 3.",
    ],
    2012: [
        "Chu tich ECB Mario Draghi tuyen bo 'se lam bat cu dieu gi can thiet' de bao ve dong Euro.",
        "Cuoc dua bau cu Tong thong My 2012 giua Barack Obama va Mitt Romney thu hut su chu y toan cau.",
        "The van hoi Olympic London 2012 dien ra thanh cong ruc ro voi su gop mat cua 204 quoc gia.",
    ],
    2013: [
        "Cuu nhan vien CIA Edward Snowden tiet lo chuong trinh giam sat PRISM, gay tranh cai quoc te.",
        "FED phat tin hieu thu hep goi QE ('Taper Tantrum'), dong USD manh len tren toan cau.",
        "Chinh phu My tam dong cua 16 ngay do bat dong tran no cong tai Quoc hoi.",
    ],
    2014: [
        "Cang thang dia chinh tri tai ban dao Crimea khien phuong Tay ap dat cac lenh trung phat kinh te.",
        "Gia dau tho WTI lao doc tu $100 xuong duoi $50/thung do cuoc cach mang dau da phien My.",
        "My va Cuba tuyen bo binh thuong hoa quan he ngoai giao sau hon 50 nam dong bang.",
    ],
    2015: [
        "195 quoc gia ky ket Hiep dinh Khi hau Paris (COP21) cam ket giam phat thai khi nha kinh.",
        "Ngan hang Trung uong Thuy Si (SNB) bat ngo tha noi ty gia dong Franc gay chan dong thi truong ngoai hoi.",
        "FED tang lai suat lan dau tien sau 9 nam duy tri muc lai suat gan 0%.",
    ],
    2016: [
        "Cuoc bau cu Tong thong My 2016 va cuoc trung cau dan y Brexit lam thay doi ban do chinh tri phuong Tay.",
        "OPEC+ dat thoa thuan cat giam san luong dau mo lich su nham on dinh gia nang luong.",
    ],
    2017: [
        "Chinh quyen My thong qua Dao luat cat giam thue doanh nghiep tu 35% xuong 21%, day chung khoan lap dinh.",
        "Làn sóng đầu tư công nghệ Blockchain và AI thu hút hàng chục tỷ USD vốn mạo hiểm toàn cầu.",
    ],
    2018: [
        "Căng thẳng thương mại Mỹ - Trung leo thang với các đợt áp thuế quan hàng trăm tỷ USD.",
        "Liên minh châu Âu chính thức áp dụng quy định bảo vệ dữ liệu cá nhân GDPR trên toàn cầu.",
    ],
    2019: [
        "Các ngân hàng trung ương toàn cầu đảo chiều hạ lãi suất để hỗ trợ tăng trưởng kinh tế.",
        "Mạng viễn thông 5G thương mại đầu tiên chính thức phủ sóng tại các siêu đô thị lớn.",
    ],
    2020: [
        "Chính phủ các nước tung gói cứu trợ tài khóa hàng nghìn tỷ USD ứng phó đại dịch toàn cầu.",
        "Xu hướng làm việc từ xa thúc đẩy cổ phiếu công nghệ đám mây, bán dẫn và thương mại điện tử.",
    ],
    2021: [
        "Sự cố siêu tàu hàng Ever Given mắc cạn tại kênh đào Suez làm gián đoạn chuỗi cung ứng toàn cầu.",
        "Tình trạng thiếu hụt chip bán dẫn toàn cầu đẩy giá card đồ họa và cổ phiếu NVIDIA, AMD tăng mạnh.",
    ],
    2022: [
        "Lạm phát toàn cầu tăng cao buộc FED nâng lãi suất quyết liệt nhất kể từ thập niên 1980.",
        "Khủng hoảng năng lượng tại châu Âu đẩy giá dầu thô và khí đốt biến động dữ dội.",
    ],
    2023: [
        "Cuộc cách mạng AI tạo sinh (Generative AI) bùng nổ, đưa nhóm cổ phiếu Magnificent 7 dẫn dắt Phố Wall.",
        "Các ngân hàng trung ương tích trữ Vàng với tốc độ kỷ lục trong lịch sử hiện đại.",
    ],
    2024: [
        "Phố Wall chính thức đón nhận dòng vốn hàng chục tỷ USD vào các quỹ ETF tài sản số.",
        "Chu kỳ hạ lãi suất mới của FED và ECB kích hoạt làn sóng đầu tư vào Vàng, Cổ phiếu AI và Crypto.",
    ],
    2025: [
        "Hạ tầng siêu máy tính AI và năng lượng sạch trở thành trọng tâm đầu tư chiến lược của các cường quốc.",
        "Vàng, Bạc và Bitcoin đồng loạt giao dịch ở vùng giá cao lịch sử giữa nhu cầu phòng hộ toàn cầu.",
    ],
}

YEARLY_POLITICAL_THEMES_EN = {
    2010: [
        "G20 Summit debates post-crisis economic stimulus packages and financial stability.",
        "EU and IMF hold emergency talks in Brussels over the Eurozone sovereign debt bailout.",
        "The US passes the Dodd-Frank Wall Street Reform Act to tighten banking regulations.",
        "Asia-Pacific free trade negotiations expand regional economic cooperation.",
        "Federal Reserve Chairman Ben Bernanke activates the QE2 quantitative easing program.",
    ],
    2011: [
        "Arab Spring protests sweep across the Middle East and North Africa, sending WTI crude oil and Gold higher.",
        "S&P downgrades US sovereign credit rating from AAA to AA+ for the first time, pushing Gold to record highs.",
        "Japan rapidly rebuilds its semiconductor and electronics supply chains following the March disaster.",
    ],
    2012: [
        "ECB President Mario Draghi pledges to do 'whatever it takes' to preserve the Euro.",
        "The 2012 US Presidential race between Barack Obama and Mitt Romney captures global attention.",
        "The London 2012 Summer Olympics celebrate a spectacular games with 204 participating nations.",
    ],
    2013: [
        "Former contractor Edward Snowden leaks NSA PRISM surveillance documents, sparking global privacy debates.",
        "The Federal Reserve signals QE tapering ('Taper Tantrum'), strengthening the US Dollar worldwide.",
        "A 16-day US federal government shutdown unfolds amid congressional debt-ceiling negotiations.",
    ],
    2014: [
        "Geopolitical tensions in Crimea prompt Western nations to impose targeted economic sanctions.",
        "WTI crude oil plunges from $100 to under $50/barrel amid the US shale oil revolution.",
        "The US and Cuba announce steps to normalize diplomatic relations after more than 50 years.",
    ],
    2015: [
        "195 nations adopt the historic Paris Climate Accord (COP21) to curb global greenhouse emissions.",
        "The Swiss National Bank unexpectedly unpegs the Franc from the Euro, rattling forex markets.",
        "The Federal Reserve raises interest rates for the first time after 9 years near zero.",
    ],
    2016: [
        "The 2016 US Presidential Election and UK Brexit referendum reshape Western political landscapes.",
        "OPEC+ reaches a landmark production cut agreement to stabilize global oil prices.",
    ],
    2017: [
        "The US enacts corporate tax cuts from 35% to 21%, propelling Wall Street indices to record highs.",
        "Global venture capital pours tens of billions of dollars into Blockchain and AI startups.",
    ],
    2018: [
        "US-China trade tensions escalate with hundreds of billions of dollars in reciprocal tariffs.",
        "The European Union officially enforces the GDPR data protection regulation worldwide.",
    ],
    2019: [
        "Global central banks pivot back to rate cuts to support economic growth amid trade headwinds.",
        "First commercial 5G mobile networks go live across major metropolitan hubs.",
    ],
    2020: [
        "Governments worldwide unleash trillions in fiscal stimulus to counter pandemic lockdowns.",
        "Remote work accelerates demand for cloud computing, semiconductors, and e-commerce giants.",
    ],
    2021: [
        "The Ever Given mega-container ship blocks the Suez Canal, disrupting global supply chains.",
        "A worldwide semiconductor shortage sends GPU prices and shares of NVIDIA and AMD soaring.",
    ],
    2022: [
        "Surging global inflation forces the Federal Reserve into its fastest rate-hiking cycle since the 1980s.",
        "Europe's energy crisis triggers extreme volatility across crude oil and natural gas markets.",
    ],
    2023: [
        "The Generative AI boom propels the 'Magnificent 7' tech giants to lead Wall Street's rally.",
        "Central banks accumulate physical Gold reserves at the fastest pace in modern history.",
    ],
    2024: [
        "Wall Street welcomes tens of billions of dollars in institutional inflows into Spot Crypto ETFs.",
        "Rate cuts by the Fed and ECB ignite a broad rally across Gold, AI equities, and Crypto.",
    ],
    2025: [
        "AI supercomputing clusters and clean energy infrastructure top global strategic investment agendas.",
        "Gold, Silver, and Bitcoin trade near historic highs amid strong global hedging demand.",
    ],
}


try:
    from eagle_news_archive_2010_2025 import (
        CATEGORY_META,
        CATEGORY_ORDER,
        ERA_META_2010_2025,
        EXACT_DATE_ARTICLES_2010_2025,
        YEARLY_CATEGORY_POOLS_2010_2025,
        build_daily_newspaper_from_archive,
    )
except Exception:
    build_daily_newspaper_from_archive = None


def generate_daily_newspaper(
    current_date: datetime.date,
    day_index: int,
    stocks_market: dict,
    crypto_market: dict,
    sport_history: list,
    fixtures: list,
    lang: str = "en",
) -> dict:
    """
    Generates the multi-article Daily Newspaper (`EagleTimes` 01/01/2010 -> 31/12/2025)
    covering 6 categories (World, Life/Nostalgia, Anime/Wibu & Game, Finance/Gold, Crypto, Sports)
    in English (`lang='en'`, default) or Vietnamese (`lang='vi'`).
    """
    ensure_market_catalog_migrated(stocks_market, crypto_market, current_date)
    if build_daily_newspaper_from_archive is not None:
        return build_daily_newspaper_from_archive(
            current_date=current_date,
            day_index=day_index,
            stocks_market=stocks_market,
            crypto_market=crypto_market,
            sport_history=sport_history,
            fixtures=fixtures,
            lang=lang,
        )

    is_vi = (lang == "vi")
    key = (current_date.year, current_date.month, current_date.day)
    if is_vi:
        if key in EXACT_DATE_EVENTS:
            pol_headline = EXACT_DATE_EVENTS[key]
        else:
            themes = YEARLY_POLITICAL_THEMES.get(current_date.year, YEARLY_POLITICAL_THEMES[2010])
            pol_headline = themes[(day_index + current_date.day) % len(themes)]
    else:
        if key in EXACT_DATE_EVENTS_EN:
            pol_headline = EXACT_DATE_EVENTS_EN[key]
        else:
            themes = YEARLY_POLITICAL_THEMES_EN.get(current_date.year, YEARLY_POLITICAL_THEMES_EN[2010])
            pol_headline = themes[(day_index + current_date.day) % len(themes)]

    stock_list = list(stocks_market.values())
    stock_list.sort(key=lambda x: abs(x.get("delta_pct", 0.0)), reverse=True)
    top_s = stock_list[0] if stock_list else {"symbol": "AAPL", "price": 10.0, "delta_pct": 1.2}
    sec_s = stock_list[1] if len(stock_list) > 1 else top_s
    gold = stocks_market.get("XAU", {"price": 1096.5, "delta_pct": 0.5})
    silver = stocks_market.get("XAG", {"price": 17.2, "delta_pct": 0.3})
    diamond = stocks_market.get("DIAMOND", {"price": 6200.0, "delta_pct": 0.2})

    if is_vi:
        fin_article = (
            f"Pho Wall & Vang ({current_date.strftime('%d/%m/%Y')}): Co phieu tam diem {top_s['symbol']} "
            f"${top_s['price']} ({top_s['delta_pct']:+.2f}%) & {sec_s['symbol']} (${sec_s['price']}). "
            f"Vang XAU ${gold['price']}/oz ({gold['delta_pct']:+.2f}%), Bac XAG ${silver['price']}/oz, "
            f"Kim Cuong GIA ${diamond['price']}/ct."
        )
    else:
        fin_article = (
            f"Wall St & Gold ({current_date.strftime('%d/%m/%Y')}): Top movers {top_s['symbol']} "
            f"${top_s['price']} ({top_s['delta_pct']:+.2f}%) & {sec_s['symbol']} (${sec_s['price']}). "
            f"Gold XAU ${gold['price']}/oz ({gold['delta_pct']:+.2f}%), Silver XAG ${silver['price']}/oz, "
            f"GIA Diamond ${diamond['price']}/ct."
        )

    btc = crypto_market.get("BTC", {"price": 0.08, "delta_pct": 0.0})
    eth = crypto_market.get("ETH", {"price": 0.31, "delta_pct": 0.0})
    sol = crypto_market.get("SOL", {"price": 0.78, "delta_pct": 0.0})
    if is_vi:
        cry_article = (
            f"Crypto ({current_date.strftime('%d/%m/%Y')}): BTC ${btc['price']} ({btc['delta_pct']:+.2f}%), "
            f"ETH ${eth['price']} ({eth['delta_pct']:+.2f}%), SOL ${sol['price']}. "
            + (
                "Dau thap nien 2010 thanh khoan tap trung o BTC & LTC; cac coin chua ra mat giu gia co so."
                if current_date.year < 2015
                else "Dong tien Spot va Futures (Long/Short) dang giao dich soi dong tren toan thi truong."
            )
        )
        last_res = to_clean_viet_ascii(sport_history[0]) if sport_history else "Vong dau moi cua 5 giai dau lon chinh thuc khoi tranh."
        next_fix = f"{fixtures[0]['home']} vs {fixtures[0]['away']} ({fixtures[0]['kickoff']})" if fixtures else "Cac CLB dang tap luyen."
        spt_article = f"Tam diem hom nay ({len(fixtures)} tran/5 giai): {next_fix}. KQ moi nhat: {last_res}"
        pol_full = f"[Chinh Tri & The Gioi {current_date.strftime('%d/%m/%Y')}] {to_clean_viet_ascii(pol_headline)}"
        fin_full = f"[Chung Khoan & Vang] {to_clean_viet_ascii(fin_article)}"
        cry_full = f"[Crypto & Blockchain] {to_clean_viet_ascii(cry_article)}"
        spt_full = f"[The Thao 24h] {to_clean_viet_ascii(spt_article)}"
    else:
        cry_article = (
            f"Crypto ({current_date.strftime('%d/%m/%Y')}): BTC ${btc['price']} ({btc['delta_pct']:+.2f}%), "
            f"ETH ${eth['price']} ({eth['delta_pct']:+.2f}%), SOL ${sol['price']}. "
            + (
                "Early 2010s liquidity centers on BTC & LTC; pre-launch tokens hold seed prices."
                if current_date.year < 2015
                else "Spot and Futures (Long/Short) order books are trading actively across global exchanges."
            )
        )
        last_res = to_clean_viet_ascii(sport_history[0]) if sport_history else "A new matchweek across all 5 major leagues kicks off today."
        next_fix = f"{fixtures[0]['home']} vs {fixtures[0]['away']} ({fixtures[0]['kickoff']})" if fixtures else "Clubs are in training."
        spt_article = f"Today's spotlight ({len(fixtures)} matches/5 leagues): {next_fix}. Latest result: {last_res}"
        pol_full = f"[World & Politics {current_date.strftime('%d/%m/%Y')}] {to_clean_viet_ascii(pol_headline)}"
        fin_full = f"[Stocks & Gold] {to_clean_viet_ascii(fin_article)}"
        cry_full = f"[Crypto & Blockchain] {to_clean_viet_ascii(cry_article)}"
        spt_full = f"[Sports 24h] {to_clean_viet_ascii(spt_article)}"

    return {
        "date_str": current_date.strftime("%d/%m/%Y"),
        "day_index": day_index,
        "politics": pol_full,
        "finance": fin_full,
        "crypto": cry_full,
        "sports": spt_full,
        "pol_lines": wrap_hud_lines(pol_full, width=64, max_lines=4),
        "fin_lines": wrap_hud_lines(fin_full, width=64, max_lines=4),
        "cry_lines": wrap_hud_lines(cry_full, width=64, max_lines=4),
        "spt_lines": wrap_hud_lines(spt_full, width=64, max_lines=4),
        "hud_pol": wrap_hud_lines(pol_full, width=64, max_lines=1)[0],
        "hud_fin": wrap_hud_lines(fin_full, width=64, max_lines=1)[0],
        "hud_cry": wrap_hud_lines(cry_full, width=64, max_lines=1)[0],
        "hud_spt": wrap_hud_lines(spt_full, width=64, max_lines=1)[0],
    }


# ============================================================================
# 5. LOTTERY PRIZE TABLES & SCHEDULED DRAW HOURS
# ============================================================================
LOTTERY_6DIGIT_TIERS = [
    {"tier": "Grand Prize (All 6 digits)", "tier_vi": "Giai Dac Biet (6 so)", "digits": 6, "payout": 200000},
    {"tier": "1st Prize (Last 5 digits)", "tier_vi": "Giai Nhat (5 so cuoi)", "digits": 5, "payout": 15000},
    {"tier": "2nd Prize (Last 4 digits)", "tier_vi": "Giai Nhi (4 so cuoi)", "digits": 4, "payout": 2500},
    {"tier": "7th Prize (Last 3 digits)", "tier_vi": "Giai Bay (3 so cuoi)", "digits": 3, "payout": 150},
    {"tier": "8th Prize (Last 2 digits)", "tier_vi": "Giai Tam (2 so cuoi)", "digits": 2, "payout": 50},
]

SCRATCH_CARD_TYPES = {
    "SILVER_20": {
        "name": "Silver Scratch ($20)",
        "name_vi": "Ve Cao Bac ($20)",
        "cost": 20,
        "outcomes": [
            (0.66, 0, "Better luck next time!"),
            (0.18, 20, "Break even! Matched 3x $20 symbols!"),
            (0.09, 40, "Matched 3 Silver Stars (+$40)!"),
            (0.045, 100, "Matched 3 Gold Bars (+$100)!"),
            (0.018, 300, "Matched 3 Diamonds (+$300)!"),
            (0.006, 1500, "SUPER PRIZE! 3 Phoenixes (+$1,500)!"),
            (0.001, 10000, "SILVER SCRATCH JACKPOT! (+$10,000)!"),
        ],
        "outcomes_vi": [
            (0.66, 0, "Chuc ban may man lan sau!"),
            (0.18, 20, "Hoan von! Trung 3 bieu tuong $20!"),
            (0.09, 40, "Trung 3 Ngoi Sao Bac (+$40)!"),
            (0.045, 100, "Trung 3 Thoi Vang (+$100)!"),
            (0.018, 300, "Trung 3 Vien Kim Cuong (+$300)!"),
            (0.006, 1500, "SIEU GIAI THUONG! 3 Phuong Hoang (+$1,500)!"),
            (0.001, 10000, "JACKPOT VE CAO BAC! (+$10,000)!"),
        ],
    },
    "GOLD_50": {
        "name": "Gold Scratch ($50)",
        "name_vi": "Ve Cao Vang ($50)",
        "cost": 50,
        "outcomes": [
            (0.65, 0, "Better luck next time!"),
            (0.18, 50, "Break even! Matched 3x $50 symbols!"),
            (0.09, 120, "Matched 3 Gold Bars (+$120)!"),
            (0.05, 300, "Matched 3 Emeralds (+$300)!"),
            (0.02, 1000, "Matched 3 Golden Crowns (+$1,000)!"),
            (0.008, 4000, "GOLD SCRATCH MEGA WIN (+$4,000)!"),
            (0.002, 25000, "GOLD SCRATCH JACKPOT (+$25,000)!"),
        ],
        "outcomes_vi": [
            (0.65, 0, "Chuc ban may man lan sau!"),
            (0.18, 50, "Hoan von! Trung 3 bieu tuong $50!"),
            (0.09, 120, "Trung 3 Thoi Vang (+$120)!"),
            (0.05, 300, "Trung 3 Ngoc Luc Bao (+$300)!"),
            (0.02, 1000, "Trung 3 Vuong Mien Vang (+$1,000)!"),
            (0.008, 4000, "DAI THANG VE CAO VANG (+$4,000)!"),
            (0.002, 25000, "JACKPOT VE CAO VANG (+$25,000)!"),
        ],
    },
    "GOLD_100": {
        "name": "Royal Gold Scratch ($100)",
        "name_vi": "Ve Cao Hoang Kim ($100)",
        "cost": 100,
        "outcomes": [
            (0.64, 0, "Better luck next time!"),
            (0.19, 100, "Break even! Matched 3x $100 symbols!"),
            (0.09, 250, "Matched 3 Emeralds (+$250)!"),
            (0.05, 600, "Matched 3 Golden Crowns (+$600)!"),
            (0.02, 2000, "Matched 3 Golden Dragons (+$2,000)!"),
            (0.008, 8000, "ROYAL GOLD MEGA WIN (+$8,000)!"),
            (0.002, 50000, "ROYAL GOLD JACKPOT (+$50,000)!"),
        ],
        "outcomes_vi": [
            (0.64, 0, "Chuc ban may man lan sau!"),
            (0.19, 100, "Hoan von! Trung 3 bieu tuong $100!"),
            (0.09, 250, "Trung 3 Ngoc Luc Bao (+$250)!"),
            (0.05, 600, "Trung 3 Vuong Mien Vang (+$600)!"),
            (0.02, 2000, "Trung 3 Rong Vang (+$2,000)!"),
            (0.008, 8000, "DAI THANG HOANG KIM (+$8,000)!"),
            (0.002, 50000, "JACKPOT HOANG KIM (+$50,000)!"),
        ],
    },
    "DIAMOND_100": {
        "name": "Diamond Scratch ($100)",
        "name_vi": "Ve Cao Kim Cuong ($100)",
        "cost": 100,
        "outcomes": [
            (0.64, 0, "Better luck next time!"),
            (0.19, 100, "Break even! Matched 3x $100 symbols!"),
            (0.09, 250, "Matched 3 Emeralds (+$250)!"),
            (0.05, 600, "Matched 3 Golden Crowns (+$600)!"),
            (0.02, 2000, "Matched 3 Golden Dragons (+$2,000)!"),
            (0.008, 8000, "DIAMOND SCRATCH MEGA WIN (+$8,000)!"),
            (0.002, 50000, "DIAMOND SCRATCH JACKPOT (+$50,000)!"),
        ],
        "outcomes_vi": [
            (0.64, 0, "Chuc ban may man lan sau!"),
            (0.19, 100, "Hoan von! Trung 3 bieu tuong $100!"),
            (0.09, 250, "Trung 3 Ngoc Luc Bao (+$250)!"),
            (0.05, 600, "Trung 3 Vuong Mien Vang (+$600)!"),
            (0.02, 2000, "Trung 3 Rong Vang (+$2,000)!"),
            (0.008, 8000, "DAI THANG KIM CUONG (+$8,000)!"),
            (0.002, 50000, "JACKPOT KIM CUONG (+$50,000)!"),
        ],
    },
    "VIP_500": {
        "name": "Fortune VIP Scratch ($500)",
        "name_vi": "Ve Cao Than Tai VIP ($500)",
        "cost": 500,
        "outcomes": [
            (0.60, 0, "Better luck next time!"),
            (0.20, 500, "Break even! Matched 3x $500 symbols!"),
            (0.10, 1250, "Matched 3x 9999 Gold Bullion (+$1,250)!"),
            (0.055, 3000, "Matched 3 Red Diamonds (+$3,000)!"),
            (0.028, 10000, "Matched 3 Imperial Dragons (+$10,000)!"),
            (0.012, 40000, "FORTUNE VIP MEGA WIN (+$40,000)!"),
            (0.005, 250000, "FORTUNE VIP GRAND JACKPOT (+$250,000)!"),
        ],
        "outcomes_vi": [
            (0.60, 0, "Chuc ban may man lan sau!"),
            (0.20, 500, "Hoan von! Trung 3 bieu tuong $500!"),
            (0.10, 1250, "Trung 3 Thoi Vang 9999 (+$1,250)!"),
            (0.055, 3000, "Trung 3 Kim Cuong Do (+$3,000)!"),
            (0.028, 10000, "Trung 3 Rong Hoang Kim (+$10,000)!"),
            (0.012, 40000, "DAI THANG THAN TAI VIP (+$40,000)!"),
            (0.005, 250000, "SIEU JACKPOT THAN TAI VIP (+$250,000)!"),
        ],
    },
}
