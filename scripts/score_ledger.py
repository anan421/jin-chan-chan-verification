#!/usr/bin/env python3
"""Score a Jin Chan Chan forecast ledger.

Read-only: this script reads forecasts/ledger.json and never writes to it.
It prints a Markdown scoring report to stdout and, when --output is given,
writes the same report to that file.

Ledger schema (Phase 2, design/forecast-ledger-schema.md, schema 1.0):
  Top level is a dict with "schema_version" ("1.0"), "meta",
  "forecasts", "resolutions", "versions". Settlement records live
  in "resolutions", separate from forecast records; the resolver
  differs from the forecaster. Older ledgers that used a "settlements"
  list or a "version" key are still read for backward compatibility.

  Each forecast record carries: forecast_id, proposition,
  forecast_type, type, participants, author, agent, created_at,
  information_cutoff, resolution_deadline, probability,
  resolution_criteria, evidence_snapshot, reasoning_summary,
  assumptions, counter_evidence, model_version, method_version,
  rule_version, world_state_version, status.
  Each resolution record carries: forecast_id, actual_outcome
  (boolean), resolved_at, outcome_evidence, resolution_status,
  resolver, dispute_status, score, review, review_reason,
  forecast_version.

Status values recognised (case-insensitive):
  hit:        "hit", "settled_hit", "occurred", "true", "yes"
  miss:       "miss", "settled_miss", "not_occurred", "false", "no"
  not due:    "pending", "not_due", "not_yet_due", "open", "future",
              "unsettled", "awaiting_settlement"
  undetermined: "undetermined", "inconclusive", "unresolvable",
              "unknown", "cannot_determine"
  A status of "settled" falls back to the record's "outcome" field, or
  to a matching settlement record.

Scoring:
  Brier score per settled forecast: (p - outcome)^2, outcome 1 for a
  hit and 0 for a miss. Mean Brier is the mean over settled forecasts.
  Calibration buckets are [0, 0.2), [0.2, 0.4), [0.4, 0.6), [0.6, 0.8),
  [0.8, 1.0]; each bucket compares mean predicted probability with the
  actual hit rate inside the bucket.
  Baselines (each method is stated in the report):
    random guess: p = 0.5 for every settled forecast.
    historical frequency: p = the overall hit rate among settled
      forecasts (in-sample base rate) for every settled forecast.
    per-player historical frequency: p = the leave-one-out hit rate of
      the same player's other settled forecasts; when the player has no
      other settled forecast, fall back to the leave-one-out overall
      base rate, and to 0.5 when there is no other settled forecast.
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date

BUCKETS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]

HIT_WORDS = {"hit", "settled_hit", "occurred", "true", "yes", "1"}
MISS_WORDS = {"miss", "settled_miss", "not_occurred", "false", "no", "0"}
PENDING_WORDS = {
    "pending", "not_due", "not_yet_due", "open", "future",
    "unsettled", "awaiting_settlement",
}
UNDETERMINED_WORDS = {
    "undetermined", "inconclusive", "unresolvable", "unknown",
    "cannot_determine", "cannot-determine",
}


def classify(record, settlement_by_id):
    """Return one of hit / miss / pending / undetermined / invalid."""
    fid = record.get("forecast_id") or record.get("id")
    outcome = None
    if fid is not None and fid in settlement_by_id:
        outcome = settlement_by_id[fid]
    if outcome is None:
        outcome = record.get("outcome")
    # The ledger stores settlement state in Chinese too, e.g.
    # settlement_status "已结算：命中" or "尚未到期". Check the
    # negative form before the positive form: "未命中" contains "命中".
    text = " ".join(
        str(record.get(k, "")) for k in ("status", "settlement_status")
    ).lower()
    if "未命中" in text or "settled_miss" in text:
        return "miss"
    if "命中" in text or "settled_hit" in text:
        return "hit"
    if "尚未到期" in text:
        return "pending"
    if "无法判定" in text:
        return "undetermined"
    status = str(record.get("status", "")).strip().lower()
    if status in HIT_WORDS:
        return "hit"
    if status in MISS_WORDS:
        return "miss"
    if status in PENDING_WORDS:
        return "pending"
    if status in UNDETERMINED_WORDS:
        return "undetermined"
    if status in {"settled", "resolved", "closed"}:
        if outcome is not None:
            word = str(outcome).strip().lower()
            if word in HIT_WORDS:
                return "hit"
            if word in MISS_WORDS:
                return "miss"
        return "undetermined"
    if outcome is not None:
        word = str(outcome).strip().lower()
        if word in HIT_WORDS:
            return "hit"
        if word in MISS_WORDS:
            return "miss"
    if status == "":
        return "undetermined"
    return "undetermined"


def player_of(record):
    player = record.get("player") or record.get("participant")
    if player is None:
        players = record.get("participants") or record.get("players")
        if isinstance(players, list) and players:
            first = players[0]
            if isinstance(first, dict):
                player = first.get("player")
            else:
                player = first
    return str(player) if player is not None else "unknown"


def resolution_outcome(res):
    """Extract a hit/miss word from one resolution record."""
    actual = res.get("actual_outcome")
    if actual is not None:
        word = str(actual).strip().lower()
        if word in HIT_WORDS:
            return "hit"
        if word in MISS_WORDS:
            return "miss"
    for key in ("settlement_status", "result", "outcome"):
        value = res.get(key)
        if value is None:
            continue
        text = str(value)
        if "未命中" in text or "settled_miss" in text:
            return "miss"
        if "命中" in text or "settled_hit" in text:
            return "hit"
        word = text.strip().lower()
        if word in HIT_WORDS:
            return "hit"
        if word in MISS_WORDS:
            return "miss"
    return None


def load_ledger(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"version": "unknown", "forecasts": data, "settlements": []}
    if isinstance(data, dict):
        forecasts = data.get("forecasts")
        if forecasts is None:
            forecasts = data.get("entries", [])
        version = (
            data.get("version")
            or data.get("ledger_version")
            or data.get("schema_version")
            or "unknown"
        )
        settlements = data.get("settlements")
        if settlements is None:
            settlements = data.get("resolutions", [])
        return {
            "version": str(version),
            "forecasts": forecasts,
            "settlements": settlements,
        }
    raise ValueError("ledger top level must be a list or an object")


def brier(p, outcome):
    return (p - outcome) ** 2


def score(ledger_path):
    ledger = load_ledger(ledger_path)
    settlements = ledger["settlements"]
    settlement_by_id = {}
    if isinstance(settlements, dict):
        settlement_by_id = {
            k: v.get("outcome") if isinstance(v, dict) else v
            for k, v in settlements.items()
        }
    elif isinstance(settlements, list):
        for s in settlements:
            if isinstance(s, dict) and "forecast_id" in s:
                outcome = resolution_outcome(s)
                if outcome is None:
                    outcome = s.get("outcome")
                settlement_by_id[s["forecast_id"]] = outcome

    rows = []
    counts = {"hit": 0, "miss": 0, "pending": 0, "undetermined": 0}
    errors = []
    for rec in ledger["forecasts"]:
        if not isinstance(rec, dict):
            errors.append(f"non-object entry skipped: {rec!r}")
            continue
        fid = rec.get("forecast_id") or rec.get("id") or "unknown"
        kind = classify(rec, settlement_by_id)
        counts[kind] += 1
        prob = rec.get("probability", rec.get("p"))
        if kind in ("hit", "miss"):
            if prob is None:
                errors.append(f"{fid}: settled but no probability")
                continue
            try:
                p = float(prob)
            except (TypeError, ValueError):
                errors.append(f"{fid}: probability not a number: {prob!r}")
                continue
            if not 0.0 <= p <= 1.0:
                errors.append(f"{fid}: probability out of range: {p}")
                continue
            rows.append({
                "id": str(fid),
                "player": player_of(rec),
                "p": p,
                "outcome": 1 if kind == "hit" else 0,
                "kind": kind,
            })
    return ledger["version"], ledger["forecasts"], counts, rows, errors


def mean(values):
    return sum(values) / len(values) if values else None


def render(ledger_path, version, total, counts, rows, errors):
    today = date.today().isoformat()
    n_settled = len(rows)
    n_hit = sum(1 for r in rows if r["outcome"] == 1)
    n_miss = n_settled - n_hit
    lines = []
    lines.append("# 预测账本评分报告")
    lines.append("")
    lines.append(f"- 评分日期：{today}")
    lines.append(f"- 账本文件：{ledger_path}")
    lines.append(f"- 账本版本：{version}")
    lines.append(f"- 预测总数：{total}")
    lines.append(f"- 已结算数：{n_settled}")
    lines.append(f"- 未结算数：{counts['pending'] + counts['undetermined']}")
    lines.append("")
    lines.append("## 分类计数")
    lines.append("")
    lines.append("| 类别 | 数量 |")
    lines.append("| --- | ---: |")
    lines.append(f"| 命中 | {counts['hit']} |")
    lines.append(f"| 未命中 | {counts['miss']} |")
    lines.append(f"| 尚未到期 | {counts['pending']} |")
    lines.append(f"| 无法判定 | {counts['undetermined']} |")
    lines.append("")
    lines.append("## Brier 分")
    lines.append("")
    if n_settled == 0:
        lines.append("已结算预测为 0 条。Brier 分无法计算。")
    else:
        lines.append("| 预测 | 玩家 | 预测概率 | 结果 | Brier 分 |")
        lines.append("| --- | --- | ---: | --- | ---: |")
        for r in rows:
            result = "命中" if r["outcome"] == 1 else "未命中"
            lines.append(
                f"| {r['id']} | {r['player']} | {r['p']:.2f} | "
                f"{result} | {brier(r['p'], r['outcome']):.4f} |"
            )
        lines.append("")
        lines.append(f"平均 Brier 分：{mean([brier(r['p'], r['outcome']) for r in rows]):.4f}")
        lines.append(f"命中率：{n_hit}/{n_settled} = {n_hit / n_settled:.4f}")
    lines.append("")
    lines.append("## 校准度")
    lines.append("")
    lines.append("概率分桶比较平均预测概率与实际发生率。")
    lines.append("")
    lines.append("| 概率桶 | 条数 | 平均预测概率 | 实际发生率 |")
    lines.append("| --- | ---: | ---: | ---: |")
    for lo, hi in BUCKETS:
        bucket = [r for r in rows if lo <= r["p"] < hi or (hi == 1.0 and r["p"] == 1.0)]
        if not bucket:
            lines.append(f"| [{lo:.1f}, {hi:.1f}) | 0 | — | — |")
        else:
            lines.append(
                f"| [{lo:.1f}, {hi:.1f}) | {len(bucket)} | "
                f"{mean([r['p'] for r in bucket]):.4f} | "
                f"{mean([r['outcome'] for r in bucket]):.4f} |"
            )
    lines.append("")
    lines.append("## 基线对比")
    lines.append("")
    if n_settled == 0:
        lines.append("已结算预测为 0 条。基线对比无法计算。")
    else:
        outcomes = [r["outcome"] for r in rows]
        base_rate = mean(outcomes)
        random_brier = mean([brier(0.5, o) for o in outcomes])
        freq_brier = mean([brier(base_rate, o) for o in outcomes])
        # Leave-one-out per-player historical frequency.
        by_player = defaultdict(list)
        for i, r in enumerate(rows):
            by_player[r["player"]].append(i)
        loo_briers = []
        for i, r in enumerate(rows):
            others_same = [rows[j] for j in by_player[r["player"]] if j != i]
            if others_same:
                p_base = mean([x["outcome"] for x in others_same])
            else:
                others_all = [rows[j] for j in range(n_settled) if j != i]
                p_base = mean([x["outcome"] for x in others_all]) if others_all else 0.5
            loo_briers.append(brier(p_base, r["outcome"]))
        player_brier = mean(loo_briers)
        forecast_brier = mean([brier(r["p"], r["outcome"]) for r in rows])
        lines.append("| 基线 | 计算方法 | 平均 Brier 分 |")
        lines.append("| --- | --- | ---: |")
        lines.append(f"| 预测本身 | 账本概率逐条计算 | {forecast_brier:.4f} |")
        lines.append(
            "| 随机猜测 | 每条预测概率固定为 0.5，与结果无关 | "
            f"{random_brier:.4f} |"
        )
        lines.append(
            "| 历史频率 | 每条预测概率固定为已结算预测的总体发生率 "
            f"（{n_hit}/{n_settled} = {base_rate:.4f}），用样本内发生率计算 | "
            f"{freq_brier:.4f} |"
        )
        lines.append(
            "| 按玩家历史频率 | 每条预测概率取同一玩家其余已结算预测的留一法发生率；"
            "该玩家无其余已结算预测时，取其余全部已结算预测的留一法总体发生率；"
            "无其余已结算预测时取 0.5 | "
            f"{player_brier:.4f} |"
        )
        lines.append("")
        lines.append(
            "说明：历史频率基线使用样本内发生率，它事先看到全部结果，"
            "因此占优。按玩家历史频率基线使用留一法，它没有看到本条结果。"
        )
    lines.append("")
    lines.append("## 结论")
    lines.append("")
    if n_settled == 0:
        lines.append("已结算预测为 0 条。评分没有统计意义。不得据此判断预测能力。")
    elif n_settled == 1:
        lines.append(
            "已结算预测只有 1 条。样本只有 1 条。分数没有统计意义。"
            "不得据此判断预测能力。"
        )
    elif n_settled < 30:
        lines.append(
            f"已结算预测只有 {n_settled} 条。样本小于 30 条。分数没有统计意义。"
            "不得据此判断预测能力。结论须等样本积累后再下。"
        )
    else:
        lines.append(
            f"已结算预测为 {n_settled} 条。样本达到 30 条。"
            "分数可以作为初步判断依据，仍须结合校准度与基线对比阅读。"
        )
    if errors:
        lines.append("")
        lines.append("## 数据问题")
        lines.append("")
        for e in errors:
            lines.append(f"- {e}")
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score a forecast ledger (read-only).")
    parser.add_argument("--ledger", default="forecasts/ledger.json")
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)
    try:
        version, forecasts, counts, rows, errors = score(args.ledger)
    except FileNotFoundError:
        print(f"账本文件不存在：{args.ledger}", file=sys.stderr)
        return 2
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"账本文件无法解析：{exc}", file=sys.stderr)
        return 2
    report = render(args.ledger, version, len(forecasts), counts, rows, errors)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
