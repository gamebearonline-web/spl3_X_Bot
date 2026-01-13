import os
import sys
import json
import tweepy
from datetime import datetime
import pytz
import time
import random

# ==============================
# ルール短縮（X用）
# ==============================
RULE_SHORT_MAP = {
    "ガチホコバトル": "ホコ",
    "ガチエリア": "エリア",
    "ガチアサリ": "アサリ",
    "ガチヤグラ": "ヤグラ",
}

X_MAX = 280


def safe_join(items):
    return ",".join([x for x in items if x])


def load_schedule_json(path: str):
    if not os.path.exists(path):
        print(f"[WARN] schedule.json が見つかりません: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("[WARN] schedule.json の読み込みに失敗:", repr(e))
        return None


# ==============================
# ★追加：ISO日時のパースと、nowに一致するサーモン枠の抽出
# ==============================
def _parse_dt_any(v):
    """
    ISO8601っぽい文字列を datetime にする（Z/オフセット両対応）。
    失敗したら None。
    """
    if not isinstance(v, str) or not v:
        return None
    try:
        s = v.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _extract_stage_name(stage_val):
    if isinstance(stage_val, str):
        return stage_val
    if isinstance(stage_val, dict):
        return (
            stage_val.get("name")
            or stage_val.get("jpName")
            or stage_val.get("nameJP")
            or stage_val.get("nameJa")
            or "不明"
        )
    return "不明"


def pick_current_salmon(s: dict, now_jst: datetime):
    """
    schedule.json 内に複数のサーモン枠がある場合、
    now_jst に一致する枠を選んで (rank, stage) を返す。
    """
    if not isinstance(s, dict):
        return None

    jst = pytz.timezone("Asia/Tokyo")

    candidates = None
    for key in ("salmonRuns", "salmonRunSchedules", "salmonRun", "salmon", "salmonSchedules"):
        v = s.get(key)
        if isinstance(v, list):
            candidates = v
            break
        if isinstance(v, dict) and isinstance(v.get("nodes"), list):
            candidates = v["nodes"]
            break
        if isinstance(v, dict) and isinstance(v.get("items"), list):
            candidates = v["items"]
            break

    if not candidates:
        return None

    for item in candidates:
        if not isinstance(item, dict):
            continue

        start_raw = item.get("startTime") or item.get("startAt") or item.get("start")
        end_raw = item.get("endTime") or item.get("endAt") or item.get("end")

        start_dt = _parse_dt_any(start_raw)
        end_dt = _parse_dt_any(end_raw)
        if not start_dt or not end_dt:
            continue

        if start_dt.tzinfo is None:
            start_dt = pytz.UTC.localize(start_dt)
        if end_dt.tzinfo is None:
            end_dt = pytz.UTC.localize(end_dt)

        start_jst = start_dt.astimezone(jst)
        end_jst = end_dt.astimezone(jst)

        if start_jst <= now_jst < end_jst:
            rank = (
                item.get("salmonDifficulty")
                or item.get("difficulty")
                or item.get("grade")
                or item.get("title")
                or item.get("rank")
                or "?"
            )

            stage = (
                item.get("salmonStage")
                or item.get("stage")
                or item.get("stageName")
                or item.get("map")
                or None
            )
            stage = _extract_stage_name(stage)

            return str(rank), str(stage)

    return None


# ==============================
# X用：文字列正規化（ルール短縮 + 空白削除）
# ==============================
def normalize_x_text(text: str) -> str:
    if not text:
        return text

    # ① ルール名短縮
    for long, short in RULE_SHORT_MAP.items():
        text = text.replace(long, short)

    # ② 改行以外の無駄空白を削除（各行strip + 全角スペース除去）
    lines = [ln.strip().replace("　", "") for ln in text.split("\n")]

    # ③ 連続する空行を除去
    cleaned = []
    for ln in lines:
        if ln or (cleaned and cleaned[-1]):
            cleaned.append(ln)

    return "\n".join(cleaned)


# ==============================
# X用：長すぎる場合の自動短縮（保険）
# ==============================
def _shorten_stages(text: str) -> str:
    """
    「：A,B」みたいな行を「：A」へ短縮（B以降を落とす）
    """
    lines = text.split("\n")
    out = []
    for ln in lines:
        if "：" in ln:
            head, tail = ln.split("：", 1)
            if "," in tail:
                tail = tail.split(",", 1)[0]
            out.append(head + "：" + tail)
        else:
            out.append(ln)
    return "\n".join(out)


def fit_x_text(text: str, max_len: int = X_MAX) -> str:
    if len(text) <= max_len:
        return text

    lines = text.split("\n")

    # 1) レギュラー行（🟡）を削る
    lines1 = [ln for ln in lines if not ln.startswith("🟡")]
    t = "\n".join(lines1)
    if len(t) <= max_len:
        return t

    # 2) 各行のステージを「2つ→1つ」にする
    t2 = _shorten_stages(t)
    if len(t2) <= max_len:
        return t2

    # 3) ルール部分を落としてステージだけに寄せる
    #    「🟠オープン：ルール：ステージ」→「🟠オープン：ステージ」
    lines2 = []
    for ln in t2.split("\n"):
        parts = ln.split("：")
        if len(parts) >= 3:
            ln = "：".join([parts[0], parts[-1]])
        lines2.append(ln)
    t3 = "\n".join(lines2)
    if len(t3) <= max_len:
        return t3

    # 4) 最後の保険：更新時刻 + サーモンランのみ
    time_line = lines[0] if lines else ""
    salmon = [ln for ln in lines if ln.startswith("🔶")]
    t4 = "\n".join([time_line] + salmon)
    if len(t4) <= max_len:
        return t4

    # 最終手段：末尾切り
    return t4[: max_len - 1] + "…"


def build_tweet_text(now_jst: datetime) -> str:
    schedule_json_path = os.getenv("SCHEDULE_JSON", "post-image/schedule.json")
    s = load_schedule_json(schedule_json_path)

    # updatedHour があればそれを使う
    if isinstance(s, dict) and "updatedHour" in s:
        try:
            hour = int(s.get("updatedHour"))
        except Exception:
            hour = now_jst.hour
    else:
        hour = now_jst.hour

    time_str = f"🗓️{now_jst.year}年{now_jst.month}月{now_jst.day}日　🕛{hour}時更新"

    if isinstance(s, dict):
        # ===== 共通 =====
        is_fest = bool(s.get("isFestActive"))

        open_rule = s.get("openRule", "不明")
        open_stages = safe_join(s.get("openStages", []) or [])
        chal_rule = s.get("challengeRule", "不明")
        chal_stages = safe_join(s.get("challengeStages", []) or [])

        # サーモン（まずは単一値で拾う）
        salmon_stage = s.get("salmonStage", "不明")
        salmon_rank = s.get("salmonDifficulty", "?")

        # ★ now に一致するサーモン枠が取れるなら、それを優先
        picked = pick_current_salmon(s, now_jst)
        if picked:
            salmon_rank, salmon_stage = picked

        # ===== フェス時 =====
        if is_fest:
            x_rule = s.get("xRule", "")
            x_stages_list = s.get("xStages", []) or []
            legacy_tri = s.get("tricolorStages", []) or []

            if (isinstance(x_rule, str) and "トリカラ" in x_rule) and x_stages_list:
                tricolor = safe_join(x_stages_list)
            else:
                tricolor = safe_join(legacy_tri)

            tri_line = f"🎆トリカラ：{tricolor}" if tricolor else "🎆トリカラ：-"

            return (
                f"{time_str}\n"
                "【フェス開催中】\n"
                f"🥳オープン：{open_stages}\n"
                f"🥳チャレンジ：{chal_stages}\n"
                f"{tri_line}\n"
                f"🔶サーモンラン：{salmon_rank}：{salmon_stage}"
            )

        # ===== 通常時 =====
        regular = safe_join(s.get("regularStages", []) or [])
        x_rule_normal = s.get("xRule", "不明")
        x_stages_normal = safe_join(s.get("xStages", []) or [])

        return (
            f"{time_str}\n"
            f"🟡レギュラー：{regular}\n"
            f"🟠オープン：{open_rule}：{open_stages}\n"
            f"🟠チャレンジ：{chal_rule}：{chal_stages}\n"
            f"🟢Xマッチ：{x_rule_normal}：{x_stages_normal}\n"
            f"🔶サーモンラン：{salmon_rank}：{salmon_stage}"
        )

    # 保険
    return (
        "【スプラ3】スケジュール更新！\n"
        f"{time_str}\n"
        "#スプラ3スケジュール #スプラトゥーン3 #Splatoon3 #サーモンラン"
    )


def print_forbidden_details(e: Exception):
    print("[ERROR] Forbidden:", repr(e))
    if hasattr(e, "api_codes"):
        print("api_codes:", getattr(e, "api_codes"))
    if hasattr(e, "api_messages"):
        print("api_messages:", getattr(e, "api_messages"))
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            print("status:", getattr(resp, "status_code", None))
            print("text:", getattr(resp, "text", "")[:1000])
        except Exception:
            pass


def main():
    consumer_key = os.getenv("TWITTER_API_KEY")
    consumer_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("[ERROR] Twitter API credentials が不足しています")
        sys.exit(1)

    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.now(jst)

    tweet_text = os.getenv("TWEET_TEXT", build_tweet_text(now))

    # ★ X用の整形（ルール短縮 + 空白削除 → 280超え対策）
    tweet_text = normalize_x_text(tweet_text)
    tweet_text = fit_x_text(tweet_text)

    image_path = os.getenv("IMAGE_PATH", "post-image/Thumbnail.png")
    if not os.path.exists(image_path):
        print(f"[ERROR] 画像ファイルが見つかりません → {image_path}")
        sys.exit(1)

    # v1.1 画像アップロード
    try:
        auth = tweepy.OAuth1UserHandler(
            consumer_key, consumer_secret,
            access_token, access_token_secret
        )
        api_v1 = tweepy.API(auth)
        media = api_v1.media_upload(filename=image_path)
        media_id = str(media.media_id)
        print(f"[INFO] 画像アップロード成功 → media_id={media_id}")
    except Exception as e:
        print("[ERROR] 画像アップロード失敗:", repr(e))
        sys.exit(1)

    # v2 投稿
    try:
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            wait_on_rate_limit=True
        )

        # Cloudflare/UA系の回避策（必要なら維持）
        client.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Accept-Language": "ja-JP,ja;q=0.9",
        })

        time.sleep(random.uniform(4, 10))
        resp = client.create_tweet(text=tweet_text, media_ids=[media_id])
        tweet_id = resp.data["id"] if resp and resp.data else "unknown"
        print(f"[SUCCESS] 投稿完了 → https://x.com/i/web/status/{tweet_id}")
        print(tweet_text)

    except tweepy.Forbidden as e:
        print_forbidden_details(e)
        sys.exit(1)
    except Exception as e:
        print("[ERROR] ツイート投稿失敗:", repr(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
