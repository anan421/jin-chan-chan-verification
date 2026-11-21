# 形式化验证管线（金铲铲复盘页）

## 目的

页面是手写数据，逐轮增量与赛季末排名是两套未对过账的数字。
本管线用机器检查代替人工目测：抽出单一事实源，两个检查器
（快速检查器 Python、证明层 Lean 4）读同一份 trace，任一
不变量失败，页面不得以“已验证”名义交付。

## 四层

1. 抽取层：`extract.py`
   来源是修复后的页面 `data.json`（单一事实源，页面只做渲染）。
   抽取由 agent 经 `artifact.inspect` 完成（页面是纯客户端静态页，
   无服务端动作，`invoke_action` 不可用），抽出的数据经
   `extract.py` 校验 schema、算哈希，存入 `traces/`。
   trace 是唯一数据源，两个检查器都读同一份 trace。
2. 快速检查层：`check.py`
   确定性 Python 断言，覆盖全部不变量。输出 `report.json` 与
   人工摘要。任一失败退出码非零。每条失败注明 exact 位置
   （赛季/轮次/玩家/字段、期望值与实际值）。
3. Lean 4 证明层：`lean/`
   Lean 4 工程（`lakefile.toml`、`lean-toolchain` 固定版本）。
   `Verification/Model.lean`：对局状态机与不变量谓词。
   `Verification/Dynamics.lean`：无界状态机 + 归纳层。
   状态 = 每名玩家的血量、金币、出局标志、负债标志、规则版本、
   日期、赛季；转移 = 轮次动作。定理用归纳法证明任何由转移
   关系生成的轨迹都保持不变量——覆盖所有未来轮次，不只现在
   的 558 条；558 条是全称定理的一个实例。金币可为负当且仅当
   该动作标了负债（`liability` 标志），金币永不钳制。
   `Verification/Prediction.lean`：预测层。策略是 `DState` 上的函数
   （`Strategy := DState → Move`）；最好回应是给定收益函数与候选
   动作列表的 argmax。定理是条件式：“如果全体玩家走 σ，则轨迹
   保持不变量 / 留在不变集内 / k 步内进入目标段”，证明用
   `invariant_run` 同一形状的归纳。Lean 证的是“给定 σ 的性质”，
   σ 本身来自博弈模型加回测，不是定理的结论。
   `Verification/Trace.lean`：由 trace.json 机器生成（不要手写）。
   `Verification/Proofs.lean`：定理——每条不变量对全部 trace 成立。
   能用 `decide` 的用 `decide`，558 条记录用 `native_decide`，
   按不变量拆成模块化定理；另有五条动态层定理把实例检查链接
   到无界定理（规则表良构、初始态满足不变量、轨迹合法、
   任意长度 run 的终态满足不变量、全部中间态满足不变量）。
   Lean 构建成功即为证明证书。
4. 运行层：`run.sh`
   一键：Agent gate（`--claims` 给出时，先跑，不过则整体失败，
   checker 与 Lean 记 `not_run`）→ 快速检查器 → 生成 Trace.lean
   → Lean 构建 → 合并报告。任一层失败，整体失败。
   `--modular` 另构建按玩家/赛季拆分的证明模块
   （`ProofsByPlayer.lean`、`ProofsBySeason.lean`）并校验其
   `.olean`；非 modular 模式删除残留的模块化源文件，防 stale 构建。
   报告存 `runs/<日期>/`，历史可审计。

## Agent 输入 gate

Agent 的输出在进入管线前先过 `gate.py`（schema 见
`rules/agent-claim-schema.json`）。AgentClaim 只有四类：
提议动作、事实修正、反驳、证据降级。每个 claim 固定字段
（claim_id、kind、subject、predicate、evidence、status、
agent_id），证据指针不能为空。四条规则：R1 schema 不合直接
拒绝；R2 证据指针不存在直接拒绝；R3 谓词不可判定只记
opinion，不得冒充已验证；R4 同一位置相反断言记 contested，
页面不得显示“已验证”，直到其中一条被证据推翻（refuted）
或修正。opinion 只进报告的假设章节，不计入已验证。

## 预测层

