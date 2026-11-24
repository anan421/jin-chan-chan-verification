# Phase 0 现状审查与架构诊断

- 项目：Jin Chan Chan Verification
- 仓库：https://github.com/anan421/jin-chan-chan-verification
- 本地：~/workspace/verification
- 基准提交：main 8fa382a（2026-11-24 23:10 +0800）
- 审查时间：2026-11-24 23:27–23:40 CST
- 审查方式：六路并行只读核查。读代码，读本地文件，跑检查。每项结论附文件路径、行号或命令输出。
- 本轮只做审查与诊断。本轮不写新功能代码。本轮不改业务规则。发现的修复列入文末清单，等 Phase 1 执行。

## 开工计划

- 问题：任务文档对现状的判断可能滞后或有偏差。先核实真实状态，再谈改进。
- 为什么优先：没有核实的现状就动手修，会修错地方。
- 查什么：git 状态、data.json、trace 与来源记录、检查器、Lean 运行报告、gate.py、预测模块、S6 监控、题集、三个页面、定时任务、运行脚本。
- 如何验证：读代码，跑检查，每项结论附文件路径、行号或命令输出。
- 本轮范围外：不写新功能代码，不改业务规则，不部署页面，不执行 Phase 7。

## 1. 当前系统真实架构

### 1.1 数据层

- 单一事实源是页面数据 `data.json`。仓库 `~/workspace/verification/data.json`、回放页 `assets/data.json`、趋势图 `assets/data.json` 三份文件 md5 相同（52cde40993787bdb29e2cdefd3a601f4，277,618 字节）。
- data.json 含 751 条动作、94 轮、32 名玩家、7 个赛季（S0–S6）。分赛季：S0 55 轮 106 条、S1 4 轮 90 条、S2 8 轮 131 条、S3 7 轮 115 条、S4 8 轮 144 条、S5 11 轮 162 条、S6 1 轮 3 条。
- S5 季末：Anthropic 121 血 / 113 金，OpenAI 79 血 / 58 金，英伟达 36 血 / 54 金。S6 季末：Anthropic 121 / 113，OpenAI 82 / 59，英伟达 37 / 55。独立重算与 meta.accounting 一致。
- meta.accounting 在 data.json 第 4 行。它记录 11 月两轮分立原因、S1 冻结开局、S2–S6 开局承接上季季末、137 条对账记录、证据三级状态、金币为模型内结算单位。
- 棋盘 `~/workspace/jin-chan-chan-3d-board/index.html` 内嵌同一份动作数据。逐轮对比与仓库 data.json 不一致数为 0。8 名 S0 专属玩家（HF、STAB、MJ、AI21、UCB、EU、USGOV、ACM）在棋盘上显示 S0 季末值。仓库 data.json 对这 8 名玩家没有 S1 及以后开局值。
- 转换链：data.json → convert_data_json.py → raw-trace-real.json（schema v3，383,834 字节）→ gen_trace_lean.py → lean/Verification/Trace.lean → lake build → run.sh → runs/&lt;时间戳&gt;/merged-report.md。
- 版本分裂：raw-trace-real.json 是 schema v3，已入库。Lean 实际读取 traces/trace-latest.json 是 schema v4，生成于 2026-11-24 05:51。traces/ 目录被 .gitignore 排除。Lean 的实际输入不在仓库内。
- provenance 文件记录来源链完整。raw trace 的 source_data_json SHA 与当前 data.json 一致。provenance 也记录缺口：连胜结算收入无来源，阵容星级无来源，借入本金无来源，全部动作 borrowed 为 0、penalty 为 0、liability 为 false。规则动作、政治记录、触发链接、游说动作、目标检查全部为空列表。页面规则章是散文，从未结构化抽取。C10–C12 因此检查 0 行。
- provenance 的 season_dates.S6 为 [20261122, 20261101]。结束日期早于开始日期。该字段存疑，需要复核。

### 1.2 验证层

- 快速检查器 check.py（814 行）读取一条规范 trace（schema v3 或 v4），全量检查，不抽样。检查项 C1–C12：计数、血量账本、金币账本、淘汰、时间与合法性、卡池、事实算术、名单、图表、元规则记录、触发链接、双重角色与目标一致性。
- convert_data_json.py（1042 行）是数据生产者，不是检查器。它做自检，失败即退出：动作总数 751，轮次总数 94，玩家 32 人，赛季 7 个，S2–S6 开局等于上一季季末，137 项 reconciliation 与计算值一致。
- gen_trace_lean.py（515 行）生成 Trace.lean。--modular 模式另写 ProofsByPlayer.lean（64 条定理）与 ProofsBySeason.lean（14 条定理）。它每次无条件重写输出文件。它不比较新旧内容是否相同。
- Lean 层：Model.lean（605 行）定义全部检查为可计算布尔函数。Proofs.lean（168 行）用 native_decide 对整条 trace 逐一定理放行。Dynamics.lean（580 行）证明无界定理：六项窄不变量在任意合法轨迹下保持。751 条动作是该定理的一个实例。
- 最新运行 runs/2026-11-24_055133/merged-report.md 总体结论为 pass。快速检查器 pass（通过 3，失败 0，数据不足 0）。Lean 构建退出码 0。Agent gate 为 skipped。预测章为 not_run，属意见，不改变总体结论。计数 751/32/7/139 已核实。0 sorry 已核实（源码中唯一的 sorry 是 Dynamics.lean 第 37 行注释）。
- 报告哈希 13a9b841… 是 meta.trace_sha256。它等于去掉哈希字段后的规范序列化哈希。文件直接哈希是 a412b041…。报告没有注明口径。读者直接对文件验哈希会得到不同值。
- 2026-11-24 05:51 的一次运行（055105）总体为 fail。Lean 构建退出码为 1，但构建日志只有两行 Build completed successfully。28 分钟后同一条 trace 在 lake clean 后重跑通过（055133）。原因是 run.sh 的 mtime 守卫误报。守卫代码自 2026-11-21 引入后未改。风险仍存在。

### 1.3 预测层

- predict.py、backtest.py、fit.py、ensemble.py、rules/payoff-model.json（v2）构成数值预测模块。当前模型是 v2 效用式。全部参数是占位值。c_rule 已在第 6 轮删除。
- data.json 的 forecast 是 2026-11-21 的 fixture 冒烟产物。它引用 fixtures/trace-fixture-ok.json。它用 18 名玩家、v1 效用式、占位参数。它的 calibration_status 是 placeholder_only。它没有反映 S6 1-1 轮的三条新动作。仓库内没有任何代码把 forecast 写回 data.json。
- 2026-11-24 的两次运行目录均无 prediction 报告。当日运行没有执行预测层。
- 真实预测只有 4 条角色扮演 S6 预测。权威记录在 ~/workspace/jin-chan-chan-3d-board/design/roleplay-s6-forecasts.md（2026-11-22）。棋盘 index.html 第 974–980 行 defaultForecasts() 存页面副本。FC-01 已命中（Brier 0.16）。FC-02、FC-03、FC-04 未到期。结算状态只存在两处：棋盘文件默认值与候选池 meta note。棋盘目录不是 git 仓库。结算无版本控制。
- 题集 v7 是 215 道、43 种。文件在 ~/workspace/verification-v1-testset-complete/testset-v7.json。分支 loop/vision-1-testset-complete 已推，未合 main。main 上没有任何 testset 文件。合并存在回归风险：分支的 data.json 是 558 条时代版本。直接合并会冲突，或回退 data.json。
- 第 11 轮打分可以逐字节复现。重跑 score_v11.py 的输出与 runs/round11-vision11-2026-11-22/score-v11.json 逐字节相同。但报告标题增益 +5.33 与脚本输出 3.67 口径不同。脚本只对实验组做泄题排除，对照组用原始均值 94.00。报告用两组审计后均值相减（97.67 − 92.33）。两个数都对，口径不同。结论不受影响：两个数都小于噪声带 11。
- 预测生成不能复现。预测文件只含 batch、round、q_id、kind、reason、facts、confidence。文件内无模型名，无模型版本，无时间戳，无生成命令。predict.py 不调任何 LLM API。预测是人工 agent 劳动，无确定性生成脚本。
- 运行数据不在仓库里。.gitignore 含 runs/ 与 traces/。第 11 轮分支提交 27d24d5 共 15 个文件，无任何 runs/ 文件。预测文件、打分 JSON、审计 JSON 只存在于本地工作区目录。

