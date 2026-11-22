#!/usr/bin/env python3
"""Build baseline-retest + round-11 question files for testset-v7 (215 q).

Reads:
  - testset-v7.json (truth; 215 questions, q79 absent; old 98 q_id 0-98,
    new 117 q_id 99-215)
  - raw-trace-real.json (558 moves, 31 rounds, 18 players)
  - ../verification-v1-round8/runs/round8-vision8-2026-11-22/questions/
    (28 round-8 files, 98 old questions; copied verbatim, only renamed)
Writes (runs/baseline-retest-2026-11-22/questions/, gitignored):
  - questions-baseline-S{season}-{round}.json, one per round (36 rounds,
    215 questions). 8 rounds hold old + new questions; 20 hold old only
    (byte-identical copies of the round-8 files, only the name changes);
    8 hold new only.
  - context-all-v7-new.json: per-question context for the 117 new
    questions (same shape as the v5 context file, audit provenance).

Format per question (same as build_questions_v8.py): q_id, player,
round_date, hp_start, gold_start, rules_version, first_appearance,
player_history_counts, player_most_frequent, player_last_kind,
player_last3. No answer field: no kind, no event_name, no action,
no source, no prev_round_kinds.

Player history (v5/v8 logic + the task's date rule):
  - prefix = the player's own moves in rounds strictly BEFORE this
    question's round (round order) AND with date strictly before this
    question's round_date. The round-order bound matters: a later round
    can carry an earlier date (S2 2-6 is dated 20230101, before S2 2-1's
    20230301), and a same-round move can predate an event-date
    round_date -- neither may leak into history. The date bound matters:
    an earlier round can carry a date on/after the round_date (S1 2-5
    is dated 20221201, same as S1 3-2's round_date).
  - player_last3 = the player's moves in the last 3 rounds before this
    round (semantic_kind != "unknown"), with entries dated on/after the
    round_date dropped (the v8 fix).
  - player_history_counts / player_most_frequent / player_last_kind are
    derived from the filtered prefix (v5 tie-break: most frequent, ties
    broken by earliest first appearance in the prefix).
  - first_appearance follows v5: kind_first_round is the earliest round
    where the kind appears in a trace move (semantic_kind) or in any
    testset-v7 question; first_appearance is true iff this question's
    round is that round.

Off-board players (22 new questions: MANUS, OPENCLAW, CURSOR, EU,
CALIF, AMD, CRWV, ZHIPU, KIMI, SAMSUNG, MICRON, MINIMAX, COGNITION,
KARPATHY): no trace move exists, so hp_start / gold_start are null
(honest nulls -- no values invented), history is empty, and
rules_version is the round's rules_version (uniform within a round in
the trace, verified). first_appearance still follows the kind rule.

Vocabulary for merged / new-only files: the round-8 34-kind list in its
original order, plus the 14 testset-v7 kinds it lacks, appended
alphabetically (48 total). Every testset-v7 kind is covered (asserted).
Old-only files keep their original 34-kind vocabulary byte-identical.

Question order in a file: old questions keep their round-8 file order,
then new questions sorted by q_id. (Scoring matches by q_id.)

Checks (run on the in-memory file set BEFORE any file is written; any
failure exits non-zero and writes nothing):
  1. The files contain exactly the 215 q_ids of testset-v7 (q79 absent).
  2. Zero occurrences of every banned field, counted as exact JSON field
     names (recursive scan): prev_round_kinds, kind, action, action_kind,
     hp_delta, gold_delta, event_name, event_real_date, source. A separate
     substring check asserts "prev_round" appears nowhere.
  3. Every question's round_date matches testset-v7.json exactly.
  4. Every file header round_date equals the trace round date (and equals
     round_trace_date).
  5. Every player_last3 entry date is strictly before its question's
     round_date.
  6. hp_start / gold_start are null exactly for the 22 off-board
     questions, ints otherwise.
Validation (reported, not fatal): the same computation is re-run for the
98 old questions against the ROUND-8 trace (this worktree's trace has
since changed 35 S5 moves; the old files are copied verbatim, so the
validation must use the trace the round-8 files were built from) and
diffed against the round-8 files. Expected diffs are only (a)
player_history_counts / player_most_frequent / player_last_kind, where
the task's date rule drops an earlier-round move dated on/after the
round_date, (b) first_appearance, where a new question puts a kind's
first testset appearance in an earlier round, and (c) round_date_override
reason text only (same trace_date, v7 wording vs v6 wording).
Any other diff field fails loudly.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ROUND8_Q = (Path.home() / "workspace" / "verification-v1-round8" / "runs"
            / "round8-vision8-2026-11-22" / "questions")
OUT = ROOT / "runs" / "baseline-retest-2026-11-22" / "questions"

BANNED_FIELDS = {"prev_round_kinds", "kind", "action", "action_kind",
                 "hp_delta", "gold_delta", "event_name", "event_real_date",
                 "source"}
# Round-8 vocabulary, original order (from a round-8 question file).
VOCAB_V8 = ["stargate", "anthropic_ipo", "msft_invest", "blackwell", "r1",
            "musk_table", "colossus", "spacex_xai", "doubao_price_war",
            "bis_rule", "chatgpt", "v3", "overseas_rental", "huang_resign",
            "sec_probe", "tongyi", "hunyuan", "ascend", "doubao", "wenxin",
            "pangu", "llama", "claude", "gemini", "megaspeed", "energy",
            "financing", "capex", "open_source", "datacenter", "compliance",
            "invest_plan", "generic", "openai_mar26"]


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def count_banned(obj, counts):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in BANNED_FIELDS:
                counts[k] += 1
            count_banned(v, counts)
    elif isinstance(obj, list):
        for v in obj:
            count_banned(v, counts)


def build_context(q, trace, kind_first_round):
    """One question's context dict (v5 shape) from the trace."""
    moves = trace["moves"]
    pid2key = trace["pid2key"]
    key2pid = trace["key2pid"]
    round_keys = trace["round_keys"]
    round_pos = trace["round_pos"]
    by_round = trace["by_round"]
    move_by_key = trace["move_by_key"]
    round_index_of = trace["round_index_of"]
    round_rules = trace["round_rules"]

    q_id = q["q_id"]
    player = q["player"]
    rdate = q["round_date"]
    rk = (q["season"], round_index_of[(q["season"], q["round_label"])])
    pid = key2pid.get(player)
    mv = move_by_key.get((q["season"], q["round_label"], player)) if pid is not None else None
    if pid is not None and mv is None:
        fail(f"q{q_id}: trace player {player} has no move in "
             f"S{q['season']} {q['round_label']}")

    if pid is None:
        prefix = []
    else:
        prefix = [m for m in moves
                  if m["player"] == pid
                  and (m["season"], m["round_index"]) < rk
                  and m["date"] < rdate
                  and m["semantic_kind"] != "unknown"]
        prefix.sort(key=lambda m: (m["season"], m["round_index"]))
    hist = [(m["semantic_kind"], m["date"]) for m in prefix]
    counts = Counter(k for k, _ in hist)
    if counts:
        first_seen = {}
        for j, (k, _) in enumerate(hist):
            first_seen.setdefault(k, j)
        most = max(counts, key=lambda k: (counts[k], -first_seen[k]))
        last_kind = hist[-1][0]
    else:
        most, last_kind = None, None

    last3 = []
    dropped = 0
    i = round_pos[rk]
    for rk2 in round_keys[max(0, i - 3):i]:
        for m in by_round.get(rk2, []):
            if pid is not None and m["player"] == pid and m["semantic_kind"] != "unknown":
                if m["date"] < rdate:
                    last3.append([m["semantic_kind"], m["date"]])
                else:
                    dropped += 1
    entry = {
        "q_id": q_id,
        "season": q["season"],
        "round_label": q["round_label"],
        "round": f"S{q['season']} {q['round_label']}",
        "date": rdate,
        "trace_date": trace["trace_date"][(q["season"], q["round_label"])],
        "player": player,
        "hp_start": mv["hp_start"] if mv is not None else None,
        "gold_start": mv["gold_start"] if mv is not None else None,
        "rules_version": (mv["rules_version"] if mv is not None
                          else round_rules[(q["season"], q["round_label"])]),
        "first_appearance": kind_first_round[q["kind"]] == rk,
        "player_history_counts": dict(counts),
        "player_most_frequent": most,
        "player_last_kind": last_kind,
        "player_last3": last3,
    }
    if mv is not None and mv["date"] != rdate:
        entry["round_date_override"] = {
            "trace_date": mv["date"],
            "reason": q.get("round_date_note",
                            "round_date fixed to the event date"),
        }
    return entry, dropped


