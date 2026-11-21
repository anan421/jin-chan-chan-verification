# 管线状态（2026-11-21 晚）

- Lean 4.36.0 + Lake 5.0.0 已装（elan，走 GitHub releases 直链）。
  elan.lean-lang.org 返回 404，GitHub API 限流——安装走 GitHub
  releases 直链。
- 管线已建成：`extract.py`、`check.py`、`gen_trace_lean.py`（v3）、
  `lean/`（TOML 配置 + `Verification/` 模块）、`run.sh`、
  `merge_report.py`、`fixtures/gen_fixture.py`、`classify.py`、
  `gate.py`、`ingest.py`、`rules/rules.json`、
  `rules/agent-claim-schema.json`。
- Fixture 验证（全量 558 条）：
  - ok 样例：快速检查器 pass，Lean 构建 pass，合并报告 pass。
    报告：`runs/2026-11-21_101127/merged-report.md`。
  - 反例（注入 S5 英伟达血量 -7/金币 -32、S5 Anthropic 血量 -17、
    S4 软银归零后仍行动、卡池超持、R1 日期提前）：快速检查器
    7 项失败（位置精确），Lean 5 条定理 `native_decide` 判假，
    合并报告 fail。报告：`runs/2026-11-21_101129/merged-report.md`。
  - 曾抓到一次空跑：`lake build` 无默认目标时返回 0 且什么都不编。
    已修：TOML 加 `defaultTargets`，`run.sh` 加 Proofs.olean 落盘校验。
- 真实 trace 尚未抽取：`traces/` 为空。
  诊断（v4）确认逐轮增量与赛季末排名两套数据未对账；修复路径为
  单一事实源 data.json。页面现为 v6（v5 为形式化检测那轮，
  v6 为段位看板）。诊断 882e34f3 结论：v6 仍无 data.json，
  仍是单一自包含 index.html，内嵌四份并行手写数据源；
  赛季末排名与总图折线均为手写静态值。真实抽取继续等待修复，
  修复未授权，不得擅自修页面。
- 抽取检查已派：inspect 882e34f3，问 v6 是否已带 data.json；
  若有，返回 data.json 内容与显示的排名/总图数据。
  回执到后：`extract.py` 入库 → `./run.sh` 跑首份真实合并报告。

## 2026-11-21 晚新增（用户批准的三件事已建成）

- 分层验证：保留有限 C1–C12 历史检查（`native_decide`），新增
  无界 `lean/Verification/Dynamics.lean` 归纳层（状态机 + 归纳，
  无界不变量）。两层都跑，任一失败整体失败。`Dynamics.lean`
  已编译通过；`Proofs.lean` 新增五条动态层定理（规则表良构、
  初始态满足不变量、轨迹合法、任意长度 run 的终态满足不变量、
  全部中间态满足不变量），并把动态实例检查并入总定理
  `all_invariants_hold`。`#print axioms` 验证：两条全称链接定理
  只依赖 Lean 标准三公理 + 两条 `native_decide` 实例证书
  （初始态与规则表），无 `sorry`、无额外公理。
- 金币语义：`liability` 标志。金币可为负当且仅当该动作标了负债；
  `Dynamics.lean` 的 `applyMove` 永不钳制金币（原型为简化做了
  钳制，建成时未沿用）。定理 `step_gold_liability` 是该语义的
  定理形式。
- AgentClaim 四类够用（提议动作、事实修正、反驳、证据降级），
  不加第五类。`rules/agent-claim-schema.json`（schema v1）与
  `gate.py` 已建成，双向验证通过：ok 输出 4 pass、1 opinion、
  退出码 0；broken 输出 5 reject、2 contested、1 opinion、
  退出码 1，四条规则 R1–R4 全部被测到。
- `gen_trace_lean.py` v3：接受 schema 3 或 4；输出全部 v3 定义
  + `traceDynInit`；`--modular` 另写 `ProofsByPlayer.lean`（18 玩家）
  与 `ProofsBySeason.lean`（5 赛季）。修过一处生成 bug：
  规则卡名列表直接插值 Python list 会产出非法 Lean 字符串
  （`'"H100"'`），已改为 join 形式。
- `Transition.lean`（731 行草稿，未完成定理段）已归档至
  `prototype/transition-draft-2026-11-21.lean`，由已批准的
  `Dynamics.lean` 取代；其元游戏/知识建模保留在设计稿 B/C 层。
- `run.sh` 已接线：gate 优先（`--claims` 给出时；gate 失败整体
  失败，checker/Lean 记 `not_run`，仍写合并报告）、非 modular
  模式删除残留模块化源文件、modular 模式显式构建两模块并校验
  `.olean`。`merge_report.py` 增加 gate 层、假设（judgment claims）
  章节与 agent 协议章节。
- 端到端测试（2026-11-21 晚，四轮）：
  - ok fixture + ok claims，非 modular：overall pass，退出码 0。
    报告：`runs/2026-11-21_111640/merged-report.md`。
  - ok fixture + ok claims，modular：overall pass，退出码 0；
    两模块 `.olean` 落盘并通过新鲜度校验。
    报告：`runs/2026-11-21_111646/merged-report.md`。
  - broken fixture + broken claims：gate fail（5 拒绝、2 contested、
    1 opinion），checker/Lean 未运行，overall fail，退出码 1。
    报告：`runs/2026-11-21_111650/merged-report.md`。
  - broken fixture，无 claims：gate 跳过，checker 10 项精确失败
    （C2×3、C3、C4、C5×2、C6、C10、C11），Lean 构建失败
    （`all_invariants_hold` 的 `native_decide` 判假），overall fail，
    退出码 1。报告：`runs/2026-11-21_111654/merged-report.md`。
  - 覆盖变化须诚实记录：broken fixture 注入的 payoff 越界只在旧
    `Transition.lean` 轨迹层能抓，`Dynamics.lean` 不含 payoff 字段，
    该层覆盖已变化（见最终报告）。

## 仍待办（未被新任务取代，仍挂起）

- 以下四项已于 2026-11-21 晚建成（见下“每日循环已建成”一节）：
  `daily_run.sh`、`ingest.py` schema 2/3/4 + v4 事件追加、
  `extract.py` v4、`classify.py` 接入 `run.sh`。本节剩余待办见
  “仍待办（每日循环后续）”。

## 仍待办（每日循环后续，2026-11-21 晚）

- 每日循环的 cron 排期：daily_run.sh 已建成并冒烟通过，但本次不排
  cron；排期另行确认（需一句话回弹确认）。
- 真实 trace 的每日运行：首份真实合并报告已跑出，但历史层总体 fail
  （两处真实数据问题，修法待 Gu 定夺）；每日循环在真实 trace 上
  跑通须等历史层全过。
- S6 开季：ingest 只追加到已有赛季；新赛季记录（名、起止日、活跃
  玩家、规则版本）须由 monitor 在事件文件里声明，机制未建。
- 触发报警目前只写 decision 文件与每日日志，不对外推送；推送渠道
  （如需）待 Gu 定夺。

## 2026-11-21 晚新增（每日循环已建成，冒烟通过）

- `daily_run.sh`：摄取当日事件 → 追加一轮 → recompute 派生值 →
  全量重验（run.sh）→ 通过才放行（trace-<date>.json +
  trace-latest.json），否则失败分类 + 阻断（release=false，
  trace-latest.json 不动）。无事件文件只记日志（exit 0）；轮次
  未凑满（缺玩家）只记日志等补齐（ingest exit 3）。不排 cron，
  不改页面。用法：`./daily_run.sh [--date ...] [--events ...]
  [--trace ...] [--data-json ...] [--predict] [--claims ...]
  [--release-dir ...]`。
- 触发规则 `daily/triggers.json`（固定）+ `daily/triggers.py`：
  报警四项——新开一轮、血量跨段位、规则版本变、预测置信变档，
  另加验证失败报警；其余只记日志。报警只写 decision 文件与日志，
  不对外推送。段位映射与页面一致（≥90 王者…<30 黑铁）。
- 版本存档 `archive/`：每版 data.json + trace 按哈希加日期存档
  （archive/<date>_<sha12>/），manifest.jsonl 为索引；任一历史版本
  可重跑验证（`./run.sh archive/<dir>/trace.json`；data.json 可重抽取）。
- `recompute.py`（新增）：从 moves 重算派生值（season_state、
  rankings、hp_series、seasons[].rounds、spec、trace_sha256），账本
  数学与 check.py 同源（复用 resolve_rules/penalty_value/cap）。
  自检：在 ok fixture 上为 no-op（全部非 meta 字段逐项相同）。
- `ingest.py`：接受 schema 2/3/4；v4 时把事件追加进 trace["events"]；
  每轮须凑满（每季活跃玩家各恰好一次），未凑满 exit 3 等待；
  每条新 move 按日期解析 rules_version（与 check.py 同源）；
  链状态改为从 moves 折叠的税前（pre-penalty）季末值（见下 bug）。
- `extract.py` 升 v4：接受 raw schema 3 或 4；`--events` 合并 v4
  事件；`--claims` 合并 schema v2 claims（只做 R1 校验，R2–R4 仍
  由 gate.py 跑；内嵌旧形状 claims 原样带过，不伪造 v2 字段）。
- `classify.py` 已接入 `run.sh`：每次检查跑完都跑分类（诊断，不改
  退出码），写 runs/<id>/classification.json，失败日志记入
  runs/failures-log.jsonl；`merge_report.py` 加“失败分类”章。
