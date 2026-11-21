#!/usr/bin/env python3
"""Ensemble prediction runner: N agent players, each with one payoff
weight set, run the same best-response dynamics on the same current
state and report the distribution of their predictions, not just the
mode.

Members (15): the 14 role-play auditors, each as one weight profile
derived from that auditor's recorded stance (the mapping is a
judgement, labelled as such; it carries no evidence), plus the
baseline member (the single-model placeholder weights from
payoff-model.json, the reference the ensemble is compared with).

Disagreement is computed, never invented: it comes only from the
weight differences acting on the same expected deltas, the same
candidates and the same current state, through predict.best_response
(read-only import; this file does not modify predict.py or
payoff-model.json).

Three honest limits of v1, recorded in the report:
- payoff-model.json v1 holds point placeholders only; it holds no
  assumption intervals, so member weights are defined here as
  documented variations around the placeholder baseline.
- c_rule is inert in v1: compliance_cost is 0 for every legal kind,
  so members that differ only in c_rule predict identically.
- tau (temperature) only sharpens or flattens the softmax; it never
  changes the modal action (argmax of a softmax is argmax of the
  utilities). Members that differ only in tau agree on actions and
  differ only in modal probability.

Disagreement metrics, per player:
- modal_counts: how many members predict each modal action.
- modal_share: largest count / N (1.0 = full consensus).
- distinct_modals: number of different modal actions.
- entropy_bits: Shannon entropy of the modal distribution (log2).
- entropy_norm: entropy_bits / log2(N) (0 = full consensus,
  1 = maximal spread).
- ensemble_distribution: mean of the members' softmax distributions;
  ensemble_modal: its argmax; ensemble_modal_probability.
- baseline_agreement: fraction of the 14 auditor members whose
  modal action equals the baseline member's modal action.
- flag: consensus (modal_share == 1.0), high_disagreement
  (modal_share < 0.5 or entropy_norm > 0.5), else medium.

Usage:
    python3 ensemble.py <trace.json> --payoff <payoff.json>
        [--out report.json] [--summary summary.txt]
Exit: 0 run completed; 2 bad input. (Smoke test only, not
calibration: payoff parameters are placeholders and the fixture
trace must not be used for calibration.)
"""
import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import predict  # noqa: E402  (read-only reuse of best_response etc.)

SMOKE_NOTE = ("Smoke test only, not calibration: payoff parameters "
              "are placeholders and the fixture trace must not be "
              "used for calibration.")
ASSUMPTION_NOTE = ("All payoff parameters are placeholders (status "
                   "placeholder, assumptions A1-A6, plus A7 for the "
                   "AAPL tier judgement). No parameter value carries "
                   "evidence. Member weight profiles are judgements "
                   "mapped from the auditors' recorded stances, not "
                   "evidence.")

