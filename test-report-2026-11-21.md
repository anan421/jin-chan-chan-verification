# 金铲铲复盘：独立测试报告

测试日期：2026-11-21（UTC 时间）。

测试员：独立测试员（tester）。测试员只测，只记录。测试员不修代码，不改页面，不改数据。

测试对象：页面最新上线版本（v13，加证据层与推演节）；管线 `~/workspace/verification/`。

测试清单：`~/workspace/verification/test-scenarios.md`，共 20 项。A 页面 8 项，B 管线 5 项，C 预测、场景、拟合、集成 5 项，D 每日循环 4 项，E 端到端与诚实标签 3 项。D4 含不排 cron。

通过标准：全部 20 项通过，任一项失败整轮不通过。

## 总体结论

19 项已验证通过。1 项未完全验证：A7（移动端 390px 实际渲染）。A7 只做了静态核对，无浏览器可用，须真机或浏览器复核。本轮不通过，原因只有 A7。

C2 在新 trace 上最终通过，但经过有疑点。C2 先失败（退出码 2），后通过（退出码 0）。两次运行之间，predict.py 被改动过。报告第 5 节记录完整经过。不得只报最后一次通过。

B1、C1、C3 在新 trace（fd79d114）上重核通过。预测层仍在被并行改动。predict.py 在 12:36:45 与 12:41:20 两次改动。C1 与 C2 的结果是快照，对应约 12:38–12:39 的 predict.py 版本。已派的语义接入任务完全落地后，C1 与 C2 须再重核一次。

## 文件哈希（测试时测得）

页面（测试全程未动）：

- 页面 assets/data.json：`07995677f405f030d66188e6ab910450bb50db96dbcc3549556f066d941f365d`，修改时间 2026-11-21 12:23:48 UTC。
- 页面 index.html：`2b144bf4926fdfa282d29e2a59b44f7a0d22efbd634dcf8e1085ac1f8a4af83e`，修改时间 2026-11-21 12:24:06 UTC。

Trace（重抽取后）：

- 旧 trace：`2d04a088a5695aa230646faf2beb74a3c5c535fad6ea378c70c9e32575a5c9e9`。
- 新 trace：`fd79d114387f30e19139c91d086446ac63df1fa4efdb8894e302abfbc4b99a63`。traces/trace-latest.json 与 traces/trace-2026-11-21.json 内容相同。
- 新 trace 内 meta.trace_sha256：`7d8dfe58667c602b100c2ba4dbc3bf356fff0f0ae17015140679f9cecafd26d8`。
- 新 trace 内 meta.source_sha256：`03492ec415e9bcb348e88f73f3e2325911f7a4cbf2652274046fe1ac329f41ac`。该字段有标签问题，见第 6 节。
- 新 trace 内 meta.extracted_at：`2026-11-21T12:30:21Z`。schema_version 4。moves 558。

合并报告：

- runs/2026-11-21_123024/merged-report.json：`05e092cc3e07292d7fa68f15133c6e926a768a23fcd198fb6e6050ef4e2ab3ad`。
- runs/2026-11-21_123045/merged-report.json：`0b44b43713dd5ffbf454a3143c67659fc043a2ba7093b5bea0e472b3fb2102c9`。

测试员重跑输出（在 /tmp/tester/，不是交付物）：

- backtest-real-new.json：`35e70ee246481780b1392afffa1970db5a3da84404c2512cec6ea53496469508`。
- scenarios-real4.json：`54b9df7754067fe2f26088aa8ea0ac563988c0a76d8bef6f9ceade820c3945b0`。
- predict-scen-real4.json：`91883f30aaacbb9ae417178f0b24595803f3101f3f70b82684a465c9d848083a`。

改动前后的页面哈希（推演节新增集成众数并列展示，Gu 已批准）：

- 改动前 data.json：`17246d90eaccd7c82b374e9b1fdd3a690661fc7ac18b1e31b88faadea917a321`（2026-11-21 12:06:23 UTC）。
- 改动前 index.html：`efc8572a29a8afd56080621619392c5e20a338f7766ae36f84182439ff77d2ff`（12:07:02 UTC）。
- 改动后 data.json：`07995677f405f030d66188e6ab910450bb50db96dbcc3549556f066d941f365d`（12:23:48 UTC）。
- 改动后 index.html：`2b144bf4926fdfa282d29e2a59b44f7a0d22efbd634dcf8e1085ac1f8a4af83e`（12:24:06 UTC）。

