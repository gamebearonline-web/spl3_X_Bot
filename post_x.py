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

    # updatedHour があればそれを使う（従来通り）
    if isinstance(s, dict) and "updatedHour" in s:
        try:
            hour = int(s.get("updatedHour"))
        except Exception:
            hour = now_jst.hour
    else:
        hour = now_jst.hour

    time_str = f"🗓️{now_jst.year}年{now_jst.month}月{now_jst.day}日　🕛{hour}時更新"

    if isinstance(s, dict):
        # ✅ フェス判定（schedule.json の isFestActive）
        is_fest = bool(s.get("isFestActive"))

        # 共通で使う値
        open_rule = s.get("openRule", "不明")
        open_stages = safe_join(s.get("openStages", []) or [])
        chal_rule = s.get("challengeRule", "不明")
        chal_stages = safe_join(s.get("challengeStages", []) or [])

        # ✅ フェス時：指定フォーマット
        if is_fest:
            # ★トリカラは schedule.json の xRule/xStages を優先して拾う（生成側がX欄に入れる仕様に対応）
            x_rule = s.get("xRule", "")
            x_stages_list = s.get("xStages", []) or []

            # 旧仕様（tricolorStages）も保険で拾う
            legacy_tri = s.get("tricolorStages", []) or []

            # トリカラ判定：xRule がトリカラ、または legacy がある場合
            if (isinstance(x_rule, str) and "トリカラ" in x_rule) and x_stages_list:
                tricolor = safe_join(x_stages_list)
            else:
                tricolor = safe_join(legacy_tri)

            # 空のときの表示（好みで変更可）
            tri_line = f"🎆トリカラ：{tricolor}" if tricolor else "🎆トリカラ：-"

            return (
                "【スプラ3】スケジュール更新！\n"
                f"{time_str}\n"
                "【フェス開催中】\n"
                f"🥳オープン：{open_stages}\n"
                f"🥳チャレンジ：{chal_stages}\n"
                f"{tri_line}"
            )

        # ✅ 通常時：従来通り
        regular = safe_join(s.get("regularStages", []) or [])
        x_rule_normal = s.get("xRule", "不明")
        x_stages_normal = safe_join(s.get("xStages", []) or [])
        salmon_stage = s.get("salmonStage", "不明")

        return (
            f"{time_str}\n"
            f"🟡レギュラー：{regular}\n"
            f"🟠オープン：{open_rule}：{open_stages}\n"
            f"🟠チャレンジ：{chal_rule}：{chal_stages}\n"
            f"🟢Xマッチ：{x_rule_normal}：{x_stages_normal}\n"
            f"🔶サーモンラン：{salmon_stage}"
        )

    # schedule.json が無い/壊れている場合の保険
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
            text_preview = getattr(resp, "text", "")[:1000]
            print("text:", text_preview)
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

    # v1.1 で画像アップロード
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

    # v2 で投稿（User-Agent偽装 + 強化ヘッダー）
    try:
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            wait_on_rate_limit=True
        )

        # Cloudflare回避用ヘッダー（ブラウザそっくり）
        client.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

        # 少し待機してボットっぽさを減らす
        time.sleep(random.uniform(4, 10))

        resp = client.create_tweet(text=tweet_text, media_ids=[media_id])
        tweet_id = resp.data["id"] if resp and resp.data else "unknown"
        print(f"[SUCCESS] 投稿完了 → https://x.com/i/web/status/{tweet_id}")
        print(f"[INFO] 投稿内容:\n{tweet_text}")

    except tweepy.Forbidden as e:
        print_forbidden_details(e)
        sys.exit(1)
    except Exception as e:
        print("[ERROR] ツイート投稿失敗:", repr(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
