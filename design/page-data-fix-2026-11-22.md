# 页面数据修复与重验证（2026-11-22）

Gu 已批准：修页面 data.json 两处错误，修完重跑一次完整验证。

## 改了什么

两处错误，每处在页面 data.json 里出现两个字段，共改了四个地方。只改这两处错误，别的不动。

**错误 1：S5 2-1，Anthropic 递交招股文件日期写错**
- 原文把递交写成 2026-10-06（轮次日期当天）。公开记录是 2026-10-26（TechCrunch、PYMNTS、USA Today、LeverageShares、CASRAI 五家来源一致）。
- 改了两处，都改成“Anthropic 将于 10 月 26 日公开递交招股文件”：
  - `seasons > S5 > rounds > 2-1 > global`：英伟达创历史高点 239.24 美元。Anthropic 将于 10 月 26 日公开递交招股文件。承诺细节公开……
  - `roundEvidence > S5:2-1 > items[0].label`：英伟达 2026-10-06 收盘 239.24 美元创纪录，盘中高点 243.37 美元；Anthropic 将于 10 月 26 日公开递交招股文件。
- 改法与题集重设计修好文件（facts-roundEvidence-fixed.json）里的文字一字相同。

**错误 2：S5 1-1，roundEvidence 挂了一条过期的 S-1/A**
- 那条是 2026-11-10 的 S-1/A（EDGAR 0001628280-26-072484），晚于轮次日期 2026-01-01，共 314 天。
- 删了两处（同一条证据的两个指针）：
  - `roundEvidence > S5:1-1 > items`：删掉唯一的 S-1/A 条目，变为空数组。
  - `roundEvidence > S5:1-1 > moves`：删掉 "4:ANTH" 指针（它指同一条 S-1/A，留着就是悬空引用），变为空对象。
- `status` 从 verified 改为 opinion（删后已无任何证据，verified 会谎称仍有验证）。
- `note` 未动（它讲的是本轮其余大动作无逐动作证据，仍为真）。

**备份**：改之前已备份原文件为 `assets/data.json.bak-2026-11-22`（sha256 07995677…，与改前一致）。

**diff 核对**：改后文件与备份逐行比对，只差上面四处，别的一字未动。

## 页内数据哈希变了

- 改前（页面自己的 JS 算法，node 复算）：fnv1a `13c90d88`。
- 改后（同一算法）：fnv1a `cdc40b08`。
- 变了，因为 S5 2-1 的 global 在 SEASONS 里面，而哈希只覆盖 PLAYERS、SEASONS、OPENINGS。只改 roundEvidence 的话哈希不会变，但 global 在 SEASONS 里，所以一定会变。
- 附带发现：之前记录的哈希 `8d90a977`，用页面自己的代码在当前文件上复算不出来（node 算出 `13c90d88`）。那个记录值可能来自更早的数据版本或别的算法。改前改后的对比用的是同一套算法，所以“变了”这个结论是可靠的。

## 重抽取与重验证

**抽取**：改好的 data.json 同步到管线 `~/workspace/verification/data.json`（新 sha256 `08ca9a1a…`，旧 `07995677…`）。重新抽取 trace：新 trace `traces/trace-2026-11-22.json`（sha256 `15e38b50…`），558 条、18 人、5 赛季。除了 meta 里的 source_sha256 变了，trace 正文与旧 trace 一字相同（两次改的都是叙述文字和证据指针，不动 558 条增量）。

**一个先有的问题**：第一次跑 convert 没加 `--page`，失败了（FACTS 交叉检查：`1073.4` 不在 data.json 里）。查后确认这不是我的改动造成的：拿备份（改前文件）跑同样失败。`1073.4` 只在 index.html 里（“813.4+260=1073.4”），不在 data.json 里。上一次成功抽取（2026-11-21 13:18）的 provenance 显示 `1073.4` 检查通过，说明当时加了 `--page`。加上 `--page index.html` 后 convert 通过。以后跑 convert 都要加 `--page`。

**验证结果：pass**。`./run.sh` 退出码 0。报告在 `runs/2026-11-22_010812/`：
- 快速检查器：pass（通过 3，失败 0，数据不足 0；558 条、18 人、5 赛季、90 个排名、12 条不变量）。
- Lean 4：pass（构建退出码 0，trace 生成退出码 0）。
- Agent gate：skipped（本次没给 claims，未跑）。
- 预测章：not_run（本次没给 --predict，历史层验证不含预测）。

## 纪律

live 模型一字未动：`rules/payoff-model.json`、`predict.py`、`backtest.py` 对 main 零差异。只改了 `data.json`、`raw-trace-real.json`、`raw-trace-real.provenance.json`（后两者是重新抽取的产物）。

## 交付物

- 页面数据：`~/workspace/ts-spaces/jin-chan-chan-fu-pan-ai-da-ting-2022-2026/assets/data.json`（已改）；备份 `assets/data.json.bak-2026-11-22`。
- 管线数据：`~/workspace/verification/data.json`（已同步，新 sha256 `08ca9a1a…`）。
- 新 trace：`~/workspace/verification/traces/trace-2026-11-22.json`（sha256 `15e38b50…`）；`traces/trace-latest.json` 已更新。
- 验证报告：`~/workspace/verification/runs/2026-11-22_010812/merged-report.md`（总体 pass）。
- 本报告：`~/workspace/verification/design/page-data-fix-2026-11-22.md`。
