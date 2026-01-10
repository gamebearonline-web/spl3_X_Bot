import argparse
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import datetime
import os
import json

# ==========================
# ★ API URL
# ==========================
API_URLS = {
    "regular": "https://spla3.yuu26.com/api/regular/schedule",
    "open": "https://spla3.yuu26.com/api/bankara-open/schedule",
    "challenge": "https://spla3.yuu26.com/api/bankara-challenge/schedule",
    "xmatch": "https://spla3.yuu26.com/api/x/schedule",
    "salmon": "https://spla3.yuu26.com/api/coop-grouping/schedule",
    "fest_open": "https://spla3.yuu26.com/api/fest/schedule",
    "fest_challenge": "https://spla3.yuu26.com/api/fest-challenge/schedule",
}

API_NOW_URLS = {
    "regular": "https://spla3.yuu26.com/api/regular/now",
    "open": "https://spla3.yuu26.com/api/bankara-open/now",
    "challenge": "https://spla3.yuu26.com/api/bankara-challenge/now",
    "xmatch": "https://spla3.yuu26.com/api/x/now",
    "salmon": "https://spla3.yuu26.com/api/coop-grouping/now",
    "fest_open": "https://spla3.yuu26.com/api/fest/now",
    "fest_challenge": "https://spla3.yuu26.com/api/fest-challenge/now",
}

# ==========================
# ★ 引数 --output 対応
# ==========================
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=str,
        default="Thumbnail/Thumbnail.png",
        help="Output image path",
    )
    return parser.parse_args()


# ==========================
# ★ パス設定
# ==========================
TEMPLATE_PATH = "spl3_Schedule_Template_ver0.png"
FEST_NOW_OVERLAY = "fest/now_fest.png"  # フェスnow用オーバーレイ
FEST_NEXT_OVERLAY = "fest/next_fest.png"  # フェスnext用オーバーレイ
OUTPUT_PATH   = "Thumbnail/Thumbnail.png"
ICON_DIR      = "icon"

os.makedirs("Thumbnail", exist_ok=True)

# ==========================
# ★ 高速化:画像キャッシュ & Session
# ==========================
session = requests.Session()
IMAGE_CACHE = {}

def fetch_image(url):
    if url not in IMAGE_CACHE:
        resp = session.get(url, headers={"User-Agent": "Spla3Img/1.0"})
        resp.raise_for_status()
        IMAGE_CACHE[url] = Image.open(BytesIO(resp.content)).convert("RGB")
    return IMAGE_CACHE[url].copy()

# 透過PNG(武器など)用：RGBAで取得してマスク貼り付け可能にする
IMAGE_CACHE_RGBA = {}

def fetch_image_rgba(url):
    if url not in IMAGE_CACHE_RGBA:
        resp = session.get(url, headers={"User-Agent": "Spla3Img/1.0"})
        resp.raise_for_status()
        IMAGE_CACHE_RGBA[url] = Image.open(BytesIO(resp.content)).convert("RGBA")
    return IMAGE_CACHE_RGBA[url].copy()


# ==========================
# ★ フェス開催中判定（グローバル）
# ==========================
def check_fest_slots():
    """
    fest/schedule を見て、now/next/next2/next3/next4 がフェス枠かを判定して返す
    判定条件：そのスロットの stages が None ではない（=フェスのステージ情報がある）
    """
    slots = {"now": False, "next": False, "next2": False, "next3": False, "next4": False}

    try:
        fest_results = fetch_schedule(API_URLS["fest_open"])  # https://spla3.yuu26.com/api/fest/schedule

        for idx, slot in enumerate(["now", "next", "next2", "next3", "next4"]):
            if idx >= len(fest_results):
                continue
            info = fest_results[idx]
            stages = info.get("stages")
            if stages is not None:
                slots[slot] = True

        if any(slots.values()):
            print(f"[INFO] フェス枠あり: {slots}")
        else:
            print("[INFO] フェス枠なし")

    except Exception as e:
        print(f"[WARN] フェス枠判定エラー: {e}")

    return slots

       

# ==========================
# ★ テーマカラー
# ==========================
MODE_COLORS = {
    "regular":   (208, 246, 35),
    "open":      (245, 73, 16),
    "challenge": (245, 73, 16),
    "xmatch":    (10, 220, 156),
    "salmon":    (255, 139, 0),
}