## A. 页面（8 项）

### A1 通过

S5 段位分布：钻石 6，铂金 6，黄金 5，青铜 1。领头羊 Anthropic，74 血，85 金。涨幅最大字节跳动，-10（84→74）。跌幅最大英伟达，-46（84→38）。测试员用 node harness 实际执行页面 JS，核实首屏看板渲染值与 data.json 一致。

### A2 通过

rankOf 函数与公开规则一致。字节 74→钻石，英伟达 38→青铜，微软 68→铂金。三名玩家已核。

### A3 通过

回放代码只读 SEASONS 与 OPENINGS，不改动源数据。轮初状态由 OPENINGS 加累计增量推导。126 个 S5 轮初状态已由 Python 独立复算。S5 轮初状态中无血量 99。旧手写英伟达 99/84 已消失。英伟达 S5 轮初轨迹：1-1 84/90，2-1 80/62，3-2 85/67，4-1 79/67，5-1 63/63，6-1 55/61，6-2 37/55。测试员用 node harness 实际驱动回放：默认 S5 6-1 轮初 18 席与独立复算 0 偏差；播放 18/18 步完成，日志含全部 18 条动作，终态与 S5 6-2 轮初逐格一致；暂停（⏸ 暂停 → ▶ 继续）、重置（第 0 / 18 步）、选赛季（S1 开局 18 席 0 偏差）、选轮（S1 2-1 轮初 0 偏差）均执行通过；倍速 1×/2×/4× 选项存在（1100/550/260ms）。

### A4 通过

roundEvidence 31 条。状态：verified 26，opinion 4（S1:1-1、S1:3-2、S3:1-1、S4:5-1），pending 1（S5:6-2）。证据指针种类：url 27，edgar 3，doc_number 1。大动作 32 条中有逐动作证据 11 条。页面有 roundEvidenceHTML（每轮可展开）与逐动作「证」标签。页内 V1 检查含证据覆盖校验。证据口径：只证标题事件本身，不证 Δ 数值。

### A5 通过（改动后重核）

推演表 11 列：玩家、类型、当前血量/金币、预测动作、众数概率 p、前三质量 top3、期望增量 E[Δ血，Δ金]、集成众数、集成 p、一致率、分歧。18 行。集成众数两处推翻（Anthropic、DeepSeek）带红色「集成推翻」徽章与淡红行底。forecast.ensemble 与 ensemble-report.json 逐字段比对：18 席共享字段全等，仅 dropped `distinct_modals` 与 `player` 两字段，数值 0 偏差。global 相同。n_members 15。member_ids 相同。来源 runs/2026-11-21_115508/ensemble-report.json，fixture trace，calibration placeholder_only。免责行含 15 名成员、占位参数、未校准、fixture trace。单模型众数：NVDA r1 p=0.938，ANTH huang_resign p=0.753，BYTE musk_table p=0.881，HUAWEI generic p=0.991，DPSK musk_table p=0.502。

### A6 通过

页头 RV-2026.2（2026-11-19 生效）。规则桌 6 席，反身性链条齐全。补丁章 SEASON_PATCHES 5 条（S1–S5 各一）。观察清单 .wrow 恰 7 项。

### A7 未完全验证（受限，唯一未闭合项）

无浏览器可用。无 chromium、puppeteer、playwright、firefox、wkhtmltoimage、weasyprint 二进制。probe-ui 只有 0 次观察。静态核对通过：viewport meta 存在；media queries 在 820/520/420/380px；全部 flex 容器 flex-wrap:wrap；表格在 overflow-x:auto 包裹内；.bunits 为 6 列 grid；无固定宽元素。390px 实际渲染（scrollWidth 量测）无法执行，须真机或浏览器复核。测试员的 node harness 不能量布局。

失败位置：移动端 390px 实际渲染未量测。

复现步骤：在真实浏览器打开页面，设视口宽 390px，量 scrollWidth 是否等于 390。或在真机打开页面，检查首屏有无横向溢出。

### A8 通过（实际执行）