验证层回答“对不对”，预测层回答“下一步可能是什么”。预测层建在
`Dynamics.lean` 与 `gate.py` 之上，输出是分布/区域（高概率），
不是单一确定动作，更不是 verdict。预测结果不进“已验证”标签。

- 博弈论玩家模型（`rules/payoff-model.json`）：18 席共用收益函数
  结构，参数按五档分（芯片供应商、云超大规模、模型实验室、
  杠杆基建、中国厂商）。收益 = w_hp·ΔHP + w_gold·Δgold −
  c_lever·杠杆惩罚 − c_rule·合规成本 + w_pos·位置项。解概念是
  马尔可夫完美均衡（MPE），策略只依赖当前状态，计算用最好回应
  动态。每个参数必须引证据或标假设；当前全部参数是占位值
  （A1–A6，另有 A7：AAPL 归入云超大规模档是判断），校准等真实
  trace，fixture 不得用于校准。
- 符号动力（`symbolic.py`）：分区用页面段位映射 × 金币符号 ×
  出局 × 规则版本；转移图用区间推理（过近似：图上“到不了”推出
  具体“到不了”，反方向不成立）；吸引子是汇 SCC；规则变化是剪边。
- Agent 作为玩家（`predict.py` + gate v2）：agent 读当前状态、
  规则版本、历史、预测输出，提议 Move，走 AgentClaim
  （kind=`propose_action`）。Schema v2 加可选 `move` 字段；R2
  扩展未来 subject（赛季 = 当前最大赛季 + 1 且玩家存在）；预测步
  “先应用、再重验”：`applyMove` 返回 none 记为“被转移关系反驳”，
  返回新状态则对扩展 trace 重跑 C1–C12 与 Lean 构建。
- 回测（`backtest.py`）：walk-forward，S1–S3 拟合、S4–S5 测试；
  每轮只给该轮之前的 trace 前缀；指标 M1–M5（动作种类、Δ血方向、
  Δ金方向、下一血量段、Δ血量级），每玩家、每赛季、全体各一张表，
  随机基线并列；超过基线 10 个百分点才算信号，M5 容差 ±10；低于
  阈值降级为 opinion，只报告，不自动修订模型。
- 协议检查（`agent_claims.py`）：覆盖率、引用、可复现、
  可判定，退出码同 check.py。
- 拟合层（`fit.py`）：显现偏好 / 平均结构化感知机，从已记录动作
  估计收益权重（五类各一份 + 全席共享参照 + α=1、γ=1 的 v1 投影），
  α 与 γ 联合网格，τ 做 softmax 极大似然，bootstrap B=50 按轮重采样。
  用法：`python3 fit.py <trace.json> --payoff rules/payoff-model.json [--fit-seasons 1,2,3] [--out-dir runs/fit-smoke-2026-11-21]`。
  输出写到 `--out-dir`（fit-report.json、payoff-model-fitted.json、
  payoff-model-fitted-v1.json），不写进 `rules/`。fixture 拟合一律
  标 smoke_test，不是校准。设计稿见 `design/fitting-layer.md`。
- 接入：`run.sh --predict`，预测在历史层之后；历史层没过不预测；
  预测失败不推翻历史层，预测章单独记 fail，run.sh 退出码只反映
  历史层。合并报告新增“预测”章（分布、命中率、假设清单），
  并写明“预测不是验证”。
- 诚实边界：Lean 证“如果策略是 σ，则性质 P 成立”；“玩家会走 σ”
  是博弈论加回测支持的模型主张，不是定理。高概率由吸引域大小
  与回测命中率两部分量化。

## Trace schema（v4）

`traces/trace-<日期>.json`，见 `extract.py` 的 `SCHEMA` 与
`fixtures/trace-fixture-ok.json`（全量一致样例）。
`check.py` 与 `gen_trace_lean.py` 接受 schema 3 或 4。
`extract.py` 为 v4：接受 raw schema 3 或 4；`--events` 合并 v4
事件；`--claims` 合并 schema v2 claims（只做 R1 校验，R2–R4 仍
由 gate.py 跑）。`ingest.py` 接受 trace schema 2/3/4，v4 时把
事件追加进 trace 的 `events`。

- `meta`：schema 版本、页面 slug、页面版本、抽取时间、来源、
  来源哈希。
- `seasons`：赛季列表，每季自带轮数与活跃玩家名单（支持追加
  S6、S7……到 2030 年及以后；赛季与轮次不在模型里写死）。