### 1.4 监控与运行层

- 6 个项目定时任务全部启用，最近运行全部成功。s6-daily-monitor 实际周期为每天 11:35:47。任务书写的约 11:00 口径不符。
- S6 监控脚本 scripts/s6_monitor.py 硬编码 18 名玩家名单。KINDS 注释写 35 种，实际 34 种。TESTSET_PATH 指向 testset-v3.json（88 道旧题集）。汇报阈值（52 道、每周一）不在脚本里，只在 design/s6-daily-monitor.md 里。
- 监控当前已跑崩。`python3 scripts/s6_monitor.py check` 退出码 1，报错 IndexError。trace 于 2026-11-24 05:51 重建为 751 条动作，玩家下标最大 31。下标 ≥18 的动作有 27 条。脚本仍按 18 名玩家取下标，越界。池文件写于 05:33，早于 trace 重建。池 meta 称 11-24 check 通过，该说法与当前 trace 文件不符。
- 候选池现为 candidates 4、missed_s5 6、kind_gap 11、new_player 1、rejected 41。4 道候选全部是 11-23 事件。池 meta 的 note 承认 88→140、35 种、18 名单口径已过期。脚本 new_pool() 仍写 testset_n 88、gap_to_140 52。
- daily_run.sh 依赖 daily/triggers.py、daily/triggers.json、daily/event-map.json。daily/ 目录整体未进仓库。traces/trace-latest.json 是 run.sh 与 daily_run.sh 的默认输入，未进仓库。新克隆仓库无法直接运行 daily_run.sh。
- 运行脚本无网络调用。页面依赖 Tailwind CDN、Three.js CDN、Google Fonts，无本地 fallback。
- runs/ 下共 68 个目录。最近两次运行产物完整。部分旧实验目录只有 1–3 个文件，属历史遗留。

### 1.5 页面层

- 棋盘展示 4 条角色扮演预测，不展示 fixture 预测。棋盘不标注预测方法。页面中「角色扮演」出现 0 次。结算由用户点击决定。旧浏览器 localStorage 会保留 outcome: null。用户必须点击「发生 (1)」才能看到命中。用户也可以改写结果或清空全部结果。新建预测表单提示写 SHA-256，但第 2197 行生成哈希的代码是普通字符串哈希，不是 SHA-256。默认 4 条哈希只有 12 位十六进制字符。
- 回放页展示的预测来自 fixture。data.json 的 forecast.trace 是 fixtures/trace-fixture-ok.json。起点血量是旧 fixture 快照值（NVDA 31 血，实际当前值 37 血；Anthropic 33 血，实际当前值 121 血）。页面有免责声明（第 724 行、第 730–731 行），但表格仍以当前推演形式呈现。
- 两页预测互相矛盾。棋盘展示 NVDA Megaspeed 命题，概率 0.60。回放页展示 NVDA 众数动作为 r1，概率 0.937515。
- 趋势图不展示任何预测。趋势图数据与回放页一致。首屏导语已改为 37 血。
- 回放页审计散文旧数字仍在。第 887 行写 S5 Anthropic 季末 74。第 895 行补注说明它是第 6 轮历史修复日志。当前 data.json reconciliation 中该值是 121。旧数字只存在于历史文本中，不存在于当前计算数据中。

## 2. 当前能力与目标能力的差距

- 愿景要求十项能力：观察现实、判断可信、映射结构化知识、理解战略目标与约束、推演行动、预测未来、验证预测、识别错误原因、更新知识模型、持续提升理解。
- 现状：观察能力有 S6 监控，但监控已跑崩。判断可信有 gate，但 gate 只查格式。映射结构化知识有 trace，但规则章与政治记录是空集。理解战略目标只有角色扮演提示词，没有玩家模型。推演行动有效用函数，但参数全是占位值。预测未来只有 4 条真实预测，且结算无版本控制。验证预测有题集打分，但生成不可复现。识别错误原因有审计报告，但方法文件泄题出现三次。更新知识模型有实验棘轮，但采用门槛下的两个方法仍标暂定。持续提升有版本记录，但 README 与 STATUS 停在 11-21。
- 最大差距在三处。第一，预测链断裂：页面展示的预测是过期 fixture，真实预测没有账本。第二，词汇无统一来源：玩家名单、动作种类、题集路径散落在各文件，监控因此跑崩。第三，验证通过不等于系统可信：检查器与 Lean 证明内部自洽，不证明排名顺序、事实正确、增量合理。
- 能力地图见附录 A。

## 3. 已核实的问题及证据

### 3.1 P0 预测数据版本漂移：证实

- data.json 的 forecast 仍引用 fixtures/trace-fixture-ok.json。证据：data.json 第 10717 行与第 11391 行。
- fixture 是合成数据。fixtures/trace-fixture-ok.json 的 meta.source 写 fixture（synthetic, consistent by construction）。它的 spec 写 18 名玩家、31 轮、5 个赛季、558 条动作。
- forecast 的 players 数组长 18 名。18 名玩家的血量与金币与 fixture 的 S5 季末 season_state 全部精确匹配。例如 NVDA 31 血 / 448 金，OAI 31 血 / 201 金，ANTH 33 血 / 185 金。匹配率 18/18。
- forecast 与当前真实数据严重脱节。当前 S6 季末 NVDA 是 37 血 / 55 金，OAI 是 82 血 / 59 金，ANTH 是 121 血 / 113 金。金币 448 与 201 在当前 751 条数据中不存在对应值。
- forecast 用旧版效用函数。forecast 的 payoff_model 是版本 1，含 c_rule 项。当前 rules/payoff-model.json 是版本 2，无 c_rule 项。forecast 缺 A8（discount）与 A9（hp_exponent）。c_rule 在第 6 轮已被删除，forecast 仍含 c_rule。
- forecast 的规则编号不存在于真实 trace。forecast 记 current_rule 为 RV-2026-11。该编号只存在于 fixture 的规则表。真实 trace 的规则编号是 RV-2018.1 至 RV-2026.2，共 14 条。
- forecast 的分布键只有 16 种旧动作种类。它不含 megaspeed、energy、financing、capex、open_source 等新种类。
- forecast 的 ensemble 时间戳停在 11-21。来源是 verification/runs/2026-11-21_115508/ensemble-report.json。成员数 15 名。回测 n 为 234，拟合窗口 S1–S3，测试窗口 S4–S5。M1 为 0.0556，低于随机基线 0.0863。结论为 below_threshold。
- data.json 全文含 S6-FC-01 0 次。S6-FC-01 的命中没有进入 forecast。
- 页面展示的预测分三处，结论不同。回放页展示的预测来自 fixture。棋盘展示的预测是 4 条角色扮演预测，不来自 fixture。趋势图不展示预测。
- 最新真实预测存放在两处。权威记录是 ~/workspace/jin-chan-chan-3d-board/design/roleplay-s6-forecasts.md。页面副本是棋盘 index.html 第 974–980 行 defaultForecasts()。仓库 data.json、回放页 data.json、趋势图 data.json 均不存放这 4 条预测。
- 预测与 Trace、规则版本、模型版本不对应。forecast 的 trace 是 fixture，规则是 fixture 规则，模型是 v1。当前真实 trace 是 751 条 v4，规则是 RV-2018.1–RV-2026.2，模型是 v2。2026-11-24 的运行没有执行预测层。当前不存在任何一条基于真实 trace 的预测输出。

### 3.2 P0 参与者与动作词汇漂移：证实

