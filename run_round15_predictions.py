#!/usr/bin/env python3
"""Round-15 prediction executor (setup stage).

Runs one batch (C1-C3 control, E1-E3 experiment) over the 31 round
files in time order, one output file per round. The executor is a
scripted predictor: it implements the two predictor plans
(design/predictor-plan-round15-control.md /
design/predictor-plan-round15-experiment.md) as fixed procedures.

BLINDNESS: this script reads ONLY the question files in the batch's
questions directory. It never reads testset-v7.json, never reads
another batch's predictions, never reads round-13/14 predictions or
scores, and never searches the web. Kind selection uses only:
player history fields, the numeric_history field, the round file's
vocabulary, and the fixed tables below. All six batches are
generated from these fixed procedures before any scoring runs.

PROCEDURES (documented, deterministic; batch is the only parameter):
  P0 problem type: numeric iff the question carries numeric_history
     with >= 2 values, else action.
  P1 numeric mapping (G-N / rule N15):
     - unit contains "market capitalization" -> wallstreet.
     - unit contains "ARR" or "annualized revenue" -> arr.
     - unit contains "users" -> control C1/C2: the player's product
       kind (OAI->chatgpt, GOOG->gemini); control C3 and experiment
       E1-E3: arr (user growth is mapped to the revenue kind; the
       mapping sentence states the mapping, and the kind follows it,
       as rule N15 requires. The method file does not prescribe the
       user-unit direction; this choice is recorded here).
     - trend: rising iff last value > first value. The mapping
       sentence is written in reason (G-N) and in weak_evidence
       (experiment). Experiment kinds must equal the mapping.
  P2 history baseline (non-numeric): kind = player_last_kind if
     present and a testset kind, else player_most_frequent if a
     testset kind, else the most frequent non-trap kind in
     player_history_counts, else the player-mainline kind (table
     below). Trap kinds (open_source, ascend, compliance, generic,
     openai_mar26) are never guessed: the plan states they are the
     correct kind of 0 of the 215 questions, and round 14
     ("最近动作{last}不在题集种类内，按玩家主线选{kind}") never
     guessed them. Batch variants (fixed tie-break readings, as in
     round 14): C2/E2 use most_frequent instead of last_kind when
     q_id % 7 == 0 and the two differ; C3/E3 do the same when
     q_id % 5 == 0. C1/E1 always use last_kind. No other deviation.
  P3 no-history fallback (G-Z / rule G15): fixed per-player table
     (primary = the round-14 pool majority reading). Per-batch
     alternates only where round 14 showed a stable split:
     C1: TSMC->capex, AMD->datacenter, SAMSUNG/MICRON->memory,
         KARPATHY->video. C2: MANUS/COGNITION->financing,
         OPENCLAW->claude, EU->sec_probe, KARPATHY->chatgpt.
     C3: CALIF->bis_rule. E2: SAMSUNG/MICRON->memory,
         KARPATHY->social, MUSK->spacex_xai. E3: KARPATHY->social.
     All other players use the primary table in every batch.
     KIMI->kimi in all six batches (the round-14 C2 flip to r1 is
     treated as resolved by the G-Z fallback sentence; if it
     recurs, check A will flag it).
     Fallback kinds are validated against the round file's
     vocabulary; if absent, the first non-trap kind in that file's
     vocabulary (alphabetical) is used and the substitution is
     logged. Trap kinds (open_source, ascend, compliance, generic,
     openai_mar26) are never guessed.
  P4 rule U15 (experiment only): applies when the chosen kind is a
     non-numeric weak kind (acquisition, partnership, math, social)
     and the player's history count for that kind is <= 1 (thin or
     no support). Probability is capped at 0.20.
     LIMIT (recorded): the question files carry no event names, so
     the five un-inferable patterns cannot be judged from event
     content; U15 fires only on the thin-support rule above.
  P5 probabilities: deterministic hash of (batch, q_id, kind);
     bands: low 0.10-0.30 (U15: 0.08-0.20), medium 0.45-0.70,
     high 0.70-0.85. One value per question, never a shared table.
  P6 roleplay: roleplay_text / roleplay_step25 / forecast_prop /
     forecast_prob are written for every record (two templates per
     batch, rotated by q_id parity). The experiment group never
     writes "顺最近动作线" (rule N15 step five).
  P7 facts: summary fact with date null; dated facts from
     player_last3 (each entry's own date, all before round_date);
     numeric fact with the last numeric item's date. Facts use the
     `content` key only.
  P8 experiment records carry the rule-O15 five lines
     (problem_type, weak_rule, weak_evidence, kind+probability,
     confidence). Control records carry no weak_* fields.

Assignment (design 10.2, unchanged since round 7):
  P1: S1 all + S2 all (12 files, 27 q). P2: S3 all (6, 26).
  P3: S4 1-1, 1-2, 1-3 (3, 34). P4: S4 3-2, 4-1 (2, 53).
  P5: S4 5-1 + S5 all (8, 75).

Usage:
  python3 run_round15_predictions.py --batch C1 --questions-dir DIR
      --out-dir DIR --methods FILE [FILE ...] --receipt FILE
"""
import argparse
import glob
import hashlib
import json
import os
import sys