# --- member profiles -------------------------------------------------
# Each profile: one auditor's recorded stance (audit14 verdict line)
# mapped to a weight vector. The mapping is a judgement: it states
# which payoff dimension that stance emphasises, nothing more.
# Baseline values are payoff-model.json v1 placeholders
# (w_hp 1.0, w_gold 1.0, c_lever 5.0, c_rule 10.0, w_pos 1.0, tau 1.0).
MEMBER_PROFILES = [
    {"member_id": "baseline", "auditor": "—",
     "stance_zh": "单模型占位权重（参照）",
     "weights": {"w_hp": 1.0, "w_gold": 1.0, "c_lever": 5.0,
                 "c_rule": 10.0, "w_pos": 1.0}, "tau": 1.0,
     "rationale_zh": "payoff-model.json v1 的占位值原样；单模型预测的参照。"},
    {"member_id": "nvda", "auditor": "NVDA",
     "stance_zh": "需求未崩（本方自证）",
     "weights": {"w_hp": 1.5, "w_gold": 1.0, "c_lever": 2.0,
                 "c_rule": 10.0, "w_pos": 1.0}, "tau": 0.7,
     "rationale_zh": "需求强、Q3 数字自证：血量权重高，杠杆惩罚低，置信锐。"},
    {"member_id": "oai", "auditor": "OAI",
     "stance_zh": "纠正最多",
     "weights": {"w_hp": 1.0, "w_gold": 1.5, "c_lever": 2.0,
                 "c_rule": 10.0, "w_pos": 1.0}, "tau": 1.0,
     "rationale_zh": "融资驱动增长（承认 3 月轮含供应商融资）：金币权重高，杠杆惩罚低。"},
    {"member_id": "msft", "auditor": "MSFT",
     "stance_zh": "不是贷款玩家",
     "weights": {"w_hp": 1.5, "w_gold": 1.0, "c_lever": 8.0,
                 "c_rule": 10.0, "w_pos": 1.0}, "tau": 1.0,
     "rationale_zh": "正自由现金流，风险在羁绊集中不在债务：血量权重高，杠杆惩罚高。"},
    {"member_id": "goog", "auditor": "GOOG",
     "stance_zh": "算力后盾，不是旁观者",
     "weights": {"w_hp": 1.0, "w_gold": 1.0, "c_lever": 8.0,
                 "c_rule": 10.0, "w_pos": 2.0}, "tau": 1.0,
     "rationale_zh": "后盾即风险（Anthropic 违约则接管租约）：位置权重高，杠杆惩罚高。"},
    {"member_id": "amzn", "auditor": "AMZN",
     "stance_zh": "口径订正两处",
     "weights": {"w_hp": 1.0, "w_gold": 1.25, "c_lever": 5.0,
                 "c_rule": 10.0, "w_pos": 1.0}, "tau": 1.0,
     "rationale_zh": "审慎、近基线：金币权重略高（AWS 积压订单），其余不变。"},
    {"member_id": "meta", "auditor": "META",
     "stance_zh": "评级未降，展望下调",
     "weights": {"w_hp": 1.0, "w_gold": 1.5, "c_lever": 8.0,
                 "c_rule": 10.0, "w_pos": 1.0}, "tau": 1.0,
     "rationale_zh": "债券利差 53bp 升至约 110bp，融资成本上升：金币权重高，杠杆惩罚高。"},
    {"member_id": "anth", "auditor": "ANTH",
     "stance_zh": "「抽血」不成立",
     "weights": {"w_hp": 1.0, "w_gold": 1.0, "c_lever": 2.0,
                 "c_rule": 10.0, "w_pos": 1.5}, "tau": 1.0,
     "rationale_zh": "钱进公司、承诺多为非刚性：杠杆惩罚低，位置权重高。"},
    {"member_id": "cnteam", "auditor": "CNTEAM",
     "stance_zh": "框架写偏，已拆席",
     "weights": {"w_hp": 1.0, "w_gold": 1.0, "c_lever": 5.0,
                 "c_rule": 20.0, "w_pos": 1.0}, "tau": 1.5,
     "rationale_zh": "规则与外部冲击主导，模型以美国事件为中心：规则成本高，置信扁。c_rule 在 v1 无效（见 limits）。"},
    {"member_id": "musk", "auditor": "MUSK",
     "stance_zh": "遗漏最严重",
     "weights": {"w_hp": 1.5, "w_gold": 0.5, "c_lever": 15.0,
                 "c_rule": 10.0, "w_pos": 1.0}, "tau": 0.7,
     "rationale_zh": "循环融资是庞氏结构变体，崩溃正在进行：杠杆惩罚最高，金币权重最低，血量权重高，置信锐。"},
    {"member_id": "dpsk", "auditor": "DPSK",
     "stance_zh": "裂缝点订正为 R1",
     "weights": {"w_hp": 1.5, "w_gold": 0.5, "c_lever": 8.0,
                 "c_rule": 10.0, "w_pos": 1.0}, "tau": 1.0,
     "rationale_zh": "效率改写版本答案，无 GPU 抵押贷款：金币权重低，血量权重高，杠杆惩罚高。"},
    {"member_id": "huawei", "auditor": "HUAWEI",
     "stance_zh": "赛季切法不适用本席",
     "weights": {"w_hp": 2.0, "w_gold": 0.75, "c_lever": 5.0,
                 "c_rule": 20.0, "w_pos": 1.0}, "tau": 1.0,
     "rationale_zh": "需求未崩、供给先崩，SMIC 良率与 HBM 是天花板：血量权重最高，规则成本高。"},
    {"member_id": "ali", "auditor": "ALI",
     "stance_zh": "不是杠杆玩家",
     "weights": {"w_hp": 1.5, "w_gold": 1.0, "c_lever": 8.0,
                 "c_rule": 10.0, "w_pos": 1.0}, "tau": 1.0,
     "rationale_zh": "资本开支来自资产负债表与经营现金流：血量权重高，杠杆惩罚高。"},
    {"member_id": "tce", "auditor": "TCE",
     "stance_zh": "不是贷款游戏",
     "weights": {"w_hp": 1.25, "w_gold": 1.5, "c_lever": 8.0,
                 "c_rule": 10.0, "w_pos": 1.0}, "tau": 1.0,
     "rationale_zh": "拿经营现金流加发债买推理算力，风险是花得太快回报太慢：金币权重高，杠杆惩罚高。"},
    {"member_id": "byte", "auditor": "BYTE",
     "stance_zh": "四处事实订正",
     "weights": {"w_hp": 1.25, "w_gold": 1.0, "c_lever": 5.0,
                 "c_rule": 20.0, "w_pos": 1.5}, "tau": 1.0,
     "rationale_zh": "受 BIS 规则冲击最大的中国玩家之一，海外项目融资被规则冻结：规则成本高，位置权重高。"},
]