# ==========================
# ★ フェス用 文字背景色
# ==========================
FEST_TEXT_BG = {
    "open":      (232, 213, 38),   # #e8d526
    "challenge": (232, 213, 38),   # #e8d526
    "xmatch":    (102, 77, 222),   # #664dde
}


# ==========================
# ★ フォント
# ==========================
def load_font(size):
    return ImageFont.truetype(r"GenEiPOPle_v1.0/GenEiPOPle-Bk.ttf", size)

FONT_TIME_NOW    = load_font(15)
FONT_STAGE_NOW   = load_font(12)
FONT_TIME_SMALL  = load_font(10)
FONT_STAGE_SMALL = load_font(10)

# ==========================
# ★ サーモン用 日付＋曜日
# ==========================
def format_salmon_datetime(iso_str: str) -> str:
    dt = datetime.datetime.fromisoformat(iso_str)
    weekday = "月火水木金土日"[dt.weekday()]
    return dt.strftime(f"%m/%d({weekday}) %H:%M")

# ==========================
# ★ テキスト描画ユーティリティ
# ==========================
def draw_text_left(draw, box, text, font, bg_fill, text_fill=(0, 0, 0), padding=2):
    x, y, w, h = box
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x
    ty = y + (h - th) / 2
    draw.rectangle([tx - padding, ty - padding, tx + tw + padding, ty + th + padding], fill=bg_fill)
    draw.text((tx, ty), text, font=font, fill=text_fill)

def draw_text_with_bg(draw, box, text, font, bg_fill, text_fill=(0, 0, 0), padding=2):
    x, y, w, h = box
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    cx = x + (w - tw) / 2
    cy = y + (h - th) / 2
    draw.rectangle([cx - padding, cy - padding, cx + tw + padding, cy + th + padding], fill=bg_fill)
    draw.text((cx, cy), text, font=font, fill=text_fill)


# ==========================
# ★ ルールアイコン座標
# ==========================
RULE_ICON_COORDS = {
    "open": {
        "now":   (400.139587, 40.380998, 45, 45),
        "next":  (429.165978, 323.062795, 30, 30),
        "next2": (429.165978, 403.09818,  30, 30),
        "next3": (429.165978, 483.352413, 30, 30),
        "next4": (429.165978, 563.109303, 30, 30),
    },
    "challenge": {
        "now":   (620.18784, 40.380998, 45, 45),
        "next":  (649.214231, 323.062795, 30, 30),
        "next2": (649.214231, 403.09818,  30, 30),
        "next3": (649.214231, 483.352413, 30, 30),
        "next4": (649.214231, 563.109303, 30, 30),
    },
    "xmatch": {
        "now":   (864.76611, 40.380998, 45, 45),
        "next":  (893.792501, 323.062795, 30, 30),
        "next2": (893.792501, 403.09818,  30, 30),
        "next3": (893.792501, 483.352413, 30, 30),
        "next4": (893.792501, 563.109303, 30, 30),
    },
}

def draw_rule_icon(base, mode, slot, rule_key):
    if not rule_key or mode not in RULE_ICON_COORDS:
        return
    if slot not in RULE_ICON_COORDS[mode]:
        return

    x, y, w, h = RULE_ICON_COORDS[mode][slot]
    icon_path = os.path.join(ICON_DIR, f"{rule_key}.png")
    if not os.path.exists(icon_path):
        return

    icon = Image.open(icon_path).convert("RGBA")
    icon = icon.resize((int(w), int(h)))
    base.paste(icon, (int(x), int(y)), icon)

# ==========================
# ★ ステージ座標（regular / open / challenge / xmatch / salmon）
# ==========================

