# 第 5 轮：玩家与动作的可行表（审计改法 5，P1）

## 问题（plain 语言）

模型会预测玩家去做他们根本做不了的动作。第 4 轮基线里，
测试窗 234 次预测中有 83 次是违规的（M7 = 35.47%），全是 llama：
llama 是 Meta 的开源模型发布，只有 META 能做，但模型把它预测给
了 16 名玩家（TSMC 10 次、AAPL 8 次、ANTH 7 次、华为 6 次……）。
实时预测里 ALI、TCE、BIDU 三家也被预测去做 llama（M7 = 3/18）。

一句纠正：审计原文说“当前华为的违规率是 100%（anthropic_ipo
p = 1.0）”，那是第 4 轮之前的退化运行（全员 anthropic_ipo
p = 1.0）。第 4 轮基线里，非 ANTH 玩家预测 anthropic_ipo 的次数
已经是 0，实时预测里华为的众数是 claude（p = 0.44）。本轮基线
的违规全部来自 llama，不是 anthropic_ipo。M7 度量先在第 4 轮
报告的 234 条记录上复算：83/234 = 0.3547，与上面一致，度量本身
验证通过。

## 种类映射（审计名 → 实际语义种类，实测 trace-latest.json）

| 审计说的种类 | 实际种类 | 证据 |
|---|---|---|
| anthropic_ipo | anthropic_ipo | 8 条：ANTH 6 条、MUSK 1 条、SFTB 1 条（S5 5-5）。只限 ANTH 预测 |
| huang_resign | huang_resign | 1 条：NVDA，S5 4，20261112。只限 NVDA，且是外生 |
| sec_probe | sec_probe | 1 条：NVDA，S5 6-1，20261120。被调查玩家就是 NVDA，且是外生 |
| llama_open | llama | 5 条：META 3 条、OAI 1 条、MSFT 1 条。只限 META 预测 |
| bis_rule | bis_rule | 4 条：ALI、TSMC、BYTE、DPSK（S5 3 与 S5 5）。外生，不进 argmax |

只限制审计明确指定的 5 个种类。其他 25 个种类（含 unknown 以外
的全部种类）默认全部玩家都可做，没有凭空加限制。注意 trace 里
MUSK 与 SFTB 各有 1 条 anthropic_ipo 的*记录*——那是记录本身
的分类，不是预测；M7 只量预测，不改记录。

## 改法

`rules/payoff-model.json` 新增顶层键 `feasible_kinds`（v1），
每种三字段：`eligible_players`（玩家 key 列表）、`one_shot`、
`exogenous`。语义：

- 表里没有的种类：全部玩家可做，不是一次性，不是外生。
- `exogenous = true`：不进任何玩家的候选集，只作场景输入
  （bis_rule、huang_resign、sec_probe）。
- `eligible_players` 列表：只有这些玩家能被预测做该种
  （anthropic_ipo 仅 ANTH、huang_resign 仅 NVDA、sec_probe 仅
  NVDA、llama 仅 META）。bis_rule 的该字段是 null，表示“作为
  玩家动作不适用”。
- `one_shot = true`：该玩家在前缀历史里已有一次该种类的动作后，
  该种类离开他的候选集（anthropic_ipo、huang_resign、sec_probe）。
  前缀口径：回测每轮只用该轮之前的前缀；实时预测用全部历史。
  本表里全部 one_shot 种类的 eligible 都是单人，所以“该玩家已
  发生”与“全局已发生”结果相同；代码用前者。
- 过滤顺序：规则禁令（banned kinds）先过滤，再过可行表，都在
  最好回应之前。被滤掉的种类不进候选集，也当不了起始动作。

## 命名决定：可行性违规率叫 M7，不是 M6

审计原文把可行性违规率叫“M6”，与已有的 M6 校准度重名（第一批
第 3 轮定的，M6 = 预测概率与实际频率的最大差距）。处理办法：
可行性违规率另起名 M7，写进 `feasible_kinds.naming_note`、
`predict.py` 与 `backtest.py` 的模块说明。M6 校准度不动，
`backtest.py` 与 `predict.py` 的报告同时出 M6（校准度）与
M7（可行性违规率）。

M7 定义：预测种类对该玩家不可做的占比。回测分母是有预测的记录
数（234 条都有预测，无预测为 0）；实时分母是有众数动作的玩家数
（18 名都有）。M7 用同一函数 `predict.kind_feasible` 从表与
前缀独立算出，不靠“掩码跑过”这个假设——掩码若在某条路漏接，
M7 会大于 0。

## 改了哪里

- `rules/payoff-model.json`：只加 `feasible_kinds` 一个顶层键。
  其余顶层键逐项核对，与 main 完全相同。占位参数未动：
  w_hp/w_gold/w_pos/temperature/discount/hp_exponent = 1.0，
  c_lever = 5.0，c_rule = 10.0。文件无对应 schema（rules/ 下
  只有 agent-claim-schema.json，与 payoff 无关），已注明。
- `predict.py`：新增 `load_feasible_kinds`（171 行）、
  `kind_feasible`（180 行）、`apply_feasibility_mask`（213 行）、
  `feasibility_report`（233 行）；`main` 在候选集生成后、起始
  动作过滤前应用掩码（1212–1214 行），报告加 `feasibility`
  小节（1467 行）与摘要行（1502 行）；`run_scenarios` 接
  `feasible` 参数，四个场景分支内同样先过掩码。
  无表的旧 payoff 文件行为不变（全部种类可做）。
