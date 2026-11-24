# Phase 1 报告：消除版本与语义漂移

- 项目：Jin Chan Chan Verification
- 仓库：https://github.com/anan421/jin-chan-chan-verification
- 基准：main 8fa382a（2026-11-24）
- 执行时间：2026-11-24 23:40–24:00 CST
- 提交：2f73d8c（Phase 1）、48f911d（合并题集分支）
- 报告依据：Phase 0 报告 ~/workspace/verification/design/phase0-review-2026-11-24.md 第 6–7 节

## 1. 本轮做了什么

- Phase 1 按四步执行：恢复监控运行、处理 fixture 预测、修运行层缺陷、修仓库卫生。六路并行执行，协调员收尾统一验证、提交、推送。
- 四步全部做完。验收标准七项中六项通过，一项部分通过（重建脚本不能完整复现，见第 5 节）。
- 本轮没有改历史事实、冻结赛季、血量金币口径。没有改结算标准。没有替换主预测架构。

## 2. 改动清单

### 2.1 监控恢复（scripts/s6_monitor.py、s6-pending-pool.json）

- 修 IndexError 越界崩溃。PLAYERS 不再硬编码 18 名。脚本启动时读 data.json 的 players 字段。玩家名单现为 32 名。下标越界时抛 ValueError 并写明原因。
- 玩家名单与动作种类改读统一来源。玩家名单读 data.json。动作种类读 testset-v7 全部问题的 kind 字段。种类数现为 43 种。KINDS 注释写 35 种、实际 34 种的问题已消除。
- TESTSET_PATH 改到 testset-v7。new_pool() 默认值改为 testset_n 215。gap_to_140 按 140 − 215 计算为 −75，并加 gap_to_140_status 字段，值为 legacy_target_pending_rescope。140 道目标仍待 Gu 重定，没有擅自定新目标。
- S6 起始日期统一为一个常量 S6_START_DATE = 20261122。候选条件为真实日期晚于 2026-11-21。旧的 S6_START = 20261121 已删除。
- 加活跃玩家概念。新增 active_players() 函数。它取 trace 里的最大赛季。它返回当季有动作的玩家。S6 活跃玩家为 NVDA 与 OAI。check 与 status 均输出历史玩家数与活跃玩家。
- 绝对路径已消除。四个路径全部由仓库根目录推导。从 /tmp 目录运行 check 也通过。
- 修去重误报。旧规则任一名称词命中即判重复。它误报两道候选。Claude Ship 仅因“Claude”一词命中 S1 旧动作。GPT-6.2 Sol Chat 标签页因“chatgpt”与“chat”命中 S5 动作。两词实为同一词。新规则要求四点同时成立：同玩家、同种类、同日期、动作文本含至少两个去重后的名称词。重叠词只算一次。
- 池文件只改 meta。各桶内容未动。桶计数保持 candidates 4、missed_s5 6、kind_gap 11、new_player 1、rejected 41。

### 2.2 预测漂移处理（data.json、三处页面数据、回放页、棋盘）

- 选择选项 B：删除 fixture 预测，改为明确标注当前无预测。选择理由是 predict.py 在真实 trace 上的输出不可信，证据见 2.2.1。
- data.json 的 forecast 块删除，替换为 status=none 标注。标注含判定日期 2026-11-24、5 条原因、被删旧块的来源记录、下一步。旧块来源记录写明：2026-11-21、fixtures/trace-fixture-ok.json、v1、18 名玩家、placeholder_only。
- 三份 data.json 同步，md5 相同（88a764b474e9a75f9266730b430e0b42）。forecast 键之前的字节与改前完全相同。其余全部顶层键的 JSON 值与改前完全相同。历史动作数据未动。血量金币未动。
- 回放页 index.html 的静态标题改为「当前无预测」。renderForecast() 增加无预测分支。FORECAST 为 none 或缺失时，渲染「当前无预测」、判定日期、trace、原因列表，不渲染旧表格。
- 棋盘 index.html 改 4 行提示文字。SHA-256 改为字符串哈希，与第 2197 行代码实现一致。4 条角色扮演预测默认值未动。

#### 2.2.1 predict.py 在真实 trace 上不可信的证据