coords_regular = {
    "now": {
        "start_time":  (37.15, 49.875, 89.302, 18.556),
        "stage0_image":(37.15, 88.716, 176.0, 99.0),
        "stage0_name": (69.849, 169.274, 107.641, 18.442),
        "stage1_image":(37.15, 198.664, 176.0, 99.0),
        "stage1_name": (69.849, 279.222, 107.641, 18.442),
    },
    "next": {
        "stage0_image":(29.622, 338.392, 96.0, 54.0),
        "stage1_image":(129.206, 338.392, 96.0, 54.0),
        "start_time":  (29.622, 325.73, 60.156, 12.674),
        "stage0_name": (41.367, 379.892, 72.51, 12.5),
        "stage1_name": (140.951, 379.934, 72.51, 12.458),
    },
    "next2": {
        "stage0_image":(29.622, 418.098, 96.0, 54.0),
        "stage1_image":(129.206, 418.098, 96.0, 54.0),
        "start_time":  (29.622, 405.611, 60.156, 12.674),
        "stage0_name": (41.367, 459.598, 72.51, 12.5),
        "stage1_name": (140.951, 459.64, 72.51, 12.458),
    },
    "next3": {
        "stage0_image":(29.622, 498.352, 96.0, 54.0),
        "stage1_image":(129.206, 498.352, 96.0, 54.0),
        "start_time":  (29.622, 485.852, 60.156, 12.674),
        "stage0_name": (41.367, 539.852, 72.51, 12.5),
        "stage1_name": (140.951, 539.894, 72.51, 12.458),
    },
    "next4": {
        "stage0_image":(29.622, 578.109, 96.0, 54.0),
        "stage1_image":(129.206, 578.109, 96.0, 54.0),
        "start_time":  (29.622, 565.435, 60.156, 12.674),
        "stage0_name": (41.367, 619.609, 72.51, 12.5),
        "stage1_name": (140.951, 619.651, 72.51, 12.458),
    },
}

coords_open = {
    "now": {
        "start_time":  (278.336, 49.875, 89.302, 18.556),
        "stage0_image":(278.336, 88.716, 176.0, 99.0),
        "stage0_name": (311.035, 169.274, 107.641, 18.442),
        "stage1_image":(278.336, 198.664, 176.0, 99.0),
        "stage1_name": (311.035, 279.222, 107.641, 18.442),
    },
    "next": {
        "stage0_image":(270.808, 338.392, 96.0, 54.0),
        "stage1_image":(370.392, 338.392, 96.0, 54.0),
        "start_time":  (270.808, 325.73, 60.156, 12.674),
        "stage0_name": (282.553, 379.892, 72.51, 12.5),
        "stage1_name": (382.137, 379.934, 72.51, 12.458),
    },
    "next2": {
        "stage0_image":(270.808, 418.098, 96.0, 54.0),
        "stage1_image":(370.392, 418.098, 96.0, 54.0),
        "start_time":  (270.808, 405.611, 60.156, 12.674),
        "stage0_name": (282.553, 459.598, 72.51, 12.5),
        "stage1_name": (382.137, 459.64, 72.51, 12.458),
    },
    "next3": {
        "stage0_image":(270.808, 498.352, 96.0, 54.0),
        "stage1_image":(370.392, 498.352, 96.0, 54.0),
        "start_time":  (270.808, 485.852, 60.156, 12.674),
        "stage0_name": (282.553, 539.852, 72.51, 12.5),
        "stage1_name": (382.137, 539.894, 72.51, 12.458),
    },
    "next4": {
        "stage0_image":(270.808, 578.109, 96.0, 54.0),
        "stage1_image":(370.392, 578.109, 96.0, 54.0),
        "start_time":  (270.808, 565.435, 60.156, 12.674),
        "stage0_name": (282.553, 619.609, 72.51, 12.5),
        "stage1_name": (382.137, 619.651, 72.51, 12.458),
    },
}