测试员用 node harness（/tmp/tester/harness3.js、harness4.js）跑页面真实 5 段 script、stub DOM 后执行 runChecks()：12/12 PASS，数据哈希 fnv1a:8d90a977，与 Gu 手机截图（2026-11-21 19:53）一致。V1–V7、V12 为纯数据检查，全过。V8–V11 依赖真实 DOM，初版 stub 下曾报 8/12（折线数 0、排名区 0 行等），逐一证实为 stub 缺真实 DOM 所致（非页面问题），补齐 stub 后 12/12。门禁文案仍为「未通过验证，修复中」。第 3 层 Lean 证书未由管线对当前文件产出并归档，属页面 fail-closed 规则，见 B1 注。

## B. 管线（5 项）

### B1 通过（旧 trace）

runs/2026-11-21_121412：check-summary verdict=pass，passed=3，failures=0，gaps=0。覆盖 558 条、18 人、5 季、90 行排名、0 规则动作、0 触发链、12 项不变量、全量。lean-build.log 末尾「Build completed successfully (14 jobs)」。merged-report.json 总体 pass。gate skipped（未提供 Agent 输出，属正常跳过）。

注：门禁文案「未通过验证，修复中」仍在页上。原因是第 3 层 Lean 证书未由管线对当前页面文件产出并归档。页面按 fail-closed 规则保持未通过文案。历史层本身已 pass。

### B2 通过

坏 fixture 重跑 runs/2026-11-21_122228 总体 fail。检查器 fail（passed=1，failures=10，gaps=0）。Lean fail（构建退出码 1）。run.sh 退出码 1（单独重跑实测）。10 处失败与修前（111654）逐项相同：C2 S4 软银 hp_end，C2 S5 英伟达 hp_end，C3 S5 英伟达 gold_end，C2 S5 Anthropic hp_end，C4 S4 软银 moves_after_death，C5 S4 4-1 英伟达 date_before_true，C5 S5 5-1 OpenAI overseas_rental，C6 pool_cost_5_overheld 12，C10 no_political_record，C11 link_order。分类：机制错 1 簇（C2/hp_end ×3），数据错 7 簇。

### B3 通过

lakefile.toml 有 defaultTargets=["Verification"]。run.sh 有 check_olean 新鲜度校验。测试员亲自重跑 `lake build`：Build completed successfully (14 jobs)，退出码 0。

### B4 通过

gate.py 四 fixture 重跑（退出码实测，无管道遮掩）：ok exit 0（pass 4、reject 0、opinion 1、contested 0、refuted 0）；broken exit 1（pass 0、reject 5、opinion 1、contested 2、refuted 2）；pred-ok exit 0（pass 1，future=true）；pred-badmove exit 0（pass 1，gate 只查 R1–R3）。predict.py 接 pred-badmove 后 CL-PB1 记 refuted_by_transition（overseas_rental 在 RV-2026-11 下被禁），fork 18 步，reverify check=pass、Lean=pass。

### B5 通过

data.json 独立复算全过：558 条、90 组守恒、72 组跨季断点为 0、量程血量 37–100、金币最低 10。管线 data.json 与页面 assets/data.json 的数值部分逐项相同，仅 meta 不同。页面独有三键 roundEvidence、roundEvidenceMeta、forecast。注：测试开始时管线 data.json（d3b36ec3）比线上页面旧；重抽取后管线 data.json 已与页面一致（07995677…）。

## C. 预测、场景、拟合、集成（5 项）

### C1 通过

Prediction.axioms.txt 只依赖标准三公理（propext、Classical.choice、Quot.sound），无 sorry。runs/2026-11-21_121419 backtest 为 walk-forward S1–S3 拟合、S4–S5 测试，fit_note 明确写明占位参数未校准。

