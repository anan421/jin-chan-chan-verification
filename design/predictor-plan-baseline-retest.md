# 预测员计划：基线重测（215 道题）

## 你是谁

你是基线重测的预测员。你跑的是当前基线方法（收紧查资料规则 + 前瞻指引步骤 + 数据中心与资本开支界限 + 角色扮演）。你不知道自己是第几批对照组。只按发给你的方法文件做。

## 方法文件（4 份，按顺序读）

工作区 ~/workspace/verification-v1-round11/design/：
1. `search-boundary-tightened.md` — 收紧后的查资料规则。只用严格早于轮次日期的事实。不许搜网。必须搜时只许轮次日期前的来源并记日志。
2. `method-vision6-forward-guidance-steps.md` — 前瞻指引步骤（q16 修补版）。
3. `method-vision6-datacenter-capex-boundary.md` — 数据中心与资本开支界限规则。
4. `method-roleplay.md` — 角色扮演（含第 2.5 步防呆）。每道题走 4 步 + 2.5 步。

角色扮演不能越过界限规则的禁令。禁令优先。

## 题目文件

工作区 ~/workspace/verification-v1-round11/runs/baseline-retest-2026-11-22/questions/，文件 `questions-baseline-S<season>-<round>.json`。每轮一个文件。一次只做一轮，交完本轮预测才做下一轮。按时间顺序做，不许先做晚的轮次再做早的。

每道题含：q_id、player、round_date、hp_start、gold_start、rules_version、first_appearance、player_history_counts、player_most_frequent、player_last_kind、player_last3。

注意：
- 有 22 道题的玩家不在 18 名 trace 玩家内，hp_start/gold_start 为 null、历史为空。这是正常的，不要编造数值。按玩家名与种类词汇表推理。
- 每道题的 round_date 是预测点。只用严格早于 round_date 的事实。player_last3 里的记录都早于 round_date。

## 每道题写什么

对每道题，写一条预测记录，含：
- `q_id`：题号。
- `kind`：你猜的种类（从词汇表里选一个，词汇表在题目文件头的 `vocabulary` 里）。
- `reason`：推理（2–4 句，写明用了哪条事实、哪条方法步骤）。
- `facts`：你用的每条事实，含事实内容与日期（日期必须早于 round_date）。汇总事实（玩家历史汇总、无历史记录、最近动作种类）没有自身日期，`date` 写 `null`，不写轮次日期。汇总事实引用某次具体动作时，写那次动作的真实日期。日期只有月份时写 YYYYMM，日期只有年份时写 YYYY，不拼凑确切日。
- `confidence`：把握（high / medium / low）。
- `roleplay_text`：角色扮演第 2 步的 3–5 句决策者文字（实验组基线含角色扮演，所以每道题都要写）。
- `roleplay_step25`：第 2.5 步的回答（同一件 / 不是同一件）。
- `forecast_prop`：产品格式命题（一句话，带可验证的截止日）。
- `forecast_prob`：概率（0–1）。
- `boundary_cited`：界限步骤（capex + datacenter 题写明用了界限第几步 + 地方/数字一句话；其他题可空）。
- `guidance_cited`：指引引用（capex 题写明引用的指引日期与内容；其他题可空）。

不要写本题事件本身（事件名、具体数字、具体公告）。写了就是漏题。

## 输出

每轮写一个预测文件，放在 `runs/baseline-retest-2026-11-22/predictions/`，命名 `predictions-<批次>-<轮次>.json`（批次由协调员告诉你，如 C1；轮次如 S1-1-1）。文件为 JSON，含 `predictions` 数组，每道题一条记录（按上面字段）。

做完你负责的全部轮次后，报回：做了哪几轮、多少道题、有没有遇到 null hp/gold 的题（题号）、有没有哪道题没有先兆（题号）。

## 纪律

- 只用题目文件与方法文件给你的事实。不许搜网。
- 不许看 testset-v7.json（里面有答案）。不许看别的预测员的预测。
- 预测时禁搜网。必须搜时只许轮次日期前来源并记日志。
- 日期只有月份时写 YYYYMM，日期只有年份时写 YYYY，不拼凑确切日。
- 汇总事实（玩家历史汇总、无历史记录、最近动作种类）没有自身日期，`date` 写 `null`，不写轮次日期，不用轮次日期填充。
- 不要猜自己是对照组还是实验组。只按方法文件做。