- 建造中发现并修掉的 bug：① ingest 曾用税后（post-penalty）
  season_state.hp_end 当下一轮 hp_start，杠杆玩家必 fail C2，
  现改为从 moves 折叠；② event-map.json 是 {"map": {...}} 嵌套，
  ingest 曾读顶层导致所有事件类型查不到，现兼容两种形状；
  ③ extract 的 R1 曾校验 predicate op（比 gate.py 的 R1 严，
  会把 R3 的 opinion 误判为拒绝），已去掉，op 只由 gate 的 R3 判；
  ④ daily_run.sh 的 run_id 曾取到 runs/ 父目录（find -newer 命中
  父目录 mtime），现用 -mindepth 1 + 时间排序取。
- 冒烟（全部 fixture，非真实事件）：A 通过（S5 第 8 轮，576 条，
  check+Lean pass，触发 new_round + tier_cross 7 处，released=true，
  存档两条）；B 阻断（P0 overseas_rental 违 RV-2026-11，C5×1，
  分类 0 机制/1 数据，released=false，exit 1）；C 存档重验通过；
  D 无事件只记日志；E 未凑满 exit 3 只记日志；触发器单测：置信档
  signal→low 报警。回归：README 的 run.sh --claims 命令仍通过，
  分类章在位。冒烟所用 check.py sha256 fc114bb9…（根因修复协调员
  并行改 C5/C6，冒烟时未落地）。

## 2026-11-21 晚新增（预测层已建成）

- 按设计稿 `design/prediction-layer.md` 建成，三路分建，协调员收齐
  并端到端验证通过。十项定夺的选择：MPE + 最好回应动态；收益参数
  全部占位（A1–A6，另 A7）；阈值超基线 10pp、M5 容差 ±10、低于阈值
  降级 opinion；预测不上页面、只进报告；默认 1 轮、最多 1 赛季；
  代码覆盖 18 席、冒烟试点 4 关键席；schema v2（move 字段 + R2
  未来 subject）；walk-forward S1–S3 拟合/S4–S5 测试；不扩展 Move；
  低于阈值只报告、不自动修订。
- Lean：`lean/Verification/Prediction.lean`（Strategy、Payoff、
  bestResponse、runStrategy，定理 a–d：策略保持不变量、不变集、
  k 步进入目标段、混合策略支撑集合法性）。`lake build` 全库通过
  （14 jobs）。`#print axioms`：全部新定理只依赖 Lean 标准三公理，
  无 sorry、无额外公理。未改 Dynamics/Model/Proofs/Trace，未扩展 Move。
- Python 核心：`rules/payoff-model.json`（v1，五档分档，参数全占位）、
  `predict.py`、`symbolic.py`、`backtest.py`。冒烟测试（fixture，
  非校准）：symbolic 240 单元、19530 边、125 SCC、120 吸引子
  （全是单格死单元，无活吸引子）；backtest 测试窗 S4–S5 n=234：
  M1 5.56%（基线 8.63%，−3.08pp）、M2 49.57%（−0.43pp）、M3 61.11%
  （+11.11pp，信号）、M4 45.73%（+33.23pp，信号）、M5 81.62%
  （+7.45pp），verdict below_threshold，只报告未修订。predict
  horizon 1：最好回应 3 轮收敛到不动点；fork（S6）重验 check=pass、
  Lean=pass；合法 propose_action 应用成功，被禁种类记
  refuted_by_transition（“被转移关系反驳”）。
- Gate 与接线：schema 升 v2（可选 move 字段，8 子字段）；gate.py v2
  （R1 校验 move 形状、R2 未来 subject、未来 fact_correction 直接
  拒绝、未来 refutation 记 opinion）；`agent_claims.py`（覆盖率、
  引用、可复现、可判定）；run.sh 加 --predict/--payoff；merge_report.py
  加“预测”章。验证：现有 fixtures 行为不变；pred-ok（CL-P1）
  过 R2 且 future=True，应用后重验通过；pred-badmove（overseas_rental）
  记 refuted_by_transition；run.sh --predict 端到端两轮通过。
- 协调员对齐：backtest.py/symbolic.py 报告补顶层 verdict/tables/
  baselines 字段以合契约（merge 的防御性适配保留为后备）；复测
  run.sh --predict（runs/2026-11-21_113735）：overall pass，预测章
  fail（预测 pass、回测 fail、符号动力 pass、协议 fail），run 退出码 0。
- 诚实记录：占位参数下 M1 低于随机基线——“下一步出什么牌”目前
  无信号，校准必须等真实 trace；协议检查在 ok fixture 上 fail
  （覆盖率 0/4 事件被引用——ok fixture 的 claim 未提任何事件 id），
  工具无错；符号图忽略玩家专属 overlay 禁种（报告 notes 已写明）。
- 仍待办（预测层后续）：真实 trace 抽取后校准收益模型（命中率须超
  基线；命中率低改模型、不改数据）；协议全过的 claims 文件（引用
  全部 4 个事件且谓词全可判定）未造。

## 集成预测（2026-11-21 晚新增）

- `ensemble.py`：15 名成员（14 方审计员立场分档 + baseline 占位参照），
  每人一套收益权重，同一当前状态、同一期望增量、同一候选集，各跑
  `predict.best_response`（只读复用，未改 predict.py 与 payoff-model.json），
  输出各自的预测动作与分布。分歧度量：每席众数分布、众数占比、
  香农熵（比特）与归一化熵、集成分布（成员分布均值）与集成众数、
  与 baseline 的一致率；flag 三档 consensus / medium / high_disagreement。
- 冒烟（fixture，非校准，runs/2026-11-21_115508/）：15 成员 × 18 席；
  平均归一化熵 0.108，平均众数占比 0.867；8 席全共识，10 席中等分歧，
  0 席高分歧；13/15 成员收敛，musk 与 dpsk 两成员最好回应循环 20 轮
  未收敛（用末轮效用出分布，与 predict.py 同口径）。
- 两处单模型预测被集成推翻：ANTH 集成众数 stargate（p=0.581），
  baseline 是 huang_resign，14 名审计员中仅 5 名同意 baseline
  （一致率 0.357）；DPSK 集成众数 stargate（p=0.527），baseline 是
  musk_table，一致率同样 0.357。NVDA 全员一致 r1（集成 p=0.899），
  HUAWEI 全员一致 generic（p=0.917）。
- 诚实记录：payoff-model.json v1 只有占位点值、无假设区间，成员权重
  是 ensemble.py 内以审计员立场映射的判断，非证据；c_rule 在 v1 无效
  （CNTEAM 与 baseline 的众数动作 18 席全同，仅概率不同，已验证）；
  tau 只改变分布锐度、不改变众数动作；分歧来自权重差异如实算，
  未编造；集成不校验 trace（broken fixture 上也能跑出报告，仅作
  稳健性检查，不得当作验证通过）。
- 验证：独立重算 ANTH 聚合（众数计数、熵、集成分布、一致率）与全局
  均值、flag 计数全匹配；重跑报告字节相同（sha256 7dd46140…）；
  JSON 无 NaN/Infinity；未改 Dynamics.lean、predict.py、
  payoff-model.json、merge_report.py、run.sh，未碰页面；集成结果只写
  JSON 文件，不进合并报告。
- 仍缺：真实 trace（校准与拟合权重）；多轮集成未建（只跑 1 轮）。

## 规则场景预测（2026-11-21 晚新增）

- `rules/scenarios.json`：4 条条件分支（SC-BASE：RV-2026.2 延续；SC-BIS-TIGHTEN：BIS 再收紧，触发 WL-BIS-COMMENT-2027-01；SC-RASA：RASA 通过，触发 WL-RASA-SENATE；SC-TRUCE-EXPIRE：贸易休战到期，触发 WL-TRUCE-2027-01 + WL-BIS-COMMENT-2027-01）。每条写清触发条件与规则变化（禁掉的动作种类、血量上下界）。未建模 4 项观察清单附理由（加州立法须合规成本词汇、NDAA 与 RASA 重复、二十一大须中方规则词汇、2028 大选超预测上限）。
- `predict.py` 加 `--scenarios/--scenarios-out`：每条场景各跑一次最好回应动态，输出按场景分列（众数动作、分布、置信分层），另附对比表（每席各场景众数、跨场景变化席）与边界诊断（第 1 轮后血量、被钳制席）。基线预测循环抽成 `forecast_rounds` 复用；重构后基线与 runs/2026-11-21_113735 逐项相同（18 席众数、分布、best_response 全等）。场景输出只写 JSON 文件，不进合并报告；未改 merge_report.py、run.sh、Dynamics.lean、payoff-model.json，未碰页面。
- 触发概率：一律 null（无数据支撑；load_scenarios 拒绝无假设标签的非空概率）。置信：基线分支标 baseline，其余标 conditional（触发才成立）；每轮置信仍按轮次分层（第 1 轮 high、2–7 轮 medium）。
- 冒烟（fixture，非校准，runs/scenario-smoke/）：predict 退出码 0，verdict pass，重验 check=pass、lean=pass。SC-BASE 与基线全等（众数变化 0、最大分布偏移 0.0，自检）；SC-BIS-TIGHTEN 改 1 席（TSMC：spacex_xai→stargate）；SC-RASA 改 3 席（GOOG：stargate→openai_mar26；ALI：stargate→doubao_price_war；TSMC：spacex_xai→v3）；SC-TRUCE-EXPIRE 改 1 席（TSMC，与 BIS-TIGHTEN 同）。7 轮内各场景变化席不变。
- 诚实记录：hp_cap 100→80 在 fixture 上 7 轮内无效果（第 1 轮后最高血量 67.0，无人被钳制；钳制保序，排名未变）——边界机制已跑通（应用记录 [100,80]），但本场景的边界变化没有咬到预测；80 取宗师/钻石边界，未按数据调低。
- 仍缺（真实 trace 相关）：① 真实 trace 已到（traces/trace-latest.json，558 条），但历史层未过（C5 S5 5-1 规则版本、C6 五费卡池），按设计稿顺序规则，场景预测不得在真实 trace 上跑，须等历史层全过（根因修复已派，Gu 已批“按推荐修，跑重验”）；② 种类词汇不匹配：场景禁令用 fixture 的语义种类词汇（msft_invest、spacex_xai、stargate、colossus），真实 trace 的种类是轮次类型 slug（battle、economy、draft……）加 4 个事件种类，只重合 4 种——场景运行在真实 trace 上会被校验拒绝；更深一层，轮次类型词汇无法表达规则驱动的禁令，须转换器加语义种类层才能在真实 trace 上写场景禁令（回测 M1 在真实 trace 上也只量轮次类型预测）。**已解决一半（2026-11-21 晚，语义种类层落地，见文末新节）：转换器加 semantic_kind，73 条已分类，4 个被禁种类全部在语义集里；回测 M1 已改语义版并在真实 trace 上跑出数字。剩余一半：`predict.py --scenarios` 仍拒（exit 2），因其种类集只读 action_kind；改 predict.py 须另行授权（最小改动 3 处，见 `design/semantic-kinds.md` 第 8 节）。**；③ 轮次横跨规则变更日（真实 S5 5-1 已暴露）同样适用于场景触发发生在轮次中间的情况，本模型按整轮适用新规则，待检查器接受横跨标注后再细化。

