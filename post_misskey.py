# post_misskey.py (X投稿文と同一フォーマット対応 + サーモンラン「now枠」難易度ランク対応)
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


# ==============================
# ★追加：ISO日時のパースと、nowに一致するサーモン枠の抽出
# ==============================
def _parse_dt_any(v):
    """
    ISO8601っぽい文字列を datetime にする（Z/オフセット両対応）。
    失敗したら None。
    """
    if not isinstance(v, str) or not v:
        return None
    try:
        s = v.strip()
        # "Z" を +00:00 に変換
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _extract_stage_name(stage_val):
    """
    stage が dict でも str でも拾えるようにする
    """
    if isinstance(stage_val, str):
        return stage_val
    if isinstance(stage_val, dict):
        return (
            stage_val.get("name")
            or stage_val.get("jpName")
            or stage_val.get("nameJP")
            or stage_val.get("nameJa")
            or "不明"
        )
    return "不明"


def pick_current_salmon(s: dict, now_jst: datetime):
    """
    schedule.json 内に複数のサーモン枠がある場合、
    now_jst に一致する枠を選んで (rank, stage) を返す。
    見つからなければ None。
    """
    if not isinstance(s, dict):
        return None

    jst = pytz.timezone("Asia/Tokyo")

    # 候補になりそうなキーを順に探す（生成JSON差を吸収）
    candidates = None
    for key in ("salmonRuns", "salmonRunSchedules", "salmonRun", "salmon", "salmonSchedules"):
        v = s.get(key)
        if isinstance(v, list):
            candidates = v
            break
        if isinstance(v, dict) and isinstance(v.get("nodes"), list):
            candidates = v["nodes"]
            break
        if isinstance(v, dict) and isinstance(v.get("items"), list):
            candidates = v["items"]
            break

    if not candidates:
        return None

    for item in candidates:
        if not isinstance(item, dict):
            continue

        start_raw = item.get("startTime") or item.get("startAt") or item.get("start")
        end_raw = item.get("endTime") or item.get("endAt") or item.get("end")

        start_dt = _parse_dt_any(start_raw)
        end_dt = _parse_dt_any(end_raw)
        if not start_dt or not end_dt:
            continue

        # tzinfo 無しなら UTC 扱い（安全策）
        if start_dt.tzinfo is None:
            start_dt = pytz.UTC.localize(start_dt)
        if end_dt.tzinfo is None:
            end_dt = pytz.UTC.localize(end_dt)

        start_jst = start_dt.astimezone(jst)
        end_jst = end_dt.astimezone(jst)

        if start_jst <= now_jst < end_jst:
            rank = (
                item.get("salmonDifficulty")
                or item.get("difficulty")
                or item.get("grade")
                or item.get("title")
                or item.get("rank")
                or "?"
            )

            stage = (
                item.get("salmonStage")
                or item.get("stage")
                or item.get("stageName")
                or item.get("map")
                or None
            )
            stage = _extract_stage_name(stage)

            return str(rank), str(stage)

    return None


