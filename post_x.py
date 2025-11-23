import os
import tweepy
import sys
from datetime import datetime
import pytz

def main():
    # GitHub Secrets / 環境変数から取得
    consumer_key = os.getenv("TWITTER_API_KEY")
    consumer_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("[ERROR] Twitter API credentials が不足しています")
        sys.exit(1)

    # ===== JST 現在時刻 =====
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    time_str = now.strftime("🗓️ %Y年%-m月%-d日　🕛 %-H時更新")

    # ===== 投稿文 =====
    default_text = (
        f"【スプラ3】スケジュール更新！\n"
        f"{time_str}\n"
        f"#スプラ3スケジュール #スプラトゥーン3 #Splatoon3 #サーモンラン"
    )
    tweet_text = os.getenv("TWEET_TEXT", default_text)

    # ===== 画像パス =====
    image_path = os.getenv("IMAGE_PATH", "Thumbnail/Thumbnail.png")
    if not os.path.exists(image_path):
        print(f"[ERROR] 画像ファイルが見つかりません → {image_path}")
        sys.exit(1)

    # ===== v1.1 (画像アップロード) =====
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

    # ===== v2 (投稿) =====
    try:
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )

        response = client.create_tweet(
            text=tweet_text,
            media_ids=[media_id]
        )
        tweet_id = response.data["id"]

        # 正しい投稿URL を作成
        user_info = client.get_me()
        username = user_info.data.username

        print(f"[SUCCESS] 投稿完了 → https://x.com/{username}/status/{tweet_id}")
        print(f"[INFO] 投稿内容:\n{tweet_text}")

    except Exception as e:
        print("[ERROR] ツイート投稿失敗:", repr(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
