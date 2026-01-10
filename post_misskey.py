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
        # 共通で使う値
        open_rule = s.get("openRule", "不明")
        open_stages = safe_join(s.get("openStages", []) or [])
        chal_rule = s.get("challengeRule", "不明")
        chal_stages = safe_join(s.get("challengeStages", []) or [])

        # フェス判定（schedule.json の isFestActive を見る）
        is_fest = bool(s.get("isFestActive"))

        # ✅ フェス時：指定フォーマットに変更
        if is_fest:
            # トリカラ枠：APIに無い場合は空行でもOKなら空にする（必要なら後で追加取得も可能）
            tricolor = safe_join(s.get("tricolorStages", []) or [])  # 無ければ空
            # 「🥳オープン：」「🥳チャレンジ：」はルール等を出したいならここで付ける
            return (
                "【スプラ3】スケジュール更新！\n"
                f"{time_str}\n"
                "【フェス開催中】\n"
                f"🥳オープン：{open_rule}：{open_stages}\n"
                f"🥳チャレンジ：{chal_rule}：{chal_stages}\n"
                f"🎆トリカラ：{tricolor}"
            )

        # ✅ 通常時：これまでのフォーマット
        regular = safe_join(s.get("regularStages", []) or [])
        x_rule = s.get("xRule", "不明")
        x_stages = safe_join(s.get("xStages", []) or [])
        salmon_stage = s.get("salmonStage", "不明")

        return (
            "【スプラ3】スケジュール更新！\n"
            f"{time_str}\n"
            f"🟡レギュラー：{regular}\n"
            f"🟠オープン：{open_rule}：{open_stages}\n"
            f"🟠チャレンジ：{chal_rule}：{chal_stages}\n"
            f"🟢Xマッチ：{x_rule}：{x_stages}\n"
            f"🔶サーモンラン：{salmon_stage}"
        )

    # schedule.json が無い/壊れてる場合
    return (
        "【スプラ3】スケジュール更新！\n"
        f"{time_str}\n"
        "#スプラ3スケジュール #スプラトゥーン3 #Splatoon3 #サーモンラン"
    )
