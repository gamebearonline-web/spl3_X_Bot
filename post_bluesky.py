# post_bluesky.py (X投稿文と同一フォーマット対応 + Bluesky画像サイズ制限対策)
import os
import sys
import json
import requests
from datetime import datetime
import pytz

from PIL import Image  # ★追加（圧縮用）


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
            # ★トリカラは schedule.json の xRule/xStages を優先
            x_rule = s.get("xRule", "")
            x_stages = s.get("xStages", []) or []

            # 旧仕様（tricolorStages）も保険で拾う
            legacy_tri = s.get("tricolorStages", []) or []

            if (isinstance(x_rule, str) and "トリカラ" in x_rule) and x_stages:
                tricolor = safe_join(x_stages)
            else:
                tricolor = safe_join(legacy_tri)

            tri_line = f"🎆トリカラ：{tricolor}" if tricolor else "🎆トリカラ：-"

            return (
                "【スプラ3】スケジュール更新！\n"
                f"{time_str}\n"
                "【フェス開催中】\n"
                f"🥳オープン：{open_stages}\n"
                f"🥳チャレンジ：{chal_stages}\n"
                f"{tri_line}"
            )

        # ✅ 通常時
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

        return res.json() if res.text else {}

    except Exception as e:
        print(f"[ERROR] Bluesky request 失敗: {url} → {repr(e)}")
        sys.exit(1)


# =========================================================
# ★ 追加：Bluesky画像サイズ制限対策（BlobTooLarge）
#   - 元画像が大きい場合、JPEG化して max_bytes 以下に落とす
#   - 生成したファイルパスと Content-Type を返す
# =========================================================
def ensure_bluesky_upload_image(image_path: str, max_bytes: int = 950 * 1024):
    """
    Returns: (upload_path, content_type)
      - upload_path: 実際にアップロードする画像パス
      - content_type: 'image/png' or 'image/jpeg'
    """
    if not image_path or not os.path.exists(image_path):
        return (image_path, "image/png")

    size = os.path.getsize(image_path)
    print(f"[INFO] Original image size: {size/1024:.2f}KB")

    if size <= max_bytes:
        # 拡張子から Content-Type 推定（基本 png想定）
        ext = os.path.splitext(image_path)[1].lower()
        if ext in (".jpg", ".jpeg"):
            return (image_path, "image/jpeg")
        return (image_path, "image/png")

    # 大きい場合：JPEGに変換して圧縮
    base, _ = os.path.splitext(image_path)
    out_path = base + "_bsky.jpg"

    try:
        img = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"[WARN] PIL open failed; upload original as-is. err={e}")
        return (image_path, "image/png")

    # 品質を下げながら max_bytes を下回るまで試す
    for q in [85, 80, 75, 70, 65, 60, 55]:
        try:
            img.save(out_path, format="JPEG", quality=q, optimize=True, progressive=True)
            new_size = os.path.getsize(out_path)
            print(f"[INFO] Compress try q={q}: {new_size/1024:.2f}KB")
            if new_size <= max_bytes:
                return (out_path, "image/jpeg")
        except Exception as e:
            print(f"[WARN] JPEG save failed q={q}: {e}")

    # どうしても収まらない場合：軽くリサイズして最後に保存
    try:
        w, h = img.size
        img2 = img.resize((int(w * 0.95), int(h * 0.95)))
        img2.save(out_path, format="JPEG", quality=55, optimize=True, progressive=True)
        new_size = os.path.getsize(out_path)
        print(f"[WARN] Forced resize: {new_size/1024:.2f}KB")
        return (out_path, "image/jpeg")
    except Exception as e:
        print(f"[WARN] Forced resize failed; upload original as-is. err={e}")
        return (image_path, "image/png")


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

    # ★追加：Bluesky制限に合わせてアップロード画像を調整
    upload_path, content_type = ensure_bluesky_upload_image(image_path)

    if upload_path and os.path.exists(upload_path):
        print(f"[INFO] 画像アップロード中 → {upload_path} ({content_type})")
        with open(upload_path, "rb") as f:
            img_bytes = f.read()

        upload_res = bluesky_request(
            "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
            headers={
                "Authorization": f"Bearer {access_jwt}",
                "Content-Type": content_type
            },
            data=img_bytes
        )

        blob = upload_res.get("blob")
        if blob:
            print("[INFO] 画像アップロード成功")
        else:
            print("[WARN] 画像アップロード応答に blob がありません（画像なし投稿で続行）")
    else:
        print(f"[WARN] 画像が見つかりません → {upload_path}")

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