- `players`：18 名玩家顺序名单（id、name、key）。
- `moves`：558 条。每条含赛季、季内轮序、轮次标签、玩家、
  血量变化、金币变化、动作种类、动作说明、日期、轮初血量、
  轮初金币、人口、连胜场次、阵容星级、借入本金、适用的规则版本
  （`rules_version`，ROUND_RV）、负债标志（`liability`）。
- `season_state`：每名玩家每季的季初血量/金币、季末血量/金币、
  借入本金、杠杆惩罚。
- `rankings`：页面显示的赛季末排名（每季 18 行，含血量、金币）。
- `hp_series`：页面显示的血量总图（18 条线，每条 5 个季末点）。
- `card_pool`：1–5 费总量。`holdings`：每名玩家持有的关键卡。
  `key_cards`：关键卡（费用、持有者、最晚不得早于的日期、
  首次出现日期 `first_date`）。
- `facts`：Anthropic IPO 分阶段数字、NVDA 跌幅两种口径、关键日期表。
- `formulas`：页面自述的结算规则（血量封顶、杠杆惩罚公式、
  惩罚作用对象）。检查器读 trace 里的规则，不猜规则。
  规则未声明时，相关检查报“数据不足”，不按猜测通过。
- `legacy_ids`：不得出现的旧标识（MSOFT、XAI、中国队）。
- `rules`：规则版本表。每条规则带版本号与生效日期（含废止日）；
  每轮按该轮日期当时生效的规则版本检查，不拿今天的规则审
  过去的轮次。参数：血量上下限、杠杆惩罚系数、惩罚作用对象、
  禁动作种类、不可用卡、适用玩家（空 = 全局规则）。
  另含“即将到来的规则变化”观察清单（2028 年美国大选、2027 年
  中国二十一大、加州议会 12 月 7 日复会、RASA 参议院审议、
  NDAA 终稿、BIS 规则意见截止 2027 年 1 月 19 日、美中贸易休战
  至 2027 年 1 月）。
- 元游戏层：`meta_players`（规则制定者，第一层角色/第二层角色）、
  `rule_actions`（规则动作：行为者、制定/修订/废止、版本、生效日、
  发布机构、文号、公开宣称目标、触发事件）、`political_record`
  （文号、发布机构、生效日期、标题、来源）、`trigger_links`
  （观察 → 规则 → 反应 → 再观察）、`lobby_actions`（公司游说）、
  `goal_checks`（宣称目标一致性规则）。

## 不变量清单

- C1 计数：31×18=558；每人 31 条；每季轮数与 spec 一致；
  排名 5×18=90 行；总图 18 条线。
- C2 血量账：逐 move 链连续（本轮轮初 = 上轮轮末），
  轮末 = 封顶（轮初 + 变化）；季末 = 封顶（末轮轮末 − 杠杆惩罚）；
  季末血量与排名一致；血量在 0–100。
- C3 金币账：逐 move 链连续；季末金币与排名一致；
  金币不为负（除非标注负债）；杠杆惩罚 = 借入本金 // 2。
- C4 出局：血量归零的玩家，后续赛季无动作。
- C5 时间：任何卡、事件、动作不得早于其真实日期。
- C6 卡池：每费持有总数 ≤ 池总量；关键卡只由一名玩家持有
  （除非标注共享）；合成规则（3 张 1 星 = 1 张 2 星）。
- C7 事实：IPO 分阶段算术（基础 + 私募 = 定价日合计；
  绿鞋后总额 + 私募 = 绿鞋后合计）；NVDA 跌幅算术；
  同一数字全页一个口径。
- C8 名单：18 名玩家每轮、每季、每张图都出现；无旧标识残留。
- C9 渲染与重算一致：排名与总图等于从逐轮增量重算的值。
- C10 规则动作与政治记录对得上：文号、发布机构、生效日期
  三者一致；`rules[]` 有对应条目；宣称目标与发布机构非空。
- C11 触发链：引用实体存在；日期有序（观察 < 规则生效 ≤
  反应 < 再观察）；每条规则动作须有触发标注或触发链引用。