## 2026-11-21 晚新增（拟合层已建成，fixture 冒烟）

- 文件：`fit.py`（拟合器）、`design/fitting-layer.md`（设计稿）、
  `rules/payoff-model.json` 升 v2。方法一句话：显现偏好 / 平均结构化
  感知机，别人固定在记录动作上，前缀链状态，30 epoch，α 与 γ 联合
  网格，τ 做 softmax 极大似然，bootstrap B=50 按轮重采样；五类各拟
  一份，另加全席共享参照，另拟一份 α=1、γ=1 的 v1 投影供
  `predict.py` / `backtest.py` 直接用。
- v2 改动：version 1→2；参数加 discount（A8，1.0）与 hp_exponent
  （A9，1.0）；assumptions 加 A8、A9；utility_form 改为 v2 式
  （α=1、γ=1 时严格还原 v1）；加 `"fit": null` 与 status 词表
  （placeholder / fitted / assumed）。五类参数值保持占位。
  `predict.py` 与 `backtest.py` 在占位 v2 文件上重跑通过，数字与 v1
  占位完全相同。未改 `lean/`、`predict.py`、`backtest.py`、`run.sh`、
  `check.py`、`gate.py`、页面。
- 冒烟结果（fixture，S1–S3 拟合，n=306，status 全是 smoke_test，
  不是校准）：共享拟合 α=1.0、γ=1.0、τ=8.0、违规率 0.732026；
  权重塌缩（w_hp 0、w_gold 0、c_lever 0.01294、c_rule 0.999916、
  w_pos 0），bootstrap 里 w_hp 为 0 的占比 1.0；占位初值违规率
  0.7092，比拟合后还低。合成恢复测试通过（已知权重生成的数据上
  违规率 0.005、余弦相似度 0.917），拟合器本身正确，fixture 数据
  里没有该效用族能解释的信号。v1 投影 hold-out 回测（S4–S5，
  n=234）：M1 10.26%（+1.63pp）、M2 44.44%（−5.56pp）、M3 55.56%
  （+5.56pp）、M4 46.15%（+33.65pp，信号）、M5 85.47%（+11.30pp，
  信号），threshold_verdict below_threshold。输出：
  `runs/fit-smoke-2026-11-21/`（fit-report.json、
  payoff-model-fitted.json、payoff-model-fitted-v1.json、
  backtest-fitted.json）。
- 负向控制未通过：broken fixture 违规率与 ok fixture 完全相同
  （S1–S3 窗口 0.732026，全窗口 0.822222）。原因：两处改动都在
  S4–S5，不在 S1–S3 窗口内；全窗口也只有两处改动，S4R1 只改日期
  与规则版本（决策不受影响），S5R1 是首发种类换首发种类（本来
  都记违规）。机器不能用违规率区分这对好坏数据。数据质量仍是
  `check.py` 的事。见设计稿第六节。
- 待真实 trace：真实 trace 已于本任务进行中落盘
  （`traces/trace-2026-11-21.json`，首份真实合并报告总体 fail，
  见 `runs/2026-11-21_115719/merged-report.md`）。历史层全过后，
  用真实 trace 重跑 `fit.py` 做第一次真拟合；`predict.py` 的 v2
  效用集成（`utility()` 改 v2 式）待后 lane；重拟合触发 T1–T5 见
  设计稿第七节。

## 首跑抽取阻塞（2026-11-21 19:37，两次 inspect 回执后）

- 页面修复已落地（数值层）：data.json 为单一数值事实源；三处硬错误已在增量侧修掉（S2 微软血量和 +15→−4；S5 Anthropic 血量和 +3→−14；S5 英伟达金币和 −3→−35），排名未动，跨季断点 72 组为 0，页内检查 12/12 PASS（fnv1a:8db822c0）。inspect 2cca789e。
- 第二层规则桌已上页（RV-2026.2、逐季补丁、7 项观察清单、6 席规则桌玩家、反身性链条），但规则元数据（ROUND_RV 31 条、SEASON_PATCHES、watchlist）只硬编码在 index.html 内，不在 data.json 中。卡池总量（29/22/18/12/10）与 15 张关键牌也只在 index.html 内。单一事实源只覆盖数值，不覆盖规则与卡牌元数据。inspect 2cca789e、67d0e647。
- **首跑阻塞：558 条增量未到手。** 两次 inspect 均未返回增量全文：检查员不手工抄录（应由脚本从 data.json 生成），且无可用的机器读取路径（artifact 文件不可直接读、无服务端动作、export 旁路不合规）。openings.S1 已全量取到；轮次日期只在轮次层；赛季对象无 start/end；holdings、key_cards min_date/first_date、结构化 formulas 在两处都不存在；formulaInputs.gaps 5 项仍为待核。
- 下一步（需授权/改动，非本轮可做）：① builder 把 ROUND_RV、卡池、关键牌、formulas、赛季日期移入 data.json；② 给管线一条机器抽取路径（构建时产出 trace JSON，或 artifact 声明返回 data.json 的动作，或分享后经公开 URL 取数）；③ 再跑 extract.py → run.sh 首份真实合并报告。不得编造增量，不得用排名反推增量入 trace（循环验证，无意义）。

## 根因修复：check.py C5 跨度规则与 C6 不同卡计数（2026-11-21 晚，Gu 已批“按推荐修，跑重验”）

- 背景：首份真实合并报告 `runs/2026-11-21_115719/merged-report.md`
  总体 fail；快速检查器 passed=3、failures=19、gaps=0，其中 C5×18
 （S5 5-1 规则版本）与 C6×1（五费卡池超持）。只改 `check.py`；
  `rules/round-spans.json` 格式已合用，未改；未改页面、data.json、
  extract.py、ingest.py、classify.py、daily_run.sh、predict.py、
  payoff-model.json、ensemble.py、convert_data_json.py；未碰 `lean/` 与
  gen_trace_lean.py（Lean 层由另一名工人按同一语义合同修，两层口径
  必须一致）。
- 前置验证（已做）：canonical trace 里确实没有已有字段能表达轮次
  跨度。`traces/trace-2026-11-21.json` 的 moves 只有单日 `date`
  （S5 5-1 全为 20261118）；seasons 只有赛季级 `start_date` /
  `end_date`（S5 为 20251201–20261121），不能表达轮内跨度；全
  trace 扫描无任何 span 字段。因此轮次跨度必须以外挂文件记录，
  即 `rules/round-spans.json`（已建好，version 1）。

### C5 跨度规则（check.py：新增 load_round_spans / ROUND_SPANS / round_span_end / rule_window_overlaps；C5 段 round_rv 分支）

- 旧口径：recorded rules_version 必须等于按 move 单日日期 D 解析出
  的 base（全局）规则 `resolve_rules(rules, D)` 的 rule_id，否则
  fail `round_rv`。
- 新口径（全文）：move 的 recorded rules_version V 接受，当且仅当
  V 是 move 日期 D 当天在效的 base（全局）规则，或 V 是一条 base
  规则且其生效窗口与该轮跨度 [D, spanEnd] 有重叠。spanEnd 取自
  `rules/round-spans.json`，key 为 (season, round_label)；无条目的
  轮次 spanEnd = D，即无跨度。规则窗口为 [effective_from,
  effective_to)，effective_to 为空表示开放。player 专属 overlay
  规则永不计入（recorded 必须是 base 规则）。禁令种类检查与日期
  检查仍用 D，不变；C2/C3 账本的规则解析仍用 D，不变。
- 为什么：轮次本身横跨规则变更日时，单日 D（转换取最早一天）不
  能代表整轮；用 D 一刀切会把轮内后半段才生效的正确版本判为错。
- 5-1 的依据：页面轮次日期原文为「2026 年 11 月 18–19 日」；转换
  取最早一天 20261118，当天在效 RV-2026.1，页面 roundRV 记为
  RV-2026.2；RV-2026.2 于 2026-11-19 生效（《联邦公报》文号
  2026-23529，印刷页 91 FR 74970），其窗口 [20261119, ∞) 与跨度
  [20261118, 20261119] 在 20261119 处重叠，故接受。轮次日期未改
  为单日，RV-2026.2 生效日未提前。
- 防御性细节（合同未明说、与合同一致）：spanEnd 早于 D 时不缩小
  跨度（取 max(D, spanEnd)）；round-spans.json 缺失或不可读时退回
  旧严格口径（无跨度）。span 文件按 (season, round_label) 查，
  因此同样作用于同 key 的 fixture 轮次；已核对两份 fixture 中
  S5 5-1 的 recorded 版本本来就等于 base(D)，无一处是靠重叠分支
  新通过的（见下回归：broken fixture 失败集与修前逐项相同）。

