import os
import sys
import json
import tweepy
from datetime import datetime
import pytz
import time
import random

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
        # "Z" を +00:00 に変換
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None

def _extract_stage_name(stage_val):
    """
    stage が dict でも str でも拾えるようにする
    """
    if isinstance(stage_val, str):
        return stage_val
    if isinstance(stage_val, dict):
        # ありがちなキー候補
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
    見つからなければ None。
    """
    if not isinstance(s, dict):
        return None

    jst = pytz.timezone("Asia/Tokyo")

    # 候補になりそうなキーを順に探す（生成JSON差を吸収）
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
        end_raw   = item.get("endTime")   or item.get("endAt")   or item.get("end")

        start_dt = _parse_dt_any(start_raw)
        end_dt   = _parse_dt_any(end_raw)
        if not start_dt or not end_dt:
            continue

        # tzinfo 無しなら UTC 扱い（安全策）
        if start_dt.tzinfo is None:
            start_dt = pytz.UTC.localize(start_dt)
        if end_dt.tzinfo is None:
            end_dt = pytz.UTC.localize(end_dt)

        start_jst = start_dt.astimezone(jst)
        end_jst   = end_dt.astimezone(jst)

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

        open_rule   = s.get("openRule", "不明")
        open_stages = safe_join(s.get("openStages", []) or [])
        chal_rule   = s.get("challengeRule", "不明")
        chal_stages = safe_join(s.get("challengeStages", []) or [])

        # まずは単一値（従来）で拾う
        salmon_stage = s.get("salmonStage", "不明")
        salmon_rank  = s.get("salmonDifficulty", "?")

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
