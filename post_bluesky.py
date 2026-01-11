# post_bluesky.py (X投稿文と同一フォーマット対応)
import os
import sys
import json
import requests
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


def build_post_text(now_jst: datetime) -> str:
    schedule_json_path = os.getenv("SCHEDULE_JSON", "post-image/schedule.json")
    s = load_schedule_json(schedule_json_path)

    # updatedHour があればそれを使う（Xと同じ挙動）
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
            x_stages = s.get("xStages", []) or []

            # 旧仕様（tricolorStages）も保険で拾う
            legacy_tri = s.get("tricolorStages", []) or []

            # トリカラ判定：xRule がトリカラ、または legacy がある場合
            if (isinstance(x_rule, str) and "トリカラ" in x_rule) and x_stages:
                tricolor = safe_join(x_stages)
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

        # ✅ 通常時：これまで通り
        regular = safe_join(s.get("regularStages", []) or [])
        x_rule_normal = s.get("xRule", "不明")
        x_stages_normal = safe_join(s.get("xStages", []) or [])
        salmon_stage = s.get("salmonStage", "不明")

        return (
            "【スプラ3】スケジュール更新！\n"
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


def bluesky_request(url, method="POST", headers=None, json=None, data=None):
    try:
        res = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json,
            data=data
        )

        if res.status_code not in (200, 201):
            print(f"[ERROR] Bluesky API error ({url}) → {res.status_code}")
            print(res.text)
            sys.exit(1)

        # uploadBlob は JSON を返すが、稀に空になるケースもあるので保険
        return res.json() if res.text else {}

    except Exception as e:
        print(f"[ERROR] Bluesky request 失敗: {url} → {repr(e)}")
        sys.exit(1)


def post_to_bluesky(image_path, text):
    HANDLE = os.getenv("BSKY_USER")
    PASSWORD = os.getenv("BSKY_PASS")

    if not HANDLE or not PASSWORD:
        print("[ERROR] Bluesky の認証情報が不足しています（BSKY_USER / BSKY_PASS）")
        sys.exit(1)

    # ===== ① ログイン =====
    print("[INFO] Bluesky にログイン中...")
    session = bluesky_request(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": HANDLE, "password": PASSWORD}
    )

    access_jwt = session.get("accessJwt")
    did = session.get("did")

    if not access_jwt or not did:
        print("[ERROR] Bluesky ログイン応答が不正です")
        print(session)
        sys.exit(1)

    print(f"[INFO] ログイン成功: DID = {did}")

    # ===== ② 画像アップロード =====
    blob = None
    if image_path and os.path.exists(image_path):
        print(f"[INFO] 画像アップロード中 → {image_path}")
        with open(image_path, "rb") as f:
            img_bytes = f.read()

        upload_res = bluesky_request(
            "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
            headers={
                "Authorization": f"Bearer {access_jwt}",
                "Content-Type": "image/png"
            },
            data=img_bytes
        )

        blob = upload_res.get("blob")
        if blob:
            print("[INFO] 画像アップロード成功")
        else:
            print("[WARN] 画像アップロード応答に blob がありません（画像なし投稿で続行）")
    else:
        print(f"[WARN] 画像が見つかりません → {image_path}")

    # ===== ③ レコード作成 =====
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "langs": ["ja"],
        "createdAt": datetime.now(pytz.utc).isoformat().replace("+00:00", "Z")
    }

    if blob:
        record["embed"] = {
            "$type": "app.bsky.embed.images",
            "images": [{"image": blob, "alt": "スプラトゥーン3 スケジュール画像"}]
        }

    payload = {
        "repo": did,
        "collection": "app.bsky.feed.post",
        "record": record
    }

    # ===== ④ 投稿 =====
    print("[INFO] Bluesky に投稿中...")
    bluesky_request(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {access_jwt}"},
        json=payload
    )

    print("[SUCCESS] Bluesky 投稿成功！")
    print("[INFO] 投稿文:\n" + text)


def main():
    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.now(jst)

    # ✅ テスト用：TWEET_TEXT があればそれを優先
    text = os.getenv("TWEET_TEXT", "").strip()
    if not text:
        text = build_post_text(now)

    image_path = os.getenv("IMAGE_PATH", "Thumbnail/Thumbnail.png")
    post_to_bluesky(image_path, text)


if __name__ == "__main__":
    main()