- verdict=fail。分叉复验 check=fail（C1），Lean=pass。规则为 RV-2026.2，日期为 20261122。
- 32 名玩家众数动作全部为 claude。众数概率为 0.0507–0.0940。模态熵为 0.0 比特。
- claude 种类共 21 条，全部属于 Anthropic。其余 31 名玩家从未做过该动作。472/751 条动作 semantic_kind 为 unknown。
- horizon 上限为 55 轮。--horizon 60 被截断为 55 轮，生成 55 轮预测。S0 有 55 轮。
- chain_state 与 S6 季末在 7 名玩家上不一致。META 链式金币为 -18，实际为 50。NVDA 链式为 73 血 / 40 金，实际为 37 血 / 55 金。7 人正好是 S0 季末与 S1 冻结开局断裂的 7 人。
- 校准温度 11.55 拟合于旧 558 条 trace。拟合窗口为 S1–S3，日期为 2026-11-21。当前 trace 为 751 条。
- 以上三处缺陷（horizon 上限、跨季串联、旧校准）未在本轮修。修好后才可重新生成预测。属于 Phase 4。

### 2.3 S6 结束日期修正（data.json、三处页面数据、raw trace、v4 trace）

- data.json 的 S6 end 由「2026 年 11 月」改为「2026 年 11 月 30 日」。值来自 data.json 的 S6 1-1 轮日期「2026 年 11 月 22–30 日」。转换器没有算错。月份写法映射为当月 1 日是转换器的既有语义。修 parse_cn_date 会改动全部赛季与轮次日期的语义，没有改。
- 修正属于已核实的错误纠正（结束日期早于开始日期不可能成立）、可逆、有完整记录（本报告与提交信息）。符合第十六节直接执行的条件。
- 重新生成 raw trace 与 v4 trace。season_dates.S6 现为 [20261122, 20261130]。provenance 的来源哈希与新 data.json 一致（3478f59a…）。动作、赛季状态、排名与旧 trace 逐项相同。v4 trace 新哈希为 0c938073…。
- 另修一处自引用：Phase 1 工人最初在标注里写了旧 trace 的两个哈希值。哈希值在数据文件里会随下一次改动过期。已删掉这两个字段。标注只保留路径、日期、数量、原因。

### 2.4 运行层修复（run.sh、daily_run.sh、predict.py）

- run.sh 的 mtime 守卫改按内容哈希判断。生成 Trace.lean 之前，对 lean/Verification/ 下全部 Lean 源文件做 SHA-256 快照，存入运行目录的 source-hashes-before.txt。守卫先检查 .olean 文件是否存在，缺失仍报错。然后对每个依赖源文件比较生成前后内容哈希。只有源文件内容变了、且 .olean 比该源文件旧时，才判定为空构建。依赖关系按实际 import 填写。守卫报错同时写入三处：标准错误、运行目录的 lean-build.log、运行目录新建的 lean-guard.log。
- 运行 ID 改为日期_时分秒-进程号-随机数，例如 2026-11-24_155316-4592-16914。
- 新增 RUN_DIR_FILE 环境变量支持。调用方设置该变量时，run.sh 在创建运行目录后立即把目录路径写入该文件。
- predict.py 的 reverify() 增加 finally 分支。tmp 非空时调用 shutil.rmtree(tmp, ignore_errors=True)。成功、失败、异常三种路径都执行删除。
- daily_run.sh 的工作目录改为 $DATE-进程号-随机数。同一天两次运行不再共享 candidate-trace.json 与 recomputed-trace.json。删除 before-run 标记文件与 find runs -newer before-run 推断逻辑。调用 run.sh 时传入 RUN_DIR_FILE，事后直接读取该文件得到 RUN_DIR。文件缺失时记一条 WARNING 日志，RUN_ID 回落为 none。
- 没有改退出码聚合逻辑与发布门控。classify.py 退出码被忽略是设计行为，没有改。

### 2.5 集成预测语义修复（ensemble.py）

- 候选动作改用 predict.kind_of 构造。kind_of 读 semantic_kind，缺失时回落到 action_kind。与 predict.py:172、backtest.py:114、fit.py:312 一致。候选集排除 unknown。起始动作改用 predict.kind_of 构造。make_expectation 补传 global_mean。
- 只改 ensemble.py 的 setup 函数。11 行新增，4 行删除。predict.py、backtest.py、fit.py、check.py、gate.py 未动。成员权重未动。效用函数版本未动。
- 验证：fixture 上修前修后输出逐字节相同（成员 15 名，玩家 18 名，mean_entropy_norm 0.131694，mean_modal_share 0.833333，收敛 15/15）。真实 trace 上修前 416 次查找中 288 次回落为 (0.0, 0.0)，占 69.2%。修后 928 次查找中 0 次回落。修前众数动作为 r1（31 名玩家）。修后众数动作为 claude（32 名玩家）。ensemble.py 不在生产管道中运行。全仓库无 import ensemble。改动只影响 ensemble 本身。
- 其余五项语义差异只记文档，未改代码。文档在 design/semantic-deltas-note.md。每项写清位置、现状、为什么本轮不改（改动会改变已测量的结果，需 Phase 4 对照实验定夺）。五项是：拟合窗口、排名并列、杠杆惩罚扣减次数、horizon 上限、hp_bounds 初始值 (100, 0)。