新 trace 重核（见第 4 节）：runs/2026-11-21_123045 总体 pass，预测章 fail（按规矩判：预测 pass、回测 fail、符号动力 pass、协议 None）。预测不是验证，不改变总体结论。回测（walk-forward S1–S3 拟合、S4–S5 测试，n=234）：M1=0.0000（基线 0.0955，裕度 -9.55pp；可分类子集 m1_n=41，m1_unknown_n=193，0/41 命中）、M2=0.3547（-14.53pp）、M3=0.2521（-24.79pp）、M4=0.3205（基线 0.125，+19.55pp，唯一信号）、M5=0.8120（-1.74pp）。低于阈值 [M1, M2, M3, M5]。阈值 margin_pp 10，below_threshold 降级为 opinion，不阻塞历史层。按赛季：S4（n=108，m1_n=22，M1 0.0）、S5（n=126，m1_n=19，M1 0.0）。按玩家：GOOG、META、BIDU 的 m1_n=0（无可分类动作）；HUAWEI 是唯一 4 项有信号的玩家（M2、M3、M4、M5）。123045 报告的预测分布为 18 名玩家众数动作全是 anthropic_ipo，p=1.0（占位参数坍缩）。该分布已过时，见第 5 节。新 predict.py 的分布为 v3（15 席）、blackwell（NVDA）、r1（ORCL、DPSK）。两种分布都是占位参数坍缩，不是真实预测。Prediction.axioms.txt 重核：全部定理只依赖 [propext] 或 [propext, Classical.choice, Quot.sound]，无 sorry（grep 为空）。123045 lean-build.log：「Build completed successfully (14 jobs)」。符号动力 pass：cells 432、edges 20925、SCCs 225、attractors 216，全是单格死单元，无活吸引子。9 个规则版本（RV-2022.1 至 RV-2026.2）。action_kinds 为轮次类型 slug 词汇。

测试员用新 predict.py 直接重跑 backtest.py：输出与 123045 逐项相同（整体、按赛季、按玩家，M1–M5、基线、裕度、信号、below_threshold 全等）。输出文件 /tmp/tester/backtest-real-new.json，sha256 35e70ee2…。backtest.py 导入 predict.py（`import predict as P`），但 12:36 的 predict.py 改动未改变回测数字。

### C2 通过（fixture 冒烟；真实 trace 先失败后通过，见第 5 节）

scenarios-report.json（runs/scenario-smoke/，sha256 `e0eb79f80a80999d261efdc433e57066dd15655962096b6c0413ff1936160eae`）：4 条分支（SC-BASE RV-2026.2 延续、SC-BIS-TIGHTEN BIS 再收紧 [WL-BIS-COMMENT-2027-01]、SC-RASA RASA 通过 [WL-RASA-SENATE]、SC-TRUCE-EXPIRE 贸易休战到期 [WL-TRUCE-2027-01, WL-BIS-COMMENT-2027-01]），触发概率一律 null。跨场景众数变化：SC-BIS-TIGHTEN 1 席（TSMC）、SC-RASA 3 席（GOOG、ALI、TSMC）、SC-TRUCE-EXPIRE 1 席（TSMC）。

真实 trace 上的场景运行：先失败（退出码 2，见第 5 节），后通过（退出码 0，见第 5 节）。最终输出 /tmp/tester/scenarios-real4.json，sha256 54b9df77…。4 条分支均有输出，触发概率一律 null。跨场景众数变化为 0（与 fixture 冒烟的 3 席变化不同）。max_shift：SC-BASE 0.0，SC-BIS-TIGHTEN 7.6e-05，SC-RASA 0.04696，SC-TRUCE-EXPIRE 7.6e-05。占位参数下，场景几乎不改变预测。须如实记录，不得说成有信号。

### C3 通过（机械验证）

fit-report.json：status smoke_test。显现偏好、平均结构化感知机（30 epochs，eta 0.1）。trace 为 fixture（sha256 864a4d3f…）。fit_window S1–S3，共 18 轮 306 个决策。v1 投影权重塌缩（w_hp 0.0、w_gold 0.0、c_lever 0.01294、c_rule 0.999916、w_pos 0.0，violation_rate 0.732026）。backtest-fitted.json 总体 verdict fail（test_window M1 0.1026、基线 0.0863、+1.63pp；M2 0.4444；M3 0.5556；M4 0.4615；M5 0.8547；below_threshold [M1, M2, M3]）。测试员亲自重跑 fit.py（输出至 /tmp/tester/fit-retest）：退出码 0，权重与原报告逐项一致，可复现。真拟合未跑时记为「待后续」，不算失败。该状态已随语义种类层落地而改变，见第 4 节 C3 重核。

### C4 通过

ensemble.py 重跑（fixture）：退出码 0。全部计算值与 runs/2026-11-21_115508/ensemble-report.json 逐项相同（HUAWEI 全共识 generic p=0.917373；DPSK stargate p=0.526593、一致率 0.357143；TSMC spacex_xai p=0.840752）。报告 sha256 不同（重跑 9e0ebcd2… 对原 7dd46140…）只因 rules/payoff-model.json 已从 v1 升到 v2（新增 A8 discount、A9 hp_exponent），嵌入的 payoff_model 版本与假设随之变，计算值无一不同。不是非确定性。