coords_challenge = {
    "now": {
        "start_time":  (519.521 - 22, 49.875, 89.302, 18.556),
        "stage0_image":(519.521 - 22, 88.716, 176.0, 99.0),
        "stage0_name": (552.22  - 22, 169.274, 107.641, 18.442),
        "stage1_image":(519.521 - 22, 198.664, 176.0, 99.0),
        "stage1_name": (552.22  - 22, 279.222, 107.641, 18.442),
    },
    "next": {
        "stage0_image":(512.0   - 22, 338.392, 96.0, 54.0),
        "stage1_image":(611.584 - 22, 338.392, 96.0, 54.0),
        "start_time":  (512.0   - 22, 325.73,  60.156, 12.674),
        "stage0_name": (523.745 - 22, 379.892, 72.51,  12.5),
        "stage1_name": (623.329 - 22, 379.934, 72.51,  12.458),
    },
    "next2": {
        "stage0_image":(512.0   - 22, 418.098, 96.0, 54.0),
        "stage1_image":(611.584 - 22, 418.098, 96.0, 54.0),
        "start_time":  (512.0   - 22, 405.611,60.156, 12.674),
        "stage0_name": (523.745 - 22, 459.598,72.51,  12.5),
        "stage1_name": (623.329 - 22, 459.64, 72.51,  12.458),
    },
    "next3": {
        "stage0_image":(512.0   - 22, 498.352,96.0, 54.0),
        "stage1_image":(611.584 - 22, 498.352,96.0, 54.0),
        "start_time":  (512.0   - 22, 485.852,60.156, 12.674),
        "stage0_name": (523.745 - 22, 539.852,72.51,  12.5),
        "stage1_name": (623.329 - 22, 539.894,72.51,  12.458),
    },
    "next4": {
        "stage0_image":(512.0   - 22, 578.109,96.0, 54.0),
        "stage1_image":(611.584 - 22, 578.109,96.0, 54.0),
        "start_time":  (512.0   - 22, 565.435,60.156, 12.674),
        "stage0_name": (523.745 - 22, 619.609,72.51,  12.5),
        "stage1_name": (623.329 - 22, 619.651,72.51,  12.458),
    },
}

coords_xmatch = {
    "now": {
        "start_time":  (760.707 - 19, 49.875, 89.302, 18.556),
        "stage0_image":(760.707 - 19, 88.716, 176.0, 99.0),
        "stage0_name": (793.406 - 19, 169.274, 107.641, 18.442),
        "stage1_image":(760.707 - 19, 198.664, 176.0, 99.0),
        "stage1_name": (793.406 - 19, 279.222, 107.641, 18.442),
    },
    "next": {
        "stage0_image":(753.178 - 19, 338.392, 96.0, 54.0),
        "stage1_image":(852.762 - 19, 338.392, 96.0, 54.0),
        "start_time":  (753.178 - 19, 325.73,  60.156, 12.674),
        "stage0_name": (764.923 - 19, 379.892, 72.51,  12.5),
        "stage1_name": (864.507 - 19, 379.934, 72.51,  12.458),
    },
    "next2": {
        "stage0_image":(753.178 - 19, 418.098, 96.0, 54.0),
        "stage1_image":(852.762 - 19, 418.098, 96.0, 54.0),
        "start_time":  (753.178 - 19, 405.611,60.156, 12.674),
        "stage0_name": (764.923 - 19, 459.598,72.51,  12.5),
        "stage1_name": (864.507 - 19, 459.64, 72.51,  12.458),
    },
    "next3": {
        "stage0_image":(753.178 - 19, 498.352,96.0, 54.0),
        "stage1_image":(852.762 - 19, 498.352,96.0, 54.0),
        "start_time":  (753.178 - 19, 485.852,60.156, 12.674),
        "stage0_name": (764.923 - 19, 539.852,72.51,  12.5),
        "stage1_name": (864.507 - 19, 539.894,72.51,  12.458),
    },
    "next4": {
        "stage0_image":(753.178 - 19, 578.109,96.0, 54.0),
        "stage1_image":(852.762 - 19, 578.109,96.0, 54.0),
        "start_time":  (753.178 - 19, 565.435,60.156, 12.674),
        "stage0_name": (764.923 - 19, 619.609,72.51,  12.5),
        "stage1_name": (864.507 - 19, 619.651,72.51,  12.458),
    },
}

