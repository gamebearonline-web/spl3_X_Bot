import os
import sys
import json
import tweepy
from datetime import datetime
import pytz


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


def build_tweet_text(now_jst: datetime):
    """
    schedule.json があればそれを使って投稿文生成
    なければ固定文にフォールバック
    """
    # 投稿側ジョブで download-artifact した後の想定パス
    schedule_json_path = os.getenv("SCHEDULE_JSON", "post-image/schedule.json")
    s = load_schedule_json(schedule_json_path)

    # 🗓️2025年12月29日　🕛3時更新
    if isinstance(s, dict) and "updatedHour" in s:
        try:
            hour = int(s.get("updatedHour"))
        except Exception:
            hour = now_jst.hour
    else:
        hour = now_jst.hour

    time_str = f"🗓️{now_jst.year}年{now_jst.month}月{now_jst.day}日　🕛{hour}時更新"

    # JSONが取れた場合：指定フォーマットで作成
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

    # フォールバック（固定文）
    return (
        "【スプラ3】スケジュール更新！\n"
        f"{time_str}\n"
        "#スプラ3スケジュール #スプラトゥーン3 #Splatoon3 #サーモンラン"
    )


def main():
    # ===== 認証情報 =====
    consumer_key = os.getenv("TWITTER_API_KEY")
    consumer_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("[ERROR] Twitter API credentials が不足しています")
        sys.exit(1)

    # ===== JST 現在時刻 =====
    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.now(jst)

    # ===== 投稿文（JSON優先）=====
    default_text = build_tweet_text(now)
    tweet_text = os.getenv("TWEET_TEXT", default_text)

    # ===== 画像パス =====
    # 生成→upload-artifact→download-artifact の構成だとこのパスになりやすい
    image_path = os.getenv("IMAGE_PATH", "post-image/Thumbnail.png")
    if not os.path.exists(image_path):
        print(f"[ERROR] 画像ファイルが見つかりません → {image_path}")
        # デバッグしやすいようにディレクトリを出す
        try:
            print("[DEBUG] カレント:", os.getcwd())
            print("[DEBUG] ls -R:")
            for root, dirs, files in os.walk("."):
                if root.count(os.sep) > 3:
                    continue
                print(root, "dirs=", dirs, "files=", files)
        except Exception:
            pass
        sys.exit(1)

    # ===== v1.1 (画像アップロード & 投稿) =====
    try:
        auth = tweepy.OAuth1UserHandler(
            consumer_key, consumer_secret,
            access_token, access_token_secret
        )
        api_v1 = tweepy.API(auth)

        media = api_v1.media_upload(filename=image_path)
        media_id = str(media.media_id)
        print(f"[INFO] 画像アップロード成功 → media_id={media_id}")

        status = api_v1.update_status(
            status=tweet_text,
            media_ids=[media_id]
        )

        tweet_id = status.id
        username = status.user.screen_name

        print(f"[SUCCESS] 投稿完了 → https://x.com/{username}/status/{tweet_id}")
        print(f"[INFO] 投稿内容:\n{tweet_text}")

    except tweepy.Forbidden as e:
        # 403 duplicate(187) などを拾える場合がある
        print("[ERROR] 投稿失敗(Forbidden):", repr(e))
        if hasattr(e, "api_codes"):
            print("api_codes:", e.api_codes)
        if hasattr(e, "api_messages"):
            print("api_messages:", e.api_messages)
        resp = getattr(e, "response", None)
        if resp is not None:
            try:
                print("status:", getattr(resp, "status_code", None))
                print("text:", getattr(resp, "text", None))
            except Exception:
                pass
        sys.exit(1)

    except Exception as e:
        print("[ERROR] 投稿失敗:", repr(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