### C6 不同卡计数规则（check.py：C6 段池子计数）

- 旧口径：每费池子计数按 holdings 逐条计数（`Counter` 对每条
  holding 加 1）。
- 新口径：共享卡（key_cards 里 shared=true）按 (cost, card) 去重
  计 1 张；非共享卡每条持有计 1。key_cards 的“多持有人须共享”
  检查（holders>1 且 shared=false 则 fail）不变。
- 为什么：同一张共享卡被多名玩家持有不是多张卡；按持有数计会把
  1 张卡算成多张，虚增池子占用。
- 本例：星门计划 1 张卡被 3 名玩家持有（key_cards：shared=True，
  holders=[1,9,17]，即 OAI、ORCL、SFTB）；cost 5 的 holdings 共
  11 条、不同卡 9 张；新口径计 9 ≤ 10，通过。
- 定界：逐卡加权合成检查（synthesis_overpool）不改——它当前不
  fail，改它是超范围；它量的是星级合成加权占用，与“池子被几张
  不同卡占用”是另一回事，修 C6 计数不牵连它。

### 回归验证（2026-11-21 晚，修后跑）

- 真实 trace `traces/trace-2026-11-21.json`：verdict=pass，
  passed=3、failures=0、gaps=0，退出码 0。18 处 C5 与 1 处 C6
  失败全部消失，无新失败（修前：fail，passed=3、failures=19）。
  独立复算：cost 5 新口径计 9；RV-2026.2 窗口确与
  [20261118, 20261119] 重叠。
- ok fixture `fixtures/trace-fixture-ok.json`：仍 pass（passed=3、
  failures=0、gaps=0），退出码 0。
- broken fixture `fixtures/trace-fixture-broken.json`：仍 fail，
  failures=10、gaps=0，退出码 1，失败集与修前逐项相同
  （C2×3、C3、C4、C5×2、C6、C10、C11 全在）。尤其注意：被注入
  的日期错误（C5 S4 4-1 date_before_true，20250101 < 20250120）
  仍被抓到（日期检查未动）；被注入的卡池超持（C6，12 条，其中
  H100 与 R1 各 2 条、均为非共享卡）新口径下仍计 12 > 10，仍 fail。
- 完整决策记录另见 `design/checker-decisions.md`（C5/C6 各一节，
  含旧口径、新口径全文、依据与定界）。
- 待 Lean 工人同合同修完后跑全量重验（`./run.sh` + `--predict`，
  按 Gu 20:00 指令）；本修只覆盖 Python 检查器部分。

## 2026-11-21 晚新增（语义种类层已建成，真实 trace 重抽取并重验）

- 目的：场景禁令与回测 M1 在真实 trace 上跑。`action_kind` 是轮次
  类型 slug，不能表达“玩家做了什么动作”；场景禁令用 fixture 的
  语义种类词汇。解法：每个 move 保留 `action_kind`（不变），新增
  `semantic_kind`（实质动作线程），按 move 自己的 action 文本分类，
  玩家与轮次编号只限定真正有歧义的关键词。设计与规则表全文见
  `design/semantic-kinds.md`。
- 改动（禁区未碰：页面、data.json、check.py、Lean、predict.py、
  payoff-model.json、ensemble.py）：
  - `convert_data_json.py`：新增 `SEMANTIC_VOCABULARY`（fixture 16 种
    + overseas_rental）与 `classify_semantic()`（15 条有序子串规则，
    第一命中即定，分不出标 `unknown`，不硬归类）；move 循环加
    `semantic_kind` 字段；自检加两项硬检查（4 个 EVENT_KINDS move
    的 semantic_kind 必须等于其事件种类；每个输出种类必须在词汇表
    内或是 `unknown`）；provenance 加 `semantic_kinds` 节。
  - `backtest.py`：改语义版。候选种类取 prefix 里的 semantic_kind，
    排除 `unknown` 与被禁种类；期望增量本地复刻
    `predict.expected_deltas` 按 semantic_kind 分组，再调
    `P.make_expectation` 与 `P.best_response`；M1 只在可分类子集上
    量（`unknown` 不计分母，记 `m1_unknown_n`）；M2–M5 不变。无
    semantic_kind 字段的 trace（如 fixture）回退到 action_kind。
- 分类结果（558 条）：73 条已分类、485 条 `unknown`。分布：
  stargate 15、anthropic_ipo 8、msft_invest 7、blackwell 6、r1 6、
  musk_table 6、colossus 4、spacex_xai 4、doubao_price_war 4、
  bis_rule 4、chatgpt 3、v3 2、overseas_rental 2、sec_probe 1、
  huang_resign 1。无实例的两种：generic（真实 trace 不用它兜底）、
  openai_mar26（move 文本无 1220/8520/1.25万亿命中）。
- 重抽取：页面 data.json 重新拷贝，194,222 字节，sha256
  `07995677f405f030d66188e6ab910450bb50db96dbcc3549556f066d941f365d`
  （含集成众数并列展示新增的 `forecast.ensemble`，与旧 raw trace
  逐条比对、忽略 semantic_kind 后 0 差异）。Raw trace
  `raw-trace-real.json`（schema v3）；canonical trace
  `traces/trace-latest.json`（schema v4，558 条，全部含
  semantic_kind），meta trace_sha256
  `7d8dfe58667c602b100c2ba4dbc3bf356fff0f0ae17015140679f9cecafd26d8`。
- 历史层重跑 `runs/2026-11-21_123024/`：总体 **pass**（检查器 0 失
  败、0 gap；Lean 构建退出码 0）。C5 跨度规则与 C6 不同卡计数未动、
  未回退。
- 回测回归（fixture）：改后数字与改前逐项相同（M1 5.56%、M2
  49.57%、M3 61.11%、M4 45.73%、M5 81.62%；M1 n=234、0 unknown）。
- 真实 trace 语义回测 `runs/2026-11-21_123045/`（测试窗 S4–S5，
  n=234）：M1 0.0%（0/41，基线 9.55%，−9.55pp；193 条 unknown 被
  排除）、M2 35.47%（−14.53pp）、M3 25.21%（−24.79pp）、M4
  32.05%（+19.55pp，有信号）、M5 81.2%（−1.74pp）。verdict fail
  （按规矩判，低于阈值）；总体 pass（历史层 pass，预测章 fail 不
  影响总体）。模型在 41 条可分类记录上预测的种类：v3 33 次、
  blackwell 4 次、r1 4 次，一次未中。只记录，不评判；校准是下一步
  （真拟合），不在本任务内。
- 场景禁令：数据侧已通——4 个被禁种类（msft_invest、spacex_xai、
  stargate、colossus）全部在真实 trace 的 semantic_kind 集合里，
  四条分支的禁令在语义集里全部可寻。代码侧未通——
  `predict.py --scenarios` 在真实 trace 上仍拒（exit 2：
  `scenario SC-BIS-TIGHTEN bans unknown kind 'msft_invest'`），因其
  种类集只读 action_kind。需另行授权的最小改动（3 处，加一个
  `kind_of` 辅助函数，semantic_kind 优先、缺失时回退
  action_kind）：`expected_deltas`、 `run_scenarios` 的
  `all_kinds`、`main` 的 `all_kinds` 与 `start_actions`。详见
  `design/semantic-kinds.md` 第 8 节。
- 已知缺口（本任务不改，记在这里）：C5 只查 action_kind，不查
  semantic_kind；`overseas_rental` 在语义层有 2 个实例（BYTE S5
  3-2、S5 4-1），C5 不认语义种类。是否把语义禁令纳入 C5，待后续
  任务定夺。

## 2026-11-21 晚新增（第一次真拟合已跑，live 已升 v3）