def question_item(ctx):
    q = {
        "q_id": ctx["q_id"],
        "player": ctx["player"],
        "round_date": ctx["date"],
        "hp_start": ctx["hp_start"],
        "gold_start": ctx["gold_start"],
        "rules_version": ctx["rules_version"],
        "first_appearance": ctx["first_appearance"],
        "player_history_counts": ctx["player_history_counts"],
        "player_most_frequent": ctx["player_most_frequent"],
        "player_last_kind": ctx["player_last_kind"],
        "player_last3": ctx["player_last3"],
    }
    if "round_date_override" in ctx:
        q["round_date_override"] = ctx["round_date_override"]
    return q


def load_trace(path):
    """Load a raw trace file into the structure build_context needs."""
    trace_raw = json.loads(Path(path).read_text(encoding="utf-8"))
    moves = trace_raw["moves"]
    assert len(moves) == 558, f"trace should be 558 moves, got {len(moves)}"
    pid2key = {p["id"]: p["key"] for p in trace_raw["players"]}
    key2pid = {v: k for k, v in pid2key.items()}
    round_keys = sorted({(m["season"], m["round_index"]) for m in moves})
    round_pos = {k: i for i, k in enumerate(round_keys)}
    by_round = defaultdict(list)
    for m in moves:
        by_round[(m["season"], m["round_index"])].append(m)
    move_by_key = {}
    for m in moves:
        move_by_key[(m["season"], m["round_label"], pid2key[m["player"]])] = m
    round_index_of = {(m["season"], m["round_label"]): m["round_index"] for m in moves}
    trace_date = {}
    round_rules = {}
    for m in moves:
        k = (m["season"], m["round_label"])
        trace_date.setdefault(k, m["date"])
        assert trace_date[k] == m["date"], f"mixed trace dates in {k}"
        round_rules.setdefault(k, m["rules_version"])
        assert round_rules[k] == m["rules_version"], f"mixed rules in {k}"
    return {"moves": moves, "pid2key": pid2key, "key2pid": key2pid,
            "round_keys": round_keys, "round_pos": round_pos,
            "by_round": by_round, "move_by_key": move_by_key,
            "round_index_of": round_index_of, "trace_date": trace_date,
            "round_rules": round_rules}


