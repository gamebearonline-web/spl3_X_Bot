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
        print("Error: Twitter API credentials が不足しています")
        sys.exit(1)

    # --------------- 日本時間（JST）で現在時刻を取得 ---------------
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)

    # 例: 2025年11月20日 18時更新
    time_str = now.strftime("🗓️ %Y年%-m月%-d日　🕛 %-H時更新")   # Linux/macOS対応（WindowsでもOK）
    # Windowsで動かす場合は下記のように書くと確実
    # time_str = now.strftime("%Y年%m月%d日 %H時更新").replace(" 0", " ").lstrip("0")

    # デフォルトのツイート文（環境変数で上書き可能）
    default_text = f"【スプラ3】スケジュール更新！\n{time_str}\n#スプラ3スケジュール #スプラトゥーン3 #Splatoon3 #サーモンラン"
    tweet_text = os.getenv("TWEET_TEXT", default_text)

    # 画像パス
    image_path = os.getenv("IMAGE_PATH", "Thumbnail/Thumbnail.png")
    if not os.path.exists(image_path):
        print(f"Error: 画像ファイルが見つかりません → {image_path}")
        sys.exit(1)

    # ---- v1.1 で画像アップロード ----
    auth = tweepy.OAuth1UserHandler(
        consumer_key, consumer_secret,
        access_token, access_token_secret
    )
    api_v1 = tweepy.API(auth)

    try:
        media = api_v1.media_upload(filename=image_path)
        media_id = str(media.media_id)
        print(f"画像アップロード成功: media_id={media_id}")
    except Exception as e:
        print("画像アップロード失敗:", e)
        sys.exit(1)

    # ---- v2 でツイート投稿 ----
    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )

    try:
        response = client.create_tweet(
            text=tweet_text,
            media_ids=[media_id]   # 正しい書き方！
        )
        tweet_id = response.data["id"]
        print(f"ツイート投稿成功！ → https://x.com/anyuser/status/{tweet_id}")
        print(f"投稿内容:\n{tweet_text}")
    except Exception as e:
        print("ツイート投稿失敗:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