### C5 通过

ensemble.py 在 broken fixture 上跑完（退出码 0），报告内无任何验证措辞（verified、pass、valid、check passed、证明、已验证、通过验证均未出现）。calibration_status placeholder_only。

## D. 每日循环（4 项）

### D1 通过

daily/triggers.json：5 条报警（new_round、tier_cross、rule_version_change、confidence_tier_change、verification_failed）加 3 条只记日志（incomplete_round、no_events、default）。附注明确「报警不等于对外推送：本管线不发任何外部消息，报警由晨检/日报读取 decision 文件呈现」。

### D2 通过

archive/ 有 6 个哈希加日期目录加 README.md 加 manifest.jsonl。每条含 date、kind、trace_sha256、data_sha256、path、verdict、run_id、source（fixture，合成数据）。归档目录内含 data.json 加 trace.json。测试员亲自对 archive/2026-11-22_8a709644f76c/trace.json 跑 check.py：verdict=pass，passed=3，failures=0，gaps=0，覆盖 moves=576（558 加 18 条追加的 smoke 轮次）、18 人、5 季、90 行排名，退出码 0。runs/2026-11-21_120232 曾以归档 trace 重跑并通过。

### D3 通过

daily_run.sh 步骤 0–7 已核（归档摄取前快照；无事件只记日志退出 0；ingest exit 3=轮次未凑满只记日志；recompute.py；./run.sh 全量验证且 classify.py 在 run.sh 内运行；triggers.py 决策；放行门：通过才发布新 trace，失败则阻断且 trace-latest.json 不动；归档摄取后快照带 verdict）。退出码 0 放行或无事可做、1 验证失败被阻断、2 输入错误。脚本声明「永不触碰页面 artifact，永不排 cron」。ingest.py 接受 schema 2/3/4。extract.py SCHEMA_VERSION=4。classify.py 已接入 run.sh。每日 smoke：runs/2026-11-21_120151（11-22，pass）、120212（11-22，pass）、120220（11-23，fail——坏事件 smoke，检查器 1 失败、Lean 构建退出码 1，正确被阻断）、120243（ok fixture 加 claims，gate pass 4 通过 1 opinion，总体 pass）。11-23 release 文件：released=false，verdict fail，reason "verification failed; page update blocked"，trace-latest.json 未动。

### D4 通过

cron.list（含 disabled）无每日循环 cron。现有任务：china-ai-infrastructure-watch、dashboard-auto-archive、deterministic-doctor（system）、feed-pulse-00..23（system）、google-termination-window-check、heartbeat、profile-image（system）、s1-edgar-watch、weekly-ai-industry-briefing、whitehouse-protocol-watch。daily_run.sh 声明永不排 cron。STATUS.md 记录本次不排 cron。

## E. 端到端与诚实标签（3 项）

### E1 通过

3 条动作 data.json → trace 逐项吻合（S5 5-1 ANTH +8/+30「分阶段募资到手。绿鞋后合计口径见本轮说明」；S5 6-1 NVDA -18/-6「SEC 调查报道。恐慌卖出」；S5 3-2 BYTE +1/0「海外算力租赁需求被点名」）。3 轮证据均有真实指针（S5:5-1 verified：edgar 0001628280-26-074944、doc_number 2026-23529、url NPR；S5:6-1 verified：2 个 URL；S5:3-2 verified：1 个 URL）。新 trace 上已重核，三条仍吻合且带 semantic_kind（anthropic_ipo、sec_probe、overseas_rental）。

### E2 通过

页面诚实标签齐全：模型分声明（「血量、金币、人口均为本页的模型分……不是股价。不是市值」）；推演免责（「本推演是模型输出，不是事实；参数未校准……集成成员权重是立场映射的判断，非证据」）；「本页不冒充证书已生成。证书未出之前，整轮状态保持「未通过」」；「标「待核」的数字未经独立核验，不得当定论读」；核验章自写已删、换 14 方真实审计；证据口径「证据只证标题事件，不证血量/金币数值（Δ 均为模型分）」；fc-meta 显示 calibration_status「仅占位参数，未校准」。报告侧：121419 报告写明「预测不是验证。预测结果不进“已验证”标签，不改变总体结论。预测章结论：fail」。

