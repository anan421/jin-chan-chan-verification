#!/usr/bin/env python3
"""Round-16 question-file verification (setup stage).

Checks both question dirs (control / experiment) against the testset
shape only (q_id set, round_date); never prints answers. Verifies:
31 files, 215 questions, no forward_guidance, 14 numeric_history
questions / 40 values, q124 has no 500, q127 has no 10, no answer
fields, numeric dates strictly before round_date, player_last3 dates
strictly before round_date, per-file SHA-256 control==experiment.
"""
import glob
import hashlib
import json
import os
import sys

BASE = os.path.expanduser("~/workspace/verification-v1-round16")
RUN = os.path.join(BASE, "runs", "round16-weak-repair-4-2026-11-26")
TS = json.load(open(os.path.join(BASE, "testset-v7.json")))
TRUTH_ROUND_DATE = {q["q_id"]: q["round_date"] for q in TS["questions"]}

ANSWER_KEYS = ("kind", "action", "event_name", "event_real_date", "source")
FAIL = []


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def check_dir(d):
    files = sorted(glob.glob(os.path.join(d, "questions-baseline-*.json")))
    assert len(files) == 31, f"{d}: {len(files)} files"
    qids = []
    n_forward = 0
    n_numeric_q = 0
    n_numeric_v = 0
    numeric_detail = {}
    for f in files:
        data = json.load(open(f))
        assert "questions" in data, f
        for q in data["questions"]:
            qids.append(q["q_id"])
            for k in ANSWER_KEYS:
                if k in q:
                    FAIL.append(f"{f} q{q['q_id']}: answer field {k} present")
            if "forward_guidance" in q:
                n_forward += 1
            if "numeric_history" in q:
                n_numeric_q += 1
                vals = q["numeric_history"]
                n_numeric_v += len(vals)
                numeric_detail[q["q_id"]] = [v["value"] for v in vals]
                for v in vals:
                    assert set(v.keys()) == {"value", "unit", "date", "source"}, (
                        f"q{q['q_id']} numeric item keys {sorted(v.keys())}")
                    if not (int(str(v["date"])) < q["round_date"]):
                        FAIL.append(f"q{q['q_id']}: numeric date {v['date']} "
                                    f"not < round_date {q['round_date']}")
            for kind, dt in q.get("player_last3", []):
                if not (dt < q["round_date"]):
                    FAIL.append(f"q{q['q_id']}: last3 date {dt} not < round_date")
            if q["round_date"] != TRUTH_ROUND_DATE[q["q_id"]]:
                FAIL.append(f"q{q['q_id']}: round_date {q['round_date']} != "
                            f"testset {TRUTH_ROUND_DATE[q['q_id']]}")
    assert sorted(qids) == sorted(TRUTH_ROUND_DATE), "q_id set mismatch"
    assert len(qids) == 215, f"{len(qids)} questions"
    return {"files": len(files), "questions": len(qids),
            "forward_guidance_q": n_forward,
            "numeric_questions": n_numeric_q, "numeric_values": n_numeric_v,
            "numeric_detail": numeric_detail}


res = {}
hashes = {}
for name in ("questions-control", "questions-experiment"):
    d = os.path.join(RUN, name)
    res[name] = check_dir(d)
    hashes[name] = {os.path.basename(f): sha(f) for f in
                    sorted(glob.glob(os.path.join(d, "*.json")))}

same = hashes["questions-control"] == hashes["questions-experiment"]
print(json.dumps(res, indent=2, ensure_ascii=False))
print("per-file SHA-256 control==experiment:", same)
for fn in sorted(hashes["questions-control"]):
    print(fn, hashes["questions-control"][fn])
# numeric specifics
det = res["questions-control"]["numeric_detail"]
assert sorted(det) == [121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131,
                       132, 133, 213], sorted(det)
assert res["questions-control"]["numeric_values"] == 40
assert 500 not in det[124], "q124 still has 500"
assert 10 not in det[127], "q127 still has 10"
assert res["questions-control"]["forward_guidance_q"] == 0
assert res["questions-experiment"]["forward_guidance_q"] == 0
if FAIL or not same:
    print("FAILURES:", FAIL, "hashes same:", same)
    sys.exit(1)
print("OVERALL ALL PASS")
with open(os.path.join(RUN, "scores", "question-verification.json"), "w") as fh:
    json.dump({"checks": res, "sha256": hashes, "identical": same}, fh,
              indent=2, ensure_ascii=False)