- 输入：真实 trace `traces/trace-latest.json`（schema 4，558 条，73 条已分类、485 条 `unknown`）。拟合窗口 S1–S3。覆盖：窗口 324 条 move。可分类 32 条。`unknown` 292 条。首轮 S1R1 排除 18 条（含 1 条可分类）。决策数 n = 31。`unknown` 记录 275 条不进拟合。状态链正常折叠。`fit.py` 改两处（禁区未碰：页面、data.json、check.py、Lean、predict.py、backtest.py、ensemble.py、convert_data_json.py）：① 候选种类与 `recorded_in_candidates` 改读 `kind_of()`（semantic_kind 优先，缺失回退 action_kind），`unknown` 排除出候选集；② 备注不再硬编码。`--status auto`（默认）按输入 trace 生成。Fixture 走冒烟备注。真实 trace 走真实拟合备注。注明 trace 路径、schema、semantic_kind 覆盖、决策数。
- 修掉一个真 bug：旧 `recorded_in_candidates` 还比 `action_kind`。真实 trace 上 31 条决策全判不在候选集。感知机零更新。权重原样等于归一化初值。修后 18 条在候选集内。Fixture 不受影响。冒烟数字重跑逐项相同。
- 拟合结果（`runs/fit-real-2026-11-21/`，fit_id `fit-2026-11-21-01`，status 全是 fitted）：共享 α = 0.75、γ = 1.0、τ = 0.25、违规率 0.709677（22/31）。权重 w_hp 0.001469、w_gold 0、c_lever 0.447213、c_rule 0.894425、w_pos 0.001488。占位 (1, 1, 5, 10, 1) 同窗口 0.806452（25/31）。好 3 条决策。按采用规则写入 live。`rules/payoff-model.json` 现为 v3 fitted。占位 v2 备份在运行目录（改前哈希 `28edce28…`，改后 `0e3d6345…`，与 fitted 文件哈希一致）。五类：china_vendor n = 8、违规率 0.836666（加权）；chip_supplier n = 2、1.0；cloud_hyperscaler n = 5、0.6；leveraged_infra n = 1、1.0；model_lab n = 15、0.562814（加权）。v1 投影共享违规率 0.83871（26/31）。比占位差。Bootstrap：w_gold 为 0 的占比 0.92。w_pos 均值 0.234、标准差 0.285。不稳定。
- 结构下限：13/31 决策是首发种类。41.9%（fixture 是 7.4%）。可学习子集 18 条。拟合 9/18 错。占位 12/18 错。v1 投影 13/18 错。网格里 α = 0.25、0.5、0.75 在 γ = 1.0 时全是 0.709677。平局取最接近 1 的 α。α 值未被数据识别。
- Hold-out 回测（S4–S5，n = 234，v1 投影）：M1 0.0%（0/41）、M2 34.62%、M3 25.21%、M4 31.62%（唯一信号）、M5 80.77%。threshold_verdict below_threshold。占位回测同窗口：M1 0.0%、M2 35.47%、M3 25.21%、M4 32.05%、M5 81.2%。拟合没有一项更好。样本内采用收益没有泛化。测试窗预测 v3 232 次、r1 2 次。
- 收敛检查（拟合 v2，α = 0.75，`predict.py --horizon 7`）：第 1–6 轮收敛（1–2 次迭代）。第 7 轮跑满 20 次迭代。循环。不收敛。第二件的发现复现。不修。超出范围。
- 两个诚实问题都复现。第一，权重塌缩。比冒烟更重。w_gold = 0。w_hp 与 w_pos 近 0。c_rule 占优但不可识别（f_rule 恒为 0）。chip_supplier（n = 2）与 leveraged_infra（n = 1）权重等于归一化初值。零更新。第二，负向控制。同一协议重跑。broken 与 ok 违规率完全相同。S1–S3 窗口 0.732026。全窗口 0.822222。证据在运行目录 `negative-control/`。
- 备注核对：四份输出全部是真实 trace 备注。唯一残留的 `fixture` 字样是 `is_fixture_trace: false` 标志与 backtest 文件 `note_correction` 里保存的原文。`backtest.py` 的备注硬编码占位口径。backtest.py 在禁区内不得改。输出文件事后订正。原文保存在 `note_correction` 里。`predict.py` 的输出仍带硬编码 `placeholder_only` 备注。predict.py 不在本次范围。未改。只在 fit-report.json 里标注。
- 还缺什么：语义覆盖是瓶颈。86.9% 的 move 是 `unknown`。只有 31 条决策进拟合。c_rule 不可识别。hold-out 没有证据表明 live v3 模型预测更好。收敛处理是独立任务。chip_supplier 与 leveraged_infra 的分档拟合是空的。详见 `design/fitting-layer.md` 新增的真拟合附录与 `runs/fit-real-2026-11-21/fit-report.json` 的 `post_fit` 块。

## 2026-11-21 晚新增（predict.py 语义接入 + v2 效用集成 + 分布差异确认）

- 语义接入（只改 `predict.py`）：新增 `kind_of(m)`（与 `backtest.py` 同步，semantic_kind 优先、缺失回退 action_kind）；`expected_deltas` 按 semantic_kind 分组；`run_scenarios` 与 `main` 的 `all_kinds` 改用 kind_of；`main` 的 `start_actions` 改用 kind_of；`apply_move` 禁令校验改用 kind_of；`normalize_move` 透传 claim 的 semanticKind/semantic_kind；`build_fork` claim 分支改用 kind_of。禁令校验（913–918 行）零改动，随 all_kinds 自动生效。line 402 fork move 字典 `"action_kind": kind` 故意不改（check.py C5 读 action_kind 做禁令检查）。场景在真实 trace 上被接受（exit 0，4 场景全出）；fixture 回归数字逐项相同（M1 5.56%、M2 49.57%、M3 61.11%、M4 45.73%、M5 81.62%，below_threshold；scenarios/backtest JSON 字节相同）。
- `unknown` 排除出候选集（与 backtest.py 一致；`start_actions` 本就按候选集过滤，无需另改）。真实 trace 概率重分最大 0.000116，恰等于被排除的 unknown 质量；18/18 众数动作相同。
- v2 效用集成（只改 `predict.py`）：`utility()` 新签名 `(params, hp_before, hp_after, dhp, dgold, lever, compliance, position)`；α 取 `hp_exponent`，γ 取 `discount` 只读不用（设计稿 §3：γ 只做拟合证据的新近加权，单步预测不折现未来奖励；多步延续值折现是未来扩展）；α==1 时用 dhp 原值；α≠1 时 f_hp = hp_after^α − hp_before^α；金币线性。第一版曾因浮点舍入翻 4 条回测记录（`(hp+dh)−hp ≠ dh`，差约 2e-15），修法为多传 dhp、α==1 用原值，修后全部干净。验证：改前改后回测 JSON 逐字节相同；α=0.5 sanity（临时文件，live 未动）：3 席众数翻转，手算 HUAWEI v3 f_hp = √76−√72 = 0.232517 逐位一致。α<1 时 best-response 20 轮不收敛（cycle），真拟合收敛检查复现。
- 分布差异确认：`runs/2026-11-21_123045/`（12:30:55，全员 anthropic_ipo p=1.0）用的是旧版 predict.py（改动在 12:36:45 与 12:41:20）；输入相同（trace 逐字节相同，payoff v2 占位未变）。机制：旧分组下 anthropic_ipo 期望值只来自 1 条 move（“分阶段募资到手”，Δ血 +8、Δ金 +30，效用和 38.00）；新分组下同一 IPO 线索 8 条 move 均值 [−2.88, +2.75]，v3（n=2，均值 [7, 2.5]）最优。最终版重跑（`/tmp/pred-final/`，占位 v2，exit 0）：15× v3、NVDA blackwell、ORCL/DPSK r1；2 轮收敛；场景全接受（BASE 0/0.0、BIS 7.6e-05、RASA 0.046962、TRUCE 7.6e-05）。仍是占位参数，未校准。
- 还缺（下一 lane）：`ensemble.py` 仍从 action_kind 建候选集、未排除 unknown；`backtest.py` 与 `predict.py` 的 smoke 备注硬编码 fixture 口径（真实 trace 上也打印）；live v3 的 `alpha_gamma_note` 有一句过期（称 predict.py 仍是 v1、忽略 α/γ，实际 predict.py 已是 v2；未改 live 文件保哈希链，待下次写 payoff-model.json 时一并改）；收敛处理是独立任务。已闭合（本 lane）：α=0.75 hold-out 已补测（见下节）；trace 标签已修（见下节）。

## trace 标签修复 + C1/C2 重核 + α=0.75 hold-out 补测（2026-11-21 晚）

### ① trace 标签修复：extract.py 的 source_sha256 曾是 raw trace 哈希
- 根因：`extract.py` main() 对输入 raw 文件整体取 sha256 后标为 `source_sha256`；输入是中间产物 raw-trace-real.json，故该值（03492ec4…）是 raw trace 的哈希，不是 data.json 的哈希。转换器早已把 data.json 哈希记在 raw trace 头部 `source_data_json.sha256`（07995677…），extract.py 只是没读它。
- 修法（只改 extract.py，未手改 trace 文件）：`build_trace()` 加 `raw_trace_sha256` 参数，meta 新增 `raw_trace_sha256` 字段（审计链保留旧值）；main() 优先读 raw 的 `source_data_json.sha256`（须为 64 位小写 hex，否则回退并打印警告），无该记录时（如 fixture）回退为 raw 输入文件哈希（此时源就是该文件，标签不误）。docstring 已写明语义。
- 重抽取（与原调用相同：`python3 extract.py raw-trace-real.json`，默认 out=traces、page-version v7）：exit 0，校验通过（schema v4，558 条）。新 trace：meta.source_sha256 = 07995677f405f030d66188e6ab910450bb50db96dbcc3549556f066d941f365d（= data.json，data.json 未动）；meta.raw_trace_sha256 = 03492ec4…；meta.trace_sha256 = 2fd0b38fc6ad80512afa466f4d55d1abfcb695f3381291a208880c9fa8e31c23（文件实测 sha256 e16c221b…，二者不同是 extract.py 既有行为：meta 哈希在嵌入哈希字段之前算出）。moves 与全部非 meta 内容与旧 trace 逐项相同。
- 旧 canonical trace 已保留：`traces/trace-2026-11-21-fd79d114.json`（live v3 fit 记录的 trace_sha256 fd79d114 仍可解析）。注意：live v3 的 fit.trace_sha256 仍指向旧 trace（新 trace 只改了 meta 标签与 extracted_at，moves 相同）；payoff-model.json 未动（禁区）。
- 历史层重跑：`runs/2026-11-21_125719/` 总体 pass（检查器 0 失败、0 gap；Lean 构建退出码 0；B1 仍 pass）。每日循环不受影响：daily_run.sh 不调 extract.py，ingest.py 从既有 canonical trace 派生，meta 标签随基 trace 带入。

