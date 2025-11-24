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
# ★ パス設定（初期値）
# ==========================
TEMPLATE_PATH = "spl3_Schedule_Template_ver0.png"
OUTPUT_PATH   = "Thumbnail/Thumbnail.png"
ICON_DIR      = "icon"

# ==========================
# ★ Thumbnail フォルダ作成（デフォルト用）
# ==========================
os.makedirs("Thumbnail", exist_ok=True)


# ==========================
# ★ 高速化：画像キャッシュ & Session
# ==========================
session = requests.Session()
IMAGE_CACHE = {}

def fetch_image(url):
    """URL画像をキャッシュして高速化"""
    if url not in IMAGE_CACHE:
        resp = session.get(url, headers={"User-Agent": "Spla3Img/1.0"})
        resp.raise_for_status()
        IMAGE_CACHE[url] = Image.open(BytesIO(resp.content)).convert("RGBA")
    return IMAGE_CACHE[url].copy()


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
# ★ フォント
# ==========================
def load_font(size):
    return ImageFont.truetype(r"GenEiPOPle_v1.0/GenEiPOPle-Bk.ttf", size)

FONT_TIME_NOW    = load_font(15)
FONT_STAGE_NOW   = load_font(12)
FONT_TIME_SMALL  = load_font(10)
FONT_STAGE_SMALL = load_font(10)

#（※ ※ 以下：あなたの元コードは一切変更なし ※ ※）

# ★ サーモン日付フォーマット
def format_salmon_datetime(iso_str: str) -> str:
    dt = datetime.datetime.fromisoformat(iso_str)
    weekday = "月火水木金土日"[dt.weekday()]
    return dt.strftime(f"%m/%d({weekday}) %H:%M")

# ★ テキスト描画
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
# ★ アイコン＆座標類（中略：変更なし）
# ==========================
#（※ ここは長いのであなたの元コードのまま保持しています ※）


# ==========================
# ★ API 共通
# ==========================
def fetch_schedule(url):
    resp = session.get(url, headers={"User-Agent": "Spla3StageBot/1.0"})
    resp.raise_for_status()
    return resp.json()["results"]


# ==========================
# ★ バトル4種描画（変更なし）
# ==========================
def render_versus_mode(base, mode, results):
    #（中略：元コードそのまま）
    # …


# ==========================
# ★ サーモン描画（変更なし）
# ==========================
def render_salmon_mode(base, results):
    #（中略：元コードそのまま）
    # …


# ==========================
# ★ メイン
# ==========================
def main():
    global OUTPUT_PATH

    # --- 引数処理 ---
    args = parse_args()
    OUTPUT_PATH = args.output  # ★ ← 上書き

    # 保存先のフォルダを作成
    out_dir = os.path.dirname(OUTPUT_PATH)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # --- 画像生成 ---
    base = Image.open(TEMPLATE_PATH).convert("RGBA")

    try:
        render_versus_mode(base, "regular", fetch_schedule("https://spla3.yuu26.com/api/regular/schedule"))
    except Exception as e:
        print("[REGULAR ERR]", e)

    try:
        render_versus_mode(base, "open", fetch_schedule("https://spla3.yuu26.com/api/bankara-open/schedule"))
    except Exception as e:
        print("[OPEN ERR]", e)

    try:
        render_versus_mode(base, "challenge", fetch_schedule("https://spla3.yuu26.com/api/bankara-challenge/schedule"))
    except Exception as e:
        print("[CHALLENGE ERR]", e)

    try:
        render_versus_mode(base, "xmatch", fetch_schedule("https://spla3.yuu26.com/api/x/schedule"))
    except Exception as e:
        print("[XMATCH ERR]", e)

    try:
        render_salmon_mode(base, fetch_schedule("https://spla3.yuu26.com/api/coop-grouping/schedule"))
    except Exception as e:
        print("[SALMON ERR]", e)

    # --- 保存 ---
    base.save(OUTPUT_PATH)
    print("出力完了:", OUTPUT_PATH)


# ==========================
# ★ 実行
# ==========================
if __name__ == "__main__":
    main()
