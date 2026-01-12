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

        salmon_stage = s.get("salmonStage", "不明")
        salmon_rank  = s.get("salmonDifficulty", "?")

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