def entropy_bits(counts):
    """Shannon entropy (bits) of a count distribution."""
    total = sum(counts.values())
    if total <= 1:
        return 0.0
    h = 0.0
    for c in counts.values():
        p = c / total
        h -= p * math.log2(p)
    return round(h, 6)


def flag_for(modal_share, entropy_norm):
    if modal_share == 1.0:
        return "consensus"
    if modal_share < 0.5 or entropy_norm > 0.5:
        return "high_disagreement"
    return "medium"


def setup(trace):
    """Mirror predict.main's setup: current state, candidates,
    expectations, start actions, acting players, HP bounds."""
    players = trace["players"]
    pmap = {p["id"]: p for p in players}
    rules = trace["rules"]
    moves = trace["moves"]
    max_date = max(m["date"] for m in moves)
    base_now, _ = check.resolve_rules(rules, max_date, players[0]["id"])
    if base_now is None:
        return None, "no base rule in effect at the latest date"
    hp_bounds = (base_now["params"]["hp_floor"],
                 base_now["params"]["hp_cap"])
    current = predict.current_states(trace)
    lasts = predict.last_moves(trace)
    all_kinds = sorted({m["action_kind"] for m in moves})
    candidates = {}
    for p in players:
        pid = p["id"]
        _, overlays = check.resolve_rules(rules, max_date, pid)
        banned = set(base_now["params"].get("banned_action_kinds", []))
        for ov in overlays:
            banned |= set(ov["params"].get("banned_action_kinds", []))
        candidates[pid] = [k for k in all_kinds if k not in banned]
    per_mean, glob_mean = predict.expected_deltas(moves)
    exp = predict.make_expectation(per_mean, glob_mean)
    start_actions = {pid: lasts[pid]["action_kind"]
                     for pid in lasts if lasts[pid]["action_kind"]
                     in candidates.get(pid, [])}
    acting = sorted(pid for pid in pmap if current.get(pid, (0, 0))[0] > 0)
    state = {pid: current[pid] for pid in pmap}
    return {"pmap": pmap, "rules": rules, "max_date": max_date,
            "base_rule": base_now["rule_id"], "hp_bounds": hp_bounds,
            "current": current, "candidates": candidates, "exp": exp,
            "start_actions": start_actions, "acting": acting,
            "state": state}, None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Ensemble prediction runner.")
    ap.add_argument("trace")
    ap.add_argument("--payoff", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--summary", default=None)
    args = ap.parse_args(argv)

    trace = predict.load_trace(args.trace)
    if trace is None:
        return 2
    payoff = predict.load_json(args.payoff, "payoff model")
    if payoff is None or "parameters" not in payoff:
        print("ensemble: bad payoff model file", file=sys.stderr)
        return 2
    if not trace["moves"] or not trace["players"]:
        print("ensemble: trace has no moves or no players", file=sys.stderr)
        return 2
    ctx, err = setup(trace)
    if ctx is None:
        print(f"ensemble: {err}", file=sys.stderr)
        return 2

    n_members = len(MEMBER_PROFILES)
    log_n = math.log2(n_members) if n_members > 1 else 1.0
    members_out = []
    # per player: list of (member_id, modal action, modal prob, dist)
    per_player = defaultdict(list)
    for prof in MEMBER_PROFILES:
        res = predict.best_response(
            ctx["state"], prof["weights"], prof["tau"],
            ctx["candidates"], ctx["exp"], ctx["start_actions"],
            ctx["acting"], ctx["hp_bounds"])
        entry = {
            "member_id": prof["member_id"],
            "auditor": prof["auditor"],
            "stance_zh": prof["stance_zh"],
            "weights": prof["weights"],
            "tau": prof["tau"],
            "rationale_zh": prof["rationale_zh"],
            "iterations": res["iterations"],
            "converged": res["converged"],
            "cycle": res["cycle"],
            "players": {},
        }
        for pid in ctx["acting"]:
            modal = res["modal"].get(pid, {})
            entry["players"][ctx["pmap"][pid].get("key")] = {
                "player": pid,
                "modal_action": modal.get("action"),
                "modal_probability": modal.get("probability", 0.0),
                "top3_mass": modal.get("top3_mass", 0.0),
                "distribution": res["distributions"].get(pid, {}),
            }
            per_player[pid].append((
                prof["member_id"], modal.get("action"),
                modal.get("probability", 0.0),
                res["distributions"].get(pid, {})))
        members_out.append(entry)

    baseline_modal = {}
    for m in members_out:
        if m["member_id"] == "baseline":
            for key, row in m["players"].items():
                baseline_modal[key] = row["modal_action"]
    players_out = []
    for pid in ctx["acting"]:
        key = ctx["pmap"][pid].get("key")
        rows = per_player[pid]
        modals = [a for _, a, _, _ in rows if a is not None]
        counts = Counter(modals)
        modal_share = (max(counts.values()) / n_members
                       if counts else 0.0)
        h = entropy_bits(counts)
        h_norm = round(h / log_n, 6) if log_n else 0.0
        ensemble_dist = {}
        for _, _, _, dist in rows:
            for k, v in dist.items():
                ensemble_dist[k] = ensemble_dist.get(k, 0.0) + v / n_members
        ensemble_dist = {k: round(v, 6)
                         for k, v in ensemble_dist.items()}
        ens_modal = (max(ensemble_dist, key=lambda k: (ensemble_dist[k], k))
                     if ensemble_dist else None)
        ens_prob = ensemble_dist.get(ens_modal, 0.0) if ens_modal else 0.0
        auditors = [r for r in rows if r[0] != "baseline"]
        base_agree = (sum(1 for _, a, _, _ in auditors
                          if a == baseline_modal.get(key))
                      / len(auditors)) if auditors else 0.0
        players_out.append({
            "player": pid, "key": key,
            "name": ctx["pmap"][pid].get("name"),
            "current_hp": ctx["current"][pid][0],
            "current_gold": ctx["current"][pid][1],
            "modal_counts": dict(counts),
            "distinct_modals": len(counts),
            "modal_share": round(modal_share, 6),
            "entropy_bits": h,
            "entropy_norm": h_norm,
            "ensemble_distribution": ensemble_dist,
            "ensemble_modal": ens_modal,
            "ensemble_modal_probability": ens_prob,
            "baseline_modal": baseline_modal.get(key),
            "baseline_agreement": round(base_agree, 6),
            "flag": flag_for(modal_share, h_norm),
        })

    flags = Counter(p["flag"] for p in players_out)
    mean_entropy = (round(sum(p["entropy_norm"] for p in players_out)
                          / len(players_out), 6) if players_out else 0.0)
    mean_share = (round(sum(p["modal_share"] for p in players_out)
                        / len(players_out), 6) if players_out else 0.0)
    converged_n = sum(1 for m in members_out if m["converged"])
    report = {
        "trace": args.trace,
        "payoff_model": {"version": payoff.get("version"),
                         "utility_form": payoff.get("utility_form")},
        "horizon": 1,
        "horizon_note": ("Ensemble runs one round only (the same "
                         "first forecast round as predict.py); "
                         "multi-round ensemble is not built."),
        "current_rule": ctx["base_rule"],
        "current_date": ctx["max_date"],
        "n_members": n_members,
        "member_ids": [m["member_id"] for m in members_out],
        "members": members_out,
        "players": players_out,
        "global": {
            "mean_entropy_norm": mean_entropy,
            "mean_modal_share": mean_share,
            "flags": dict(flags),
            "consensus_players": [p["key"] for p in players_out
                                  if p["flag"] == "consensus"],
            "high_disagreement_players": [p["key"] for p in players_out
                                          if p["flag"] == "high_disagreement"],
            "converged_members": converged_n,
            "cycled_members": n_members - converged_n,
        },
        "limits": [
            "payoff-model.json v1 holds point placeholders only; it "
            "holds no assumption intervals, so member weights are "
            "documented variations around the placeholder baseline, "
            "defined in ensemble.py, not taken from the payoff file.",
            "c_rule is inert in v1: compliance_cost is 0 for every "
            "legal kind, so members that differ only in c_rule "
            "predict identically. CNTEAM differs from baseline only "
            "in c_rule and tau, so its modal actions equal "
            "baseline's exactly; only its modal probabilities differ.",
            "tau only sharpens or flattens the softmax; it never "
            "changes the modal action. Members that differ only in "
            "tau agree on actions and differ only in modal "
            "probability.",
            "Disagreement is computed from weight differences only; "
            "it is not fabricated. Where all members agree, the "
            "report says so.",
        ],
        "assumptions": list(payoff.get("assumptions", [])),
        "assumption_note": ASSUMPTION_NOTE,
        "calibration_status": "placeholder_only",
        "smoke_test_note": SMOKE_NOTE,
        "verdict": "smoke_ok",
    }
    if args.out:
        Path(args.out).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8")
    lines = [
        f"ensemble: members={n_members} players={len(players_out)} "
        f"mean_entropy_norm={mean_entropy} mean_modal_share={mean_share}",
        f"ensemble: flags={dict(flags)} "
        f"converged_members={converged_n}/{n_members}",
        f"ensemble: high_disagreement="
        f"{report['global']['high_disagreement_players']}",
        f"ensemble: {SMOKE_NOTE}",
    ]
    for p in players_out:
        lines.append(
            f"  {p['key']} flag={p['flag']} share={p['modal_share']} "
            f"Hn={p['entropy_norm']} ensemble_modal={p['ensemble_modal']} "
            f"p={p['ensemble_modal_probability']} "
            f"baseline={p['baseline_modal']} "
            f"base_agree={p['baseline_agreement']}")
    summary = "\n".join(lines)
    print(summary)
    if args.summary:
        Path(args.summary).write_text(summary, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