- C12 双层角色：游说 actor 须为第一层公司玩家；规则动作 actor
  须为规则制定者；政府第一层为裁判。宣称目标一致性按 trace
  的 `goal_checks` 执行（restrictive 要求规则有禁动作或不可用卡；
  public 要求有公开文号；param_change 要求相对上一全局版本
  至少改一个参数）。
- D 层（无界）：规则表良构（每版本血量下限 ≤ 上限，版本 id 唯一）；
  每名玩家初始态满足动态不变量；任意长度的合法 run，其终态与
  全部中间态都满足动态不变量（血量在当前规则版本界内；金币 ≥ 0
  除非上一动作为负债；归零当且仅当出局；规则生效日 ≤ 当前日期）。
  覆盖全量，不抽样：C1–C12 与 D 层覆盖全部不变量、全部玩家、
  全部轮次、全部赛季。

## 运行

```sh
# 抽取（agent 经 artifact.inspect 读修复后的 data.json，写出原始数据文件）
python3 extract.py <原始数据.json> --page-version v5
# 一键跑完整管线（默认读 traces/trace-latest.json）
./run.sh
# 指定 trace
./run.sh traces/trace-2026-11-21.json
# 先过 Agent gate（Agent 输出 JSON），再跑全量
./run.sh --claims fixtures/agent-output-ok.json fixtures/trace-fixture-ok.json
# modular 模式：另构建按玩家/赛季拆分的证明模块
./run.sh --modular --claims fixtures/agent-output-ok.json fixtures/trace-fixture-ok.json
# 预测层：历史层通过后跑预测（分布、回测、符号动力、协议检查）
./run.sh --predict --claims fixtures/agent-output-pred-ok.json fixtures/trace-fixture-ok.json
# 抽取 v4：合并事件与 gated claims（claims 只做 R1 校验）
python3 extract.py <原始数据.json> --events daily/events-2026-11-22.json \
    --claims fixtures/agent-output-ok.json
# 每日循环：摄取当日事件 → 追加一轮 → 重算派生值 → 全量重验 →
# 通过才放行 trace 更新，否则分类 + 阻断（不排 cron，不改页面）
./daily_run.sh [--date 2026-11-22] [--events daily/events-2026-11-22.json]
               [--data-json <assets/data.json>] [--predict] [--claims ...]
# 重验任一历史存档版本
./run.sh archive/2026-11-22_<sha12>/trace.json
```

每日循环的触发规则在 `daily/triggers.json`（固定）：新开一轮、
血量跨段位、规则版本变、预测置信变档、验证失败——报警；其余只记
日志。报警只写 `daily/decision-<日期>.json` 与每日日志，不对外推送。
每版 data.json + trace 按哈希加日期存档在 `archive/`（见
`archive/README.md`）；失败时 `daily/release-<日期>.json` 记
released=false，trace-latest.json 不动。
# 集成预测：15 名成员（14 方审计员立场 + baseline 参照）各跑最好回应，报预测分布与分歧度（只写 JSON，不进合并报告）
python3 ensemble.py fixtures/trace-fixture-ok.json --payoff rules/payoff-model.json --out runs/<时间>/ensemble-report.json
# 规则场景预测：每条场景各跑一次最好回应，输出按场景分列（只写 JSON，不进合并报告）
python3 predict.py fixtures/trace-fixture-ok.json --payoff rules/payoff-model.json --scenarios rules/scenarios.json --scenarios-out runs/<时间>/scenarios-report.json --out runs/<时间>/prediction-report.json
```

## 失败分类

验证失败分两类：数据错与机制/设计错。`classify.py` 按失败
模式分类（跨 ≥3 玩家或 ≥2 赛季的系统性模式、规则未声明、
失败在修复后复发——用 `runs/failures-log.jsonl` 追踪复发），
每类机制簇附设计反思问题。机制错要反思设计本身并迭代优化，
不只改数据。分类已接入 `run.sh`：每次检查跑完都跑分类，写
`runs/<id>/classification.json`，并进合并报告的“失败分类”章；
分类是诊断，不改 run.sh 的退出码。

## 复用到以后的页面

抽取器与运行器通用。模型按页面换：`lean/Model.lean` 与
`check.py` 的不变量清单是本页面的规则；新页面换一份
`spec`、`formulas` 与对应的 `Model.lean`，trace schema 不变。