def compute_kind_first_round(moves, questions, round_index_of):
    """Earliest round per kind: trace moves + testset questions (v5 rule)."""
    kind_first_round = {}
    for m in moves:
        if m["semantic_kind"] == "unknown":
            continue
        rk = (m["season"], m["round_index"])
        k = m["semantic_kind"]
        if k not in kind_first_round or rk < kind_first_round[k]:
            kind_first_round[k] = rk
    for q in questions:
        rk = (q["season"], round_index_of[(q["season"], q["round_label"])])
        k = q["kind"]
        if k not in kind_first_round or rk < kind_first_round[k]:
            kind_first_round[k] = rk
    return kind_first_round


def main():
    dry_run = "--dry-run" in sys.argv
    ts = json.loads((ROOT / "testset-v7.json").read_text(encoding="utf-8"))
    questions = ts["questions"]
    truth = {q["q_id"]: q for q in questions}
    assert len(truth) == 215, f"testset-v7 should be 215, got {len(truth)}"
    assert 79 not in truth, "q79 should be absent in testset-v7"
    old_ids = sorted(q for q in truth if q < 99)
    new_ids = sorted(q for q in truth if q >= 99)
    assert len(old_ids) == 98 and len(new_ids) == 117

    trace = load_trace(ROOT / "raw-trace-real.json")
    kind_first_round = compute_kind_first_round(
        trace["moves"], questions, trace["round_index_of"])

    vocab = list(VOCAB_V8)
    for k in sorted({q["kind"] for q in questions} - set(vocab)):
        vocab.append(k)
    assert len(vocab) == 48, f"vocabulary should be 48, got {len(vocab)}"
    assert {q["kind"] for q in questions} <= set(vocab), "vocab misses a v7 kind"
    print(f"vocabulary: {len(vocab)} kinds "
          f"(34 round-8 + {len(vocab) - 34} new)")

    # ---- Validation: recompute the 98 old questions from the ROUND-8
    # trace, diff vs round-8 files. The round-8 trace is used here because
    # this worktree's trace has since changed 35 S5 moves (hp/gold,
    # actions, semantic kinds); the old files are copied verbatim, so the
    # validation must run against the trace the round-8 files were built
    # from. kind_first_round uses the round-8 trace moves + all 215 v7
    # questions, so a new question predating a kind's first appearance
    # still shows up as a (benign, expected) first_appearance diff. ----
    trace_r8 = load_trace(ROUND8_Q.parents[2] / "raw-trace-real.json")
    kfr_r8 = compute_kind_first_round(
        trace_r8["moves"], questions, trace_r8["round_index_of"])

    # ---- Validation: recompute the 98 old questions, diff vs round-8 ----
    old_files = {}
    for f in sorted(ROUND8_Q.glob("questions-round8-*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        old_files[(d["season"], d["round_label"])] = d
    assert len(old_files) == 28, f"expected 28 round-8 files, got {len(old_files)}"
    old_round8 = {}
    for d in old_files.values():
        for q in d["questions"]:
            old_round8[q["q_id"]] = q
    assert set(old_round8) == set(old_ids), "round-8 files != old 98 q_ids"
    allowed_diff = {"player_history_counts", "player_most_frequent",
                    "player_last_kind", "first_appearance"}
    diff_summary = Counter()
    diff_detail = []
    for qid in old_ids:
        ctx, _ = build_context(truth[qid], trace_r8, kfr_r8)
        mine = question_item(ctx)
        ref = old_round8[qid]
        for field in set(mine) | set(ref):
            if mine.get(field) != ref.get(field):
                if field == "round_date_override":
                    # Same override (same trace_date), only the reason text
                    # differs: v7 carries the round-7 wording, v6 the
                    # round-8 wording. Old files are copied verbatim, so
                    # this never reaches the output.
                    m_ovr, r_ovr = mine.get(field), ref.get(field)
                    if (isinstance(m_ovr, dict) and isinstance(r_ovr, dict)
                            and m_ovr.get("trace_date") == r_ovr.get("trace_date")):
                        diff_summary[field] += 1
                        diff_detail.append((qid, field, r_ovr, m_ovr))
                        continue
                    fail(f"old-validation q{qid}: round_date_override "
                         f"trace_date differs: mine={m_ovr!r} round8={r_ovr!r}")
                if field not in allowed_diff:
                    fail(f"old-validation q{qid}: unexpected diff in {field}: "
                         f"mine={mine.get(field)!r} round8={ref.get(field)!r}")
                diff_summary[field] += 1
                diff_detail.append((qid, field, ref.get(field), mine.get(field)))
    print(f"old-98 recomputation vs round-8 files: "
          f"{dict(diff_summary) or 'IDENTICAL'}")
    for qid, field, ref_v, mine_v in diff_detail:
        print(f"  q{qid} {field}: round8={ref_v!r} -> recomputed={mine_v!r}")

    # ---- Build the 117 new questions ----
    new_ctx = []
    total_dropped = 0
    offboard = []
    for qid in new_ids:
        ctx, dropped = build_context(truth[qid], trace, kind_first_round)
        total_dropped += dropped
        if ctx["hp_start"] is None:
            offboard.append(qid)
        new_ctx.append(ctx)
    print(f"new questions built: {len(new_ctx)}; "
          f"player_last3 stale entries dropped: {total_dropped}; "
          f"off-board (hp/gold null): {len(offboard)} q_ids {offboard}")

    # ---- Assemble 36 round files (in memory) ----
    by_round_new = defaultdict(list)
    for ctx in new_ctx:
        by_round_new[(ctx["season"], ctx["round_label"])].append(ctx)
    all_rounds = sorted(set(old_files) | set(by_round_new),
                        key=lambda k: (k[0], trace["round_index_of"][k]))
    files = {}
    for key in all_rounds:
        season, label = key
        tdate = trace["trace_date"][key]
        if key in old_files:
            old_qs = old_files[key]["questions"]
            items = [dict(q) for q in old_qs]
            n_old = len(items)
            # Merged rounds take the v7 vocabulary (new kinds must be
            # answerable); old-only rounds keep the round-8 file exactly.
            vocab_out = vocab if by_round_new.get(key) else old_files[key]["vocabulary"]
        else:
            items, n_old = [], 0
            vocab_out = vocab
        for ctx in sorted(by_round_new.get(key, []), key=lambda c: c["q_id"]):
            items.append(question_item(ctx))
        files[key] = {
            "round": f"S{season} {label}",
            "season": season,
            "round_label": label,
            "round_date": tdate,
            "round_trace_date": tdate,
            "vocabulary": vocab_out,
            "questions": items,
        }
        print(f"S{season}-{label}: {len(items)} questions "
              f"({n_old} old + {len(items) - n_old} new)")

    # ---- Pre-issue checks on the in-memory file set ----
    failures = []
    all_ids = []
    counts = defaultdict(int)
    for key, data in files.items():
        name = f"questions-baseline-S{key[0]}-{key[1]}.json"
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if data["round_date"] != data["round_trace_date"]:
            failures.append(f"{name}: header round_date != round_trace_date")
        if data["round_date"] != trace["trace_date"][key]:
            failures.append(f"{name}: header round_date != trace date")
        if "prev_round" in text:
            failures.append(f"{name}: contains 'prev_round' substring")
        count_banned(data, counts)
        for q in data["questions"]:
            all_ids.append(q["q_id"])
            if q["round_date"] != truth[q["q_id"]]["round_date"]:
                failures.append(
                    f"{name} q{q['q_id']}: round_date {q['round_date']} != "
                    f"testset-v7 {truth[q['q_id']]['round_date']}")
            for e in q.get("player_last3") or []:
                if e[1] >= q["round_date"]:
                    failures.append(
                        f"{name} q{q['q_id']}: player_last3 entry {e} "
                        f"not before round_date {q['round_date']}")
            if (q["hp_start"] is None) != (q["q_id"] in offboard):
                failures.append(
                    f"{name} q{q['q_id']}: hp_start null mismatch "
                    f"(off-board set)")
    if set(all_ids) != set(truth):
        failures.append(
            f"q_id set mismatch: missing {sorted(set(truth) - set(all_ids))}, "
            f"extra {sorted(set(all_ids) - set(truth))}")
    if len(all_ids) != 215:
        failures.append(f"total questions {len(all_ids)} != 215")
    if len(all_ids) != len(set(all_ids)):
        failures.append("duplicate q_ids across files")
    banned_total = {k: counts.get(k, 0) for k in sorted(BANNED_FIELDS)}
    print("banned-field counts (exact JSON field names):", banned_total)
    if any(banned_total.values()):
        failures.append(f"banned fields present: "
                        f"{ {k: v for k, v in banned_total.items() if v} }")
    print(f"rounds: {len(files)}, questions: {len(all_ids)}, "
          f"unique q_ids: {len(set(all_ids))}")
    if failures:
        print("PRE-ISSUE CHECKS FAILED:")
        for f_ in failures:
            print("  FAIL:", f_)
        sys.exit(1)
    print("PRE-ISSUE CHECKS PASSED: 215-ID set exact, banned fields all 0, "
          "round_dates match testset-v7, player_last3 all before round_date.")

    if dry_run:
        print("DRY RUN: no files written.")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for key, data in files.items():
        name = f"questions-baseline-S{key[0]}-{key[1]}.json"
        if key in old_files and not by_round_new.get(key):
            # Old-only round: byte-identical copy of the round-8 file,
            # only the name changes.
            import shutil
            src = next(ROUND8_Q.glob(
                f"questions-round8-S{key[0]}-{key[1]}.json"))
            shutil.copyfile(src, OUT / name)
        else:
            (OUT / name).write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8")
    (OUT.parent / "context-all-v7-new.json").write_text(
        json.dumps(new_ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(files)} files to {OUT} + context-all-v7-new.json")


if __name__ == "__main__":
    main()
