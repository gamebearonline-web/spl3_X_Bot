import tweepy
import os

def main():
    image_path = "Thumbnail.png"
    text = "【スプラ3】最新ステージ情報"

    if not os.path.exists(image_path):
        print("画像が存在しません:", image_path)
        return

    # --- X(Twitter) API 認証 ---
    consumer_key = os.getenv("TWITTER_API_KEY")
    consumer_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        print("Error: Twitter credentials missing!")
        return

    # v1.1 API（画像アップロード可能な唯一の手段）
    auth = tweepy.OAuth1UserHandler(
        consumer_key,
        consumer_secret,
        access_token,
        access_token_secret
    )
    api = tweepy.API(auth)

    # --- 画像投稿 ---
    media = api.media_upload(image_path)
    api.update_status(status=text, media_ids=[media.media_id_string])

    print("X に投稿しました！")

if __name__ == "__main__":
    main()