### E3 通过

三处硬错误已由测试员从 data.json 独立复算：S2 微软血量增量和 -4（开局 96→季末 92）；S5 Anthropic 血量增量和 -14（开局 88→季末 74）；S5 英伟达金币增量和 -35（开局 90→季末 55）。排名未动（与修复前基线一致，见 reconciliation 137 项）。

## 4. 新 trace 重核（B1、C1、C2、C3）

新 trace：fd79d114…，schema v4，558 条，73 条已分类、485 条 unknown（87%）。语义种类分布（unknown 除外 15 种）：stargate 15、anthropic_ipo 8、msft_invest 7、musk_table 6、blackwell 6、r1 6、spacex_xai 4、colossus 4、doubao_price_war 4、bis_rule 4、chatgpt 3、v3 2、overseas_rental 2、huang_resign 1、sec_probe 1。

### B1 重核通过

runs/2026-11-21_123024/ 总体 pass。gate skipped（未提供 Agent 输出，正常跳过）。快速检查器 pass（passed=3，failures=0，gaps=0；覆盖 558 条、18 人、5 季、90 行排名、0 规则动作、0 触发链、12 项不变量、全量）。Lean pass（构建退出码 0，trace 生成退出码 0；lean-build.log 末尾「Build completed successfully (14 jobs)」）。trace meta：schema_version 4，extracted_at 2026-11-21T12:30:21Z，page_version v7，moves 558。

### C1 重核通过

见 C1 节。回测数字与 123045 一致。测试员用新 predict.py 重跑 backtest.py，输出逐项相同。预测分布已过时，见第 5 节。

### C2 重核：先失败、后通过

见第 5 节。

### C3 重核通过（机械验证，非正式校准）

测试员在 /tmp/tester/fit-real/ 对新 trace 跑 fit.py（仅作机械验证，不发布到 runs/，不是第一次真拟合——正式真拟合已另派任务，等 v2 效用集成后做）。退出码 0。fit-report.json：status smoke_test。trace 字段为 traces/trace-latest.json，trace_sha256 fd79d114…（与文件一致）。fit_window S1–S3，18 轮，306 个决策（S1R1 因空前缀被跳过，故 306 而非 324）。方法为显现偏好、平均结构化感知机（30 epochs，eta 0.1，discount-weighted by gamma，HP power alpha）。v1 投影共享权重 w_hp 0.193893、w_gold 0.0、c_lever 0.436579、c_rule 0.873158、w_pos 0.096947，violation_rate 0.888889（未加权）/ 0.863588（discount-weighted），alpha 1.0、gamma 0.9、temperature 0.25、n=306、mean_loglik -1.154714。分档 violation：china_vendor 0.848086（n=102）、chip_supplier 0.906097（n=34）、cloud_hyperscaler 0.802167（n=85）、leveraged_infra 0.87629（n=34）、model_lab 0.905695（n=51）。alpha_grid [0.25, 0.5, 0.75, 1.0]、gamma_grid [0.9, 0.95, 0.98, 1.0]、tau_grid [0.25, 0.5, 1, 2, 4, 8]。selection_rule 为最低 discount-weighted violation，ties 倾向 alpha=1、gamma=1。拟合参数与假设分开标（payoff-model-fitted.json 的 parameters 每项含 status fitted 与 assumption 链接 A1–A5；assumptions 列表独立）。notes 明确：fit-window violation 是 in-sample 指标，不是校准；真正检验是 backtest.py 用 payoff-model-fitted-v1.json 在 hold-out 窗口（S4–S5）跑 M1–M5；c_rule 不可识别（f_rule 对一切合法动作均为 0，梯度恒为 0，只随归一化移动）。标签 bug 见第 6 节。

## 5. C2 事件时间线与预测分布差异（须如实记录）

### C2：第一次运行失败

时间：2026-11-21 约 12:33–12:34 UTC。命令：`python3 predict.py --trace traces/trace-latest.json --payoff rules/payoff-model.json --scenarios rules/scenarios.json --out /tmp/tester/predict-scen-real.json --scenarios-out /tmp/tester/scenarios-real.json`。退出码 2。stderr：`predict: scenario SC-BIS-TIGHTEN bans unknown kind 'msft_invest' (not in the trace kind set)`。无任何输出文件。测试员用同一命令重跑一次，仍为退出码 2，同一 stderr。