### 2.6 仓库卫生与文档（README、STATUS、.gitignore、新入库文件）

- rebuild_monthly.py 修到 751 条。第 4 行文档 643 条改为 751 条。第 12 行 S6 1-1 轮 1 条改为 3 条。第 786 行内嵌核算文本 749 条改为 751 条，并补齐黄仁勋复任与 Megaspeed 的分立原因与两轮标签。断言改为 751 条。文档加注：本脚本为一次性迁移脚本，2026-11-23 已跑，当前轮次代码已是按月代码，重跑会失败。原始 643 条输入未进仓库。
- gen_board_data.py 硬编码绝对路径改为从仓库位置推导工作区根目录。另清一处绝对路径。断言与打印 749 条改为 751 条。S6 季末不再比旧快照。快照改为结转语义：S0 专属玩家在后续赛季快照里冻结为 S0 季末值。步骤 1 与步骤 4 改为可重复跑。
- check_consistency.py 的 749 条改为 751 条。快照校验改为结转语义，与线上棋盘一致。
- gpt1-to-2022-events-2018-2019.json 的玩家代码 USG 改为 USGOV 一处。USG 不是玩家，USGOV 才是。
- design/testset-coverage-plan.md 顶部加标注。它是 v6 时代的历史设计记录，框架已过时，仍是 v7 的设计依据。
- .gitignore 加 *.bak。加两份模块化 Lean 生成物（ProofsByPlayer.lean、ProofsBySeason.lean）。定夺理由：文件头注明机器生成，勿手改。run.sh --modular 可重建。默认运行会删除它们，入库会在每次默认运行产生多余删除 diff。无任何已入库文件引用它们。Trace.lean 是已入库的规范生成物，模块化文件只是可选附加模块。
- 两份 .bak 文件移到 /tmp/phase1-backup/。文件未删除，未进仓库。/tmp 重启会丢。如需长期保存，须移到持久位置。
- README 新增当前状态一节（751 条、32 名玩家、94 轮、页面 v13、2026-11-24 三项决定、最新运行总体 pass）。558 条改为 751 条共 3 处。玩家 18 名改为 32 名。C1 计数公式改为当前值。C2 血量 0–100 改为 0–140。C8 名单改为按赛季名单。抽取示例页面版本 v5 改为 v13。
- STATUS 置顶当前状态一节。删掉两处已证伪表述：traces/ 为空改为已抽取 751 条，页面 v6 改为 v13。
- 本次提交含 12 个修改文件与 9 个新文件。rebuild_monthly_report.json 仍是 749 时代旧报告，不在入库清单内，未更新，未删除，仍为未跟踪文件。

### 2.7 题集分支合并

- loop/vision-1-testset-complete 已变基到最新 main。变基干净完成，无冲突。分支提交现为 8fa382a、fd4e4e9（原题集提交 34881fa 的重播）、aab94af（meta.note 修复）。
- testset-v7.json 的 meta.note 由「Trace stays 558 moves.」改为「Trace stays 751 moves.」。testset-v7.json 完好：215 道题，43 个种类，分集 A 108、B 107，q_id 为 0–215 缺 q79。
- 分支已推送（forced update 34881fa...aab94af）。已合并进 main，合并提交 48f911d。合并后 data.json md5 不变（88a764b4…）。题集文件现已在 main 里。
- 第 11 轮分支 loop/vision-1-round11-baseline 已推送（新分支）。增益口径说明文件 design/round11-gain-caliber-note-2026-11-24.md 已在该分支提交 263e1a5。历史报告原文未动。分数未动。该分支仍未合 main。

## 3. 验证结果与证据

### 3.1 验收标准核对（Phase 0 第 7.1 节）

