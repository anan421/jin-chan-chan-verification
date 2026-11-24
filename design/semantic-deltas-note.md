# 语义差异记录（Phase 1，文档，不改代码）

- 项目：Jin Chan Chan Verification
- 基准提交：main 8fa382a
- 记录日期：2026-11-24
- 记录范围：Phase 0 报告第 3.6 节列出的语义不一致中，本轮只修 ensemble.py 的种类错位。其余差异只记录在本文档中，不改代码。
- 术语：semantic_kind 指实质动作线索。action_kind 指回合类型代码或旧 fixture 的动作名。kind_of 指 predict.py:172、backtest.py:114、fit.py:312 定义的同一规则：读 semantic_kind，缺失时回落到 action_kind。

## 0. 本轮已修（对照项，不属于未修差异）

- 位置：ensemble.py setup（约第 193–210 行）。
- 修前：setup 用 m["action_kind"] 构造候选动作与起始动作。setup 调用 predict.make_expectation(per_mean, glob_mean) 时未传 global_mean。
- 修后：setup 用 predict.kind_of 构造候选动作与起始动作。候选集排除 "unknown"，与 predict.py:1127 与 backtest.py:348–349 一致。setup 经 predict.expectation_support 取全局均值，并传给 make_expectation，与 predict.py:1137–1139 与 backtest.py:325–328 一致。
- 成员权重未动。15 名成员的 v1 占位值保持原样。效用函数版本未动。predict.py、backtest.py、fit.py、check.py、gate.py 未动。
- Phase 0 推论验证：Phase 0 推论称修前真实 trace 上期望全部回落为 (0.0, 0.0)。核查结果否定该推论。修前候选集为 13 个 action_kind 值。其中 4 个（r1、huang_resign、anthropic_ipo、sec_probe）恰好与 semantic_kind 同名，各只有 1 条动作，且该动作的 action_kind 等于 semantic_kind。32 名行动玩家乘 13 个候选等于 416 次查找。其中 288 次回落为 (0.0, 0.0)，占 69.2%。其中 128 次命中真实均值，占 30.8%。r1 的全局均值为 (0.375, 3.125)。其余三者的全局均值均为负。r1 因此成为 31 名玩家的众数动作。TSMC 的众数动作为 wild。修后候选集为 29 个语义种类。928 次查找全部命中非零期望。全局均值 (0.253, 0.5126) 兜底未命中项。众数动作全部变为 claude。验证命令与数值见第 6 节。

## 1. fit 与 backtest 的拟合窗口不同

- 位置：fit.py:762（--fit-seasons 默认 "1,2,3"）；fit.py:324–337（build_decisions 按 fit_seasons 过滤动作）；backtest.py:446–447（fit_seasons = seasons[:3]，test_seasons = seasons[3:]）；rules/calibration.json（fit_window 为 ["S1", "S2", "S3"]）。
- 现状：真实 trace 的赛季为 S0–S6。fit 的默认窗口为 S1–S3。backtest 的动态窗口为 S0–S2。两者相差一个赛季。backtest 含 S0，不含 S3。fit 含 S3，不含 S0。fixture 上两者一致。fixture 的赛季为 S1–S5，前 3 个赛季为 S1–S3。calibration.json 记录的窗口与 fit 一致，与 backtest 在真实 trace 上的窗口不一致。backtest 的测试窗口为 S3–S6。S3 既在 fit 的拟合窗口内，又在 backtest 的测试窗口内。
- 为什么本轮不改：改动任一窗口都会改变已测量的结果。拟合权重、校准温度（11.554）与第 11 轮基线数字均基于现有窗口。统一窗口属于方法定义变更。Phase 4 须先在两个窗口上分别跑对照实验，再定夺统一口径。

## 2. 排名并列处理不同

- 位置：predict.py:332–337（ranks_of）；data.json meta.derived.standings；check.py:311–320 与 349–357（C9）；lean/Verification/Model.lean:46–50（Ranking 结构含 rank 字段）与 307–346（checkGroup、checkLedger）。
- 现状：三处口径不同。predict 按血量降序、金币降序、玩家编号升序重排。data.json 称“赛季末排名（血量/金币）由程序从 openings 与逐轮增量算出，按血量降序、meta 既定顺序处理并列”。meta 既定顺序本身没有在数据中列出可执行的顺序表。check.py 的 C9 只验证 rankings 行的 hp_end、gold_end 与 season_state 一致，不验证 rank 字段值。Lean 的 checkGroup 与 checkLedger 同样只比对 hp_end、gold_end 与赛季、玩家，不比较 rank 值。rank 字段存在于结构中，但排序在任何检查中都不验证。并列时三处可能给出不同名次。
- 为什么本轮不改：改动任一口径都会改变排名输出。predict 的位置项依赖 ranks_of，排名变化会改变已测量的预测结果。统一口径须先把 meta 既定顺序写成可执行的形式，再由 Phase 4 对照实验定夺。

## 3. 杠杆惩罚扣减次数不同

