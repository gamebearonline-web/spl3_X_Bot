# scripts/eval_salmon_difficulty.py
import argparse
import json
import os
from typing import Any, Dict, List, Optional

DEFAULT_TIER_BASE = {"S+": 500, "S": 400, "A": 300, "B": 200, "C": 100}

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, obj: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def is_random_weapon(name: str) -> bool:
    n = (name or "").strip()
    return ("ランダム" in n) or (n.lower() == "random") or ("random" in n.lower())

def is_kuma_weapon(name: str) -> bool:
    n = (name or "").strip()
    # サーモンランのクマ武器表記の揺れに広め対応
    return ("クマサン" in n) or n.startswith("クマ") or ("クマブキ" in n)

def normalize_weapon_name(x: Any) -> Optional[str]:
    """
    schedule.json から武器名を取り出すためのヘルパ。
    想定パターン:
      - "モップリン"
      - {"name":"モップリン"}
      - {"weapon":{"name":"モップリン"}}
      - {"weapon":{"name":{"ja_JP":"モップリン"}}} 等
    """
    if x is None:
        return None
    if isinstance(x, str):
        return x.strip()

    if isinstance(x, dict):
        # 1) {"name": "..."}
        if "name" in x:
            v = x["name"]
            if isinstance(v, str):
                return v.strip()
            if isinstance(v, dict):
                # 多言語オブジェクトを想定
                for k in ("ja_JP", "ja", "jp", "name"):
                    if k in v and isinstance(v[k], str):
                        return v[k].strip()

        # 2) {"weapon": {...}}
        if "weapon" in x and isinstance(x["weapon"], dict):
            return normalize_weapon_name(x["weapon"])

    return None

def extract_salmon_weapons(schedule: Dict[str, Any]) -> List[str]:
    """
    spl3_X_Bot の schedule.json は環境や版で形がブレる可能性があるため、
    いくつかの候補パスから武器配列を探す。
    """
    candidates = []

    # よくあるキーを広めに探索
    # 例: schedule["salmonRun"]["weapons"]
    if isinstance(schedule.get("salmonRun"), dict):
        candidates.append(schedule["salmonRun"].get("weapons"))
        candidates.append(schedule["salmonRun"].get("weaponList"))

    # 例: schedule["salmon"]["weapons"]
    if isinstance(schedule.get("salmon"), dict):
        candidates.append(schedule["salmon"].get("weapons"))

    # 例: schedule["coop"]["weapons"]
    if isinstance(schedule.get("coop"), dict):
        candidates.append(schedule["coop"].get("weapons"))

    weapons_raw = None
    for c in candidates:
        if isinstance(c, list) and len(c) > 0:
            weapons_raw = c
            break

    if not isinstance(weapons_raw, list):
        return []

    out: List[str] = []
    for w in weapons_raw:
        name = normalize_weapon_name(w)
        if name:
            out.append(name)
    return out

def calc_difficulty_rank(weapon_names: List[str], weapon_rank: Dict[str, Any]) -> str:
    if any(is_random_weapon(n) for n in weapon_names):
        return "?"

    kuma_count = sum(1 for n in weapon_names if is_kuma_weapon(n))

    if kuma_count == 4:
        return "SS"
    if kuma_count >= 1:
        return "S"

    # 通常武器4つ
    scores: List[float] = []
    for n in weapon_names:
        info = weapon_rank.get(n)
        if not info or "score" not in info:
            # 未登録が混ざった場合は安全側で ? にする（誤評価防止）
            return "?"
        scores.append(float(info["score"]))

    avg_score = sum(scores) / len(scores)
    min_score = min(scores)
    difficulty_score = 0.6 * avg_score + 0.4 * min_score

    if difficulty_score >= 420:
        return "A"
    if difficulty_score >= 380:
        return "B"
    if difficulty_score >= 340:
        return "C"
    if difficulty_score >= 300:
        return "D"
    return "E"

def patch_schedule(schedule: Dict[str, Any], rank: str) -> Dict[str, Any]:
    # どこからでも読めるようにトップにも入れる（描画側が楽）
    schedule["salmonDifficulty"] = rank

    # salmonRun があればそこにも入れておく
    if isinstance(schedule.get("salmonRun"), dict):
        schedule["salmonRun"]["difficulty"] = rank
    if isinstance(schedule.get("salmon"), dict):
        schedule["salmon"]["difficulty"] = rank
    if isinstance(schedule.get("coop"), dict):
        schedule["coop"]["difficulty"] = rank

    return schedule

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schedule", default=os.getenv("SCHEDULE_JSON", "post-image/schedule.json"))
    ap.add_argument("--weapon-rank", default=os.getenv("WEAPON_RANK_JSON", "data/weapon_rank.json"))
    args = ap.parse_args()

    schedule = load_json(args.schedule)
    weapon_rank = load_json(args.weapon_rank)

    weapons = extract_salmon_weapons(schedule)
    rank = calc_difficulty_rank(weapons, weapon_rank)

    schedule = patch_schedule(schedule, rank)
    save_json(args.schedule, schedule)

    print(f"[OK] salmonDifficulty={rank} weapons={weapons}")

if __name__ == "__main__":
    main()