| 验收项 | 结果 |
|---|---|
| S6 监控 check 命令退出码 0 | 通过。运行两次，两次输出逐字相同。check ok: {'candidates': 4, 'missed_s5': 6, 'kind_gap': 11, 'new_player': 1, 'rejected': 41}。 |
| data.json 不再含有 fixture 预测 | 通过。forecast 块改为 status=none 标注。回放页渲染「当前无预测」。 |
| 同一条未变的 trace 连续跑两次 ./run.sh --modular，两次 overall 均为 pass | 通过。最终 trace 上两次运行 2026-11-24_155316-4592-16914 与 2026-11-24_155205-4402-18896 均为 pass。两次均无 lean-guard.log。 |
| 跑一次 predict，/tmp 无残留目录 | 通过。新代码跑一次后 /tmp 无新增 predict-lean-* 目录。当前 /tmp 有 0 个该目录。 |
| 两次并行运行不互相覆盖 | 通过。同一秒内启动两次 ./run.sh --modular，得到两个不同目录，两次退出码均为 0，overall 均为 pass，各自合并报告完整。 |
| rebuild_monthly.py 能复现当前 data.json | 部分通过。S0 一半完整复算通过。55 轮 106 条逐条与当前 data.json 一致。S0 季末一致。内嵌核算文本与 meta.accounting 逐字相等。完整重跑失败：第 561 行 KeyError '1-1'。原始 643 条输入未进仓库，无任何副本。完整重执行复现已不可能。见第 5 节。 |
| 关键文件已入库 | 通过。提交 2f73d8c 含 12 个修改文件与 9 个新文件。题集分支合并提交 48f911d。 |
| README 与 STATUS 与实际状态一致 | 通过。README 全文 558 出现 0 次。STATUS 残留 558 只在注明历史的 2026-11-21 各节与 fixture 行。749 只剩联邦公报页码 91 FR 74970 一处。 |
| check.py pass，Lean 构建退出码 0，0 sorry | 通过。两次运行 coverage：moves_checked 751，players_checked 32，seasons_checked 7，rankings_checked 139，invariants 12，sampled false，complete true。Lean 构建 14 个任务与 11 个任务全部成功。 |
| 三处页面数据 md5 仍一致，S5 季末与 S6 季末不变 | 通过。三份 data.json md5 相同。check_consistency.py 全部通过：棋盘 94 轮 751 条，快照与开局一致，S5/S6 季末值正确。 |

### 3.2 各路验证摘要

- 监控：导入验证通过（PLAYERS 32，KINDS 43，TESTSET_N 215，S6_START_DATE 20261122，下标 31 映射 ACM，下标 18 映射 KIMI）。去重验证通过（4 道候选全部判为非重复，合成真重复可检出）。分类验证通过（有效 S6 事件进 candidates，未知种类进 kind_gap，未知玩家进 new_player，日期 20261121 进 missed_s5，日期 20261122 进 candidates）。异目录验证通过（从 /tmp 运行 check 退出码 0）。
- 运行层：守卫四种情形隔离测试全部符合预期（内容不变且 .olean 旧，通过；内容变了且 .olean 旧，失败且写 lean-guard.log；内容变了且 .olean 已重建，通过；.olean 缺失，失败且写 lean-guard.log）。RUN_DIR_FILE 管道验证通过（写入路径与报告实际路径完全一致）。daily_run.sh 全文已无 find -newer 与 before-run。三个文件语法检查全部通过（bash -n 与 py_compile）。
- 集成预测：fixture 修前修后输出逐字节相同。真实 trace 修前修后期望回落 288/416 → 0/928。run.sh 全文无 ensemble，全仓库无 import ensemble。
- 仓库卫生：gen_board_data.py 在 /tmp 副本连续跑两次，两次退出码均为 0，两次输出棋盘均与线上棋盘逐字节一致。check_consistency.py 只读运行全部通过。三个脚本 py_compile 通过。git check-ignore 确认两份模块化 Lean 文件被忽略。

## 4. Phase 0 订正

- Phase 0 报告第 3.6 节第二项的表述已订正。原文称 ensemble.py 在真实 trace 上期望查找「全部落空，回落为 (0.0, 0.0)」。Phase 1 实测：修前 416 次查找中 288 次回落，占 69.2%。128 次命中真实均值，占 30.8%。原因是 4 个 action_kind 取值（r1、huang_resign、anthropic_ipo、sec_probe）恰好与 semantic_kind 同名。机制（键错位）证实，「全部」的量词是错的。修后 928 次查找中 0 次回落。订正已追加写入 Phase 0 报告末尾。
- 另一项订正：2026-11-21 的 ensemble 存档报告不能用当前代码复现。存档值 0.108003、0.866667、收敛 13/15。本次修前重跑值 0.131694、0.833333、收敛 15/15。原因是 predict.py 在 11-21 11:55 运行后又提交第 3、4、6、9 轮改动。ensemble.py 与 fixture 文件自基线提交后未变。修前修后比较用同一份输入，比较本身不受影响。
- 第 11 轮增益口径差异已书面记录。脚本输出 G_audited = 3.67。报告标题写 G = +5.33。脚本只对实验组做泄题排除，对照组用原始均值 94.00。报告用两组审计后均值相减（97.67 − 92.33）。差值 1.67 等于对照组审计调整量（94.00 − 92.33）。两个数都对，口径不同。结论不受影响：两个数都小于噪声带 11。角色扮演继续标为「暂定进基线」。