### C2：predict.py 被改动

predict.py 的 mtime 为 2026-11-21 12:36:45 UTC。在测试员第一次 C2 运行与重跑之间被改动过。rules/payoff-model.json（11:58:06）与 rules/scenarios.json（11:58:27）未动。已派的「predict.py 语义接入 + v2 效用集成 + 第一次真拟合」任务可能在此期间改了 predict.py。

测试员核查发现，该理解与代码不符：当时 predict.py 的 `kind_of(m)` 返回 `m.get("semantic_kind") or m["action_kind"]`。`all_kinds`（main 内第 862 行）与 run_scenarios 内第 708 行均用 kind_of 构建。测试员直接对 trace 算 kind 集，msft_invest 确实在内（16 种全集含 msft_invest、spacex_xai、stargate、colossus 等）。`load_trace` 只做 JSON 读取与顶层字段检查，不剥离 semantic_kind。`moves` 与 `all_kinds` 在 main 内 validation 之前未被重赋值。旧版 predict.py 的校验逻辑已不可查（文件已被覆盖）。第一次 exit 2 是真实发生的事实，但其内部原因未完全定论。

### C2：插桩重跑与原版重跑通过

测试员用插桩副本（/tmp/tester/predict-debug.py，仅加两行 DEBUG 打印，不改原文件）重跑：DEBUG 显示 all_kinds 含 msft_invest，n_moves=558、has_semantic=558，validation 通过，退出码 0。随后用原版 predict.py 按最初完全相同的命令重跑（2026-11-21 12:38 UTC）：退出码 0。场景输出已写出：/tmp/tester/scenarios-real4.json（78,571 字节）、/tmp/tester/predict-scen-real4.json（32,644 字节）。SC-BASE modal_changes_vs_baseline=0。SC-BIS-TIGHTEN 0、max_shift 7.6e-05。SC-RASA 0、max_shift 0.04696。SC-TRUCE-EXPIRE 0、max_shift 7.6e-05。reverify check=pass、Lean=pass。场景禁令已应用：SC-RASA 生效禁令为 [colossus, msft_invest, overseas_rental, spacex_xai, stargate]，分布中已无这些种类。触发映射见 scenarios.json：SC-BASE 无触发；SC-BIS-TIGHTEN WL-BIS-COMMENT-2027-01；SC-RASA WL-RASA-SENATE；SC-TRUCE-EXPIRE WL-TRUCE-2027-01 加 WL-BIS-COMMENT-2027-01。触发概率一律 null。watchlist_source 为 rules/rules.json watchlist 7 项。跨场景众数变化为 0（comparison 中 18 席 changed_across_scenarios 全为 false）。

C2 重核结论：按最后一次实测，真实 trace 上的场景运行通过。但第一次 exit 2 与 predict.py 中途被改动的事实必须如实写入报告，不得只报最后一次通过。

### 预测分布差异（未解之谜）

123045 报告的预测分布为全员 anthropic_ipo，p=1.0。测试员后来的 predict.py 运行显示 NVDA modal=blackwell（p=0.999748）、OAI/MSFT/GOOG modal=v3（p 约 0.98–0.999）。两者输入同为 rules/payoff-model.json v2 与新 trace，分布不同。原因未查明。可能与 predict.py 在 12:36 被改动有关。完整新分布（predict-scen-real4.json，base forecast）：NVDA blackwell 0.9997；OAI v3 0.9800；MSFT v3 0.9997；GOOG v3 0.9997；ANTH v3 0.9998；META v3 0.9946；AMZN v3 0.9951；MUSK v3 0.9937；AAPL v3 0.9999；ORCL r1 0.9985；BYTE v3 0.9992；ALI v3 0.9991；TCE v3 0.6205；BIDU v3 0.9860；HUAWEI v3 0.9432；DPSK r1 0.9526；TSMC v3 0.8153；SFTB v3 0.9945。众数只有三种：v3（15 席）、blackwell（NVDA）、r1（ORCL、DPSK）。占位参数坍缩仍在，只是换了一种坍缩。

### predict.py 再次被改动

