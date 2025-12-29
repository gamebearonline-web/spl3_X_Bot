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
    
    if isinstance(s, dict) and "updatedHour" in s:
        try:
            hour = int(s.get("updatedHour"))
        except Exception:
            hour = now_jst.hour
    else:
        hour = now_jst.hour
    time_str = f"🗓️{now_jst.year}年{now_jst.month}月{now_jst.day}日　🕛{hour}時更新"
    
    if isinstance(s, dict):
        regular = safe_join(s.get("regularStages", []) or [])
        open_rule = s.get("openRule", "不明")
        open_stages = safe_join(s.get("openStages", []) or [])
        chal_rule = s.get("challengeRule", "不明")
        chal_stages = safe_join(s.get("challengeStages", []) or [])
        x_rule = s.get("xRule", "不明")
        x_stages = safe_join(s.get("xStages", []) or [])
        salmon_stage = s.get("salmonStage", "不明")
        
        return (
            "【スプラ3】スケジュール更新！\n"
            f"{time_str}\n"
            f"🟡レギュラー：{regular}\n"
            f"🟠オープン：{open_rule}：{open_stages}\n"
            f"🟠チャレンジ：{chal_rule}：{chal_stages}\n"
            f"🟢Xマッチ：{x_rule}：{x_stages}\n"
            f"🔶サーモンラン：{salmon_stage}"
        )
    
    return (
        "【スプラ3】スケジュール更新！\n"
        f"{time_str}\n"
        "#スプラ3スケジュール #スプラトゥーン3 #Splatoon3 #サーモンラン"
    )

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
    
    # v1.1認証
    try:
        auth = tweepy.OAuth1UserHandler(
            consumer_key, consumer_secret,
            access_token, access_token_secret
        )
        api = tweepy.API(auth, wait_on_rate_limit=True)
    except Exception as e:
        print("[ERROR] API認証失敗:", repr(e))
        sys.exit(1)
    
    # 画像をv1.1でアップロード
    try:
        media = api.media_upload(filename=image_path)
        media_id = media.media_id_string
        print(f"[INFO] 画像アップロード成功 → media_id={media_id}")
    except Exception as e:
        print("[ERROR] 画像アップロード失敗:", repr(e))
        sys.exit(1)
    
    # v1.1で画像付き投稿（Freeプラン対応）
    try:
        time.sleep(random.uniform(3, 8))
        
        status = api.update_status(
            status=tweet_text,
            media_ids=[media_id]
        )
        
        tweet_id = status.id_str
        print(f"[SUCCESS] 投稿完了！ → https://x.com/i/web/status/{tweet_id}")
        print(f"[INFO] 投稿内容:\n{tweet_text}")
        
    except Exception as e:
        print("[ERROR] 投稿失敗:", repr(e))
        if hasattr(e, "response") and e.response is not None:
            try:
                print("status:", e.response.status_code)
                print("text:", e.response.text)
            except:
                pass
        sys.exit(1)

if __name__ == "__main__":
    main()