- `backtest.py`：模块说明加 M7 定义；`run_window` 接
  `feasible` 参数，每轮候选集在该轮前缀上过掩码；每条记录加
  `m7_violation` 字段；新增 `feasibility_summary`（234 行）；
  报告加 `feasibility` 小节（552 行），总表加
  `m7_violation_rate` / `m7_pass`，摘要加 M7 行。`b1` 基线
  加了空候选集保护（分母为 0 时取 0.0）；本轮实测无空候选集，
  无预测记录为 0。
- 读者相容性（实测）：`fit.py` 在 fixture 上跑完
  （--bootstrap 5，exit 0），输出的 payoff-model-fitted.json
  透传 `feasible_kinds`；`ensemble.py` 在真实 trace 上跑完
  （exit 0，205KB 报告）。两者只读 `parameters` /
  `players` / `player_types`，新顶层键不破坏它们。

## 验收（实测数字，基线为第 4 轮 runs/2026-11-21_134835/）

- run.sh --predict 全过：exit 0，总体 pass，预测章 opinion
  （runs/2026-11-21_135637/merged-report.md）。
- M7 = 0.0：回测 0/234，通过；实时 0/18，通过。非 ANTH 玩家
  预测 anthropic_ipo 的次数：回测 0，实时 0。llama 预测只剩
  META（回测 8 次，实时 0 次——META 实时改投 claude）。
- 测试窗对照（S4–S5，n=234，M1 分母 83）：

  | 指标 | 第 4 轮基线 | 本轮 | 变化 |
  |---|---|---|---|
  | M1 | 1.2%（1/83） | 2.4%（2/83） | 变好 |
  | M2 | 35.47% | 35.47% | 不变 |
  | M3 | 25.21% | 25.21% | 不变 |
  | M4 | 54.70% | 57.26% | 变好 |
  | M5 | 91.88% | 93.16%（首次成信号，margin +10.23pp） | 变好 |
  | M6 校准度 | 0.922 | 0.9507 | 变差 |
  | 退化率（实时） | 0.000 | 0.000 | 不变 |
  | 熵（测试窗） | 1.769 比特 | 2.054 比特 | 变好 |
  | M7 可行性违规率 | 35.47%（83/234） | 0.0%（0/234） | 变好 |

- 结论：**没变好**。按验收规则，任一项变差即不算变好：
  M6 校准度从 0.922 升到 0.9507（越小越好）。最差桶是
  [0.9, 0.99)：2 条记录，平均预测概率 0.9507，实际命中 0。
  M1 多中的 1 次是 S4 第 3 轮 OAI 猜中 capex（另一中仍是 META
  的 open_source）。M5 首次越过信号线，但要小心：llama（期望
  dHP +3.20）被拿掉后，预测的血量增量构成变了，M4/M5 的好转
  可能有一半是构成变化，不是模型懂动作——与第 4 轮同样的
  机械性警告。
- 收敛情况（任务要求报告，不得比第 4 轮更差而不说明）：**变好了**。
  实时预测最好回应 3 次迭代收敛（converged=True，cycle=False）；
  第 4 轮是 20 次迭代跑满、cycle=True。掩码缩小候选集后，
  动态不再来回换动作。
- 场景分支：4 个场景全出，exit 0；众数变化 0，最大分布偏移
  0.0076–0.0704。
- fixture 烟囱：fixture 回测与预测都能跑（无 semantic_kind，
  走 action_kind 回退）；fixture 回测 M7 = 0.0，v3 2 次，
  最大占比 33.8%→35.0%（r1）。

## 还差什么

- M6 校准度 0.9507，仍不通过（阈值 < 0.2）：模型更自信了
  （实时众数概率 0.40–0.88，第 4 轮是 0.30–0.60），命中还是
  接近 0。掩码修的是“能不能做”，没修“有多确定”。
- 实时预测更集中了：claude 16/18（88.9%），第 4 轮是 12/18
  （66.7%）；实时熵 1.224 → 0.503 比特。llama 被拿掉后，META
  也改投 claude。测试窗熵升了、实时熵降了，两个口径要分开看。
- 被挤掉的 llama 预测没有均匀散开：v3 预测从 5 次涨到 32 次，
  分布在 15 名玩家。v3 只有 2 个样本（n=2），收缩后期望仍有
  +2.30 dHP——掩码把玩家从一种薄证据赶到了另一种薄证据上。
  这是第 6 轮 c_rule 与后续估计量工作的弹药，不是本轮的错。
- 测试窗最大种类占比 46.2% → 54.3%（claude 127/234），越过
  第 4 轮立的 50% 线。只作诊断记录，不进本轮验收门（门里只有
  上表 8 项）。
- ensemble.py 与 fit.py 自建候选集，未接掩码（本轮范围外）。
  本轮实测：ensemble 基线众数 0 违规（它的种类是轮次类型
  slug，与语义表基本不重合）；fit 的候选集只用于拟合，不出
  预测。后续轮若动它们，再接掩码。
- 环境备注：跑本轮时 /tmp（512M tmpfs）被 44 个陈旧的
  predict-lean-* 临时目录占满，导致一次场景运行写盘失败
  （0 字节 pred-sc.json）。已清掉这 44 个目录（无运行中进程），
  重跑后全过。predict.py 的 reverify 临时目录从不清理，是
  长期隐患，值得后轮修掉。

## 禁区遵守

没改页面；没改 data.json；没改 check.py 与 Lean 检查路径；
没推 GitHub；没合并到 main。live payoff-model.json 只加
feasible_kinds 表，占位参数未动。只改 predict.py、backtest.py、
rules/payoff-model.json 与本设计稿。