def build_post_text(now_jst: datetime) -> str:
    schedule_json_path = os.getenv("SCHEDULE_JSON", "post-image/schedule.json")
    s = load_schedule_json(schedule_json_path)

    # 更新時刻（schedule.json の updatedHour を優先）
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

        # ✅ サーモン（まずは単一値で拾う）
        salmon_stage = s.get("salmonStage", "不明")
        salmon_rank = s.get("salmonDifficulty", "?")

        # ★ now に一致するサーモン枠が取れるなら、それを優先
        picked = pick_current_salmon(s, now_jst)
        if picked:
            salmon_rank, salmon_stage = picked

        # ✅ フェス時：指定フォーマット
        if is_fest:
            # ★トリカラは schedule.json の xRule/xStages を優先して拾う
            x_rule = s.get("xRule", "")
            x_stages = s.get("xStages", []) or []

            # 旧仕様（tricolorStages）も保険で拾う
            legacy_tri = s.get("tricolorStages", []) or []

            # トリカラ判定：xRule がトリカラ、または legacy がある場合
            if (isinstance(x_rule, str) and "トリカラ" in x_rule) and x_stages:
                tricolor = safe_join(x_stages)
            else:
                tricolor = safe_join(legacy_tri)

            tri_line = f"🎆トリカラ：{tricolor}" if tricolor else "🎆トリカラ：-"

            return (
                f"{time_str}\n"
                "【フェス開催中】\n"
                f"🥳オープン：{open_stages}\n"
                f"🥳チャレンジ：{chal_stages}\n"
                f"{tri_line}\n"
                f"🔶サーモンラン：{salmon_rank}：{salmon_stage}"
            )

        # ✅ 通常時：これまでのフォーマット（サーモンにランク追加）
        regular = safe_join(s.get("regularStages", []) or [])
        x_rule_normal = s.get("xRule", "不明")
        x_stages_normal = safe_join(s.get("xStages", []) or [])

        return (
            f"{time_str}\n"
            f"🟡レギュラー：{regular}\n"
            f"🟠オープン：{open_rule}：{open_stages}\n"
            f"🟠チャレンジ：{chal_rule}：{chal_stages}\n"
            f"🟢Xマッチ：{x_rule_normal}：{x_stages_normal}\n"
            f"🔶サーモンラン：{salmon_rank}：{salmon_stage}"
        )

    # schedule.json が無い/壊れてる場合
    return (
        "【スプラ3】スケジュール更新！\n"
        f"{time_str}\n"
        "#スプラ3スケジュール #スプラトゥーン3 #Splatoon3 #サーモンラン"
    )


def misskey_request(url, method="POST", headers=None, data=None, files=None, json=None):
    try:
        res = requests.request(method, url, headers=headers, data=data, files=files, json=json)
        if res.status_code not in (200, 204):
            print(f"[ERROR] Misskey API error: {url}")
            print(f"status={res.status_code}")
            print(res.text)
            sys.exit(1)
        return res.json() if res.text else {}
    except Exception as e:
        print(f"[ERROR] Misskey request failed: {repr(e)}")
        sys.exit(1)


def post_to_misskey(image_path, text):
    token = os.getenv("MISSKEY_TOKEN")
    if not token:
        print("[ERROR] MISSKEY_TOKEN が設定されていません")
        sys.exit(1)

    # ✅ 他インスタンス対応
    MISSKEY_API = os.getenv("MISSKEY_API", "https://misskey.io/api")

    # ======== ① 画像アップロード ========
    file_id = None
    if image_path and os.path.exists(image_path):
        print(f"[INFO] 画像アップロード中 → {image_path}")

        with open(image_path, "rb") as f:
            # 画像形式は png 前提（jpeg化してる場合は content-type を変えてもOK）
            files = {"file": ("thumbnail.png", f, "image/png")}
            data = {"i": token}

            res = misskey_request(
                f"{MISSKEY_API}/drive/files/create",
                data=data,
                files=files
            )

        file_id = res.get("id")
        print(f"[INFO] Misskey 画像アップロード成功 → file_id={file_id}")
    else:
        print(f"[WARN] 画像ファイルが見つかりません → {image_path}")

    # ======== ② 投稿データ ========
    note = {
        "i": token,
        "text": text,
        "visibility": "public"
    }

    if file_id:
        note["fileIds"] = [file_id]

    # ======== ③ 投稿 ========
    print("[INFO] Misskey に投稿中...")
    post_res = misskey_request(
        f"{MISSKEY_API}/notes/create",
        json=note
    )

    note_id = post_res.get("createdNote", {}).get("id", "")
    print(f"[SUCCESS] Misskey 投稿成功！ note_id={note_id}")

    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.now(jst)
    print("[INFO] 投稿日時(JST):", now.strftime("%Y-%m-%d %H:%M:%S"))
    print("[INFO] 投稿文:\n", text)


def main():
    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.now(jst)

    # ✅ テスト用：TWEET_TEXT があればそれを優先
    text = os.getenv("TWEET_TEXT", "").strip()
    if not text:
        text = build_post_text(now)

    image_path = os.getenv("IMAGE_PATH", "Thumbnail/Thumbnail.png")
    post_to_misskey(image_path, text)


if __name__ == "__main__":
    main()