- S6 Monitor 硬编码 18 名玩家。证据：scripts/s6_monitor.py 的 PLAYERS 列表。导入验证输出 PLAYERS = 18。
- 监控不区分历史玩家与活跃玩家。PLAYERS 是单一静态名单。脚本内无赛季活跃概念，无按赛季过滤。32 名历史玩家来自 data.json 的 players。当前赛季活跃玩家只有 2 名：raw-trace-real.json 的 S6 动作共 3 条，玩家下标 0（NVDA）占 2 条，下标 1（OAI）占 1 条。
- 18 名单漏掉后加的 14 名玩家：KIMI、MANUS、ZHIPU、MINIMAX、OPENCLAW、PANW、HF、STAB、MJ、AI21、UCB、EU、USGOV、ACM。
- 种类数不是 35 个。KINDS 定义上方注释写 35 kinds。导入验证输出 KINDS = 34。classify() 的报错文案仍写 35 个种类。
- 题集路径已过期。TESTSET_PATH 指向 /home/hatch/workspace/verification-v1-walkforward/testset-v3.json，即 88 道旧题集。脚本没有引用题集 v7。
- 赛季起始日期有两个写法。S6_START = 20261121。池文件 meta.s6_start_date 写 20261122。两者含义一致，写法不同。
- 监控当前已跑崩。`python3 scripts/s6_monitor.py check` 退出码 1，报错 IndexError: list index out of range。调用链：check（第 247 行）→ is_duplicate（第 110 行）→ player_of_trace_move（第 92 行）→ PLAYERS[p] 越界。直接复现：player_of_trace_move({'player': 18}) 同样抛 IndexError。
- 根因：traces/trace-latest.json 于 2026-11-24 05:51 UTC 被重建为 751 条动作，玩家下标最大 31。下标 ≥18 的动作有 27 条。首个下标 ≥18 的动作位于第 9 条（2018-12 欧盟动作，玩家 29）。脚本文件注释仍写 558 条。
- 参与者、动作种类、规则没有权威统一来源。定义散落在五处：data.json 的 players、fixture 的 16 种词汇、s6_monitor.py 的 PLAYERS 与 KINDS、convert_data_json.py 的语义种类词汇、rules/ 下的规则文件。没有一个模块读取统一定义。
- 补充：题集玩家与棋盘玩家不完全一致。题集含 31 名玩家。题集特有玩家包括 AMD、CALIF、CRWV、CURSOR、KARPATHY、MICRON、SAMSUNG。题集用 ZHIPU，池用 Z.ai，写法不统一。

### 3.3 P0 证据检查深度不足：证实

- evidence_resolves() 只查格式。证据：gate.py:205-215。url 分支只检查正则匹配。edgar 分支只检查 10 位数字-2 位数字-6 位数字的编号格式。doc_number 分支只检查编号是否在 trace 内存在。trace 分支只检查位置是否存在。
- gate.py 全文无网络请求。导入块只含 argparse、json、re、sys、pathlib。无法访问的 URL 只要格式正确就通过。内容错误、内容过期、内容与主张矛盾的 URL 也通过。
- schema 文件自述同一结论。rules/agent-claim-schema.json 中 url 种类的说明写明 ref is a well-formed https URL (format only; the gate does not fetch)。
- 谓词真值只对两类主张求值。gate.py:372-373：只有 fact_correction 与 refutation 两类主张求真值。propose_action 与 evidence_downgrade 两类主张不求真值，只检查可判定性与证据解析。
- 矛盾处理只覆盖同一主体的部分算子。R4（gate.py:395-450）只检查 eq 取值不同、in_range 区间不交、eq 与 ne 取值重叠三种情形。lt、gt、lte、gte、contains、exists 之间永不判冲突。两个不同证据指针各自支持相反主张时，gate 不比较证据内容，不判冲突。两个主张指向不同主体时，即使内容矛盾，gate 也不判冲突。
- move 对象只做类型检查。validate_move（gate.py:82）只检查 8 个子字段存在与类型。它不检查 actionKind 是否属于 trace 的种类集合。它不检查 rulesVersion 是否为真实规则。它不检查日期是否合法。它不检查动作是否合法。动作合法性由 predict.py:510 的 apply_move 在应用时另行检查。
- AgentClaim 只存证据指针。rules/agent-claim-schema.json：evidence 只有 kind 与 ref 两个子字段。主张不存内容摘录，不存内容哈希，不存核验结果。核验结果只存在于 gate 的报告中，不存在于主张本身。note 字段明确写明永不作为证据，永不计为已验证。
- agent_claims.py 的四项协议检查复用 Gate.evidence_resolves 与 Gate.predicate_decidable。它继承 gate 的格式级证据检查，不补内容核验。

### 3.4 P1 实验产物与可复现性：部分证实

- 题集实际规模属实。testset-v7.json 的 meta.n 为 215。种类集合 43 个。分集 A 108、B 107。q_id 为 0–215 缺 79（q79 已删）。全部真实日期不晚于 2026-11-21，无 S6 事件。
- 题集不在 main 里。main 上 git ls-files | grep -i testset 返回空。main 共 84 个跟踪文件。testset-v7.json 与 design/testset-v7-report.md 只在分支 loop/vision-1-testset-complete 上跟踪（该分支 98 个文件）。
- 分支已推，未合 main。本地与远端同为 34881fa（2026-11-22 14:55:56 UTC）。合并基点为 fa6b6b1。分支比基点多 1 个提交。main 比基点多 1 个提交（8fa382a）。分支的 data.json 是 558 条时代版本。直接合并会冲突，或回退 data.json。合并前须先变基并解决 data.json 冲突。
- testset-v7 的 meta.note 写 Trace 保持 558 条。该表述已过时。当前 trace 为 751 条。
- 打分可以复现，而且逐字节相同。重跑 score_v11.py 的输出与 runs/round11-vision11-2026-11-22/score-v11.json 逐字节相同。两道复现门均 PASS。
- 报告标题增益与脚本输出口径不同。脚本输出 G_audited = 3.67。报告标题写 G = +5.33。脚本只对实验组做泄题排除，对照组用原始均值 94.00。报告用两组审计后均值相减（97.67 − 92.33）。两个数都对，口径不同。脚本本身复现不出报告标题数。结论不受影响：3.67 与 5.33 都小于噪声带 11。
- 预测生成不能复现。预测文件只含 batch、round、q_id、kind、reason、facts、confidence。文件内无模型名，无模型版本，无时间戳，无生成命令。预测员计划要求人工按方法文件逐轮做题。predict.py 不调任何 LLM API。预测是人工 agent 劳动，无确定性生成脚本。
- 运行数据不在仓库里。.gitignore 含 runs/ 与 traces/。分支提交 27d24d5 共 15 个文件，无任何 runs/ 文件。只凭 git 仓库内容无法重跑打分。必须连同本地工作区目录一起取。
- 重建脚本不能复现当前数据。rebuild_monthly.py 第 890 行断言 report['moves_total'] == 749。第 784 行内嵌核算文本写动作总数 749。第 4 行文档写输入为 643 条。第 12 行写 S6 1-1 轮为 1 条。当前数据是 751 条，S6 是 3 条。重跑该脚本会触发断言失败。
- 第 11 轮分支未推。loop/vision-1-round11-baseline（27d24d5，2026-11-22 15:54:59 UTC）是唯一本地独有分支。ls-remote 确认远端无此 ref。
- 报告自述两处系统性问题。方法文件例题泄题是第三次：q30–q32 例题逐字就是题本身。日期违规共 123 条：生成器把历史汇总事实盖轮次日期戳。

### 3.5 P1 运行环境与依赖：大体证实，一项证伪