coords_salmon = {
    "now": {
        "start_time": (977.6,   49.9,   192.0,   18.6),
        "end_time":   (977.564, 68.431, 192.002, 18.556),
        "stage_image":(977.564, 172.5,  192.0,   115.0),
        "stage_name": (1019.744,269.058,107.641, 18.442),
        "weapon0": (967.885401, 103.20998),
        "weapon1": (1021.671449, 103.20998),
        "weapon2": (1075.457496, 103.20998),
        "weapon3": (1129.243543, 103.508658),
    },
    "next": {
        "start_time": (977.904 +2, 325.73, 60.156, 12.674),
        "end_time":   (1068.904 +10,325.73, 91.0,   12.674),
        "stage_image":(977.904, 338.392,96.0,  54.0),
        "stage_name": (989.649, 379.892,72.51, 12.5),
        "weapon0": (1079.911278, 340.06515),
        "weapon1": (1109.763201, 340.06515),
        "weapon2": (1079.911278, 369.917073),
        "weapon3": (1109.763201, 369.917073),
    },
    "next2": {
        "start_time": (977.904 +2, 405.611,60.156, 12.674),
        "end_time":   (1068.904 +10,405.611,91.0,  12.674),
        "stage_image":(977.904, 418.098,96.0,  54.0),
        "stage_name": (989.649, 459.598,72.51, 12.5),
        "weapon0": (1079.911278, 419.362218),
        "weapon1": (1109.763201, 419.362218),
        "weapon2": (1079.911278, 449.214141),
        "weapon3": (1109.763201, 449.214141),
    },
    "next3": {
        "start_time": (977.904 +2, 485.852,60.156, 12.674),
        "end_time":   (1068.904 +10,485.852,91.0,  12.674),
        "stage_image":(977.904, 498.352,96.0,  54.0),
        "stage_name": (989.649, 539.852,72.51, 12.5),
        "weapon0": (1079.911278, 500.084767),
        "weapon1": (1109.763201, 500.084767),
        "weapon2": (1079.911278, 529.93669),
        "weapon3": (1109.763201, 529.93669),
    },
    "next4": {
        "start_time": (977.904 +2, 565.435,60.156, 12.674),
        "end_time":   (1068.904 +10,565.435,95.661,12.674),
        "stage_image":(977.904, 578.109,96.0,  54.0),
        "stage_name": (989.649, 619.609,72.51, 12.5),
        "weapon0": (1079.911278, 580.145118),
        "weapon1": (1109.763201, 580.145118),
        "weapon2": (1079.911278, 609.997041),
        "weapon3": (1109.763201, 609.997041),
    },
}

COORDS_TABLE = {
    "regular":   coords_regular,
    "open":      coords_open,
    "challenge": coords_challenge,
    "xmatch":    coords_xmatch,
    "salmon":    coords_salmon,
}

# ==========================
# ★ BIG RUN アイコン座標
# ==========================
BIG_RUN_COORDS = {
    "now":   (998.564, 180, 150, 75),
    "next":  (990, 340, 70, 35),
    "next2": (990, 420, 70, 35),
    "next3": (990, 501, 70, 35),
    "next4": (990, 581, 70, 35),
}

def draw_big_run(base, slot, is_big_run):
    if not is_big_run:
        return
    if slot not in BIG_RUN_COORDS:
        return

    x, y, w, h = BIG_RUN_COORDS[slot]
    icon_path = os.path.join(ICON_DIR, "big_run.png")
    if not os.path.exists(icon_path):
        return

    img = Image.open(icon_path).convert("RGBA")
    img = img.resize((int(w), int(h)))
    base.paste(img, (int(x), int(y)), img)


# ==========================
# ★ BOSS（オカシラ）
# ==========================
BOSS_COORDS = {
    "now":  (1118.0, 40.0),
    "next": (1144.939975, 354.991111),
    "next2":(1144.939975, 434.288179),
    "next3":(1144.939975, 515.010729),
    "next4":(1144.939975, 595.071079),
}

BOSS_SIZES = {
    "now":  (45, 45),
    "next": (30, 30),
    "next2":(30, 30),
    "next3":(30, 30),
    "next4":(30, 30),
}

def draw_boss_icon(base, slot, boss_id):
    if not boss_id or slot not in BOSS_COORDS:
        return

    icon_file = boss_id + ".png"
    icon_path = os.path.join(ICON_DIR, icon_file)
    if not os.path.exists(icon_path):
        return

    x, y = BOSS_COORDS[slot]
    w, h = BOSS_SIZES[slot]

    icon = Image.open(icon_path).convert("RGBA")
    icon = icon.resize((int(w), int(h)))
    base.paste(icon, (int(x), int(y)), icon)