predict.py 的 mtime 在测试员取哈希时为 2026-11-21 12:41:20 UTC。已派的语义接入任务仍在改动 predict.py。C1 与 C2 的结果是快照，对应约 12:38–12:39 的 predict.py 版本。该任务完全落地后，C1 与 C2 须再重核一次。

## 6. 标签与口径问题（须修，不阻塞本轮）

### trace meta.source_sha256 标签有误

trace meta 的 source_sha256（03492ec4…）实际等于中间产物 raw-trace-real.json 的 sha256，不是 data.json 的哈希。字段名有误导。真正的数据源哈希在 raw-trace-real.provenance.json 里：source sha256 `07995677f405f030d66188e6ab910450bb50db96dbcc3549556f066d941f365d`（与当前 data.json 一致），bytes 194222，注明「machine copy (cp) of page assets/data.json；no hand transcription, no rank back-computation」。转换器代码证实：`src_sha = hashlib.sha256(raw_bytes).hexdigest()`，raw_bytes 即所读 data.json 文件字节。B1 仍判通过，但须在报告里写明。

### fit.py 硬编码「fixture」备注 bug

fit-report.json 的 smoke_test_note 与 payoff-model-fitted.json 的 note/note_zh 均为硬编码字符串，称「fitting the fixture / fixture 上的冒烟拟合」，与本次运行实际输入（真实 trace，fd79d114）矛盾。报告的 trace 字段正确，但人类可读备注错误。正式真拟合发布前必须修掉，否则校准报告会自称是 fixture 拟合。重拟合触发 T1–T5 只写在 design/fitting-layer.md 第七节，未在 fit.py 里实现为代码检查（无自动触发检测）。

## 7. 失败与未闭合项清单

| 编号 | 状态 | 失败位置 / 复现步骤 |
|---|---|---|
| A7 | 未完全验证 | 移动端 390px 实际渲染未量测。无浏览器可用。复现：在真实浏览器打开页面，设视口宽 390px，量 scrollWidth 是否等于 390。或在真机打开页面，检查首屏有无横向溢出。静态核对已通过（见 A7 节）。 |
| C2 | 最终通过，但经过有疑点 | 第一次运行退出码 2（见第 5 节）。predict.py 在两次运行之间被改动（mtime 12:36:45）。原因未完全定论。重跑后退出码 0。须在报告里保留完整经过。 |
| 预测分布 | 未解差异 | 123045 全员 anthropic_ipo p=1.0，对测试员后续运行 NVDA blackwell、OAI/MSFT/GOOG v3。原因未查明。可能与 predict.py 被改动有关。 |
| trace 标签 | 须修 | meta.source_sha256 实为 raw-trace-real.json 的哈希，见第 6 节。 |
| fit 备注 | 须修 | fit-report.json 与 payoff-model-fitted.json 的备注硬编码称 fixture 拟合，与真实 trace 输入矛盾，见第 6 节。 |

## 8. 测试工作文件（tester 侧，不是交付物）

Node harness：/tmp/tester/harness.js、harness2.js、harness3.js、harness4.js（跑页面真实 script、stub DOM；harness3 达成页内检查 12/12 执行，harness4 达成回放交互执行）。

期望值文件：/tmp/tester/expected-s5-5-1.json（标签有误，实为 S5 6-1 轮初）、/tmp/tester/expected-s5-6-1.json、/tmp/tester/expected-replay.json。

重跑输出：/tmp/tester/fit-retest/（fixture 拟合重跑，与原报告逐项一致）、/tmp/tester/ensemble-retest.json（值与原报告一致）、/tmp/tester/ensemble-broken.json、/tmp/tester/gate2-*.json、/tmp/tester/predict-badmove.json、/tmp/tester/fit-real/（新 trace 机械拟合，仅作验证用，不发布）、/tmp/tester/scenarios-real4.json（78,571 字节）、/tmp/tester/predict-scen-real4.json（32,644 字节）、/tmp/tester/predict-debug.py（插桩副本，仅加 DEBUG 打印）、/tmp/tester/backtest-real-new.json（新 predict.py 下回测重跑，与 123045 逐项相同）。

测试员自身产生的运行目录：runs/2026-11-21_122228/（坏 fixture 重跑，总体 fail，预期内）、runs/2026-11-21_122316/（坏 fixture 退出码重跑，总体 fail，预期内）。其余新目录（123024、123045）为语义种类层协调员的运行。
