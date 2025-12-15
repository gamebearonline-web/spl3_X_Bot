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
FEST_TEMPLATE_PATH = "spl3_Schedule_Template_fest.png"
OUTPUT_PATH   = "Thumbnail/Thumbnail.png"
ICON_DIR      = "icon"

os.makedirs("Thumbnail", exist_ok=True)

# ==========================
# ★ 高速化：Session & Cache
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
# ★ フェス開催中判定
# ==========================
def is_fest_now():
    try:
        resp = session.get(
            "https://spla3.yuu26.com/api/fest/schedule",
            headers={"User-Agent": "Spla3StageBot/1.0"},
            timeout=10,
        )
        data = resp.json()
        results = data.get("results", [])

        if not results:
            return False

        now = datetime.datetime.now(datetime.timezone.utc)

        for fest in results:
            start = datetime.datetime.fromisoformat(fest["start_time"])
            end   = datetime.datetime.fromisoformat(fest["end_time"])
            if start <= now <= end:
                return True

        return False

    except Exception as e:
        print("[FEST CHECK ERR]", e)
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
# ★ フォント
# ==========================
def load_font(size):
    return ImageFont.truetype(
        r"GenEiPOPle_v1.0/GenEiPOPle-Bk.ttf",
        size
    )

FONT_TIME_NOW    = load_font(15)
FONT_STAGE_NOW   = load_font(12)
FONT_TIME_SMALL  = load_font(10)
FONT_STAGE_SMALL = load_font(10)

# ==========================
# ★ サーモン用 日付
# ==========================
def format_salmon_datetime(iso_str):
    dt = datetime.datetime.fromisoformat(iso_str)
    weekday = "月火水木金土日"[dt.weekday()]
    return dt.strftime(f"%m/%d({weekday}) %H:%M")

# ==========================
# ★ テキスト描画
# ==========================
def draw_text_left(draw, box, text, font, bg_fill, text_fill=(0,0,0), padding=2):
    x, y, w, h = box
    bbox = draw.textbbox((0,0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    ty = y + (h - th)/2
    draw.rectangle([x-padding, ty-padding, x+tw+padding, ty+th+padding], fill=bg_fill)
    draw.text((x, ty), text, font=font, fill=text_fill)

def draw_text_with_bg(draw, box, text, font, bg_fill, text_fill=(0,0,0), padding=2):
    x, y, w, h = box
    bbox = draw.textbbox((0,0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    cx = x + (w - tw)/2
    cy = y + (h - th)/2
    draw.rectangle([cx-padding, cy-padding, cx+tw+padding, cy+th+padding], fill=bg_fill)
    draw.text((cx, cy), text, font=font, fill=text_fill)


# ==========================
# ★ API
# ==========================
def fetch_schedule(url):
    resp = session.get(url, headers={"User-Agent": "Spla3StageBot/1.0"})
    resp.raise_for_status()
    return resp.json()["results"]


# ==========================
# ★ バトル描画
# ==========================
def render_versus_mode(base, mode, results):
    draw = ImageDraw.Draw(base)
    color = MODE_COLORS[mode]
    coords_mode = COORDS_TABLE[mode]

    for idx, slot in enumerate(["now","next","next2","next3","next4"]):
        if idx >= len(results) or slot not in coords_mode:
            continue

        info = results[idx]
        cslot = coords_mode[slot]

        st = datetime.datetime.fromisoformat(info["start_time"]).strftime("%H:%M")
        et = datetime.datetime.fromisoformat(info["end_time"]).strftime("%H:%M")
        time_text = f"{st}~{et}"

        font_time  = FONT_TIME_NOW if slot=="now" else FONT_TIME_SMALL
        font_stage = FONT_STAGE_NOW if slot=="now" else FONT_STAGE_SMALL

        if "start_time" in cslot:
            draw_text_with_bg(draw, cslot["start_time"], time_text, font_time, color)

        for i, stg in enumerate(info.get("stages", [])[:2]):
            if f"stage{i}_image" in cslot:
                ix, iy, iw, ih = cslot[f"stage{i}_image"]
                try:
                    img = fetch_image(stg["image"]).resize((int(iw),int(ih)))
                    base.paste(img, (int(ix),int(iy)))
                except:
                    pass

            if f"stage{i}_name" in cslot:
                draw_text_with_bg(draw, cslot[f"stage{i}_name"], stg["name"], font_stage, color)


# ==========================
# ★ サーモン描画
# ==========================
def render_salmon_mode(base, results):
    draw = ImageDraw.Draw(base)
    color = MODE_COLORS["salmon"]
    coords = COORDS_TABLE["salmon"]

    for idx, slot in enumerate(["now","next","next2","next3","next4"]):
        if idx >= len(results):
            continue

        info = results[idx]
        cslot = coords[slot]

        font_time  = FONT_TIME_NOW if slot=="now" else FONT_TIME_SMALL
        font_stage = FONT_STAGE_NOW if slot=="now" else FONT_STAGE_SMALL

        draw_text_left(draw, cslot["start_time"],
                       format_salmon_datetime(info["start_time"]),
                       font_time, color)

        draw_text_left(draw, cslot["end_time"],
                       "~"+format_salmon_datetime(info["end_time"]),
                       font_time, color)

        stage = info.get("stage")
        if stage:
            ix, iy, iw, ih = cslot["stage_image"]
            try:
                img = fetch_image(stage["image"]).resize((int(iw),int(ih)))
                base.paste(img, (int(ix),int(iy)))
            except:
                pass

            draw_text_with_bg(draw, cslot["stage_name"], stage["name"], font_stage, color)


# ==========================
# ★ メイン
# ==========================
def main():
    global OUTPUT_PATH
    args = parse_args()
    OUTPUT_PATH = args.output

    out_dir = os.path.dirname(OUTPUT_PATH)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # ★ フェス背景分岐（ここが目的部分）
    if is_fest_now() and os.path.exists(FEST_TEMPLATE_PATH):
        print("🎉 フェス開催中：フェス背景")
        base = Image.open(FEST_TEMPLATE_PATH).convert("RGBA")
    else:
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
