import os
import tweepy
import sys

def main():
    # GitHub Secrets / 環境変数から取得
    consumer_key = os.getenv("TWITTER_API_KEY")
    consumer_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("❌ Error: Missing Twitter API credentials.")
        sys.exit(1)

    # ---- v2 Client（Freeプラン対応の create_tweet 用）----
    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )

    # 投稿文章（環境変数で上書きも可）
    tweet_text = os.getenv("TWEET_TEXT", "【スプラ3】最新ステージ情報！")

    # 投稿する画像パス（環境変数で上書きも可）
    image_path = os.getenv("IMAGE_PATH", "Thumbnail/Thumbnail.png")

    if not os.path.exists(image_path):
        print(f"❌ Error: 画像ファイルが存在しません → {image_path}")
        sys.exit(1)

    # ---- v1.1 API（media_upload のために必要）----
    auth = tweepy.OAuth1UserHandler(
        consumer_key,
        consumer_secret,
        access_token,
        access_token_secret
    )
    api_v1 = tweepy.API(auth)

    # 画像アップロード（v1.1）
    try:
        media = api_v1.media_upload(image_path)
        media_id = media.media_id
        print(f"📸 画像アップロード成功: media_id={media_id}")
    except Exception as e:
        print("❌ 画像アップロード失敗:", e)
        sys.exit(1)

    # ツイート作成（v2）
    try:
        response = client.create_tweet(
            text=tweet_text,
            media={"media_ids": [str(media_id)]}
        )
        tweet_id = response.data["id"]
        print(f"🎉 Success: 画像付きツイート成功 → https://twitter.com/i/web/status/{tweet_id}")
    except Exception as e:
        print("❌ ツイート投稿失敗:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