## 5. 未解决事项

- rebuild_monthly.py 不能完整重跑复现当前 data.json。原始 643 条输入未进仓库，无任何副本。git 历史只有 558 条与 751 条两个版本。space-versions v11 与 v12 为 558 条。.space-build 为 751 条。修好的数字与核算文本已与当前 data.json 一致，但完整重执行复现已不可能。须定夺：把脚本标为历史产物，或重建输入。
- rebuild_monthly_report.json 仍是 749 时代旧报告。未更新，未删除，仍为未跟踪文件。
- testset-v7.json 的 meta.removed_q79 仍写 trace stays 558 moves。它是 2026-11-22 的删除历史记录。当时 trace 确为 558 条。本轮只改 meta.note，未动该历史记录。须定夺是否加注。
- rules/payoff-model.json 的 players 列表仍为 18 条。属模型文件本身的口径，不在本轮范围。残留漂移，待 Phase 4 处理。
- predict.py 的三处缺陷未修：horizon 上限取单季最大轮数（55 轮）、chain_state 跨季串联、校准拟合于旧 trace。修好后才可重新生成预测。属于 Phase 4。
- 五项语义差异只记文档，未改代码。统一口径需 Phase 4 对照实验定夺。文档在 design/semantic-deltas-note.md。
- hp_bounds (100, 0) 的倒置初始值仍在 backtest.py 中。实测在真实 trace 上没有被实际使用（94 个不同日期全部解析到基础规则）。改动前应先补一个无基础规则 trace 的测试用例。
- daily_run.sh 全流程没有端到端跑过。通过路径会把重算 trace 写入 trace-latest.json。只验证了 RUN_DIR_FILE 管道本身与代码。完整 daily 流程仍需在真实事件日验证。
- 并行运行仍共享 lean/Verification/*.lean 与 lean/.lake。仓库仍无任何锁机制。目录唯一性已修，并行构建竞争本身不在本轮范围。
- 棋盘新建预测表单仍用普通字符串哈希。文字已改诚实，但哈希本身仍不防篡改。改实现不在本轮范围。
- 两份 .bak 文件现存在 /tmp/phase1-backup/。/tmp 重启会丢。如需长期保存，须移到持久位置。
- 140 道目标仍待 Gu 重定。gap_to_140 已标记为旧目标口径待重定。数值 −75 如实计算。未擅自定新目标。
- S6 池现 4 道候选，距 30 道复测门槛仍远。第 12 轮方向未定。

## 6. 下一阶段计划（Phase 2：真实预测账本）

- 目标：建立可信预测闭环。预测账本、证据快照、独立结算、实时评分。
- 第一步：设计追加式预测账本。字段按任务文档第 6.1 节：forecast_id、命题、类型、参与者、创建时间、信息截止时间、结算截止时间、概率、结算标准、证据快照、推理摘要、假设、反证据、模型版本、方法版本、规则版本、世界状态版本、状态。预测发布后不得直接覆盖原始内容。新版本追加，旧版本保留并关联。
- 第二步：把 4 条角色扮演 S6 预测迁入账本。保留原始时间 2026-11-22、概率、哈希。FC-01 的结算记录一并迁入：命中，Brier 0.16，证据为 BIS 最终规则联邦纪事文件号 2026-23999。结算记录与预测记录分开存放。结算者与预测者分离。
- 第三步：建立评分脚本。账本读入，输出 Brier 分、校准度、与简单基线（随机、历史频率、按玩家历史频率）的对比。评分只读账本，不改账本。
- 第四步：改棋盘结算流程（只改本地源文件）。账本条目在页面上只读。结算状态来自账本文件，不来自 localStorage。用户新增预测走单独的本地通道，与账本条目明确区分，不得混入同一列表。
- 在 predict.py 的三处缺陷修好之前，不生成新的模型预测。账本先记录已有的 4 条预测与后续角色扮演预测。
- Phase 2 完成后写 Phase 2 报告，汇报改了什么、验证结果、证据、未解决事项、下一阶段计划。再启动 Phase 3。
