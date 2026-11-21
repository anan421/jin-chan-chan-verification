#!/usr/bin/env python3
"""Merge the agent gate, fast-checker report and Lean build result
into one report.

Layers, in run order: agent gate (optional, --claims given) ->
fast checker -> Lean proof. A gate failure means the checker and
Lean layers are not run; they are recorded as not_run, not pass.

Prediction chapter (optional, --prediction-run): the prediction
reports (predict, backtest, symbolic, agent_claims protocol) are
merged as a separate "## 预测" chapter. Its verdict is computed
from the prediction reports only: fail if any prediction report is
missing, any verdict is fail, backtest is below threshold, or a
claim was refuted by the transition relation; pass otherwise;
not_run when prediction was not attempted. The overall verdict is
still decided by the history layers only; prediction never enters
the "verified" label, and the chapter states plainly that
prediction is not verification.
"""
import argparse
import json
import sys
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _contains(obj, needle):
    if isinstance(obj, str):
        return needle in obj
    if isinstance(obj, dict):
        return any(_contains(v, needle) for v in obj.values())
    if isinstance(obj, list):
        return any(_contains(v, needle) for v in obj)
    return False


def _report_verdict(rep, required_keys):
    """Resolve one prediction report's verdict.

    The contract says each prediction report carries a top-level
    "verdict". The symbolic tool as built carries none, but exits 0
    with a structurally complete report; for such a report, a
    missing verdict is read as pass when all required content keys
    are present, and as fail otherwise. A report that does carry a
    verdict is taken at face value.
    """
    if rep is None:
        return None
    if not isinstance(rep, dict):
        return "fail"
    v = rep.get("verdict")
    if v in ("pass", "fail", "not_run"):
        return v
    # Backtest as built carries no "verdict": it carries
    # "threshold_verdict" ("below_threshold" / "above_threshold")
    # and "below_threshold" (a list of failing metrics, or True).
    tv = rep.get("threshold_verdict")
    if tv == "below_threshold":
        return "fail"
    if tv in ("above_threshold", "pass"):
        return "pass"
    bt = rep.get("below_threshold")
    if bt is True or (isinstance(bt, list) and bt):
        return "fail"
    # required_keys: one group (tuple of str) or alternatives
    # (tuple of groups); a report is complete when any group is
    # fully present.
    if required_keys:
        groups = required_keys
        if groups and isinstance(groups[0], str):
            groups = (groups,)
        if any(all(k in rep for k in g) for g in groups):
            return "pass"
    return "fail"


def _find_below_threshold(backtest):
    """True when the backtest report says it is below threshold."""
    if not isinstance(backtest, dict):
        return False
    if backtest.get("threshold_verdict") == "below_threshold":
        return True
    bt = backtest.get("below_threshold")
    if bt is True or (isinstance(bt, list) and bt):
        return True
    if backtest.get("below_threshold") is True:
        return True
    for key in ("meets_thresholds", "threshold_met", "passed_thresholds",
                "above_threshold"):
        if backtest.get(key) is False:
            return True
    thresholds = backtest.get("thresholds")
    tables = backtest.get("tables")
    if isinstance(thresholds, dict) and isinstance(tables, dict):
        overall = tables.get("overall")
        if isinstance(overall, dict):
            for metric, thr in thresholds.items():
                val = overall.get(metric)
                if val is None:
                    val = overall.get(str(metric).upper())
                if isinstance(val, (int, float)) \
                        and isinstance(thr, (int, float)) and val < thr:
                    return True
    return False


def _metric_str(d, keys):
    """Render M1-M5 style metrics from a dict, tolerating key case."""
    if not isinstance(d, dict):
        return None
    parts = []
    for k in keys:
        v = d.get(k)
        if v is None:
            v = d.get(k.upper())
        if v is None:
            v = d.get(k.lower())
        if isinstance(v, (int, float)):
            parts.append(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}")
    return ", ".join(parts) if parts else None


