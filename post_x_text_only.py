import os
import json
import tweepy

# ==================================================
# 認証情報
# ==================================================
API_KEY = os.environ["TWITTER_API_KEY"]
API_SECRET = os.environ["TWITTER_API_SECRET"]
ACCESS_TOKEN = os.environ["TWITTER_ACCESS_TOKEN"]
ACCESS_SECRET = os.environ["TWITTER_ACCESS_SECRET"]

SCHEDULE_JSON = os.environ.get("SCHEDULE_JSON", "/tmp/schedule.json")

# ==================================================
# schedule.json 読み込み
# ==================================================
if not os.path.exists(SCHEDULE_JSON):
    raise FileNotFoundError(f"schedule.json not found: {SCHEDULE_JSON}")

with open(SCHEDULE_JSON, "r", encoding="utf-8") as f:
    s = json.load(f)

# ==================================================
# 投稿文組み立て（指定フォーマット）
# ==================================================
time_str = s.get("time_str", "")
regular = s.get("regular", "")
open_rule = s.get("open_rule", "")
open_stages = s.get("open_stages", "")
chal_rule = s.get("chal_rule", "")
chal_stages = s.get("chal_stages", "")
x_rule = s.get("x_rule", "")
x_stages = s.get("x_stages", "")
salmon_stage = s.get("salmon_stage", "")

text = (
    "【スプラ3】スケジュール更新！\n"
    f"{time_str}\n"
    f"🟡レギュラー：{regular}\n"
    f"🟠オープン：{open_rule}：{open_stages}\n"
    f"🟠チャレンジ：{chal_rule}：{chal_stages}\n"
    f"🟢Xマッチ：{x_rule}：{x_stages}\n"
    f"🔶サーモンラン：{salmon_stage}"
)

# ==================================================
# X 投稿（文字のみ）
# ==================================================
auth = tweepy.OAuth1UserHandler(
    API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET
)
api = tweepy.API(auth)

# ★ media_upload は絶対に呼ばない
api.update_status(status=text)

print("[OK] X 文字のみ投稿（スプラ3スケジュール）成功")
