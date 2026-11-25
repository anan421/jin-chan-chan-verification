#!/usr/bin/env python3
"""Check fact dates in prediction files (U3 fix checker).

Rule (design/search-boundary-tightened.md 1.1, 1.2):
  - A summary fact (player history summary, no history, latest action
    kind) has no date of its own. Its `date` must be null. It must never
    carry the round_date.
  - A fact date must be strictly earlier than the question round_date.
    A date equal to round_date is a violation. A later date is a
    violation.
  - A month-only date is YYYYMM (6 digits). It counts as YYYYMM01.
  - A year-only date is YYYY (4 digits). It cannot be judged against
    round_date. It is a warning, not a violation (audit precedent:
    10 year-only facts in the baseline retest were left unjudged).
  - A full date is YYYYMMDD or YYYY-MM-DD.

Usage:
  python3 check_fact_dates.py runs/baseline-retest-2026-11-22/predictions
  python3 check_fact_dates.py --testset testset-v7.json <pred-dir> [...]
  python3 check_fact_dates.py --self-test   # fixture: fixed format -> 0

Exit code: 0 when violations == 0, else 1. Warnings do not change
the exit code. Output is JSON on stdout (one summary object).

Round-14 fix (2026-11-25, verification-v1-round14):
  The round-13 audit found 521 MISSING_DATE findings on the round-13
  predictions, and re-checked every one: all 521 were false positives.
  The summary patterns were too narrow. This revision adds the
  round-13 wording families (see SUMMARY_PATTERNS): history counts
  with a numeral between the noun and the verb, latest-action-kind
  phrasings, first-appearance, round-date-as-absence, no-quotable-
  guidance, and the round-start blood/gold snapshot. It also reads
  the `text` fact key on equal footing with `content` (round-13
  E2/E3 facts use `text`). Nothing else changes: a dated fact is
  still judged against round_date exactly as before.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SUMMARY_PATTERNS = (
    # Round-11 originals (unchanged).
    re.compile(r"玩家历史"),
    re.compile(r"历史动作"),
    re.compile(r"无历史记录"),
    re.compile(r"历史为空"),
    re.compile(r"最近一次动作"),
    re.compile(r"最近一轮"),
    re.compile(r"player_last3"),
    re.compile(r"player_history_counts"),
    re.compile(r"最常做"),
    re.compile(r"最常做的种类"),
    # Round-14 additions. Each pattern is a summary / absence / state
    # phrasing with no date of its own (round-13 audit, 521 false
    # positives, all null-date facts in the four audit categories
    # plus the no-guidance statements). They only exempt a fact
    # whose `date` is null; a dated fact is still date-checked.
    # History counts: the numeral sits between 历史 and 动作, so the
    # old contiguous "历史动作" never matched. Covers 历史 3 次动作,
    # 历史三次动作, 历史两次动作, 历史次数：, 历史：, 历史只有 1 次动作,
    # 历史仅 1 次动作, 历史 Claude 2 次, 历史昇腾 2 次, 历史汇总,
    # 玩家历史动作 (0 occurrences in round 13; listed in the audit).
    re.compile(r"历史汇总"),
    re.compile(r"历史次数"),
    re.compile(r"历史[:：]"),
    re.compile(r"历史\s*(?:\d+|[一二两三四五六七八九十]+)\s*次动作"),
    re.compile(r"历史(?:只有|仅|只)\s*(?:\d+|[一二两三四五六七八九十]+)?\s*(?:次)?动作"),
    re.compile(r"历史\s*[A-Za-z_\u4e00-\u9fa5]+\s+\d+\s*次"),
    re.compile(r"玩家历史动作"),
    # Latest-action kind: 最近动作种类 / 最近种类 / 最近一类动作是 X /
    # 最近一种类 / 最近两次动作 / 最近三轮动作 / 最新动作种类 /
    # 此前动作种类 / 玩家上一动作种类为 X. The bare "最近动作" also
    # covers 最近动作： and 无带日期的最近动作.
    re.compile(r"最近动作"),
    re.compile(r"最近[一二两三四五六七八九十\d]+[次轮]动作"),
    re.compile(r"最近种类"),
    re.compile(r"最近一类动作"),
    re.compile(r"最近一种类"),
    re.compile(r"最新动作种类"),
    re.compile(r"此前动作种类"),
    re.compile(r"上一动作种类"),
    re.compile(r"最近三轮记录"),
    # No history: first appearance in this round.
    re.compile(r"首次出现"),
    # No usable precursor: the fact states the round date itself and
    # that no earlier fact exists. The date in the text IS the round
    # date, not a fact date.
    re.compile(r"轮次日期为"),
    # No quotable forward guidance (guidance_cited absence statements).
    re.compile(r"无可引用的(?:前瞻)?指引"),
    re.compile(r"题目文件(?:未提供|无|里没有).{0,8}指引"),
    # Round-start state snapshot: blood and gold at round start.
    re.compile(r"轮次开始时血量"),
)
MONTH_MENTION = re.compile(r"(\d{4})[年\-](\d{1,2})月(?!\d)")
DAY_MENTION = re.compile(r"\d{1,2}日")


def norm_date(raw):
    """Return (kind, comparable_int_or_None, had_suffix). kind: null,
    month, year, full, bad. had_suffix is True when the raw value
    carried a "前" / "前累计" suffix (round-11 predictor habit)."""
    if raw is None:
        return "null", None, False
    s = str(raw).strip()
    # Predictor habit seen in round 11: a round date with a "before"
    # suffix, e.g. "20250127前累计". The suffix adds no date info.
    # Strip it, then judge the date itself. The suffix is reported
    # separately: the round date is still stamped on a summary fact.
    had_suffix = bool(re.search(r"(前累计|前)$", s))
    s = re.sub(r"(前累计|前)$", "", s)
    if re.fullmatch(r"\d{6}", s):
        return "month", int(s + "01"), had_suffix
    if re.fullmatch(r"\d{4}-\d{2}", s):
        return "month", int(s.replace("-", "") + "01"), had_suffix
    if re.fullmatch(r"\d{8}", s):
        return "full", int(s), had_suffix
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return "full", int(s.replace("-", "")), had_suffix
    if re.fullmatch(r"\d{4}", s):
        return "year", None, had_suffix
    return "bad", None, had_suffix
    if re.fullmatch(r"\d{4}-\d{2}", s):
        return "month", int(s.replace("-", "") + "01"), had_suffix
    if re.fullmatch(r"\d{8}", s):
        return "full", int(s), had_suffix
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return "full", int(s.replace("-", "")), had_suffix
    if re.fullmatch(r"\d{4}", s):
        return "year", None, had_suffix
    return "bad", None, had_suffix


def fact_text_and_key(fact):
    """Return (text, key) for a fact. `content` and `text` are equal:
    `content` wins when non-empty, otherwise `text`. Round-13 E2/E3
    facts use `text` only (123 facts); the old inline fallback did
    the same, this makes it explicit and auditable."""
    content = fact.get("content")
    if content:
        return content, "content"
    return fact.get("text") or "", "text" if "text" in fact else "content"


def is_summary(content):
    return any(p.search(content or "") for p in SUMMARY_PATTERNS)


def check_file(path, round_dates):
    """Check one prediction file. Return (findings, counts)."""
    findings = []
    counts = {"facts": 0, "violations": 0, "warnings": 0}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:  # unreadable file: one finding, no crash
        findings.append({"file": str(path), "type": "UNREADABLE",
                         "detail": str(exc)})
        counts["violations"] += 1
        return findings, counts
    for pred in data.get("predictions", []):
        q_id = pred.get("q_id")
        rd = round_dates.get(q_id)
        if rd is None:
            continue
        rd = int(str(rd).replace("-", ""))
        for fact in pred.get("facts", []) or []:
            counts["facts"] += 1
            content, fact_key = fact_text_and_key(fact)
            kind, value, had_suffix = norm_date(fact.get("date"))
            base = {"file": Path(path).name, "q_id": q_id,
                    "round_date": rd, "fact": content,
                    "fact_key": fact_key,
                    "fact_date_raw": fact.get("date")}
            if kind == "null":
                if is_summary(content):
                    continue  # fixed format: summary fact, no date
                findings.append({**base, "type": "MISSING_DATE",
                                 "detail": "date is null but the fact "
                                 "is not a summary fact"})
                counts["violations"] += 1
            elif kind == "bad":
                findings.append({**base, "type": "BAD_FORMAT",
                                 "detail": "date is not null, YYYYMM, "
                                 "YYYY, YYYYMMDD or YYYY-MM-DD"})
                counts["violations"] += 1
            elif kind == "year":
                findings.append({**base, "type": "YEAR_ONLY_UNJUDGEABLE",
                                 "detail": "year-only date cannot be "
                                 "judged against round_date"})
                counts["warnings"] += 1
            elif kind in ("month", "full"):
                if value is not None and value >= rd:
                    if had_suffix and value == rd:
                        # Same stamp, different surface: "20250127前累计"
                        # states "cumulative before round_date", so the
                        # old audit did not count it as a date violation.
                        # Under the new rule it is still non-compliant:
                        # a summary fact must carry null, not the round
                        # date with a suffix. Reported separately so the
                        # audit's 84 stays intact.
                        findings.append({
                            **base, "type": "ROUND_DATE_STAMPED_SUFFIX",
                            "detail": "summary fact carries the round "
                            "date with a 'before' suffix; new rule "
                            "requires date null"})
                    else:
                        findings.append({
                            **base, "type": "DATE_EQUALS_ROUND_DATE"
                            if value == rd else "DATE_AFTER_ROUND_DATE",
                            "detail": "fact date is not strictly "
                            "earlier than round_date"})
                    counts["violations"] += 1
                elif kind == "full":
                    # Heuristic warning only: content states a month but
                    # no day, yet the date carries an exact non-1st day.
                    # It may be a real exact date, so a human must judge.
                    day = value % 100
                    if day != 1 and MONTH_MENTION.search(content) \
                            and not DAY_MENTION.search(content):
                        findings.append({
                            **base, "type": "MONTH_FABRICATION_SUSPECT",
                            "detail": "content states only a month but "
                            "the date carries an exact day; human review "
                            "needed"})
                        counts["warnings"] += 1
    return findings, counts


def self_test():
    """Fixture check: fixed-format facts must yield 0 violations."""
    import tempfile
    fixture = {"predictions": [
        {"q_id": 1, "facts": [
            {"content": "谷歌玩家历史：gemini 3 次，最常做 gemini",
             "date": None},
            {"content": "Manus 玩家历史为空", "date": None},
            {"content": "2021-11 马斯克发起投票", "date": "202111"},
            {"content": "2021-12 马斯克当选年度人物",
             "date": "2021-12-01"},
            {"content": "某事件发生于 2024 年", "date": "2024"}]},
        {"q_id": 2, "facts": [
            {"content": "谷歌玩家历史：gemini 3 次", "date": "20250127"}]},
        # Round-14: `text`-key facts are treated exactly like `content`.
        {"q_id": 3, "facts": [
            {"text": "最近动作种类：gemini", "date": None},
            {"text": "某公司发布新模型", "date": None},
            {"text": "某事件发生于 2024 年", "date": "20250127"}]},
    ]}
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "predictions-X-S1-1-1.json"
        p.write_text(json.dumps(fixture, ensure_ascii=False),
                     encoding="utf-8")
        findings, counts = check_file(p, {1: 20250127, 2: 20250127,
                                          3: 20250127})
    bad = [f for f in findings if f["type"] != "YEAR_ONLY_UNJUDGEABLE"]
    print(json.dumps({"fixture_facts": counts["facts"],
                      "violations": counts["violations"],
                      "warnings": counts["warnings"],
                      "findings": findings},
                     ensure_ascii=False, indent=2))
    # Expect exactly 3 violations (the stamped q2 summary fact, the
    # text-key generic dateless fact, the text-key dated fact) and
    # 1 warning (the year-only fact). The fixed q1 facts and the
    # text-key summary fact must pass.
    assert counts["violations"] == 3, counts
    assert counts["warnings"] == 1, counts
    assert sorted(f["type"] for f in bad) == [
        "DATE_EQUALS_ROUND_DATE", "DATE_EQUALS_ROUND_DATE",
        "MISSING_DATE"], bad
    print("SELF-TEST PASSED: fixed format passes, stamped fact is caught.")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    # Targets are the non-option arguments, excluding the value that
    # follows --testset. (Round-13 bug: the --testset path itself was
    # treated as a target, inflating the file count by one.)
    args = []
    skip_next = False
    for a in argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if a == "--testset":
            skip_next = True
            continue
        if not a.startswith("--"):
            args.append(a)
    testset = ROOT / "testset-v7.json"
    for i, a in enumerate(argv):
        if a == "--testset" and i + 1 < len(argv):
            testset = Path(argv[i + 1])
    ts = json.loads(testset.read_text(encoding="utf-8"))
    questions = ts["questions"] if isinstance(ts, dict) else ts
    round_dates = {q["q_id"]: q["round_date"] for q in questions}
    all_findings = []
    totals = {"files": 0, "facts": 0, "violations": 0, "warnings": 0}
    for target in args:
        for path in sorted(Path(target).glob("*.json")) \
                if Path(target).is_dir() else [Path(target)]:
            findings, counts = check_file(path, round_dates)
            totals["files"] += 1
            totals["facts"] += counts["facts"]
            totals["violations"] += counts["violations"]
            totals["warnings"] += counts["warnings"]
            all_findings.extend(findings)
    by_type = {}
    for f in all_findings:
        by_type[f["type"]] = by_type.get(f["type"], 0) + 1
    print(json.dumps({"totals": totals, "by_type": by_type,
                      "findings": all_findings},
                     ensure_ascii=False, indent=2))
    return 0 if totals["violations"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
