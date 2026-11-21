"""Audit round 5 predictions for contamination + clean score.

Audit standard (applied uniformly, decided before reading the facts):
- CONTAMINATED: a fact that reports this player's own action in this round
  as a news item about that player, beyond the general event; OR a fact
  dated after the question's event_real_date that states the player's action.
- NOT contamination: general event announcements that name the player among
  participants (Stargate announcement, model release, rule publication,
  earnings, IPO filing) -- the predictor still has to map the event to a
  kind, and the mapping is often wrong (Grok 4 -> spacex_xai vs colossus;
  Ernie 4.5 open-source -> wenxin vs open_source; NVDA in Stargate ->
  blackwell vs stargate). Inferences from a general fact about another
  player (e.g. "Tencent is in the same wave" from Huawei's Feb 1 launch)
  are inference, not contamination.
- The given headline event itself is input, not contamination.
- Facts from facts-roundEvidence.json round-level entries are allowed input;
  per_move_keys entries (the game's own record of the player's action) would
  be contamination -- none were used.

Result of the audit (read all 83 questions' facts_used):
- q53 (S5 1-1 HUAWEI): 2 facts dated 2026-09-30, after the 2026-09-17
  cutoff, stating the player's Ascend action (Xu Zhijun's statement +
  IDC data). CONTAMINATED. Excluded from the clean score.
- All other 82 questions: clean. No per-move evidence cited; no
  "[player]+[kind]" searches; only q53 has facts after the cutoff.

Writes: runs/date-fix-round5-2026-11-22/audit.json
"""
import json, os

RUNDIR = "/home/hatch/workspace/verification-r5-date/runs/date-fix-round5-2026-11-22"
scored = json.load(open(os.path.join(RUNDIR, "scored-date-fix.json")))
summary = json.load(open(os.path.join(RUNDIR, "score-summary.json")))

CONTAMINATED = {
    53: {
        "round": "S5 1-1", "player": "HUAWEI",
        "reason": "2 facts dated 2026-09-30, after the 2026-09-17 cutoff, "
                  "stating the player's Ascend action (Xu Zhijun's statement "
                  "at the Sept 30 Huawei Connect conference + IDC data). "
                  "Date violation + states the player's own action.",
        "facts": [
            "2026-09-30 徐直军在华为全联接大会上表示，昇腾在中国市场的出货量已经超过英伟达",
            "2026-09-30 IDC 数据：2026 年上半年中国数据中心 AI 加速器市场英伟达 34%、华为昇腾 28%，差距从 31 个百分点收窄到 6 个百分点",
        ],
    },
}

clean = [s for s in scored if s["q_idx"] not in CONTAMINATED]
sf_clean = sum(1 for s in clean if s["search_first_correct"])
df_clean = sum(1 for s in clean if s["date_fix_correct"])
print(f"full: search-first {summary['search_first']}/83, date-fix {summary['date_fix']}/83")
print(f"clean (excl. q53): search-first {sf_clean}/{len(clean)}, date-fix {df_clean}/{len(clean)}")

def group_stats(rows, name):
    sf = sum(1 for s in rows if s["search_first_correct"])
    df = sum(1 for s in rows if s["date_fix_correct"])
    print(f"  {name}: search-first {sf}/{len(rows)}, date-fix {df}/{len(rows)} (diff {df - sf:+d})")
    return {"n": len(rows), "search_first": sf, "date_fix": df}

print("clean breakdown:")
changed = [s for s in clean if s["cutoff_changed"]]
unchanged = [s for s in clean if not s["cutoff_changed"]]
loosened = [s for s in clean if s["loosened"]]
tightened = [s for s in clean if s["tightened"]]
g_changed = group_stats(changed, "cutoff changed")
g_unchanged = group_stats(unchanged, "cutoff unchanged")
g_loosened = group_stats(loosened, "loosened")
g_tightened = group_stats(tightened, "tightened")

# sensitivity: without the S4 3-2 energy round (theme-round artifact)
no_energy = [s for s in clean if s["round"] != "S4 3-2"]
sf_ne = sum(1 for s in no_energy if s["search_first_correct"])
df_ne = sum(1 for s in no_energy if s["date_fix_correct"])
print(f"  without S4 3-2 (energy round): search-first {sf_ne}/{len(no_energy)}, date-fix {df_ne}/{len(no_energy)}")

# sensitivity: without S4 3-2 AND without q53 (same as clean without energy)
print(f"  S4 3-2 alone: search-first {sum(1 for s in scored if s['round']=='S4 3-2' and s['search_first_correct'])}/10, "
      f"date-fix {sum(1 for s in scored if s['round']=='S4 3-2' and s['date_fix_correct'])}/10")

audit = {
    "standard": "see module docstring",
    "contaminated": CONTAMINATED,
    "contaminated_count": len(CONTAMINATED),
    "full": {"n": 83, "search_first": summary["search_first"], "date_fix": summary["date_fix"]},
    "clean": {"n": len(clean), "search_first": sf_clean, "date_fix": df_clean},
    "clean_changed": g_changed,
    "clean_unchanged": g_unchanged,
    "clean_loosened": g_loosened,
    "clean_tightened": g_tightened,
    "without_S4_3_2": {"n": len(no_energy), "search_first": sf_ne, "date_fix": df_ne},
    "date_violations": 2,
    "borderline_but_clean": {
        7: "TCE S4 1-1: fact '腾讯云同属这一波' is the predictor's inference "
           "from Huawei's Feb 1 R1 launch (source labeled '其他玩家事实'), "
           "not a sourced news item about Tencent's action. Inference, not contamination.",
    },
}
json.dump(audit, open(os.path.join(RUNDIR, "audit.json"), "w"),
          ensure_ascii=False, indent=1)
print("wrote audit.json")