# ==========================
# ★ サーモン武器
# ==========================
def draw_salmon_weapons(base, slot, weapons):
    if slot not in coords_salmon:
        return
    cslot = coords_salmon[slot]

    size = (50, 50) if slot == "now" else (30, 30)

    for i in range(4):
        key = f"weapon{i}"
        if key not in cslot:
            continue
        if i >= len(weapons):
            continue

        wx, wy = cslot[key]
        try:
            # ★ここが重要：RGBAで取得して透過を保持
            img = fetch_image_rgba(weapons[i]["image"]).resize(size)
            # RGBのbaseに貼るので、maskとしてimg自身(α)を渡す
            base.paste(img, (int(wx), int(wy)), img)
        except Exception as e:
            # もし今後も出ない場合の原因が分かるようにログ出す（任意）
            print(f"[WARN] weapon paste failed slot={slot} i={i}: {e}")



# ==========================
# ★ API 共通
# ==========================
def fetch_schedule(url):
    try:
        print(f"[DEBUG] Fetching: {url}")
        resp = session.get(url, headers={"User-Agent": "Spla3StageBot/1.0"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        print(f"[DEBUG] {url} returned {len(results) if results else 0} results")
        if results is None:
            return []
        return results
    except Exception as e:
        print(f"[ERR] fetch_schedule failed for {url}: {e}")
        import traceback
        traceback.print_exc()
        return []

def fetch_now(url):
    try:
        print(f"[DEBUG] Fetching now: {url}")
        resp = session.get(url, headers={"User-Agent": "Spla3StageBot/1.0"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results")
        print(f"[DEBUG] {url} returned: {type(results)}")
        if not results:
            return {}
        return results[0] if isinstance(results, list) else results
    except Exception as e:
        print(f"[ERR] fetch_now failed for {url}: {e}")
        import traceback
        traceback.print_exc()
        return {}


# ==========================
# ★ バトル（regular / open / challenge / xmatch）
# ==========================
def render_versus_mode(base, mode, results, fest_slots=None):
    print(f"[DEBUG] render_versus_mode: mode={mode}, results count={len(results) if results else 0}")

    if not results:
        print(f"[WARN] {mode} has no results")
        return

    coords_mode = COORDS_TABLE[mode]
    draw = ImageDraw.Draw(base)

    for idx, slot in enumerate(["now", "next", "next2", "next3", "next4"]):
        if slot not in coords_mode or idx >= len(results):
            continue

        info  = results[idx]
        cslot = coords_mode[slot]

        stages = info.get("stages")
        if stages is None:
            print(f"[WARN] {mode} {slot}: stages is None, skipping")
            continue

        # ★スロット別フェス判定（open/challengeだけ fest_slots を渡す運用）
        is_fest_slot = bool(fest_slots and fest_slots.get(slot, False))

        # 背景色決定（フェス枠だけ FEST_TEXT_BG を使う）
        if is_fest_slot and mode in FEST_TEXT_BG:
            bg_color = FEST_TEXT_BG[mode]
        else:
            bg_color = MODE_COLORS[mode]

        # フォント選択
        font_time  = FONT_TIME_NOW if slot == "now" else FONT_TIME_SMALL
        font_stage = FONT_STAGE_NOW if slot == "now" else FONT_STAGE_SMALL

        # 時刻表示
        if "start_time" in cslot and info.get("start_time") and info.get("end_time"):
            start = datetime.datetime.fromisoformat(info["start_time"].replace("Z", "+00:00"))
            end   = datetime.datetime.fromisoformat(info["end_time"].replace("Z", "+00:00"))
            time_text = f"{start.strftime('%H:%M')}~{end.strftime('%H:%M')}"
            draw_text_with_bg(draw, cslot["start_time"], time_text, font_time, bg_fill=bg_color)

        # ステージ描画
        stages = info.get("stages", [])
        for i in (0, 1):
            if i >= len(stages):
                continue
            stg = stages[i]

            if f"stage{i}_image" in cslot:
                ix, iy, iw, ih = cslot[f"stage{i}_image"]
                try:
                    img = fetch_image(stg["image"]).resize((int(iw), int(ih)))
                    base.paste(img, (int(ix), int(iy)))
                except Exception:
                    pass

            if f"stage{i}_name" in cslot:
                draw_text_with_bg(draw, cslot[f"stage{i}_name"], stg["name"], font_stage, bg_fill=bg_color)

        # ルールアイコン
        rule_key = info.get("rule", {}).get("key")
        draw_rule_icon(base, mode, slot, rule_key)



# ==========================
# ★ サーモンラン
# ==========================
def render_salmon_mode(base, results):
    print(f"[DEBUG] render_salmon_mode: results count={len(results) if results else 0}")
    
    if not results:
        print(f"[WARN] salmon has no results")
        return
    
    coords_mode = COORDS_TABLE["salmon"]
    # ... 残りのコード
    draw = ImageDraw.Draw(base)
    color = MODE_COLORS["salmon"]

    for idx, slot in enumerate(["now", "next", "next2", "next3", "next4"]):
        if slot not in coords_mode or idx >= len(results):
            continue

        info = results[idx]
        cslot = coords_mode[slot]

        boss_id = info.get("boss", {}).get("id")
        is_big_run = info.get("is_big_run", False)

        start_label = format_salmon_datetime(info["start_time"])
        end_label   = "~" + format_salmon_datetime(info["end_time"])

        font_time  = FONT_TIME_NOW if slot == "now" else FONT_TIME_SMALL
        font_stage = FONT_STAGE_NOW if slot == "now" else FONT_STAGE_SMALL

        if "start_time" in cslot:
            draw_text_left(draw, cslot["start_time"], start_label, font_time, bg_fill=color)

        if "end_time" in cslot:
            draw_text_left(draw, cslot["end_time"], end_label, font_time, bg_fill=color)

        stage = info.get("stage")
        if stage:
            if "stage_image" in cslot:
                ix, iy, iw, ih = cslot["stage_image"]
                try:
                    img = fetch_image(stage["image"])
                    img = img.resize((int(iw), int(ih)))
                    base.paste(img, (int(ix), int(iy)))
                except Exception:
                    pass

            if "stage_name" in cslot:
                draw_text_with_bg(draw, cslot["stage_name"], stage["name"], font_stage, bg_fill=color)

        draw_salmon_weapons(base, slot, info.get("weapons", []))
        draw_boss_icon(base, slot, boss_id)
        draw_big_run(base, slot, is_big_run)

# ==========================
# ★ 指定位置に貼る用ユーティリティを追加（RGBAで貼る）
# ==========================
def paste_overlay_rect(base: Image.Image, overlay_path: str, x: int, y: int, w: int, h: int):
    """
    overlay画像を指定矩形(x,y,w,h)へリサイズしてRGBA合成で貼る
    """
    if not os.path.exists(overlay_path):
        print(f"[WARN] overlay not found: {overlay_path}")
        return

    try:
        ov = Image.open(overlay_path).convert("RGBA")
        ov = ov.resize((int(w), int(h)))
        # baseはRGBでもOK。maskにov自身(α)を渡して合成
        base.paste(ov, (int(x), int(y)), ov)
    except Exception as e:
        print(f"[WARN] overlay paste failed: {overlay_path} err={e}")

# ==========================
# ★ フェスオーバーレイ適用
# ==========================
def apply_fest_overlays(base, fest_slots):
    """
    フェス枠のスロットだけオーバーレイを貼る
    - now:  x20 y10  w928 h311
    - next: x20 y320 w928 h104
    - next2:x20 y400 w928 h104
    - next3:x20 y480 w928 h104
    - next4:x20 y560 w928 h104
    """
    if not fest_slots or not any(fest_slots.values()):
        return

    # now
    if fest_slots.get("now"):
        paste_overlay_rect(base, FEST_NOW_OVERLAY, 20, 10, 920, 310)
        print(f"[INFO] フェスnowオーバーレイ適用: {FEST_NOW_OVERLAY}")

    # next1~4
    next_rects = {
        "next":  (20, 320, 928, 311),
        "next2": (20, 400, 928, 104),
        "next3": (20, 480, 928, 104),
        "next4": (20, 560, 928, 104),
    }

    for slot, (x, y, w, h) in next_rects.items():
        if fest_slots.get(slot):
            paste_overlay_rect(base, FEST_NEXT_OVERLAY, x, y, w, h)
            print(f"[INFO] フェス{slot}オーバーレイ適用: {FEST_NEXT_OVERLAY}")


# ==========================
# ★ メイン（レイヤー順序 修正版）
#   最下層：通常テンプレ
#   次：フェステンプレ（オーバーレイ）
#   最上層：API出力結果
# ==========================
def main():
    global OUTPUT_PATH

    args = parse_args()
    OUTPUT_PATH = args.output

    out_dir = os.path.dirname(OUTPUT_PATH)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # テンプレ確認
    if not os.path.exists(TEMPLATE_PATH):
        print(f"[ERROR] テンプレートが見つかりません: {TEMPLATE_PATH}")
        return

    print(f"[INFO] ベーステンプレートを使用: {TEMPLATE_PATH}")
    base = Image.open(TEMPLATE_PATH).convert("RGB")

    # ✅ フェス枠（now/next/next2/next3/next4）をスロット別に判定
    fest_slots = check_fest_slots()  # {"now":bool, "next":bool, ...}

    # ✅ ここで先にフェスオーバーレイを貼る（＝フェステンプレを下地にする）
    apply_fest_overlays(base, fest_slots)

    try:
        # regular は常に通常
        render_versus_mode(base, "regular", fetch_schedule(API_URLS["regular"]), fest_slots=None)

        # open/challenge はスロット別に合成して描画
        open_normal = fetch_schedule(API_URLS["open"])
        open_fest   = fetch_schedule(API_URLS["fest_open"])
        chal_normal = fetch_schedule(API_URLS["challenge"])
        chal_fest   = fetch_schedule(API_URLS["fest_challenge"])

        def merge_by_fest_slot(normal_results, fest_results, fest_slots_dict):
            merged = []
            for idx, slot in enumerate(["now", "next", "next2", "next3", "next4"]):
                if fest_slots_dict.get(slot) and idx < len(fest_results):
                    merged.append(fest_results[idx])
                elif idx < len(normal_results):
                    merged.append(normal_results[idx])
                elif idx < len(fest_results):
                    merged.append(fest_results[idx])
                else:
                    merged.append({})
            return merged

        open_merged = merge_by_fest_slot(open_normal, open_fest, fest_slots)
        chal_merged = merge_by_fest_slot(chal_normal, chal_fest, fest_slots)

        render_versus_mode(base, "open", open_merged, fest_slots=fest_slots)
        render_versus_mode(base, "challenge", chal_merged, fest_slots=fest_slots)

        # xmatch / salmon は通常
        render_versus_mode(base, "xmatch", fetch_schedule(API_URLS["xmatch"]), fest_slots=None)
        render_salmon_mode(base, fetch_schedule(API_URLS["salmon"]))

    except Exception as e:
        print(f"[ERR] レンダリングエラー: {e}")

    # ==========================
    # ✅ JSON出力（nowスロットの情報を優先）
    # ==========================
    schedule_json_path = os.getenv("SCHEDULE_JSON", "/tmp/schedule.json")

    # nowスロットがフェスならフェスnow API、そうでなければ通常now API
    if fest_slots.get("now"):
        open_now = fetch_now(API_NOW_URLS["fest_open"])
        chal_now = fetch_now(API_NOW_URLS["fest_challenge"])
    else:
        open_now = fetch_now(API_NOW_URLS["open"])
        chal_now = fetch_now(API_NOW_URLS["challenge"])

    reg_now = fetch_now(API_NOW_URLS["regular"])
    x_now = {} if fest_slots.get("now") else fetch_now(API_NOW_URLS["xmatch"])
    coop_now = fetch_now(API_NOW_URLS["salmon"])

    payload = {
        "updatedHour": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).hour,
        "isFestActive": bool(fest_slots.get("now")),
        "festSlots": fest_slots,

        "regularStages": [s.get("name") for s in (reg_now.get("stages") or [])][:2],

        "openRule": (open_now.get("rule") or {}).get("name", "不明"),
        "openStages": [s.get("name") for s in (open_now.get("stages") or [])][:2],

        "challengeRule": (chal_now.get("rule") or {}).get("name", "不明"),
        "challengeStages": [s.get("name") for s in (chal_now.get("stages") or [])][:2],

        "xRule": (x_now.get("rule") or {}).get("name", "不明"),
        "xStages": [s.get("name") for s in (x_now.get("stages") or [])][:2],

        "salmonStage": (coop_now.get("stage") or {}).get("name", "不明"),
        "salmonWeapons": [w.get("name") for w in (coop_now.get("weapons") or [])][:4],
    }

    with open(schedule_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[INFO] JSON出力完了: {schedule_json_path}")

    base.save(OUTPUT_PATH)
    print(f"[INFO] 画像出力完了: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()