def main():
    ap = argparse.ArgumentParser(description="Merge gate + check + Lean results.")
    ap.add_argument("--check-report", default=None,
                    help="check.py report JSON (absent when gate failed)")
    ap.add_argument("--classification-report", default=None,
                    help="classify.py report JSON (absent when the checker "
                    "did not run)")
    ap.add_argument("--lean-log", default=None,
                    help="Lean build log (absent when gate failed)")
    ap.add_argument("--lean-rc", type=int, required=True)
    ap.add_argument("--gen-rc", type=int, required=True)
    ap.add_argument("--gate-report", default=None,
                    help="gate.py report JSON (absent when --claims not given)")
    ap.add_argument("--gate-rc", type=int, default=0)
    ap.add_argument("--prediction-report", default=None,
                    help="predict.py report JSON")
    ap.add_argument("--backtest-report", default=None,
                    help="backtest.py report JSON")
    ap.add_argument("--symbolic-report", default=None,
                    help="symbolic.py report JSON")
    ap.add_argument("--protocol-report", default=None,
                    help="agent_claims.py protocol report JSON")
    ap.add_argument("--prediction-run", action="store_true",
                    help="prediction was attempted (history passed and "
                    "--predict given); without it, missing prediction "
                    "reports mean not_run, not fail")
    ap.add_argument("--trace", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    trace = load_json(args.trace)
    check = load_json(args.check_report) if args.check_report else None
    classification = load_json(args.classification_report) \
        if args.classification_report else None
    gate = load_json(args.gate_report) if args.gate_report else None
    prediction = load_json(args.prediction_report) \
        if args.prediction_report else None
    backtest = load_json(args.backtest_report) \
        if args.backtest_report else None
    symbolic = load_json(args.symbolic_report) \
        if args.symbolic_report else None
    protocol = load_json(args.protocol_report) \
        if args.protocol_report else None
    lean_log = (Path(args.lean_log).read_text(encoding="utf-8", errors="replace")
                if args.lean_log else "")

    if gate is None:
        gate_verdict = "skipped"
    else:
        gate_verdict = gate["verdict"]
    if check is None:
        check_verdict = "not_run"
    else:
        check_verdict = check["verdict"]
    if check is None:
        # Gate failed: checker and Lean never ran; their rc defaults (0)
        # must not be read as a pass.
        lean_verdict = "not_run"
    elif args.lean_rc == 0 and args.gen_rc == 0:
        lean_verdict = "pass"
    else:
        lean_verdict = "fail"
    overall = ("pass" if gate_verdict in ("pass", "skipped")
               and check_verdict == "pass" and lean_verdict == "pass"
               else "fail")

    # --- Prediction chapter verdict (history-independent) -----------
    pred_reports = {"prediction": prediction, "backtest": backtest,
                    "symbolic": symbolic, "protocol": protocol}
    attempted = args.prediction_run or any(
        v is not None for v in pred_reports.values())
    below_threshold = _find_below_threshold(backtest)
    refuted_by_transition = bool(
        prediction is not None
        and _contains(prediction, "refuted_by_transition"))
    if not attempted:
        prediction_verdict = "not_run"
    elif any(v is None for v in pred_reports.values()):
        prediction_verdict = "fail"
    elif any(rv == "fail" or rv == "not_run" for rv in (
            _report_verdict(prediction, ("players",)),
            _report_verdict(backtest, (("tables",), ("test_window",))),
            _report_verdict(symbolic, ("cells", "edges", "sccs",
                                       "attractors", "pruning")),
            _report_verdict(protocol, ("checks",)))):
        prediction_verdict = "fail"
    elif below_threshold or refuted_by_transition:
        prediction_verdict = "fail"
    else:
        prediction_verdict = "pass"
    prediction_section = {
        "verdict": prediction_verdict,
        "attempted": attempted,
        "prediction": _report_verdict(prediction, ("players",)),
        "backtest": _report_verdict(backtest, (("tables",),
                                              ("test_window",))),
        "symbolic": _report_verdict(symbolic, ("cells", "edges", "sccs",
                                               "attractors", "pruning")),
        "protocol": _report_verdict(protocol, ("checks",)),
        "below_threshold": below_threshold,
        "refuted_by_transition": refuted_by_transition,
        "missing": [k for k, v in pred_reports.items() if v is None]
        if attempted else [],
    }

    merged = {
        "trace": args.trace,
        "trace_sha256": trace.get("meta", {}).get("trace_sha256"),
        "page_version": trace.get("meta", {}).get("page_version"),
        "overall": overall,
        "layers": {
            "agent_gate": {
                "verdict": gate_verdict,
                "exit": args.gate_rc,
                "counts": gate["counts"] if gate else None,
            },
            "fast_checker": {
                "verdict": check_verdict,
                "passed": len(check["passed"]) if check else 0,
                "failures": len(check["failures"]) if check else 0,
                "gaps": len(check["gaps"]) if check else 0,
            },
            "lean": {
                "verdict": lean_verdict,
                "build_exit": args.lean_rc,
                "trace_gen_exit": args.gen_rc,
            },
        },
        "gate_claims": gate["claims"] if gate else [],
        "failures": check["failures"] if check else [],
        "gaps": check["gaps"] if check else [],
        "classification": classification,
        "prediction": prediction_section,
        "lean_log_tail": lean_log.strip().splitlines()[-30:] if lean_log else [],
    }
    Path(args.out_json).write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# 验证报告（{trace.get('meta', {}).get('page_version', '?')}）",
          "",
          f"总体结论：**{overall}**",
          f"trace：`{args.trace}`",
          f"trace 哈希：`{merged['trace_sha256']}`",
          "",
          "## 各层结果",
          "",
          f"- Agent gate：{gate_verdict}"
          + (f"（通过 {gate['counts']['pass']}，拒绝 "
             f"{gate['counts']['reject']}，opinion "
             f"{gate['counts']['opinion']}，contested "
             f"{gate['counts']['contested']}，refuted "
             f"{gate['counts']['refuted']}）" if gate else "（未提供 Agent 输出，跳过）"),
          f"- 快速检查器：{check_verdict}"
          + (f"（通过 {len(check['passed'])}，失败 "
             f"{len(check['failures'])}，数据不足 {len(check['gaps'])}）"
             if check else "（gate 未通过，未运行）"),
          f"- Lean 4：{lean_verdict}"
          + (f"（构建退出码 {args.lean_rc}，trace 生成退出码 {args.gen_rc}）"
             if lean_verdict != "not_run" else "（gate 未通过，未运行）"),
          ""]
    if gate:
        md.append("## Agent 协议（gate R1–R4）")
        md.append("")
        md.append("R1 schema 不合直接拒绝；R2 证据指针不存在直接拒绝；"
                  "R3 谓词不可判定只记 opinion，不得冒充已验证；R4 同一位置"
                  "相反断言记 contested，页面不得显示“已验证”，直到其中一条"
                  "被证据推翻（refuted）或修正。")
        md.append("")
        for c in gate["claims"]:
            md.append(f"- {c['claim_id']}（{c['kind']}）：{c['verdict']} "
                      f"— {c['reason']}")
        md.append("")
        opinions = [c for c in gate["claims"] if c["verdict"] == "opinion"]
        if opinions:
            md.append("### 假设（judgment claims，只进备注，不计入已验证）")
            md.append("")
            md.append("以下 claim 未通过机器判定，按协议记为 opinion："
                      "证书列出它们作为假设，机器证明数学，agent 提供判断。")
            md.append("")
            for c in opinions:
                md.append(f"- {c['claim_id']}（{c['kind']}）：{c['reason']}")
            md.append("")
    if check and check["failures"]:
        md.append("## 失败（exact 位置）")
        md.append("")
        for f in check["failures"]:
            md.append(f"- {f['check']} S{f['season']} round={f['round']} "
                      f"player={f['player']} field={f['field']} "
                      f"期望 {f['expected']} 实际 {f['actual']} {f['note']}")
        md.append("")
    if check and check["gaps"]:
        md.append("## 数据不足")
        md.append("")
        for g in check["gaps"]:
            md.append(f"- {g['check']}: {g['note']}")
        md.append("")
    md.append("## 失败分类")
    md.append("")
    if classification is None:
        md.append("未运行（gate 未通过，检查器未运行）。")
        md.append("")
    elif not classification.get("clusters"):
        md.append("无失败簇（检查通过，或失败数为零）。")
        md.append("")
    else:
        md.append(f"机制错 {classification.get('mechanism_count', 0)} 簇，"
                  f"数据错 {classification.get('data_count', 0)} 簇。"
                  f"机制错要反思设计本身并迭代优化，不只改数据。")
        md.append("")
        for c in classification["clusters"]:
            md.append(f"- {c['class'].upper()} {c['check']}/{c['field']} "
                      f"×{c['count']} 赛季={c['seasons']} "
                      f"玩家数={len(c['players'])}：{c['note']}")
            if c.get("design_question"):
                md.append(f"  设计问题：{c['design_question']}")
        md.append("")
    if lean_verdict == "fail":
        md.append("## Lean 构建日志（末尾）")
        md.append("")
        md.append("```")
        md.extend(merged["lean_log_tail"])
        md.append("```")
    # --- Prediction chapter -----------------------------------------
    md.append("## 预测")
    md.append("")
    md.append("预测不是验证。预测结果不进“已验证”标签，不改变总体结论。")
    md.append("")
    md.append(f"预测章结论：**{prediction_verdict}**"
              f"（预测：{prediction_section['prediction']}，"
              f"回测：{prediction_section['backtest']}，"
              f"符号动力：{prediction_section['symbolic']}，"
              f"协议检查：{prediction_section['protocol']}）")
    md.append("")
    if prediction_verdict == "not_run":
        md.append("预测未跑：历史层未全过，或未给 --predict。")
        md.append("")
    else:
        if prediction_section["missing"]:
            md.append("缺失的预测报告："
                      + ", ".join(prediction_section["missing"]) + "。")
            md.append("")
        if below_threshold:
            md.append("回测低于阈值。")
            md.append("")
        if refuted_by_transition:
            md.append("有 claim 被转移关系反驳（refuted_by_transition）。")
            md.append("")
        # Distribution: per-player mode action + top-k probability mass.
        players = prediction.get("players") if isinstance(
            prediction, dict) else None
        if players:
            md.append("### 分布")
            md.append("")
            items = players.items() if isinstance(players, dict) \
                else [(p.get("key") or p.get("name") or p.get("player", "?"), p)
                      for p in players if isinstance(p, dict)]
            for name, p in items:
                if not isinstance(p, dict):
                    continue
                dist = p.get("distribution") or p.get("dist") or {}
                mode = p.get("modal_action") or p.get("mode") \
                    or p.get("mode_action")
                topk = p.get("top3_mass") or p.get("top_k_mass") \
                    or p.get("top_k_probability_mass")
                top3 = ""
                if isinstance(dist, dict) and dist:
                    ranked = sorted(dist.items(), key=lambda kv: -kv[1])[:3]
                    top3 = ", ".join(f"{k}={v:.3f}" for k, v in ranked)
                    if mode is None:
                        mode = ranked[0][0]
                    if topk is None:
                        topk = round(sum(v for _, v in ranked), 3)
                md.append(f"- {name}：众数动作 {mode}"
                          + (f"（p={p.get('modal_probability'):.3f})"
                             if isinstance(p.get("modal_probability"),
                                          (int, float)) else "")
                          + (f"，前 3 名概率质量 {topk}" if topk is not None
                             else "")
                          + (f"，前 3：{top3}" if top3 else ""))
            md.append("")
        # Hit rate: M1-M5 vs baselines and thresholds.
        if isinstance(backtest, dict):
            md.append("### 命中率")
            md.append("")
            tables = backtest.get("tables") or {}
            overall_tbl = tables.get("overall") if isinstance(
                tables, dict) else None
            if overall_tbl is None:
                tw = backtest.get("test_window")
                overall_tbl = tw.get("overall") if isinstance(tw, dict) \
                    else None
            hit = _metric_str(overall_tbl, ["m1", "m2", "m3", "m4", "m5"])
            if hit:
                md.append(f"- 全体：{hit}")
            elif isinstance(overall_tbl, dict):
                parts = []
                for i in (1, 2, 3, 4, 5):
                    hr = overall_tbl.get(f"m{i}_hit_rate")
                    bl = overall_tbl.get(f"m{i}_baseline")
                    mg = overall_tbl.get(f"m{i}_margin_pp")
                    if isinstance(hr, (int, float)):
                        s = f"M{i}={hr:.4f}"
                        if isinstance(bl, (int, float)):
                            s += f"（基线 {bl:.4f}"
                            s += f"，裕度 {mg:+.2f}pp" \
                                if isinstance(mg, (int, float)) else ""
                            s += "）"
                        parts.append(s)
                if parts:
                    md.append("- 全体：" + "，".join(parts)
                              + f"（n={overall_tbl.get('n')}）")
                below = overall_tbl.get("below_threshold")
                if isinstance(below, list) and below:
                    md.append("- 低于阈值：" + ", ".join(below))
            baselines = backtest.get("baselines")
            if isinstance(baselines, dict):
                base = _metric_str(baselines, ["m1", "m2", "m3", "m4", "m5"])
                if base:
                    md.append(f"- 随机基线：{base}")
                else:
                    md.append(f"- 随机基线：{json.dumps(baselines, ensure_ascii=False)}")
            thresholds = backtest.get("thresholds")
            if isinstance(thresholds, dict):
                thr = _metric_str(thresholds, ["m1", "m2", "m3", "m4", "m5"])
                md.append("- 阈值：" + (thr if thr else json.dumps(
                    thresholds, ensure_ascii=False)))
            if isinstance(tables, dict):
                for scope in ("per_player", "per_season"):
                    tbl = tables.get(scope)
                    if isinstance(tbl, dict):
                        md.append(f"- {scope}：{len(tbl)} 条记录")
            tw = backtest.get("test_window") if isinstance(
                backtest.get("test_window"), dict) else None
            if tw:
                if isinstance(tw.get("by_season"), dict):
                    md.append(f"- 按赛季：{', '.join(sorted(tw['by_season']))}"
                              f"（{len(tw['by_season'])} 个赛季）")
                if isinstance(tw.get("by_player"), dict):
                    md.append(f"- 按玩家：{len(tw['by_player'])} 名玩家")
            if not hit and not isinstance(overall_tbl, dict) \
                    and not baselines and not thresholds:
                md.append(f"- 回测报告：{json.dumps(backtest, ensure_ascii=False)[:500]}")
            md.append("")
        # Assumptions.
        assumptions = prediction.get("assumptions") if isinstance(
            prediction, dict) else None
        md.append("### 假设清单")
        md.append("")
        if isinstance(assumptions, list) and assumptions:
            for a in assumptions:
                if isinstance(a, dict):
                    md.append(f"- {a.get('id', '')}"
                              + (f"（{a.get('parameter')}）"
                                 if a.get("parameter") else "")
                              + f"：{a.get('text', '')}")
                else:
                    md.append(f"- {a}")
        else:
            md.append("- （预测报告未给假设清单）")
        md.append("")
        if isinstance(prediction, dict) and prediction.get("applied_claims"):
            md.append("### 已应用的 claim")
            md.append("")
            for c in prediction["applied_claims"]:
                if isinstance(c, dict):
                    md.append(f"- {c.get('claim_id')}: "
                              f"{c.get('result') or c.get('status') or c.get('verdict') or ''}"
                              + (f" — {c.get('reason')}" if c.get("reason") else ""))
                else:
                    md.append(f"- {c}")
            md.append("")
        if isinstance(protocol, dict):
            md.append("### 协议检查")
            md.append("")
            for k, v in (protocol.get("checks") or {}).items():
                if isinstance(v, dict):
                    md.append(f"- {k}：{v.get('verdict')} — {v.get('detail', '')}")
            md.append("")
    Path(args.out_md).write_text("\n".join(md), encoding="utf-8")
    print(f"merge: overall={overall} -> {args.out_json}")
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
