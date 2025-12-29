import os
import json
import tweepy

API_KEY = os.environ["TWITTER_API_KEY"]
API_SECRET = os.environ["TWITTER_API_SECRET"]
ACCESS_TOKEN = os.environ["TWITTER_ACCESS_TOKEN"]
ACCESS_SECRET = os.environ["TWITTER_ACCESS_SECRET"]

schedule_json = os.environ.get("SCHEDULE_JSON", "")
override = (os.environ.get("POST_TEXT_OVERRIDE", "") or "").strip()

text = override
if not text:
    if schedule_json and os.path.exists(schedule_json):
        with open(schedule_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        text = (data.get("text") or "").strip()

if not text:
    text = "【テスト】X 文字のみ投稿"

auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth)

# ★重要：画像アップロードは一切しない（Cloudflare回避テスト）
api.update_status(status=text)

print("[OK] X 文字のみ投稿 成功")