- 位置：check.py:285–300（C3 季末）；predict.py:571（build_fork），612–625；predict.py:900（forecast_rounds），934–935（多轮状态推进）；backtest.py:86–113（chain_state）。
- 现状：扣减次数分三档。check 在每季季末扣一次。pen 从 hp_end 或 gold_end 扣减，取决于 penalty_applies_to。check 同时验证 season_state.penalty 等于 pen。build_fork 在分叉季扣一次。分叉季的 season_state 用同一公式写入 pen、hp_end、gold_end。forecast_rounds 的多轮状态推进扣零次。状态推进只做血量钳制与金币累加。backtest 的 chain_state 扣零次。其文档串明示不含季末惩罚项（"without the season-end penalty term"）。此处“扣减”指状态值（hp_end、gold_end）与 penalty 字段的实际扣减，不指效用函数内的杠杆项。best_response（predict.py:415）与 fit 特征（fit.py:419）在效用或特征中计 lever = 1（金币为负时）。该项是效用惩罚，不是状态扣减。当前真实 trace 全部 borrowed 为 0、penalty 为 0。季末扣减在数值上为零。差异只在机制层面，不在当前数值层面。
- 为什么本轮不改：统一扣减次数会改变分叉预测与回测的状态轨迹，进而改变已测量的结果。季末扣一次是否为规则本意，需 Phase 4 对照实验定夺。当前 borrowed 全为零，改动没有可观测的数值验证信号。

## 4. predict horizon 上限在真实 trace 上是 55 轮

- 位置：predict.py:1076（--horizon 默认 1）；predict.py:1147–1148（cap_rounds = max(s["rounds"] for s in trace["seasons"])；effective_horizon = min(args.horizon, cap_rounds)）；predict.py:900–915（forecast_rounds）。
- 现状：默认 horizon 为 1 轮。上限为单赛季最大轮数。真实 trace 各赛季轮数为 S0 55、S1 4、S2 8、S3 7、S4 8、S5 11、S6 1。上限为 55 轮。fixture 上限为 7 轮。文档称上限为 1 个赛季。1 个赛季在真实 trace 上等于 55 轮。--horizon 超过上限时，predict 返回 beyond 结论（低置信度符号结论），不做逐轮推演。
- 为什么本轮不改：上限 55 是 cap_rounds 定义的直接结果。改定义（例如按中位赛季轮数封顶，或按固定轮数封顶）会改变多轮预测输出与已测量的外推行为。是否收紧上限，需 Phase 4 对照实验定夺。

## 5. backtest.py run_window 的 hp_bounds 初始值 (100, 0)

- 位置：backtest.py:363–370（run_window）。
- 现状与结论：初始值 (100, 0) 在真实 trace 上没有被实际使用。代码先设 hp_bounds = (100, 0)。随后立即按 test[0] 的日期与玩家解析基础规则。base0 非空时改写为真实 (hp_floor, hp_cap)，再传入 best_response。核查：真实 trace 的 94 个不同日期全部解析到基础规则。最早规则 RV-2018.1 自 20180101 生效。base0 从不为空。结论：(100, 0) 只在 test 日期早于全部基础规则生效日时才到达 best_response。当前 trace 不触发该分支。残留风险：该初始值本身是倒置的。floor 100 大于 cap 0。若某条 trace 触发该分支，predict.clamp(v, 100, 0) 对一切输入返回 100。全部血量被钉在 100。check.resolve_rules 在无基础规则时返回 base None（check.py:77–93）。
- 为什么本轮不改：本轮任务限定只改 ensemble.py。把初始值改为真实规则值或显式报错属于 backtest.py 的改动，需 Phase 4 定夺。改动前应先补一个无基础规则 trace 的测试用例，确认新行为。

## 6. 验证记录（ensemble.py 修前修后）

- 命令：python3 ensemble.py fixtures/trace-fixture-ok.json --payoff rules/payoff-model.json；python3 ensemble.py traces/trace-latest.json --payoff rules/payoff-model.json。两次运行均在修前与修后各跑一次。payoff 文件两次相同（rules/payoff-model.json，v2）。
- Fixture：修前修后输出逐字节相同（cmp 通过，JSON 与 summary 文本均相同）。成员 15 名。玩家 18 名。mean_entropy_norm 0.131694。mean_modal_share 0.833333。flags 为 consensus 6、medium 12。收敛成员 15/15。
- 真实 trace 修前：玩家 32 名。mean_entropy_norm 0.004531。mean_modal_share 0.995833。flags 为 consensus 31、medium 1。收敛成员 15/15。众数动作：r1 共 31 名玩家，wild 共 1 名（TSMC）。众数概率范围 0.606–0.984。
- 真实 trace 修后：玩家 32 名。mean_entropy_norm 0.013384。mean_modal_share 0.983333。flags 为 consensus 30、medium 2。收敛成员 15/15。众数动作：claude 共 32 名玩家。众数概率范围 0.336–0.954。
- 期望查找计数（直接诊断，非 ensemble 输出）：修前 416 次查找中 288 次为 (0.0, 0.0)。修后 928 次查找中 0 次为 (0.0, 0.0)。
- 注意：修前 fixture 运行的数值（0.131694、0.833333、收敛 15/15）与 runs/2026-11-21_115508/ensemble-report.json 存档值（0.108003、0.866667、收敛 13/15）不同。ensemble.py 与 fixture 文件自基线提交 98be845 后未变。predict.py 在 11-21 11:55 运行后又提交了第 3、4、6、9 轮改动（d632a8d 13:40、b0e4e07 13:49、f7cfa44 14:04、b8ed917 14:38）。存档报告早于这些改动。修前修后比较用同一份输入，比较本身不受影响。
- run.sh 影响：ensemble.py 不在生产管道中运行。run.sh 全文无 "ensemble"。全仓库无 "import ensemble"。改动只影响 ensemble 本身。run.sh 全流程不受影响。完整 run.sh 未跑，只做 grep 核查。