- 绝对路径依赖属实。scripts/s6_monitor.py 第 28–30 行硬编码 TRACE_PATH 与 TESTSET_PATH。gen_board_data.py 第 5–6 行硬编码页面数据路径与棋盘路径。rebuild_monthly.py 第 19 行设定 WS = '/home/hatch/workspace/'。runs/agent-prototype-2026-11-21/make_contexts.py 第 13 行硬编码页面数据路径。run.sh 与 daily_run.sh 本身使用相对路径，未发现绝对路径。
- gitignore 排除但运行时必需的文件属实。.gitignore 第 2 行 .lake/，第 7 行 runs/，第 8 行 archive/，第 9 行 daily/，第 10 行 traces/。git check-ignore -v 证实 traces/trace-latest.json、runs/2026-11-24_055133/merged-report.md、lean/.lake/build/lib/lean/Verification/Proofs.olean、daily/decision-2026-11-24.json、archive/manifest.jsonl 均被排除。daily/ 目录整体未进仓库最严重。git ls-files daily/ 返回 0 行。
- 临时目录不清理属实。run.sh 与 daily_run.sh 全文无 mktemp、rm -rf /tmp、TMPDIR。predict.py 第 676 行调用 tempfile.mkdtemp(prefix="predict-lean-")。全文件无 rmtree 调用。历史后果已有记录：design/batch-2-report.md 第 25 行记录 /tmp（512M tmpfs）曾被 44 个陈旧的 predict-lean-* 临时目录占满，导致一次场景运行写盘失败（0 字节输出）。同一文件第 50 行与 design/improvement-loop.md 第 54 行均标注该隐患未修复。当前 /tmp 有 0 个 predict-lean-* 目录，tmpfs 使用率 1%。目录已被人工清理，代码缺陷仍在。
- 运行 ID 冲突机制属实，实际冲突未观测到。run.sh 第 43 行：RUN_ID="$(date +%Y-%m-%d_%H%M%S)"。ID 精确到秒，无随机后缀。同一秒内两次运行共享同一目录。mkdir -p 不报错。第二次运行覆盖 trace.json，截断 lean-build.log，覆盖合并报告。daily_run.sh 第 58 行工作目录只按日期区分。同一天两次运行共享 candidate-trace.json 与 recomputed-trace.json。两个脚本均无锁。全文搜索 flock、lockfile、.lock 无命中。gen_trace_lean.py 每次运行都重写同一批 lean/Verification/*.lean 文件。两次并行 lake build 共享同一 .lake 目录。实际观测：runs/ 下 68 个目录无重名。冲突机制证实存在，实际冲突尚未观测到。
- Lean mtime 守卫假失败风险属实，代码未修复。run.sh 第 117–137 行 check_olean 用 [ "$olean" -ot "$src" ] 判断。gen_trace_lean.py 每次无条件重写生成文件，时间戳更新，内容不变。Lake 按内容哈希决定是否重建。内容不变时它不重写 .olean。两者判断标准不一致。触发条件：在 --modular 模式下，用同一条未变的 trace 连续跑两次。证据：055105 运行构建成功而总体失败，同一 trace 在 lake clean 后重跑通过。git log 显示守卫只在 2026-11-21 的基线提交 98be845 引入，之后没有修改。守卫报错只写到标准错误，没有存入运行目录。这是记录缺口。
- 旧 .olean 导致静默通过的风险未证实。Lake 按内容哈希决策。内容不变时，旧 .olean 与当前源文件语义一致。守卫的误判方向是假失败，不是假通过。两处残留风险仍存疑：守卫不检查 Trace.olean；非模块化模式删除模块化源文件（run.sh 第 95–96 行），但不删除旧模块化 .olean。
- 失败后误发布在脚本层面证伪。run.sh 第 246–250 行汇总退出码。GATE_RC、CHECK_RC、GEN_RC、LEAN_RC、MERGE_RC 全部为 0，否则退出码为 1。daily_run.sh 第 189–190 行只在 RUN_RC 等于 0 时复制 trace-$DATE.json 与 trace-latest.json。第 215–218 行在失败时写 released: False，记录 trace-latest.json untouched，退出 1。daily_run.sh 头部注释注明脚本不碰页面 artifact，不调度 cron。发布动作在脚本之外，由人工或上层 agent 执行。脚本本身不能把失败输出当作成功部署。
- 退出码处理有三处注意点。第一，classify.py 的退出码被忽略。run.sh 只回显 run: classify exit=$?，不改变任何返回码。注释注明分类只是诊断，不改变退出码。设计如此。第二，预测层失败不改变退出码。run.sh 头部注释注明预测失败不改变退出码，退出码只反映历史层。合并报告把预测章标为 opinion。设计如此。第三，daily_run.sh 的运行目录归属用推断方式确定。第 156 行创建 before-run 标记文件。第 160 行用 find runs -newer before-run 取时间戳最新的运行目录。并行运行或人工运行可能使该推断认错目录。失败归档可能关联错误的运行目录。该路径存疑，未观测到实例。
- 外部依赖属实。运行脚本无网络调用。页面依赖 Tailwind CDN、Three.js CDN、Google Fonts，无本地 fallback。CDN 不可用时页面样式与 3D 渲染失效。本地依赖：Python 3 标准库，无第三方 pip 包导入。Elan 工具链（~/.elan/bin/lake，Lean 4.36.0）。lake-manifest.json 依赖包为空。lake 不在默认 PATH 中。两个脚本均在开头执行 export PATH="$HOME/.elan/bin:$PATH。

### 3.6 P1 模型语义不一致：证实，共十处

- 动作种类不一致。ensemble.py:193 用 action_kind 构造候选动作。predict.py:172、backtest.py:114、fit.py:312 用 semantic_kind。check.py:378 用 action_kind 作最早日期与禁令的键。真实 trace 的 action_kind 只有 8 个回合类型代码：event 262 条、battle 204 条、wild 57 条、economy 57 条、draft 54 条、final 40 条、streak 36 条、civil_war 19 条。semantic_kind 是实质动作线索，其中 472 条为 unknown。ensemble.py 在真实 trace 上预测回合类型，不是预测实质动作。
- 期望表键错位。ensemble.py:203 调用 predict.make_expectation(per_mean, glob_mean) 时未传 global_mean。predict.expected_deltas 的表以语义种类为键。候选动作是回合类型代码时，期望查找全部落空，回落为 (0.0, 0.0)。该结论由代码直接推出，未在真实 trace 上运行验证。fixture 上无此问题，因为 fixture 的 action_kind 本身就是语义种类（chatgpt、r1 等 16 种），且无 semantic_kind 字段。
- 玩家状态不一致。predict.py:543 取最新 season_state 的 hp_end、gold_end。backtest.py:86 的 chain_state 从最早 season_state 的 hp_start、gold_start 起算，串联全部前置动作。check.py 按季内串联。真实 trace 中 S0 季末与 S1 季初不同，7 名玩家存在差异。例如 NVDA 为 S0 季末 112 血 / 5 金，S1 季初 76 血 / 20 金。data.json 的 meta.accounting 自述 S1 为冻结开局，不承接 S0 季末。chain_state 从 S0 季初起算并跨季串联，因此它在 S1 及之后赛季的状态与 season_state 的记载值不一致。check.py 只做季内串联，从不比较 hp_start 与上一季 hp_end 是否连续，因此该断裂不被 check 捕获。
- 杠杆惩罚出现三次不同处理。check 在季末扣一次。build_fork 在分叉季扣一次。forecast_rounds 与 chain_state 完全不扣。apply_move（predict.py:510）也不扣惩罚，只做血量钳制与金币非负检查。
- 动作合法性不一致。check C5 检查动作最早日期与回合跨度例外。apply_move 不检查这两项。apply_move 按语义种类查禁令。check 按 action_kind 查禁令。真实 trace 上两者键集合不同。gate 只做类型检查。
- 规则版本不一致。predict 主流程取最大日期的基础规则。backtest 与 fit 取逐动作日期的规则。data.json forecast 的 RV-2026-11 不存在于真实 trace。真实 trace 的规则编号为 RV-2018.1 至 RV-2026.2 等 14 条，血量上下界为 0–140。fixture 的规则编号为 RV-2022-10 等，血量上下界为 0–100。
- 时间范围不一致。backtest 拟合窗口取赛季列表前 3 个，测试赛季取其余全部（backtest.py:446-447）。fixture 上为 S1–S3 拟合、S4–S5 测试。真实 trace（S0–S6）上为 S0–S2 拟合、S3–S6 测试。fit 默认 --fit-seasons 1,2,3（fit.py:762）。真实 trace 上为 S1–S3，与 backtest 的 S0–S2 不同。rules/calibration.json 记拟合窗口为 S1–S3，与 fit 的默认值一致，与 backtest 在真实 trace 上的动态窗口不一致。predict 默认 horizon 为 1 轮。上限为单赛季最大轮数（predict.py:1143）。fixture 上上限为 7。真实 trace 上 S0 有 55 轮，上限为 55。predict.py 文档称上限为 1 个赛季，但 1 个赛季在真实 trace 上等于 55 轮。
- 赛季边界不一致。check 不验证跨季连续性。predict 的 current_states 只取最新季的季末值。build_fork 创建 max(season)+1 季、1 轮的分叉。backtest 与 fit 的 chain_state 无视全部赛季边界与季初重置。gate 的未来主体定义为 max_season + 1 季、已存在玩家、已知字段，与 predict 的分叉季定义一致。这是少数一致处。
- 排名口径不一致。check C9 只验证 rankings 的 hp_end、gold_end 与 season_state 一致，及 hp_series 对应点一致。check 从不验证 rank 字段本身的排序是否正确（check.py:541-553）。我在 check.py、Model.lean、Dynamics.lean、Proofs.lean 中搜索 rank 字段引用，结果为零。predict 按血量降序、金币降序、玩家编号升序重排。data.json 的 meta.accounting 称并列按 meta 既定顺序处理。三处口径不同。
- 效用函数不一致。当前 rules/payoff-model.json 是版本 2。效用式为 u = w_hp * [(hp_after)^alpha - (hp_before)^alpha] + w_gold * dgold - c_lever * leverage_penalty + w_pos * position_term。参数全部是占位值。c_rule 已在第 6 轮删除，文件 A4 条自述其不可识别。predict.py:339 的 utility 实现 v2 效用式。discount 只读取，不用于折现未来收益。compliance 参数保留但忽略。fit.py 拟合 v2 权重与 v1 投影两套结果，并声明 v2 权重不可直接代入 v1 线性式。ensemble.py 的 15 名成员权重全部使用 v1 占位值（含 c_rule 10.0 或 20.0），且不含 hp_exponent 与 discount。predict.utility 忽略 c_rule，因此只在 c_rule 上不同的成员预测结果完全相同。ensemble.py:19-24 的 limits 自述该结论。CNTEAM 成员只在 c_rule 与 tau 上不同于基线成员，因此其模态动作与基线完全相同。data.json 的 forecast 使用 v1 效用式，含 - c_rule * compliance_cost 项，与当前 payoff-model.json v2 不一致。
- 补充：ensemble.py 的语义种类对齐缺失是静默的。代码中无 TODO、无 FIXME、无占位对齐逻辑。全仓库检索 TODO 与 FIXME 返回零命中。ensemble.py 全文零次出现 semantic。它从不读取 semantic_kind。它不调用 predict.kind_of。它不在生产管道中运行。run.sh 不调用它。data.json 的 forecast 内嵌的 ensemble 结果来自 2026-11-21 的 fixture 运行。
- 补充：run.sh:163-180 只在传入 --claims 时才把 --gate-report 传给 predict。未传 --gate-report 时 predict 记录 gate_note，称主张未经 gate 直接应用，仅为冒烟测试路径。

### 3.7 其他已核实的问题

- README 与 STATUS 已过时。README.md 共 242 行。STATUS.md 共 540 行。STATUS.md 第 1 行标题为「管线状态（2026-11-21 晚）」。两文件均未更新到 2026-11-24。「558」在 README 出现 4 次，在 STATUS 出现 8 次。「751」在两文件出现 0 次。两文件均未提及 2026-11-24 三项决定、S6-FC-01、月度重组、751 条。STATUS 第 20 行写真实 trace 尚未抽取，traces/ 为空。该表述为假。traces/ 现有 6 个文件。STATUS 第 22 行写页面现为 v6。raw-trace-real.provenance.json 记录页面版本为 v13。README 第 29 行写 558 条是全称定理的一个实例。第 158 行写 C1 计数为 31×18=558，每人 31 条。当前结构为 751 条、32 名玩家、94 轮。计数公式已失效。
- 未进仓库的关键文件共 13 个。rebuild_monthly.py、gen_board_data.py、check_consistency.py、4 个 gpt1 事件文件、design/testset-coverage-plan.md 重要且应该进仓库。ProofsByPlayer.lean 与 ProofsBySeason.lean 是生成物，是否入库存疑。rebuild_monthly_report.json 已过时。两份 .bak 文件不应进仓库。.gitignore 没有忽略 *.bak。
- 棋盘新建预测表单的哈希说明与代码不符。表单提示写 SHA-256。第 2197 行生成哈希的代码是普通字符串哈希。默认 4 条哈希只有 12 位十六进制字符。
- s6-daily-monitor 的实际周期与任务书不符。任务书写每天约 11:00。实际周期为每天 11:35:47。
- 池文件 meta 与脚本默认值不一致。池 meta 写 testset_n 215、gap_to_140 -75。脚本 new_pool() 仍写 testset_n 88、gap_to_140 52（第 52–53 行）。
- testset-v7 的 meta.note 写 Trace 保持 558 条。该表述已过时。当前 trace 为 751 条。
- design/testset-coverage-plan.md 已过时。它写现状为 testset-v6 共 98 道，目标 140 道，缺口 42 道。testset-v7 已达 215 道。该计划的框架已过时。它仍是 v7 的设计依据。应该作为历史设计记录入库。
- 审计散文旧数字仍在回放页。第 887 行写 S5 Anthropic 季末 74。第 876 行保留 558 时代的表述。第 895 行补注说明它是第 6 轮历史修复日志。当前 data.json reconciliation 中该值是 121。旧数字只存在于历史文本中，不存在于当前计算数据中。

## 4. 对本方案的审查与修正

### 4.1 已经实现的部分

- Python + Lean 双层验证架构已实现。快速检查器全量检查 751 条动作。Lean 证明有限历史不变量与无界 Dynamics 不变量。最新运行 overall=pass，0 sorry。
- 实验纪律已实现。噪声带、并行对照、配对比较、预先写假设与证伪条件、审计、暂定进基线，全部在第 7–11 轮执行过。采用门槛明确。第 9 轮界限规则与第 11 轮角色扮演未过门槛，标暂定，没有强行采用。
- S6 监控已实现概念，但已跑崩（见 3.2）。候选池、每周汇总、52 道阈值的机制存在。池 meta 的 note 已承认口径过期。
- 题集 v7 已建成。215 道、43 种。打分可逐字节复现。
- 角色扮演试点已实现。试点对直接问 +3.0。4 条 S6 预测已登记。首条已命中。
- 预测实验室的报告与审计流程已实现。第 11 轮报告、基线重测、审计 JSON 全部存在。

### 4.2 有价值且尚未实现的部分

- 现实、认知、模拟三层逻辑分离有价值。现状是三层混在 data.json 里。血量金币增量与现实事件并列存放，没有分层标记。没有分层，事实与推断的边界无法检查。
- 证据生命周期有价值。现状是主张只存指针，gate 只查格式。内容获取、内容支持判断、冲突记录、修正记录全部缺失。
- 真实预测账本有价值。现状是页面展示过期 fixture 预测，真实预测只存在棋盘默认值与本地存储。追加式账本、信息截止时间、独立结算、版本保留，全部缺失。这是近期最值得优先建设的能力。
- 玩家模型有价值。现状是角色扮演提示词。没有持续更新的玩家认知状态。没有事实与推断的区分。
- 预测任务拆分有价值。现状是一个效用模型同时承担主动行为、外部事件、反应、影响、状态五类问题。第 7 轮实验数字（效用模型 1/83，全局频率 6/83，按玩家历史 23/83）提示复杂模型丢失了简单模型的信号。根因没有验证。
- 因果模型有价值。现状是时间先后与统计相关混用。没有可修订的因果假设记录。
- 错误归因与经验记录有价值。现状是审计报告写文字复盘。没有结构化归因类型。没有经验状态机（候选、已验证、有条件成立、存在争议、已被反驳、已废弃）。复盘文字不会自动进入长期知识。
- 实验棘轮与回滚有价值。现状是采用后没有回滚记录。方法一旦暂定进基线，没有规定后续真实预测恶化时如何回滚。

### 4.3 不适用或需要修正的部分

- 任务文档的 P0 表述需要分拆。文档问页面展示的预测是否来自 fixture。核实结果是分拆的：回放页是，棋盘不是，趋势图不展示预测。文档的笼统问法需要修正为按页面分拆。
- 任务文档没有写 S6 监控已跑崩。文档假设监控在运行，只是词汇过时。核实结果是监控的 check 命令已退出码 1 失败。Phase 1 必须先恢复监控运行，再谈词汇统一。
- 任务文档的 P1 表述「运行失败后是否可能错误发布结果」已证伪。脚本层面没有误发布路径。daily_run.sh 的发布门控只在通过时复制，失败时明确阻断。该怀疑可以关闭。残留的存疑点是运行目录推断方式（find -newer），不是误发布。
- 80% 目标需要重新审视。愿景目标是题集 140 道以上、总分猜中 80% 以上、最弱一项不低于 50%、分数在没用来选方法的题集上量。现状是基线在 v7 上 45.4%。v7 的 215 道已用于方法选择（第 7–11 轮）。用同一套题宣称真实预测准确率违反方法选择与能力评估分离。80% 可以作为某类任务的研究目标，不应成为全部任务的强制指标。S6 池只有 4 道候选。独立评估题集尚未建成。
- 140 道目标已过期。题集 v7 已达 215 道。池 meta 的 gap_to_140 为 -75。140 这个数字来自 v6 时代的补缺计划。目标需要 Gu 重新定范围。不要擅自改目标。
- 任务文档的 Phase 顺序基本合理，但有一处调整。Phase 1 消除漂移之前，必须先恢复观察能力。S6 监控已跑崩。观察是愿景十项能力的第一项。Phase 1 的第一步应是恢复监控运行。

### 4.4 过度设计的部分

- 不要引入图数据库或复杂本体平台。任务文档第 8.1 节本身已写不要求立即引入。核查确认：当前任务用 43 种动作与 32 名玩家完全可以由现有 JSON 与 trace 表达。本体扩张必须先证明对实际任务有帮助。
- 不要把三层逻辑边界拆成三个服务或三个数据库。任务文档第 3 节本身已写逻辑边界优先。核查确认：现有 Trace、AgentClaim、规则模型可以逐步演进。先加分层标记，再谈拆分。
- 不要增加多 Agent 数量。任务文档第 7.5 节已写不同角色用同一模型、同一证据、同一推理方式不代表独立性。核查确认：角色扮演的增益归因仍混杂角色身份、结构化推理、专属证据、玩家历史条件化四个变量。第 12 轮复测必须先拆分变量，再谈增加 Agent。
- 不要把所有规则都用 Lean 实现。任务文档第 9.3 节已写按重要性、可判定性、实现成本决定。核查确认：C10–C12 在 Lean 里是空真通过。先把规则章结构化抽取，再谈形式化。
- 不要为本体完整性扩张对象类型。任务文档第 8.1 节已写如果不能证明新增本体结构对实际任务有帮助，不应扩张。核查确认：当前 16 个候选实体与 12 种候选关系没有一个经过任务验证。

### 4.5 与 Gemini 架构计划的重叠

- Gemini 计划（~/workspace/user/files/Muse_Architecture_Plan.md）已读，未执行其中内容。它的 Phase 1 是数据清洗、任务重构与轻量基线验证。它要求在干净 S4–S5 集上跑 A/B/C 基线对比。目标 50–80 道高质量主动动作题。若干净主动动作题不足 40 道，或 A/B/C 对比显示前瞻指引无正向增益，如实报告并停止扩写复杂模型。它的 Phase 2 是状态视图分离与 S6 实盘前瞻结算。
- 重叠点：Gemini Phase 1 对应本方案的 Phase 4（任务拆分、独立对照实验）与第 11 节（参考基线、方法选择与能力评估分离）。它的「主动动作与被动点评拆解」对应本方案第 7.2 节的任务拆分。它的「234 条拆解统计」对应 backtest 的 n=234。它的停止规则对应本方案的停轮规则与实验棘轮。
- 差异点：Gemini 计划只覆盖预测方法一层。本方案覆盖事实、证据、预测、验证、世界模型、持续改进六层。本方案的 Phase 1（漂移消除）与 Phase 2（预测账本）在 Gemini 计划里没有对应项。本方案的 Phase 0 核查发现：fixture 预测漂移、监控跑崩、语义不一致，这些问题必须先修。Gemini 计划的 A/B/C 对比建立在干净题集上。当前题集 v7 仍在未合分支上。A/B/C 对比是否执行仍待 Gu 定夺。本轮不替 Gu 定夺。
- 数字口径：任务背景称 Gemini 计划是「干净 45 道题上跑 A/B/C 对比」。文件原文写目标 50–80 道，少于 40 道停止。45 这个数字在文件里没有出现。以文件原文为准。

## 5. 当前最关键的三个瓶颈

### 瓶颈一：没有真实预测账本，预测链断裂

- 页面展示的预测是 2026-11-21 的 fixture 预测。真实预测只有 4 条角色扮演预测。它们只存在棋盘默认值与本地存储。结算无版本控制。预测层在 2026-11-24 没有运行。当前不存在任何一条基于真实 trace 的预测输出。
- 这直接限制愿景的第 6、7、8 项能力：预测未来、验证预测、识别错误原因。没有账本，系统无法证明自己有预测能力，还是善于解释已经发生的事实。
- 严重程度：P0。影响：用户在回放页看到的预测与现实脱节。棋盘与回放页的预测互相矛盾。

### 瓶颈二：参与者与动作词汇没有统一来源，监控已跑崩

- 玩家名单、动作种类、题集路径散落在五处。没有一个模块读取统一定义。S6 监控因此跑崩。check 命令退出码 1。每日观察已停止。
- 32 名历史玩家与当季活跃玩家没有区分。新玩家加入要改多处。题集玩家与棋盘玩家写法不统一（ZHIPU 与 Z.ai）。
- 这直接限制愿景的第一项能力：观察现实世界。观察停了，后续预测、验证、改进全部失去输入。
- 严重程度：P0。影响：S6 每日监控自 2026-11-24 05:51 起失效。

### 瓶颈三：验证通过不等于系统可信，检查存在结构性盲区

- Lean 与检查器证明给定输入的内部自洽。它们不证明排名顺序、事实正确、增量合理。rank 字段在任何检查中都不出现。C10–C12 检查空集。赛季动作总数是自引用。杠杆罚金机制只在借入为 0 的平凡实例下通过。
- 运行层有三处同类风险：mtime 守卫仍可误报，/tmp 临时目录永不清理且已有一次写盘失败，运行 ID 精确到秒且无锁。
- 文档与实际状态脱节。README 与 STATUS 停在 11-21。13 个关键文件未进仓库。重建脚本不能复现当前数据。
- 这直接限制愿景的第 2、9、10 项能力：判断可信、更新知识模型、持续提升理解。验证通过的信号会误导人以为系统可信。
- 严重程度：P1。影响：一次假失败已经发生过。一次 /tmp 写盘失败已经发生过。

## 6. 下一轮最值得开展的最小改进或实验

- 最小改进是 Phase 1：消除版本与语义漂移。分四步，按顺序做。
- 第一步：恢复 S6 监控运行。修 player_of_trace_move 的越界错误。玩家名单与动作种类改读 data.json 与 testset-v7，不再硬编码。TESTSET_PATH 指到 testset-v7。new_pool() 的默认值改到 215 道。验证：check 命令退出码 0，status 命令正常，池文件正常更新。
- 第二步：处理 data.json 的 fixture 预测。两个选项，二选一。选项 A：用 predict.py 在真实 trace 上重新生成预测，版本号升到 v2，移除 c_rule，标注未校准与生成时间。选项 B：删掉 forecast 块，改为明确标注当前无预测。选择标准是 predict.py 在真实 trace 上的输出是否可信。predict.py 在真实 trace 上有 horizon 上限 55 轮与跨季串联两处已知问题。先跑一次看输出，再定选项。无论选哪项，回放页不得再以当前推演形式展示 fixture 预测。
- 第三步：修运行层三处缺陷。run.sh 的 mtime 守卫改按内容哈希判断，不再按时间戳比较。predict.py 的临时目录在使用后删除。运行 ID 加随机后缀。验证：同一条未变的 trace 连续跑两次 --modular，两次都通过。跑一次 predict，/tmp 无残留目录。
- 第四步：修仓库卫生。rebuild_monthly.py 改到 751 条，验证它能复现当前 data.json。gen_board_data.py、check_consistency.py、4 个 gpt1 文件、design/testset-coverage-plan.md 入库。*.bak 加进 .gitignore，两份 .bak 移出工作区。ProofsByPlayer.lean 与 ProofsBySeason.lean 定夺归属：入库或加入 .gitignore。README 与 STATUS 更新到 751 条、32 名玩家、94 轮、页面 v13、2026-11-24 三项决定。
- 不在本轮做：ensemble.py 的语义对齐改动、三层逻辑模型、预测账本、玩家模型、因果模型。这些属于 Phase 2–5。先让 Phase 1 的四步全部通过，再启动 Phase 2。
- 最小实验（与改进并行，不阻塞改进）：在真实 trace 上跑一次 ensemble.py，验证期望表键错位是否导致期望全部回落为零。只跑一次，只记录结果，不改代码。目的是把第 3.6 节第二项的「由代码直接推出，未在真实 trace 上运行验证」变成已验证的结论。

## 7. 验收标准和实施计划

### 7.1 Phase 1 验收标准

- S6 监控 check 命令退出码 0。status 命令正常。池文件正常更新。玩家名单与动作种类来自统一来源，不再硬编码。
- data.json 不再含有 fixture 预测。回放页不再展示 fixture 预测。或者新的真实预测已生成，版本号为 v2，无 c_rule，标注未校准与生成时间。
- 同一条未变的 trace 连续跑两次 ./run.sh --modular，两次 overall 均为 pass。跑一次 predict，/tmp 无残留 predict-lean-* 目录。两次并行运行不互相覆盖（运行 ID 唯一）。
- rebuild_monthly.py 能复现当前 data.json。关键文件已入库。README 与 STATUS 与实际状态一致。git status 无非预期的未跟踪文件。
- 全部改动通过现有检查：check.py pass，Lean 构建退出码 0，0 sorry。三处页面数据 md5 仍一致。S5 季末与 S6 季末不变。

### 7.2 实施计划

- 顺序：监控恢复 → 预测漂移处理 → 运行层修复 → 仓库卫生。每步单独验证，单独记录。
- 每步改动可逆。改动前备份原文件。改动后跑对应检查。检查失败则回退，不带病进入下一步。
- 涉及第十六节需确认的事项（改现实事实、改冻结赛季、改血量金币口径、改玩家角色与关键定义、改结算标准、替换主预测架构、大规模迁移数据、删除历史记录），先形成研究结论和方案文档。只有当 Phase 0 证据证明某项是已核实的错误纠正、可逆、有完整记录时，才直接执行。否则只写方案文档，列为待用户醒后定夺。
- 棋盘、回放页、趋势图三处页面的改动，先改本地源文件并跑核验。部署由主代理处理。本轮不调用 artifact 工具。
- Phase 1 完成后写 Phase 1 报告，汇报改了什么、验证结果、证据、未解决事项、下一阶段计划。再启动 Phase 2。

## 附录 A：能力地图

### A.1 已实现并验证

| 能力 | 证据 | 依赖与调用关系 |
|---|---|---|
| 历史账本全量检查 C1–C9 | check.py pass，751 条、32 名玩家、7 赛季、139 条排名，零失败 | data.json → convert_data_json.py → raw trace → check.py |
| 有限历史不变量 Lean 证明 | Proofs.lean native_decide 全过，0 sorry | Trace.lean → lake build → Proofs.lean |
| 无界 Dynamics 不变量 | invariant_run 与 invariant_runStates 归纳证明，139 个初始状态 | Dynamics.lean → Proofs.lean 链接定理 |
| 数据一致性（历史动作层） | 三份 data.json md5 相同，棋盘内嵌数据逐轮对比不一致数为 0 | data.json → gen_board_data.py → 棋盘；data.json → 回放页与趋势图 assets |
| 题集打分复现 | 重跑 score_v11.py 输出逐字节相同 | testset-v7.json（分支）→ score_v11.py → score-v11.json |
| 定时任务运行 | 6 个任务全部启用，最近运行全部成功 | cron → 各监控脚本与 agent |
| git 同步状态 | main 与 origin/main 同为 8fa382a，无未推送提交 | 本地仓库 → origin |

### A.2 已实现但未充分验证

| 能力 | 缺口 | 依赖与调用关系 |
|---|---|---|
| 排名顺序 | rank 字段在任何检查中都不出现 | 转换器排序代码（无检查）→ data.json rankings |
| 杠杆罚金机制 | 全部 borrowed 为 0，penalty 为 0，只在平凡实例下通过 | convert_data_json.py（写死 0）→ check C2/C3 与 Lean |
| C10–C12 元规则检查 | 规则动作、政治记录、触发链接、游说动作、目标检查全部为空列表，空真通过 | 页面规则章散文（从未结构化抽取）→ 空列表 → 检查 |
| 轮次跨度例外 | rules/round-spans.json 只有 2 条，手工文件，正确性不在任何检查内 | round-spans.json → check C5 与 predict |
| 预测展示 | 回放页展示 fixture 预测，棋盘展示角色扮演预测，两者矛盾 | data.json forecast（fixture）→ 回放页；roleplay-s6-forecasts.md → 棋盘默认值 |
| S6 监控 | check 命令已跑崩，退出码 1 | traces/trace-latest.json → s6_monitor.py → s6-pending-pool.json |
| ensemble 集成预测 | 真实 trace 上期望表键错位，未运行验证；不在生产管道中运行 | ensemble.py → predict.expected_deltas（键错开） |
| 预测层运行 | 2026-11-24 的运行没有执行预测层 | run.sh --predict → predict.py、backtest.py、agent_claims.py |
| 赛季动作总数 | C1 把总数与 seasons[].moves 比较，该数字由同一转换器写入，自引用 | convert_data_json.py（自检硬编码 751）→ trace → check C1 |

### A.3 仅停留在设计阶段

- 现实、认知、模拟三层逻辑模型。任务文档第 3 节有设计，无代码。
- 证据生命周期。任务文档第 5.2 节有设计，无代码。主张只存指针。
- 真实预测账本与独立结算。任务文档第 6 节有设计，无代码。结算只存在棋盘默认值与池 note。
- 玩家模型。任务文档第 7.3 节有设计，无代码。只有角色扮演提示词。
- 预测任务拆分（主动行为、外部事件、反应、影响、状态）。任务文档第 7.2 节有设计，无代码。
- 因果模型。任务文档第 8.3 节有设计，无代码。
- 元博弈深化。任务文档第 8.2 节有设计，无代码。规则变化只记录为动作增量。
- 结构化经验记录。任务文档第 10.2 节有设计，无代码。复盘只写文字。
- 多 Agent 合议（InfoDelphi 式）。第 12 轮候选，无代码。角色扮演的四个变量尚未拆分。

### A.4 已废弃或被新方案取代

- payoff 模型 v1：被 v2 取代。但 data.json forecast 与 ensemble.py 仍用 v1。残留未清理。
- 558 条 trace：被 751 条取代。但 README、STATUS、testset-v7 meta.note、rebuild_monthly.py、rebuild_monthly_report.json、s6_monitor.py 注释仍写 558。残留未清理。
- 18 名玩家名单：被 32 名取代。但 s6_monitor.py 的 PLAYERS、data.json forecast、池 meta 的旧备注仍用 18 名。残留未清理。
- testset v3（88 道）与 v6（98 道）：被 v7（215 道）取代。但 s6_monitor.py 的 TESTSET_PATH 仍指 v3。testset-v7 仍在未合分支上。
- C1 旧恒等式（每赛季每玩家动作数等于轮次数）：月度结构下已失效，改用赛季记录的动作总数。
- Dynamics 连续轨迹：S0→S1 断点处三名玩家金币跌破零，已改为按（玩家，赛季）分段跑。
- 31×18=558 计数公式：已失效。当前结构为 751 条、32 名玩家、94 轮。

### A.5 尚未解决的问题

- P0：data.json forecast 是 fixture 预测，回放页展示它。无真实预测输出。
- P0：S6 监控跑崩。玩家与动作词汇无统一来源。
- P0：gate 只查证据格式。主张只存指针。
- P1：预测模块十处语义不一致。ensemble 在真实 trace 上预测回合类型，不是实质动作。
- P1：题集不在 main 里。分支合并有 data.json 回退风险。
- P1：预测生成不可复现。运行数据不在仓库里。
- P1：mtime 守卫仍可误报。/tmp 临时目录永不清理。运行 ID 精确到秒，无锁。
- P1：README 与 STATUS 过时。13 个关键文件未进仓库。重建脚本不能复现当前数据。
- P1：第 11 轮报告标题增益与脚本输出口径不同（+5.33 与 3.67）。
- P1：方法文件例题泄题第三次。日期违规 123 条。等 Gu 定是否动手修（待定事项，不在本轮动）。
- P1：第 12 轮方向未定（等 S6 候选够 30 道复测角色扮演，或先修新种类弱项）。S6 池现 4 道，距 30 道门槛仍远。
- P1：棋盘结算无版本控制。棋盘目录不是 git 仓库。localStorage 默认值只在首次访问时生效。
- P1：棋盘新建预测表单提示写 SHA-256，代码是普通字符串哈希。
- P1：provenance 的 season_dates.S6 结束日期早于开始日期，待复核。

## 附录 B：Phase 7 记录（只记录，不开发）

- 用户于 2026-11-24 23:29 下达 Phase 7 补充任务。产品化与交互体验优化。
- Phase 7 是独立补充。现阶段不开发。原则上等 Phase 0–6 完成并通过验收后才启动。启动时根据系统实际能力重新审查，不要机械实现全部建议。
- 设计方向全文已存为 ~/workspace/verification/design/phase7-product-design-2026-11-24.md。
- 六个功能区：AI 大厅、对局复盘、玩家档案、预测中心、沙盘推演、研究实验室。
- 实施前要求：先做界面审查，再提 A/B/C 三种演进方案。
- 本报告只记录以上方向。Phase 7 的任何开发工作都不在本轮、本阶段执行。

## 第十四节回答

- 本轮发现了什么：系统真实状态与任务文档的判断大体一致，但有三处比文档写的更严重。S6 监控不是词汇过时，而是已经跑崩。回放页展示的预测不是一般的过期预测，而是合成 fixture 预测。语义不一致不是个别差异，而是十处系统性分歧。
- 哪些问题已经被证实：P0 三项全部证实（预测漂移、词汇漂移、证据深度）。P1 三项中两项证实（可复现性部分证实、运行环境大体证实、语义不一致证实）。失败后误发布证伪。
- 改了什么：本轮没有改任何业务代码与业务数据。本轮只写了这份报告。
- 为什么这样改：本轮是审查轮。任务要求先核实，再动手。
- 系统实际提升了什么：本轮没有提升系统能力。本轮提升了对系统状态的认识。六项核查结论全部有文件路径、行号或命令输出支撑。
- 有哪些证据：六路核查报告。关键证据点：data.json 第 10717 行 fixture 引用，gate.py:205-215 格式检查，s6_monitor.py check 退出码 1，ensemble.py:193 回合类型候选动作，run.sh 第 117–137 行 mtime 守卫，055105 与 055133 两次运行的产物对比。
- 有没有引入新问题：没有。本轮只读，没有修改任何文件。
- 哪些目标仍未达到：愿景十项能力中，预测链断裂、观察停止、验证盲区三处瓶颈仍在。80% 目标仍远。S6 池只有 4 道候选，距 30 道复测门槛仍远。
- 哪些结论不能成立：751 条重验通过不能理解为事实正确、增量合理、排名正确、规则表正确。Lean 通过不能当作现实事实正确。回放页的预测不能当作当前预测。第 11 轮报告标题的 +5.33 不能直接用脚本输出复现。README 与 STATUS 不能当作当前状态。
- 下一轮最值得研究什么：Phase 1 的四步。先恢复监控运行。再处理 fixture 预测。然后修运行层三处缺陷。最后修仓库卫生。同时跑一次 ensemble.py 在真实 trace 上的验证，把期望表键错位从代码推论变成运行结论。

## Phase 1 修复清单（只列清单，本轮不执行）

1. 修 s6_monitor.py：玩家名单与动作种类改读统一来源，TESTSET_PATH 指到 testset-v7，new_pool() 默认值改到 215 道，修 player_of_trace_move 越界。
2. 处理 data.json forecast：真实 trace 重新生成（v2、无 c_rule、标注未校准），或删掉并标注当前无预测。回放页同步处理。
3. 修 run.sh mtime 守卫：改按内容哈希判断。修 predict.py /tmp 泄漏：用后删除。运行 ID 加随机后缀。修 daily_run.sh 运行目录推断。
4. 修 rebuild_monthly.py 到 751 条并验证复现。入库 gen_board_data.py、check_consistency.py、4 个 gpt1 文件、design/testset-coverage-plan.md。*.bak 加进 .gitignore。定夺 ProofsByPlayer.lean 与 ProofsBySeason.lean 归属。更新 README 与 STATUS。
5. 变基并合并 loop/vision-1-testset-complete 分支。data.json 冲突以 main 的 751 条为准。修 testset-v7 meta.note 的 558 表述。
6. 复核 provenance 的 season_dates.S6 [20261122, 20261101]。确认后修正。
7. 记录第 11 轮报告增益口径差异（+5.33 与 3.67），不改写历史结论。
8. 修棋盘新建预测表单的哈希说明，与代码实现一致（本地文件改动，部署由主代理处理）。
9. 跑一次 ensemble.py 在真实 trace 上，验证期望表键错位结论。只记录结果，不改代码。

## 订正（2026-11-24 Phase 1）

- 第 3.6 节第二项的表述需要订正。原文称 ensemble.py 在真实 trace 上期望查找「全部落空，回落为 (0.0, 0.0)」。Phase 1 实测：修前 416 次查找中 288 次回落，占 69.2%。128 次命中真实均值，占 30.8%。原因是 4 个 action_kind 取值（r1、huang_resign、anthropic_ipo、sec_probe）恰好与 semantic_kind 同名。机制（键错位）证实，「全部」的量词是错的。修后 928 次查找中 0 次回落。证据：Phase 1 报告。
- 第 3.6 节第二项的另一句「未在真实 trace 上运行验证」现已验证。结论如上。
