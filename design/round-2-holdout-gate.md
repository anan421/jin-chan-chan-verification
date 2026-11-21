# 第 2 轮报告：采用规则改成 hold-out 门控（审计改法 2）

日期：2026-11-21。分支：`loop/round-2-holdout-gate`。状态：已合并到 main。

## 改了什么

三处，全部在分支上一个 commit。

1. `fit.py`
   - 新增 `ADOPTION_RULE`（新采用规则文本）、`evaluate_holdout_gate(fitted_path, placeholder_path)` 与 `_backtest_overall()`。
   - 门控三条同时满足才能升 live：(a) hold-out（S4–S5）上至少三项 M1–M5 优于占位；(b) M1 高于随机基线至少 10pp；(c) M2、M3 高于 50%。样本内违规率只作诊断，不作采用依据。无对照表不得升版。
   - 新增 `--holdout-fitted` / `--holdout-placeholder` 两个参数（须成对给）。只给一个报错退出。分母不一致（m1_n 不同）报错退出，不写采用建议。
   - `fit-report.json` 的 `adoption_rule` 改为新文本；`adoption_recommendation` 改为 `{meets_rule, holdout_gate, in_sample_diagnostic, note}`，其中 `holdout_gate` 是五项并列对照表与三条逐项 verdict；样本内比较移到 `in_sample_diagnostic`，注明只作诊断。
   - 无 hold-out 文件时 `holdout_gate` 为 null，`meets_rule` 为 false。stdout 打印门控逐项结果。
   - 旧的样本内采用判断（拟合窗口违规率不高于占位即采用）已删掉。
2. `design/fitting-layer.md`
   - 第六节新增“采用门控（hold-out gate）”小节，三条写死；注明取代附录 fit02 弱口径。
   - 第七节新增“门控评估：v3 与 fit-2026-11-21-02”，含对照表与逐项 verdict；每次重拟的采用都过门控。
   - 附录“采用规则修订”加一段：弱口径已废止，以第六节为准。
3. `run.sh`：头部注释一句改口径。“missing report（prediction chapter: fail）”改为“missing report（prediction chapter: opinion）”。只改注释，不改行为。

禁区遵守：没改页面；没改 `data.json`；没改 `check.py` 与 Lean 检查路径；没推 GitHub；没写 live 文件（`rules/payoff-model.json` 仍为占位 v2，git 状态只显示上述三文件有改动）。历史运行输出（`runs/fit-real-2026-11-21*/fit-report.json` 等）没动。

## run.sh 全链结果

`./run.sh --predict`，exit 0，overall=pass。报告：`runs/2026-11-21_133458/merged-report.md`（runs/ 在 .gitignore 内，不提交）。

- 检查器：verdict=pass，passed=3，failures=0，gaps=0。558 条 move，18 名玩家，5 赛季，90 排名，12 不变量。
- Lean 构建：exit=0。
- 预测层跑完（symbolic 432 单元、225 SCC、216 吸引子，全是单格死单元；backtest threshold_verdict=below_threshold，预测章 opinion）。预测失败不改 exit code，符合 run.sh 口径。

## fit.py 新规则实证

干跑 1（真实 trace + fit02 的 hold-out 对照）：

```
python3 fit.py traces/trace-latest.json --payoff rules/payoff-model.json \
  --out-dir runs/round-2-holdout-gate/fit-dryrun --fit-id fit-dryrun-round2 \
  --holdout-fitted runs/fit-real-2026-11-21-02/backtest-fitted.json \
  --holdout-placeholder runs/fit-real-2026-11-21-02/backtest-placeholder.json
```

- 拟合逐项复现 fit02：共享 α=1.0、γ=0.9、τ=0.25、违规率 0.952044，权重与 fit02 逐项相同。
- stdout：`fit: hold-out gate: wins=2/5 (need >=3): FAIL; M1-baseline=-1.89pp (need >=10): FAIL; M2=34.19% M3=24.79% (need >50): FAIL; adoption meets_rule=False`
- 输出 `runs/round-2-holdout-gate/fit-dryrun/fit-report.json` 的 `adoption_rule` 是新文本，`adoption_recommendation.holdout_gate` 含五项对照表与三条 verdict，`in_sample_diagnostic` 只记样本内违规率（拟合 0.952044 对占位 0.880952）。

干跑 2（无对照表，fixture trace，`--bootstrap 5`，不给 hold-out 参数）：

- stdout：`fit: hold-out gate: no comparison table supplied; adoption NOT possible (meets_rule=False)`
- 报告里 `holdout_gate` 为 null，`meets_rule` 为 false。

## v3 门控评估结论

数字取自文件实测。v3 的 hold-out 回测是 `runs/holdout-alpha075-2026-11-21/backtest-report.json`（α=0.75 的 v2 效用，S4–S5，n=234，m1_n=41）。占位对照是 `runs/2026-11-21_123045/backtest-report.json`（同一窗口，n=234，m1_n=41）。分母一致。评估由 `fit.py` 的 `evaluate_holdout_gate` 实跑得出（另见设计稿第七节）。

| 指标 | 拟合 v3 | 占位 | 差值 | 输赢 |
|---|---|---|---|---|
| M1 | 0.0% | 0.0% | 0.0pp | 平 |
| M2 | 34.62% | 35.47% | −0.85pp | 差 |
| M3 | 25.21% | 25.21% | 0.0pp | 平 |
| M4 | 31.20% | 32.05% | −0.85pp | 差 |
| M5 | 79.91% | 81.20% | −1.29pp | 差 |

- (a) 优于占位 0 项（差 3 项，平 2 项），不满足。
- (b) M1 0.0%，基线 9.55%，低于基线 9.55pp，不满足。
- (c) M2 34.62%、M3 25.21%，都低于 50%，不满足。

结论：**v3 按新规则应不被采用。三条全不满足。**第一次真拟合自己的 v1 投影回测（M4 31.62%、M5 80.77%）与占位比也是 0 胜 3 差 2 平，结论相同。v3 当时按旧样本内规则升 live 是错的，第 1 轮已回退到占位 v2。

顺带：fit-2026-11-21-02 也过不了门。只赢 M1（+2.41pp）与 M5（+0.43pp），共 2 项；M1 2.41% 低于基线 4.30%；M2 34.19%、M3 24.79% 低于 50%。三条全不满足，不采用。

## 验收

- fit.py 报告新规则：是（两轮干跑实证）。
- run.sh 全过：是（exit 0，overall=pass，历史层全过）。
- v3 按新规则应不被采用已写进报告与设计稿：是（本文件与设计稿第七节）。