### ② C1/C2 重核（最终版 predict.py + 新 trace 2fd0b38f…）：均通过
- 预测（`./run.sh --predict --payoff runs/fit-real-2026-11-21/payoff-model-placeholder-v2.json`，占位 v2，与 123045 同条件）：`runs/2026-11-21_125725/` 总体 pass；预测章 fail（按规矩判：预测 pass、回测 fail、符号动力 pass、协议缺失）。合并报告预测章与 123045 逐项相同（prediction pass、backtest fail、symbolic pass、protocol None、below_threshold True），只 trace_sha256 不同（7d8dfe58… → 2fd0b38f…）。
- 回测数字与 123045 逐项相同（overall/by_season/by_player 全等）：M1 0.0%（0/41）、M2 35.47%、M3 25.21%、M4 32.05%（唯一信号）、M5 81.2%，verdict fail。
- 预测分布与 `/tmp/pred-final/prediction.json` 逐项相同（18 行：众数 + 概率 + top3_mass 全等）：15× v3、NVDA blackwell p=0.999748、ORCL r1 p=0.998485、DPSK r1 p=0.952574、TCE v3 p=0.620522、TSMC v3 p=0.815352；2 轮收敛；reverify check=pass、Lean=pass（覆盖 576 条、6 季、108 排名——含 S6 fork）。
- 场景（`predict.py --scenarios` 直跑，新 trace，占位 v2）：exit 0，4 场景全出，触发概率一律 null；max_shift 与 /tmp/pred-final 逐项相同（SC-BASE 0.0、SC-BIS-TIGHTEN 7.6e-05、SC-RASA 0.046962、SC-TRUCE-EXPIRE 7.6e-05），跨场景众数变化 0；场景文档全文与 /tmp/pred-final/scenarios.json 相同（除 trace 路径字段，值相同）。输出在 `runs/scenarios-recheck-2026-11-21/`。
- 须知：prediction-report.json 的 verdict 在 /tmp/pred-final 是 fail、在本次重核是 pass，差异来自调用方式，不是行为变化：predict.py 的 verdict 只在传入 --backtest-report 时计入回测阈值（fail 当且仅当有 claim 被 refuted、reverify 失败、或回测 below_threshold）；/tmp/pred-final 传了 backtest 报告（below_threshold → fail），本次 run.sh 与直跑均未传（→ pass）。合并报告才是同口径对照，二者预测章相同。
- 符号动力与 123045 逐字节相同（432 单元、20925 边、225 SCC、216 吸引子，全是单格死单元）。

### ③ α=0.75 hold-out 补测（live v3，测试窗 S4–S5，n=234）：只记录
- 运行：`runs/holdout-alpha075-2026-11-21/backtest-report.json`（`backtest.py traces/trace-latest.json --payoff rules/payoff-model.json`；live v3 共享参数 w_hp 0.001469、w_gold 0、c_lever 0.447213、c_rule 0.894425、w_pos 0.001488、τ=0.25、α=0.75、γ=1.0；predict.py/backtest.py 只读共享 `parameters`，per-type 参数不参与预测）。
- 结果（verdict fail，below_threshold [M1, M2, M3, M5]）：

  | 指标 | α=0.75 live v3（本次） | v1 投影 hold-out | 占位（123045） |
  |---|---|---|---|
  | M1 | 0.0%（0/41，基线 9.55%） | 0.0% | 0.0% |
  | M2 | 34.62%（基线 50%） | 34.62% | 35.47% |
  | M3 | 25.21%（基线 50%） | 25.21% | 25.21% |
  | M4 | 31.20%（基线 12.5%，+18.70pp，唯一信号） | 31.62% | 32.05% |
  | M5 | 79.91%（基线 82.93%） | 80.77% | 81.20% |

  分季：S4（n=108）M1 0.0%、M2 45.37%、M3 35.19%、M4 34.26%、M5 91.67%；S5（n=126）M1 0.0%、M2 25.40%、M3 16.67%、M4 28.57%、M5 69.84%。M1 分母 41（193 条 unknown 排除）。
- 并列事实（不评判）：被采用的 α=0.75 模型在 hold-out 上没有一项优于 v1 投影（M4 −0.42pp、M5 −0.86pp、其余三项相等），也没有一项优于占位。另：v1 投影与 live v3 不止 α 不同——v1 投影的 w_hp 是 0.0（α=1 下重拟合的结果），live v3 的 w_hp 是 0.001469；c_lever/c_rule/w_pos/τ 基本相同。所以本次对照不是纯 α 消融，是“被采用的拟合模型”对“α=1 重拟合模型”。
- 口径须知：backtest.py 输出的 fit_note 与 calibration_status 是硬编码（称“placeholder parameters, not calibrated”、placeholder_only），与本次输入（live v3 fitted，fit-2026-11-21-01）矛盾——报告 JSON 内的文字不可引为本次运行的口径；数字以本节为准。修备注是已知缺口（见“还缺”），本次未改 backtest.py。

### 还缺
- 被采用模型（live v3）的预测分布（predict.py 直跑）尚未产出——本次只补了 hold-out 回测，未跑 v3 预测。
- ensemble.py 仍从 action_kind 建候选集（真实 trace 上集成未重跑）。
- C5 与语义层词汇不一致（overseas_rental 语义层有 2 个实例，C5 只查 action_kind）。
- live v3 的 alpha_gamma_note 过期句、backtest.py/predict.py 的 smoke 备注硬编码，待下次写相关文件时一并改。

## 语义词汇扩展 + 第二次真拟合（2026-11-21 晚）

### ① 词汇扩展：规则 16–29，新种类 14 个
- 转换器 `convert_data_json.py`：`SEMANTIC_VOCABULARY` 17 → 31 种；`classify_semantic()` 追加规则 16–29，整块排在 15 条旧规则之后（第一命中即定）。新种类：tongyi、hunyuan、ascend、doubao、wenxin、pangu、llama、claude、gemini、megaspeed、energy、financing、capex、open_source。文心/盘古不在任务枚举清单内，是探针发现的同形产品线（BIDU 11 条、HUAWEI 6 条），一并覆盖，见 design/semantic-kinds.md。
- 探针核验（全量 558 条）：通义 12 条（1 条已是 blackwell）、混元 10 条、昇腾 10 条（1 条已是 r1）、豆包 10 条（2 条已是价格战）、文心 13 条（2 条已是价格战）、Llama 6 条、Claude 5 条、Gemini 3 条 + Bard 1 条、核电 2 条扩为 energy 10 条（同轮电力/绿电/燃气/供电）、Megaspeed 1 条、融资 11 条 + 债务 5 条 + 借钱 3 条 = financing 19 条、资本开支 16 条中 15 条归 capex（1 条 AAPL 含借钱，归 financing）、开源 37 条中 24 条归 open_source（产品名 11 条、bis_rule 1 条、不开源 1 条除外）。融资探针结论：不过宽，11 命中全是融资线程。订单/推理/算力/股价等扩散词不建种类（见 design/semantic-kinds.md §5 剩余缺口表）。
- 回归保证三重：内存模拟先验 73 条不变；重抽取后与备份 trace 比对，非语义字段 0 差异、旧已分类 73 条逐项不变、新分类 139 条全来自 unknown 池；转换器自检新增 `EXPECTED_LEGACY_COUNTS` 冻结 15 种旧种类计数（任一移动即失败）。设计文档 design/semantic-kinds.md 已更新（§2 表、§3 规则 16–29、§4a 新歧义排除、第 4 节“产品名本身不对应任何种类”旧说法已标注废止、§5 缺口表更新、§7 新回测数、§9 自检三项、§11 本次重抽取）。

### ② 重抽取 + 历史层重验
- data.json 未动（重拷贝后 sha256 仍为 07995677…）。旧 trace 已备份：`traces/trace-2026-11-21-2fd0b38f.json`。新 trace：meta.trace_sha256 4ec473d2…，文件实测 sha256 f4bcebd9…，meta.source_sha256 07995677…（= data.json）。
- 新覆盖率：212 条已分类、346 条 unknown（62.0%，原 86.9%）；拟合窗口 S1–S3 已分类 129/324 条；回测窗口 S4–S5 M1 分母 83 条（原 41 条）。
- 历史层重跑：`runs/2026-11-21_131852/` 总体 pass（检查器 0 失败、0 gap，Lean 构建退出码 0）。C5/C6 修法未动、未回退。

### ③ 重拟合 + hold-out（runs/fit-real-2026-11-21-02/，fit-2026-11-21-02；不写 live）
- 拟合（S1–S3，n=126，占位 v2 作 --payoff，--status auto）：共享 α=1.0、γ=0.9、τ=0.25、违规率 0.952044（加权；未加权 0.960317 = 121/126），权重 (w_hp 0、w_gold 0、c_lever 0.445106、c_rule 0.890213、w_pos 0.096961)；v1 投影违规率 0.960317。占位同窗口 0.880952（111/126）——拟合比占位差 10 条决策，方向与第一次反了（第一次好 3 条）。五类：china_vendor n=59 违规率 0.876806、chip_supplier n=5 0.6、cloud_hyperscaler n=29 0.896552、leveraged_infra n=7 0.725063、model_lab n=26 0.884615。Bootstrap：w_gold 为 0 占比 0.96，w_hp 为 0 占比 0.70。
- 结构下限：首发 34/126（27.0%，原 41.9%）；可学习子集 92 条，拟合 87/92 错，占位 77/92 错——拟合在可学习子集上也差 10 条。α 网格仍平坦（α=0.25/0.5/0.75 在 γ=1.0 时未加权违规率全是 0.952381），α 未被数据识别；τ=0.25 仍是网格下限。
- Hold-out（S4–S5，n=234，M1 分母 83）：拟合 v1 投影 M1 2.41%（2/83，都在 S4；基线 4.30%）、M2 34.19%、M3 24.79%、M4 35.90%（唯一信号）、M5 82.48%；占位 M1 0.0%、M2 35.04%、M3 25.21%、M4 36.32%、M5 82.05%。拟合赢 M1（+2.41pp）与 M5（+0.43pp），输 M2/M3/M4——混合，未达采用标准。
- 采用规则已改（v3 的教训，见 design/fitting-layer.md 新增附录）：只有 hold-out 优于占位才采用，样本内好不算。结论：**不采用**。live payoff-model.json 未动（仍为 v3，fit-2026-11-21-01，sha256 0e3d6345…，与第一次拟合后相同）。拟合输出只在 runs/fit-real-2026-11-21-02/（fit-report.json 含 post_fit、payoff-model-fitted.json/v1、backtest-fitted.json 备注已订正、backtest-placeholder.json、backtest-fixture-regression.json、predict-convergence-check.json、negative-control/）。
- 两个诚实问题都复现：权重塌缩（w_hp=w_gold=0，c_rule 占优但不可识别）；负向控制 broken 与 ok 违规率完全相同（S1–S3 0.732026，全窗口 0.822222；四份报告与第一次逐项数值 0 差异）。新增：拟合反噬（可学习子集上拟合比占位差 10 条）；收敛恶化（拟合 v2 在 horizon 7 下 7 轮全部 20 次迭代循环；对照：占位 v2 在同一新 trace 上 7 轮全部 1–2 次迭代收敛，循环是拟合权重造成的）。
- Fixture 回归：fit/backtest 在 fixture 上数字与改前逐项相同（负向控制四份报告 0 差异；回测 M1 10.26%、M2 44.44%、M3 55.56%、M4 46.15%、M5 85.47%，与冒烟逐项相同；仅新增语义层字段）。

