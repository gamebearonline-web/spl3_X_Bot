import argparse
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import datetime
import os

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
OUTPUT_PATH   = "Thumbnail/Thumbnail.png"
ICON_DIR      = "icon"

os.makedirs("Thumbnail", exist_ok=True)

# ==========================
# ★ 高速化：画像キャッシュ & Session
# ==========================
session = requests.Session()
IMAGE_CACHE = {}

def fetch_image(url):
    if url not in IMAGE_CACHE:
        resp = session.get(url, headers={"User-Agent": "Spla3Img/1.0"})
        resp.raise_for_status()
        IMAGE_CACHE[url] = Image.open(BytesIO(resp.content)).convert("RGBA")
    return IMAGE_CACHE[url].copy()

# ==========================
# ★ フェス開催中判定（slot単位）
# ==========================
def is_fest_active_slot(start_time, end_time):
    """
    slot が現在時刻にかかっていれば True
    """
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        start = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end   = datetime.datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        return start <= now <= end
    except Exception:
        return False




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

# challenge は X軸 -22px
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

# xmatch は X軸 -19px
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

# salmon（start_time / end_time / stage / weapon0~3）
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
    """ビッグランの場合に big_run.png を描画"""
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
# ★ サーモン武器（高速化版）
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
            img = fetch_image(weapons[i]["image"])
            img = img.resize(size)
            base.paste(img, (int(wx), int(wy)), img)
        except Exception:
            pass


# ==========================
# ★ API 共通（Session使用）
# ==========================
def fetch_schedule(url):
    resp = session.get(url, headers={"User-Agent": "Spla3StageBot/1.0"})
    resp.raise_for_status()
    return resp.json()["results"]


# ==========================
# ★ バトル（regular / open / challenge / xmatch）
# ==========================
def render_versus_mode(base, mode, results):
    coords_mode = COORDS_TABLE[mode]
    draw = ImageDraw.Draw(base)

    for idx, slot in enumerate(["now", "next", "next2", "next3", "next4"]):
        if slot not in coords_mode or idx >= len(results):
            continue

        info  = results[idx]
        cslot = coords_mode[slot]

        # ----------------------------
        # 時刻判定（この slot が今か？）
        # ----------------------------
        start = datetime.datetime.fromisoformat(info["start_time"].replace("Z", "+00:00"))
        end   = datetime.datetime.fromisoformat(info["end_time"].replace("Z", "+00:00"))
        now   = datetime.datetime.now(datetime.timezone.utc)

        is_now_slot = start <= now < end

        # ----------------------------
        # フェス slot 判定（超重要）
        # ----------------------------
        is_fest_slot = (
            is_now_slot and
            info.get("is_fest", False)   # ← フェス schedule のみ True
        )

        # ----------------------------
        # 背景色決定
        # ----------------------------
        if is_fest_slot:
            if mode in ("open", "challenge"):
                bg_color = "#e8d526"
            elif mode == "xmatch":
                bg_color = "#664dde"
            else:
                bg_color = MODE_COLORS[mode]
        else:
            bg_color = MODE_COLORS[mode]

        # ----------------------------
        # 表示用フォント
        # ----------------------------
        if slot == "now":
            font_time  = FONT_TIME_NOW
            font_stage = FONT_STAGE_NOW
        else:
            font_time  = FONT_TIME_SMALL
            font_stage = FONT_STAGE_SMALL

        # ----------------------------
        # 時刻表示
        # ----------------------------
        if "start_time" in cslot:
            time_text = f"{start.strftime('%H:%M')}~{end.strftime('%H:%M')}"
            draw_text_with_bg(
                draw,
                cslot["start_time"],
                time_text,
                font_time,
                bg_fill=bg_color,
            )

        # ----------------------------
        # ステージ描画
        # ----------------------------
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
                draw_text_with_bg(
                    draw,
                    cslot[f"stage{i}_name"],
                    stg["name"],
                    font_stage,
                    bg_fill=bg_color,
                )

        # ----------------------------
        # ルールアイコン
        # ----------------------------
        rule_key = info.get("rule", {}).get("key")
        draw_rule_icon(base, mode, slot, rule_key)




# ==========================
# ★ サーモンラン（ビッグラン対応）
# ==========================
def render_salmon_mode(base, results):
    coords_mode = COORDS_TABLE["salmon"]
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

        if slot == "now":
            font_time  = FONT_TIME_NOW
            font_stage = FONT_STAGE_NOW
        else:
            font_time  = FONT_TIME_SMALL
            font_stage = FONT_STAGE_SMALL

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
# ★ メイン
# ==========================
def main():
    global OUTPUT_PATH

    args = parse_args()
    OUTPUT_PATH = args.output

    out_dir = os.path.dirname(OUTPUT_PATH)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # ★ 背景は常に通常テンプレ
    base = Image.open(TEMPLATE_PATH).convert("RGBA")

    
    try:
        render_versus_mode(base, "regular", fetch_schedule("https://spla3.yuu26.com/api/regular/schedule"))
        render_versus_mode(base, "open", fetch_schedule("https://spla3.yuu26.com/api/bankara-open/schedule"))
        render_versus_mode(base, "challenge", fetch_schedule("https://spla3.yuu26.com/api/bankara-challenge/schedule"))
        render_versus_mode(base, "xmatch", fetch_schedule("https://spla3.yuu26.com/api/x/schedule"))
        render_salmon_mode(base, fetch_schedule("https://spla3.yuu26.com/api/coop-grouping/schedule"))
    except Exception as e:
        print("[ERR]", e)

    base.save(OUTPUT_PATH)
    print("出力完了:", OUTPUT_PATH)


if __name__ == "__main__":
    main()








