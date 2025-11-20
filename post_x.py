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
        print("Error: Twitter API credentials が不足しています")
        sys.exit(1)

    # 投稿文章（環境変数で上書き可能）
    base_text = os.getenv("TWEET_TEXT", "【スプラ3】スケジュールが更新されました！")
    tweet_text = f"{base_text}\n{date_str} {hour_str}時 更新"

    # 投稿する画像パス（環境変数で上書き可能）
    image_path = os.getenv("IMAGE_PATH", "Thumbnail/Thumbnail.png")

    if not os.path.exists(image_path):
        print(f"Error: 画像ファイルが見つかりません → {image_path}")
        sys.exit(1)

    # ---- v1.1 API で画像アップロード（v2 の Client ではまだ不安定なため）----
    auth = tweepy.OAuth1UserHandler(
        consumer_key,
        consumer_secret,
        access_token,
        access_token_secret
    )
    api_v1 = tweepy.API(auth)

    try:
        media = api_v1.media_upload(filename=image_path)
        media_id = str(media.media_id)  # 文字列に変換
        print(f"画像アップロード成功: media_id={media_id}")
    except Exception as e:
        print("画像アップロード失敗:", e)
        sys.exit(1)

    # ---- v2 Client でツイート投稿（FreeプランでもOK）----
    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )

    try:
        response = client.create_tweet(
            text=tweet_text,
            media_ids=[media_id]      # これが正しい書き方！
        )
        tweet_id = response.data["id"]
        print(f"ツイート投稿成功！ → https://twitter.com/user/status/{tweet_id}")
        # または x.com で見たい場合は：
        # print(f"https://x.com/user/status/{tweet_id}")
    except Exception as e:
        print("ツイート投稿失敗:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
