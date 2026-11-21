#!/usr/bin/env python3
"""Build per-round question files for round 4 (exception override).

Input: search-first full-83 predictions (baseline). Output: one question
file per round containing ONLY the baseline guess + its cited facts +
reasoning. The actual answers (actual_kind, correct) are stripped, so a
predictor who only reads their own round's file cannot see any answer.
"""
import json
import os
from collections import OrderedDict

SRC = "/home/hatch/workspace/verification-r2-search/runs/search-first-full83-2026-11-22/predictions-full83.json"
OUTDIR = "/home/hatch/workspace/verification-r4-exception/runs/exception-override-round4-2026-11-22"

VOCAB = ["anthropic_ipo", "ascend", "bis_rule", "blackwell", "capex",
         "chatgpt", "civil_war", "claude", "colossus", "doubao",
         "doubao_price_war", "energy", "financing", "gemini",
         "huang_resign", "hunyuan", "llama", "megaspeed", "msft_invest",
         "musk_table", "open_source", "overseas_rental", "pangu", "r1",
         "sec_probe", "spacex_xai", "stargate", "tongyi", "v3", "wenxin"]

def main():
    preds = json.load(open(SRC))
    assert len(preds) == 83, len(preds)
    # safety: confirm no answer fields leak into output
    rounds = OrderedDict()
    for p in preds:
        assert "actual_kind" in p and "correct" in p  # source has them; we strip
        q = {
            "player": p["player"],
            "date": p.get("date", p.get("round_date")),
            "baseline_kind": p["predicted_kind"],
            "baseline_confidence": p["confidence"],
            "baseline_facts": p["facts_used"],
            "baseline_reasoning": p["reasoning"],
            "event_given": p["event_given"],
            "event_real_date": p.get("event_real_date"),
            "unfair_date": p.get("unfair_date", False),
            "first_appearance": p["first_appearance"],
        }
        rounds.setdefault(p["round"], []).append(q)
    os.makedirs(OUTDIR, exist_ok=True)
    for rnd, qs in rounds.items():
        dates = {q["date"] for q in qs}
        assert len(dates) == 1, (rnd, dates)
        fname = "questions-" + rnd.replace(" ", "-") + ".json"
        doc = {
            "round": rnd,
            "date": dates.pop(),
            "vocabulary": VOCAB,
            "questions": qs,
        }
        with open(os.path.join(OUTDIR, fname), "w") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        print(fname, len(qs), "questions")
    # leak check: no answer text anywhere in output
    for fn in os.listdir(OUTDIR):
        txt = open(os.path.join(OUTDIR, fn)).read()
        assert "actual_kind" not in txt and '"correct"' not in txt, fn
    print("leak check passed: no actual_kind / correct in question files")
    print("rounds:", len(rounds), "total:", sum(len(v) for v in rounds.values()))

if __name__ == "__main__":
    main()