### 还缺（下一 lane）
- 信号，不是覆盖率：已分类 73 → 212 条、可学习决策 18 → 92 条，拟合反而更差。下一步是 Gu 三步方案的第③步：改模型或改预测目标（只预测对事件的反应，不预测事件本身）。
- ensemble.py 仍从 action_kind 建候选集（真实 trace 上集成未重跑）。
- C5 与语义层词汇不一致（overseas_rental 语义层有 2 个实例，C5 只查 action_kind）。
- live v3 的 alpha_gamma_note 过期句、backtest.py/predict.py 的 smoke 备注硬编码，待下次写相关文件时一并改；收敛处理是独立任务。

## 改进循环第一批（3 轮，2026-11-21 晚；审计 P0 全部落地）
- 第 1 轮（a18018d/57d6685）：live v3 回退占位 v2（version 2，fit null，参数 1.0/5.0/10.0）；预测章标 opinion；alpha_gamma_note 过期句已改；A1–A9 与占位值一致；v3 保留在 runs/fit-real-2026-11-21/。run.sh 历史层全过。
- 第 2 轮（18db859/d6d24e9）：采用规则改成 hold-out 门控（fit.py 新增 ADOPTION_RULE 与 evaluate_holdout_gate()；design/fitting-layer.md 第六、七节；每次拟合附 hold-out 对照表）。v3 三条全不满足（优于占位 0 项；M1 0.0% 低于基线 9.55%；M2/M3 34.62%/25.21% 低于 50%），应不被采用；fit02 也过不了门。run.sh 全过。run.sh 头部注释已改（opinion 口径）。
- 第 3 轮（d632a8d/cec2ec3）：退化分布守卫（predict.py 新增 degeneracy_metrics() 与 degeneracy 块；merge_report.py 预测章加退化守卫小节，guard fail > opinion；backtest.py 新增 M6 校准度）。当前运行退化率 0.000（0/18，熵 1.275 比特），守卫未触发；守卫已验证会触发（旧退化报告与合成退化报告都记 fail，总体仍 pass）。M6 = 0.9971（阈值 < 0.2，不通过；顶桶 [0.99, 1.0] n=28，均值 0.997141，实际命中率 0.0）。run.sh 全过（runs/2026-11-21_133910/ 总体 pass，预测章 opinion）。
- 批结论：预测本身没有变好（M1 仍 0/83，M2/M3 低于抛硬币）；变好的是诚实度与安全性（坏模型下线、门控防再犯、退化自动标 fail、校准度可量）。详见 design/batch-1-report.md。下一批按审计 P1：期望增量收缩、可行表、删 c_rule。
- GitHub 远程已接：https://github.com/anan421/jin-chan-chan-verification（private）。本地 main 在 cec2ec3，未推 GitHub（按任务要求只用本地 git；推不推由 parent 定夺）。

## 改进循环第二批（3 轮，2026-11-21 晚；审计 P1 改法 4–6）

- 第 4 轮（b0e4e07/72fc739，合并）：期望增量加最小支持数与收缩（n < 5 的种类不用历史均值，改用 (n×种类均值 + 5×全局均值)/(n+5)，k=5；分层（玩家，种类）→ 种类 → 全局均值）。backtest.py 的语义期望增量复刻改成直接委托 predict.expected_deltas（单一实现）。v3 收缩后 dHP +7.00 → +2.30。验收：run.sh 全过（runs/2026-11-21_134835/ 总体 pass，预测章 opinion）；最大种类占比 74.4% → 46.2%（< 50%）；v3 预测 174 → 5 次；M1 0.0% → 1.2%（1/83），M2 35.04% → 35.47%，M3 持平 25.21%，M4 36.32% → 54.70%，M5 82.05% → 91.88%，M6 0.9971 → 0.922（仍不通过），退化率 0.000，熵 1.216 → 1.769 比特。血量段与规则版本分组没做（S1–S3 前缀 94 个格，0 个达到 n ≥ 5，数据撑不起）。诚实说明：M4/M5 好转一半是机械的；基线 v3 次数实测 174 次（任务书写的 232 次是旧退化运行数）。新回归：实时预测最佳回应不再收敛（20 次迭代跑满，cycle=True）。
- 第 5 轮（0a1d47e，未合并，分支 loop/round-5-feasibility-mask 保留）：可行表（feasible_kinds：anthropic_ipo 仅 ANTH、huang_resign 仅 NVDA、sec_probe 仅 NVDA、llama_open → llama 仅 META；one_shot；exogenous 不进 argmax）。可行性违规率叫 M7（审计的“M6”与已有 M6 校准度重名）。验收：run.sh 全过（runs/2026-11-21_135637/ 总体 pass）；M7 = 0（0/234，实时 0/18）；M1 1.2% → 2.4%（2/83），M4 54.70% → 57.26%，M5 91.88% → 93.16%（首次成信号），熵 1.769 → 2.054 比特，收敛变好（3 次迭代收敛）。但 M6 0.922 → 0.9507 变差，按门规则“一项变差即不算变好”，不合并。副作用：v3 预测 5 → 32 次；实时预测更集中（claude 16/18）；测试窗最大种类占比 46.2% → 54.3%。环境备注：/tmp 被 44 个陈旧的 predict-lean-* 临时目录占满导致一次场景运行写盘失败，已清掉；predict.py 的 reverify 临时目录从不清理，是长期隐患。
- 第 6 轮（f7cfa44/bc4a708，合并）：删 c_rule（fit.py 特征构造、L2 归一化、live 参数、效用式；A4 改成墓碑）。识别诊断已产出（runs/fit-round-6-2026-11-21/fit-report.json）：梯度非零比例 w_hp 0.913、w_gold 0.913、c_lever 0.0、w_pos 0.391；bootstrap 零值占比 w_hp 0.62、w_gold 0.68、c_lever 0.0、w_pos 0.64。w_hp 从 0 升到 0.127，第一次看得见真实大小。w_gold 0.68 ≥ 50%，报告已写明“金钱项未识别”。新发现：c_lever 梯度非零比例也是 0.0——它的 0.987 基本是占位初值经归一化剩下的，不是学出来的；诊断本身会动（fixture 冒烟上是 0.010563），真实 trace 上的 0.0 是数据事实。验收：run.sh 全过（runs/2026-11-21_140227/ 总体 pass）；测试集与基线逐项相同（M1 1.2%、M2 35.47%、M3 25.21%、M4 54.70%、M5 91.88%、M6 0.922、退化率 0.000、熵 1.7693）。
- 批结论：预测本身还是不行（M1 1/83，M2/M3 低于抛硬币，M6 0.922 不通过）；变好的是估计量与诚实度（小样本不再主导预测；权重里不再有无信息参数；识别诊断能量出来；坏改动按规矩退回）。详见 design/batch-2-report.md。下一批按审计 P1 改法 7–9：τ 网格下限、收敛守卫、v2 拟合与 v1 部署不一致。
- 本地 main 在 bc4a708，未推 GitHub（推由 parent 定夺；origin/main 在 fb5c763）。

## 改进循环第三批（2026-11-21 晚，研究果实 1–3）

- 输入：`design/how-others-predict.md`（BootLoops 研究，8 条果实）。本批取果实 1–3。
- 第 7 轮（基础比率先行，分支 loop/round-7-base-rates，提交 1ae740f，未合并）：每种动作先算前缀频率当出发概率，模型分布乘以出发概率再归一化；单一实现 `predict.base_rates()`。猜中 1/83 → 1/83 持平；血量方向 +2.14pp、段位 +2.56pp、校准度 0.922 → 0.6099（仍不通过）、熵 1.769 → 2.113、最大占比 46.2% → 30.3%、v3 5 → 0。只用基础比率猜中 6/83，比模型好，果实未被证伪；合并后的模型输给只用基础比率的傻猜。24/83 条首发记录不在候选集里，上限 59 条。边界：先验只改报告分布与 modal 动作，不进最好回应迭代层。
- 第 8 轮（多路合并，分支 loop/round-8-multi-path，提交 dabcdb8 + 更正 affaeab，未合并）：16 条路（效用模型、只用基础比率、15 名成员权重），按拟合窗表现加权，λ 网格搜索选 0.0。猜中 1/83 → 1/83 持平，4 项变差（血量方向 −0.43pp、段位 −2.56pp、最大占比 46.2% → 55.6% 越过 50%、v3 5 → 9）。合并后 1 次不如最好的一路（只用基础比率）6 次，果实 2 被证伪。15 路共用同一套打分规则，不是真正独立的路。实时众数 claude 7、llama 9、r1 2（轮报告初版写成 8/8，复核抓出，已更正）。
- 第 9 轮（事后校准，分支 loop/round-9-calibration，提交 b8ed917 + 更正 ff82d98，合并 4079257）：温度缩放 T=11.554，封顶 0.99，只在拟合窗 S1–S3 上拟合；参数存 `rules/calibration.json`，实现只有一份 `calibration.py`。校准度 0.922 → 0.0521，通过 <0.2；其余指标全不变；猜中仍 1/83。实时众数动作 18/18 相同，众数概率 0.3028–0.5988 → 0.0514–0.0649。拟合窗 M6 0.6947 → 0.0236，对数损失 4.2088 → 2.6634（只比均匀猜测 2.6779 好一点，排序本身几乎无信号）。果实目标“最高一档差距低于 0.2”：最高档在测试窗上改前改后都是空的，目标无法按原口径量；按 M6 口径通过（0.0521 < 0.2）。校准是把高档清空了，不是修好了高档的近乎确定断言。
- 基线描述纠正：任务书的“最高一档 [0.99,1.0] 28 条、均值 0.997”是第 3 轮之前的退化运行的数字；main 实测最高档 0 条，M6=0.922 来自 [0.9,0.99) 档（1 条，p=0.922，命中 0）。基线本身无漂移。
- 当前 live：version 2 占位参数 + `rules/calibration.json`（T=11.554，封顶 0.99）。测试窗：猜中 1/83、血量方向 35.47%、金币方向 25.21%、段位 54.70%、量级 91.88%、校准度 0.0521（通过）、退化率 0.000、熵 1.7693。main 在 4079257，未推 GitHub。
- 仍待办：首发种类进候选集（24/83 不可达）；收敛回归（20 次迭代跑满）；c_lever 梯度非零比例 0.0；ensemble 语义对齐；新数据重算缩放无自动机制；拟合窗 34/126 条记录未进拟合；C5 与语义层词汇不一致；predict.py reverify 临时目录不清理。