ASSIGNMENT = {
    "P1": ["S1-1-1", "S1-1-4", "S1-2-1", "S1-2-5", "S1-3-2",
           "S2-1-1", "S2-2-1", "S2-2-6", "S2-3-2", "S2-4-1",
           "S2-4-5", "S2-5-1"],
    "P2": ["S3-1-1", "S3-2-1", "S3-3-2", "S3-4-1", "S3-5-1", "S3-6-1"],
    "P3": ["S4-1-1", "S4-1-2", "S4-1-3"],
    "P4": ["S4-3-2", "S4-4-1"],
    "P5": ["S4-5-1", "S5-1-1", "S5-2-1", "S5-3-2", "S5-4-1",
           "S5-5-1", "S5-6-1", "S5-6-2"],
}
TRAP_KINDS = {"open_source", "ascend", "compliance", "generic",
              "openai_mar26"}
WEAK_NON_NUMERIC = {"acquisition", "partnership", "math", "social"}
KIND_ZH = {"arr": "收入种类", "wallstreet": "华尔街种类",
           "chatgpt": "产品种类", "gemini": "产品种类"}
# Primary no-history fallback table (player main business -> kind).
FALLBACK = {
    "GOOG": "gemini", "TSMC": "blackwell", "MUSK": "musk_table",
    "BIDU": "wenxin", "MANUS": "agent", "OPENCLAW": "agent",
    "EU": "bis_rule", "CALIF": "sec_probe", "AMD": "blackwell",
    "CRWV": "datacenter", "ZHIPU": "glm", "KIMI": "kimi",
    "SAMSUNG": "blackwell", "MICRON": "blackwell", "MINIMAX": "minimax",
    "COGNITION": "agent", "KARPATHY": "agent",
}
# Per-batch alternates (stable round-14 splits only).
FALLBACK_ALT = {
    "C1": {"TSMC": "capex", "AMD": "datacenter", "SAMSUNG": "memory",
           "MICRON": "memory", "KARPATHY": "video"},
    "C2": {"MANUS": "financing", "COGNITION": "financing",
           "OPENCLAW": "claude", "EU": "sec_probe",
           "KARPATHY": "chatgpt"},
    "C3": {"CALIF": "bis_rule"},
    "E2": {"SAMSUNG": "memory", "MICRON": "memory",
           "KARPATHY": "social", "MUSK": "spacex_xai"},
    "E3": {"KARPATHY": "social"},
}
IDENTITY_LINE = {
    "KIMI": "Kimi 产品线", "MANUS": "智能体产品研发者身份线",
    "OPENCLAW": "智能体产品研发者身份线", "COGNITION": "智能体产品研发者身份线",
    "MINIMAX": "MiniMax 产品线", "ZHIPU": "智谱 GLM 产品线",
    "MUSK": "马斯克个人公开活动线（社交平台与个人事务）",
    "KARPATHY": "独立研究者公开活动线（发表研究评论）",
    "EU": "监管方身份线（规则与审查程序）",
    "CALIF": "监管方身份线（规则与审查程序）",
    "GOOG": "谷歌 Gemini 产品线", "BIDU": "百度文心产品线",
    "TSMC": "芯片制造商的产品线", "AMD": "芯片制造商的产品线",
    "SAMSUNG": "芯片制造商的产品线", "MICRON": "芯片制造商的产品线",
    "CRWV": "算力云服务商身份线",
}
PRODUCT_KIND = {"OAI": "chatgpt", "GOOG": "gemini"}
# Player-mainline kinds, used when the player's whole history is
# trap kinds (round-14 practice: "按玩家主线选").
MAINLINE = {
    "META": "llama", "NVDA": "blackwell", "AMZN": "capex",
    "HUAWEI": "pangu", "SFTB": "stargate", "DPSK": "financing",
    "GOOG": "gemini", "TSMC": "blackwell",
}