## 改进循环第四批结果（2026-11-21，3 轮，main 仍在 b23a778，三轮全退回）

- 第 10 轮：按玩家分参考类（果实 4）。每个玩家一份自己的种类历史（拉普拉斯平滑），n<5 回退同类平均、再回退全局平均；`per_player_rates()` 由 predict.py 与 backtest.py 共用。run.sh 全过（runs/2026-11-21_144922/）。猜中 1/83 没变；M2 +2.14pp、M5 +0.86pp（测不出来）；M6 0.0521→0.0537（仍通过）。只用分玩家规则 23/83（27.71%，玩家层 30.0% > 同类层 15.38%），只用全局基础比率 6/83（复现第 7 轮）。果实 4 未被证伪，但合进模型后只剩 1/83——先验是对的，合并方式是问题（与第 7 轮同一结论）。退回，分支 loop/round-10-per-player（12c6d0e）保留。
- 第 11 轮：首发种类进候选集。候选集改成全部已知语义种类词汇（31 种），首发种类给下限先验 1/(N+K)（K=31）、期望增量用前缀全局均值。run.sh 全过（runs/2026-11-21_145923/；复核员重跑 runs/2026-11-21_150540/）。猜中上限 59→83 打开了，但 24 条首发记录猜中 0 条，模型一次也没以首发种类作众数；猜中仍 1/83。证伪条件触发。归因：均匀先验对照结果完全一样——不是 floor 先验压住了首发，是首发期望（同一全局均值）在 234 次里一次也没赢过见过的种类，且所有首发种类效用全相等。退回，分支 loop/round-11-first-appearance（fc65e75）保留。复核员确认无偷看未来。附带发现：design/semantic-kinds.md §7 的 fixture 数字漂移是先前就有的（基线提交 98be845 里已写入），待修。
- 第 12 轮：拆问题（果实 5）。三问：Q1 新/旧种类、Q2 动哪种、Q3 幅度档（zero/mid 1–4/big ≥5，只看 |dHP|）；反对 0–3 项（前缀来源）+ 支持（效用 softmax × 分玩家先验），log 空间相加、惩罚 exp(−λ·反对数)，λ=1.0。run.sh 全过（runs/2026-11-21_151549/；复核员重跑 runs/2026-11-21_152059/）。猜中仍 1/83；Q1 59/83 与只猜“旧”打平（模型一次也没预测“新”），Q2 1/83，Q3 150/234 与前缀多数档打平（模型 big 0 次；150 次命中是 147 次 mid 对 mid 加 3 次 zero 对 zero）。证伪条件触发，果实 5 在这个窗口上被证伪。M5 第一次成 signal（margin 10.23pp），但超出门槛只有约半条记录的量，不计为变好。退回，分支 loop/round-12-decompose（e619e24）保留。候选集统一为共享 candidate_kinds()（第 11 轮复核员指出的顺序不一致已统一）。
- 批结论：预测本身还是不行（猜中 1/83）；三轮全退回，main 未动。变好的是上限与分布的形状，不是猜中的次数。详见 design/batch-4-report.md。
- 停止条件记账：连续没有变好的轮次已到 3 轮（第 10、11、12 轮），按循环设计应停，报结果。但 Gu 2026-11-21 22:06 说“重要的是多尝试”，是否继续由 Gu 定夺。下一批方向（若继续）：换合并方式 → 首发种类给不同期望 → 果实 6（单独成批）→ 收敛守卫。
- 仍待办（本批未动）：收敛守卫（审计改法 8）、果实 6、c_lever 归一化假象、ensemble 语义对齐、C5 与语义层词汇不一致、reverify 临时目录不清理、semantic-kinds.md §7 fixture 数字漂移。

## 锦标赛第 4 轮：项目/手段分开（2026-11-22 00:44–00:53；分支 loop/round4-project-means，未合 main，未推 GitHub）

- 方法：在先查资料 Agent（60/83）基础上只加一个小改动——每道题分两步写清楚：① 先定这个玩家在做什么项目/线索；② 再定他用什么手段（从事实定，不要从项目名字定）。输入和先查资料同一套（轮次日期之前的事实 + 标题事件；主角不给；真实日期在轮次日期之后的不给）。13 个轮次预测员单轮隔离，每人只看自己那一轮的题目文件 + 事实库。题目文件复用主题轮分人线的 13 份（83 道），标题事件逐题复现先查资料口径（headline-events.json）。用脚本打分。
- 分数：项目/手段分开 46/83（55.4%），先查资料 60/83，净 -14，没有打过先查资料，假设没有证实。配对：都对 44、只项目/手段对 2、只先查资料对 16、都错 21。首发 15/24（先查资料 18/24），重复 31/59（42/59）。把握反的：high 18/22（82%）、medium 21/50（42%）、low 7/11（64%）。
- 在哪里赢：只赢 2 道，都是 MUSK 的 financing（S5 1-1、S5 6-2）。亮点轮：S4 3-2 能源轮 10/10、S4 4-1 9/10（和先查资料打平或只差 1 道）。
- 在哪里输（16 道独输）：S4 1-1（5/12 对 8/12，主题和自己的产品分错了）、S4 1-3（0/4 全错）、S5 3-2（1/5，bis_rule 一个也没猜）、ANTH 的 IPO 线 4 道全错（全猜 claude，实际全是 anthropic_ipo）、S5 2-1（0/3 全错）。
- MUSK 专项：5/10，和先查资料一样。简报法丢掉的 3 道只修了 1 道（S4 5-1），另外 2 道（S5 2-1、S5 6-1）又猜回了 spacex_xai；修好的 2 道（S5 1-1、S5 6-2）正好抵掉，净 0。
- capex 专项：0/5，比先查资料（2/5）更差。猜了 5 次 capex，全猜错了人；5 道实际 capex 全错过（S4 1-3 OAI、S5 1-1 BYTE/ALI/TCE、S5 6-2 TCE）。
- 种类分布（输的原因）：自己的产品种类猜 23 次（实际 10 次，先查资料 15 次）；主题种类猜 29 次（实际 43 次，先查资料 35 次）；猜的种类等于该玩家历史上最常做的种类 38/83（先查资料 30/83）；anthropic_ipo 只猜 2 次（实际 8 次）；bis_rule 只猜 1 次（实际 4 次）；stargate 猜 8 次（实际 15 次）。
- 为什么输（五条）：① 默认方向反了——两步法默认从玩家出发，只有没信号时才退回习惯或主题；数据说默认应该是主题种类（和主题轮分人线同一教训）。② “手段级信号”偏向产品发布——产品发布总有明确日期，融资、capex、规则反应、上市的信号总是不新鲜或没有。③ “没有信号就按习惯猜”是错的后备规则——习惯在主题轮里最容易错。④ 持续的故事线没有新鲜信号——IPO、星门、融资线不会每轮都有新报道。⑤ MUSK 还是分不清——产品新闻永远新鲜，融资信号总是不新鲜。
- 诚实说明：有 2 道对的题用了轮次日期之后的事实（S4 1-1 BYTE 的 Doubao-1.5-pro 2025-01-22、ALI 的 Qwen2.5-Max 2025-01-28/29，轮次日期 2025-01-20；预测员标为“仅标注，不作支撑”，但它自己的总结又说这两道是因为“有自己的产品发布手段信号”才猜的，前后矛盾）；去掉这两道，干净分是 44/83（53.0%），结论不变。打分脚本里 project == means 这一项是 0/83，是无效检查（project 和 means 都是自由写的一句话，永远不可能字面相等）；报告里用种类分布代替它。Agent 可能知道答案，分数当上限读。13 轮单轮隔离，没有发现漏题。
- 结论：这个方法不用了，不应该采用，也不应该作为下一轮的基础。下一轮应该试“先查资料 + 例外覆盖”（默认猜主题种类，只在有强证据表明某个人是例外时才偏离），不要再从玩家出发、不要再要求每轮都有新鲜的手段级信号。capex 还是没解决，要换修法（找触发器）。
- 交付物：报告 design/project-means-round4.md；13 轮题目文件 + 事实库 + headline-events.json + 13 轮预测 + score.py + scored-project-means.json（runs/project-means-round4-2026-11-22/，runs/ 是 gitignored，只在 worktree 里）。live 模型一字未动（git diff d044512 对 payoff-model.json、predict.py、backtest.py、data.json 是空的）。工作在独立 worktree ~/workspace/verification-r4-project，没碰共享目录。