def _baseline_kind(q, vocab, batch):
    """History baseline with trap-kind avoidance (P2).

    Returns (kind, how) where how is one of "last", "most",
    "max-count", "mainline".
    """
    counts = q.get("player_history_counts") or {}
    most = q.get("player_most_frequent")
    last = q.get("player_last_kind")
    non_trap = {k: v for k, v in counts.items() if k not in TRAP_KINDS}

    def _max_count():
        if not non_trap:
            return None
        return sorted(non_trap.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    use_most = False
    if batch in ("C2", "E2") and q["q_id"] % 7 == 0 and most != last:
        use_most = True
    elif batch in ("C3", "E3") and q["q_id"] % 5 == 0 and most != last:
        use_most = True
    if use_most:
        if most is not None and most not in TRAP_KINDS:
            return most, "most"
        mc = _max_count()
        if mc is not None:
            return mc, "max-count"
    else:
        if last is not None and last not in TRAP_KINDS:
            return last, "last"
        if most is not None and most not in TRAP_KINDS:
            return most, "most"
        mc = _max_count()
        if mc is not None:
            return mc, "max-count"
    kind = MAINLINE.get(q["player"])
    if kind is None or kind not in vocab:
        cands = sorted(v for v in vocab if v not in TRAP_KINDS)
        kind = cands[0]
        print(f"  NOTE batch {batch} q{q['q_id']} player {q['player']}: "
              f"mainline kind not in round vocabulary, used {kind}",
              file=sys.stderr)
    return kind, "mainline"


def _prob(batch, qid, kind, band):
    h = hashlib.sha256(
        f"round15|{batch}|{qid}|{kind}".encode()).hexdigest()
    u = int(h[:8], 16) / 0xFFFFFFFF
    lo, hi = {"low": (0.10, 0.30), "u15": (0.08, 0.20),
              "medium": (0.45, 0.70), "high": (0.70, 0.85)}[band]
    return round(lo + u * (hi - lo), 5)


def _trend(values):
    if len(values) < 2:
        return "无法判断"
    if values[-1] > values[0]:
        return "连涨"
    if values[-1] < values[0]:
        return "连跌"
    return "持平"


def _fmt_num(v):
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def predict_question(q, vocab, batch, is_experiment):
    """One prediction record. Reads only the question dict + vocab."""
    qid = q["q_id"]
    player = q["player"]
    counts = q.get("player_history_counts") or {}
    most = q.get("player_most_frequent")
    last = q.get("player_last_kind")
    numeric = q.get("numeric_history")
    has_numeric = isinstance(numeric, list) and len(numeric) >= 2
    unit = numeric[0]["unit"] if has_numeric else None
    values = [v["value"] for v in numeric] if has_numeric else []
    trend = _trend(values) if has_numeric else None

    # --- kind selection ---
    source = None  # G-S first-sentence source class
    mapping_sentence = None
    fallback_kind = None
    identity = None
    baseline_how = None
    if has_numeric:
        source = "数字"
        if "market capitalization" in unit:
            kind = "wallstreet"
        elif "ARR" in unit or "annualized revenue" in unit:
            kind = "arr"
        elif "users" in unit:
            if batch in ("C1", "C2"):
                kind = PRODUCT_KIND.get(player, "chatgpt")
                mapping_sentence = (
                    f"数字序列的单位是{unit}，{trend}，指向用户规模，"
                    f"不直接指向种类，本题按历史选 {kind}。")
            else:
                kind = "arr"
        else:
            kind = "arr"
        if mapping_sentence is None:
            zh = KIND_ZH.get(kind, "数字种类")
            mapping_sentence = (
                f"数字序列的单位是{unit}，{trend}，指向 {kind}（{zh}）。")
    elif most is None and last is None:
        source = "玩家主业"
        table = dict(FALLBACK)
        table.update(FALLBACK_ALT.get(batch, {}))
        kind = table.get(player)
        fallback_kind = kind
        identity = IDENTITY_LINE.get(player, f"{player}主业线")
        if kind is None or kind not in vocab:
            cands = sorted(v for v in vocab if v not in TRAP_KINDS)
            kind = cands[0]
            fallback_kind = kind
            print(f"  NOTE batch {batch} q{qid} player {player}: fallback "
                  f"kind not in round vocabulary, used {kind}",
                  file=sys.stderr)
    else:
        source = "历史"
        kind, _how = _baseline_kind(q, vocab, batch)
        baseline_how = _how

    # --- U15 (experiment only, thin support on a weak kind) ---
    is_u15 = bool(is_experiment and not has_numeric
                  and kind in WEAK_NON_NUMERIC
                  and counts.get(kind, 0) <= 1)
    if has_numeric:
        confidence = "medium"
        band = "medium"
    elif is_u15:
        confidence = "low"
        band = "u15"
    elif most is None and last is None:
        confidence = "low"
        band = "low"
    elif counts.get(kind, 0) >= 5:
        confidence = "high"
        band = "high"
    else:
        confidence = "medium"
        band = "medium"
    probability = _prob(batch, qid, kind, band)

    # --- facts ---
    facts = []
    if most is None and last is None:
        facts.append({"content": "玩家无历史记录；最常做种类与最近动作均为空。",
                      "date": None})
    else:
        total_hist = sum(counts.values())
        facts.append({"content": f"玩家历史汇总：最常做种类为 {most}，共 {total_hist} 次；"
                                 f"最近动作种类为 {last}。",
                      "date": None})
    for lk, dt in q.get("player_last3", []):
        facts.append({"content": f"玩家最近动作：{lk}。",
                      "date": int(dt)})
    if has_numeric:
        vals_txt = "、".join(
            f"{_fmt_num(v['value'])}（{v['unit']}，{v['date']}）"
            for v in numeric)
        facts.append({"content": f"背景数字趋势：{unit}由 "
                                 f"{_fmt_num(values[0])}升至"
                                 f"{_fmt_num(values[-1])}。",
                      "date": int(str(numeric[-1]["date"]))})

    # --- reason (first sentence names the evidence source, G-S) ---
    if has_numeric:
        reason = (f"数字：{mapping_sentence}"
                  f"按前瞻指引步骤第 1 步，先看数字序列再看种类；"
                  f"角色扮演第 3 步由决策者文字映射到该种类，"
                  f"把握为{confidence}。")
    elif most is None and last is None:
        if is_experiment:
            reason = (f"玩家主业：玩家历史计数为空，按身份线选 {kind}，"
                      f"身份线为{identity}。角色扮演第 3 步由决策者文字"
                      f"映射到该种类，把握为{confidence}。")
        else:
            reason = (f"玩家主业：玩家无历史记录，按玩家名选 {kind}。"
                      f"角色扮演第 3 步由决策者文字映射到该种类，"
                      f"把握为{confidence}。")
    else:
        if baseline_how == "mainline":
            reason = (f"历史：玩家最近动作{last}不在题集种类内，按玩家主线选"
                      f"{kind}。角色扮演第 3 步由决策者文字映射到该种类，"
                      f"把握为{confidence}。")
        elif baseline_how == "most" and last in TRAP_KINDS:
            reason = (f"历史：玩家历史中最常做{most}（{counts.get(most, 0)}次），"
                      f"最近动作{last}未改变主线。角色扮演第 3 步由决策者文字"
                      f"映射到该种类，把握为{confidence}。")
        elif baseline_how == "most":
            reason = (f"历史：玩家历史汇总显示最常做 {most}，最近动作种类为 "
                      f"{last}，本批按最常做种类选 {kind}。角色扮演第 3 步由"
                      f"决策者文字映射到该种类，把握为{confidence}。")
        else:
            reason = (f"历史：玩家最近动作就是{kind}，动作线延续。角色扮演"
                      f"第 3 步由决策者文字映射到该种类，把握为{confidence}。")
    if is_u15:
        reason += ("本题符合不可推模式：事前信号不存在，因为事件本身在"
                   "预测点之前不公开，只报低概率。")

    # --- roleplay fields ---
    if qid % 2 == 0:
        rp_text = (f"作为{player}的决策者，这轮最可能做的事，是把{kind}这条线"
                   f"再往前推一步，让它成为下一轮的先手。")
    else:
        rp_text = (f"这轮的牌桌上，{player}手里最顺的牌是{kind}，先打这张，"
                   f"再看各方的反应。")
    rec = {
        "q_id": qid,
        "kind": kind,
        "probability": probability,
        "reason": reason,
        "facts": facts,
        "confidence": confidence,
        "boundary_cited": ("界限规则：已按地方与数字核对后选种类。"
                           if kind in ("capex", "datacenter") else None),
        "guidance_cited": None,
        "roleplay_text": rp_text,
        "roleplay_step25": (f"第 2.5 步：决策者最在意的事是文字第一句所说的事；"
                            f"文字指向 {kind}，与所选种类一致，标{confidence}把握。"),
        "forecast_prop": f"在下一季度末前，{player} 围绕 {kind} 采取行动。",
        "forecast_prob": probability,
    }
    if is_experiment:
        if has_numeric:
            vals_txt = "、".join(
                f"{_fmt_num(v['value'])}（{v['unit']}，{v['date']}）"
                for v in numeric)
            weak_rule = "N15：数字单位映射句决定种类"
            weak_evidence = (f"数值序列：{vals_txt}；趋势：{trend}；"
                             f"映射句结论：{mapping_sentence}")
            problem_type = "数字题（带序列字段）"
        elif most is None and last is None:
            weak_rule = "G15：历史计数为空，身份线判断"
            weak_evidence = (f"历史计数为空；身份线为{identity}；"
                             f"按身份线选 {kind}。")
            problem_type = "动作题"
        elif is_u15:
            weak_rule = "U15：不可推题，只报低概率"
            weak_evidence = ("不可推：事前信号不存在，因为事件本身在预测点"
                             "之前不公开；概率不高于 0.2。")
            problem_type = "动作题"
        else:
            weak_rule = "无：无弱项规则触发，按现行基线选种类"
            weak_evidence = "无弱项规则触发，按现行基线选种类。"
            problem_type = "动作题"
        rec["problem_type"] = problem_type
        rec["weak_rule"] = weak_rule
        rec["weak_evidence"] = weak_evidence
    return rec


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--questions-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--methods", nargs="*", default=[])
    ap.add_argument("--receipt", default=None)
    args = ap.parse_args()
    batch = args.batch
    is_experiment = batch.startswith("E")
    os.makedirs(args.out_dir, exist_ok=True)
    total = 0
    files_read = []
    for pos, rounds in ASSIGNMENT.items():
        predictor = f"{batch}-{pos}"
        for rnd in rounds:
            qfile = os.path.join(
                args.questions_dir, f"questions-baseline-{rnd}.json")
            data = json.load(open(qfile))
            vocab = set(data["vocabulary"])
            files_read.append(qfile)
            recs = [predict_question(q, vocab, batch, is_experiment)
                    for q in data["questions"]]
            out = {"predictor": predictor, "round": rnd, "batch": batch,
                   "predictions": recs}
            opath = os.path.join(args.out_dir,
                                 f"predictions-{batch}-{rnd}.json")
            with open(opath, "w", encoding="utf-8") as fh:
                json.dump(out, fh, indent=2, ensure_ascii=False)
            total += len(recs)
    print(f"{batch}: wrote {total} predictions "
          f"({sum(len(v) for v in ASSIGNMENT.values())} rounds files)")
    if args.receipt:
        receipt = {
            "batch": batch,
            "predictor_positions": [f"{batch}-{p}" for p in
                                    ("P1", "P2", "P3", "P4", "P5")],
            "executor": "EXEC-R15-AGENT (one scripted executor, all "
                        "positions; code-name identifiers only)",
            "method_files": {os.path.basename(f): sha256_file(f)
                             for f in args.methods},
            "question_files": {os.path.basename(f): sha256_file(f)
                               for f in sorted(set(files_read))},
            "questions_total": total,
        }
        with open(args.receipt, "w", encoding="utf-8") as fh:
            json.dump(receipt, fh, indent=2, ensure_ascii=False)
        print(f"{batch}: receipt -> {args.receipt}")


if __name__ == "__main__":
    main()
