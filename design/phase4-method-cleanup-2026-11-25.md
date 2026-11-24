# Phase 4 方法文件清理记录

- 日期：2026-11-25
- 执行员：Phase 4 方法文件清理执行员
- 依据：`design/phase4-control-experiment-protocol-2026-11-25.md` 第 11 节（泄漏审计）与第 12 节（替换方案）、第 12.10 节（协调表处理）
- 范围：只替换 41 处泄漏例题。只处理第 12.10 节的 6 个协调表文件。不改题集。不改账本。不改冻结赛季。不改结算口径。不提交 git。
- 写作风格：ASD-STE100。短句。一句一个意思。术语全文一致。主动语态。不用俚语成语比喻。

## 1. 替换结果总览

- 41 处替换全部执行。41 处原文位置全部找到。41 处原文与协议第 11 节描述一致。无未找到项。无与协议不符项。
- 替换文本全部按协议第 12 节逐字采用。替换文本全部保留「（纯属构造）」标记。替换文本不含协议里的「[替换A1]」类编号。
- 文件 G 的总览表改写不带「（纯属构造）」标记。表改写本身就是替换。协议第 12.8 节的 G1 文本是改写说明，不是表内文字。

| 文件 | 替换数 | 状态 |
|---|---|---|
| A `method-vision6-datacenter-capex-boundary.md`（round11） | A1–A4，共 4 处 | 4 处全部已替换并复核通过 |
| B `method-vision6-forward-guidance-steps.md`（round11） | B1–B10，共 10 处 | 10 处全部已替换并复核通过 |
| C `method-roleplay.md`（round11） | C1–C3，共 3 处 | 3 处全部已替换并复核通过 |
| D `method-vision6-overseas-leasing-weight.md`（round10） | D1–D2，共 2 处 | 2 处全部已替换并复核通过 |
| E `kind-boundary-rules.md`（round10） | E1–E3，共 3 处 | 3 处全部已替换并复核通过 |
| F `search-boundary-tightened.md`（round11） | F1–F5，共 5 处 | 5 处全部已替换并复核通过 |
| G `roleplay-pilot-test-scenarios.md`（roleplay-pilot） | G1，共 1 处 | 1 处已替换并复核通过 |
| H `semantic-kinds.md`（verification） | H1–H13，共 13 处 | 13 处全部已替换并复核通过 |
| 合计 | 41 处 | 41 处全部已替换 |

## 2. 逐项状态

### 文件 A（4 处）

- A1：已替换。原文「q30，BYTE，数据中心（S4 1-2）。先兆：火山引擎宣布自有园区计划」已删除。替换为北极光算力绿谷园区虚构例题。
- A2：已替换。原文「q31，META，数据中心（S4 1-2）。先兆：宣布曼哈顿规模园区计划」已删除。替换为云杉智能蓝港园区虚构例题。
- A3：已替换。原文「q32，ALI，数据中心（S5 4-1）。事件：广州首个真武国产万卡智算集群投产运营，计划扩至 10 万卡」已删除。替换为青石网络白山集群虚构例题。
- A4：已替换。原文反例块「q10–q19」与 q19 的「Q3 现金资本开支 759 亿美元」与 q14 的「115→140→190→200 亿美元三连涨」已删除。替换为两道虚构题反例。

### 文件 B（10 处）

- B1：已替换。原文 q10 例题块已删除。替换为红杉云虚构例题。
- B2：已替换。原文 q11 例题块已删除。替换为蓝鲸云虚构例题。
- B3：已替换。原文 q12 例题块已删除。替换为绿谷科技虚构例题。
- B4：已替换。原文 q13 例题块已删除。替换为白塔智能虚构例题。
- B5：已替换。原文 q14 例题块已删除。替换为晨光半导体虚构例题。
- B6：已替换。原文 q15 例题块已删除。替换为海星模型虚构例题。
- B7：已替换。原文 q16 例题块（含两场电话会管理层原话）已删除。替换为磐石科技虚构例题。
- B8：已替换。原文 q17 例题块已删除。替换为清泉能源虚构例题。
- B9：已替换。原文 q18 例题块已删除。替换为长风资本虚构例题。
- B10：已替换。原文 q19 例题块已删除。替换为云杉智能虚构例题。

### 文件 C（3 处）

- C1：已替换。原文第 2 步例子（q10，亚马逊 CFO）与第 3 步「指向 capex」句与第 4 步「比如 q10：命题 2024-03-31 前亚马逊在财报中确认 2024 年资本开支将上升」已删除。替换为雪松数据虚构例子与虚构命题。
- C2：已替换。原文注意事项里的「（E1 q30：预测员明知界限规则第 5 步禁令，仍凭角色扮演猜数据中心且猜中。）」已删除。替换为虚构情形注意事项。
- C3：已替换。原文第 4 步「（E2 q70：种类猜 r1，命题却写亚马逊在 Bedrock 上线 Nova Premier。）」句已删除。替换为虚构情形注意事项。

### 文件 D（2 处）

- D1：已替换。原文 q67 例题块（含 q7 注释）已删除。替换为蓝鲸云虚构例题。
- D2：已替换。原文更正记录整条（含「只对 q7（S5 5-1，轮次 11-18）有效」）已删除。替换为虚构更正记录。

### 文件 E（3 处）

- E1：已替换。原文「Grok 4 发布 = spacex_xai，不是 colossus」已删除。替换为虚构模型「海星 4」边界。
- E2：已替换。原文「文心 4.5 开源 = wenxin，不是 open_source」已删除。替换为虚构产品「晨光 4.5」边界。
- E3：已替换。原文「盘古 5.5 = pangu，不是 ascend」已删除。替换为虚构模型「磐石 5.5」边界。

### 文件 F（5 处，加过期写法删除）

- F1：已替换。原文「Meta Q4 2023 资本开支」已删除。替换为「红杉云第四季度资本开支」。
- F2：已替换。原文「BIS 远程规则 2026 年 11 月」已删除。替换为「蓝港出口管制规则 2026 年」。
- F3：已替换。原文「DeepSeek V3 2024 年 12 月」已删除。替换为「海星模型第三代 2024 年」。
- F4：已替换。原文「字节 700 亿美元资本开支」已删除。替换为「磐石科技 600 亿元资本开支」。
- F5：已替换。原文「SEC 查英伟达会计」已删除。替换为「证监会查清泉能源会计」。
- 过期写法已删除。第 1 节「第 13 题事件 10 月 30 日、轮次 12 月 1 日；」已删除。其余句子一字未动。

### 文件 G（1 处）

- G1：已替换。场景总览表只留三栏：轮次（按时间顺序）、题号、决策者角色。玩家栏已删除。种类栏已删除。原型预测类别栏已删除。轮次日期栏已删除。10 道试点题的题号与决策者角色不变。

### 文件 H（13 处）

- H1：已替换。规则 1 命中 move 单元格整格已替换为虚构动作「虚构公司灯塔算力收到 SEC 问询函。股价下跌」。
- H2：已替换。规则 2 命中 move 单元格整格已替换为虚构动作「虚构公司星野科技首席执行官辞职。股价下跌」。
- H3：已替换。规则 10 单元格内引文「豆包多模态跟进。价格再降」已替换为虚构引文「虚构公司竹影数据新品上线。价格再降」。其余 3 条引文未动。
- H4：已替换。规则 11 单元格内引文「阿里海外云节点受远程规则关注」已替换为虚构引文「虚构公司松涛科技海外节点适用远程规则限制」。其余 3 条引文未动。
- H5：已替换。规则 12 单元格内 5 条泄漏引文已替换为 5 条虚构引文：「9009 亿美元承诺签字方」→「4200 亿元承诺签字方」；「IPO 进程启动」→「IPO 申请已递交」；「分阶段募资到手」→「分阶段募资到手」（纯属构造，文本与原前缀相同）；「上市次日跌 8.5%」→「上市次日跌 6.2%」；「募资已到账」→「募资已到账」（纯属构造，文本与原前缀相同）。其余 3 条引文未动。注意：q2 与 q4 的题集动作字段比引文更长。引文只是动作前缀。全文扫描确认无全文重合。见第 6 节。
- H6：已替换。规则 14 单元格内引文「GPT-4 接入 Bing 和 Office」已替换为虚构引文「虚构公司雾凇云 GPT-4 已上线客服系统」。其余 2 条引文未动。
- H7：已替换。规则 15 单元格内引文「抢租海外算力报道的主角之一」已替换为虚构引文「虚构公司青石网络海外算力租赁订单激增」。其余 1 条引文未动。
- H8：已替换。规则 16 注文内引文「通义新版发布。阿里云打包 B200 替代方案」已替换为虚构引文「虚构公司雪松数据新版发布。云平台打包芯片替代方案」。其余注文未动。
- H9：已替换。规则 24 单元格内引文「Bard 演示出错。市值蒸发」已替换为虚构引文「虚构公司灯塔算力 Bard 演示故障。股价下跌」。其余内容未动。
- H10：已替换。规则 25 命中 move 单元格整格已替换为虚构动作「虚构公司星野科技的 Megaspeed 渠道影响供应链声誉。官方否认相关说法」。例外说明见第 6 节。
- H11：已替换。规则 26 单元格内 2 条泄漏引文已替换：「三哩岛核电合同。保电力」→「虚构公司清泉能源签核电重启合同。保障供电」；「自建燃气电厂抢时间」→「虚构公司雾凇云自建燃气电厂抢工期」。其余 8 条引文未动。
- H12：已替换。规则 27 单元格内 2 条泄漏引文已替换：「约 380 亿美元债务包挂单」→「虚构公司丹青智能 410 亿美元债务债券挂单未售」；「债务融资继续加码」→「虚构公司红枫科技债务融资规模继续扩大」。其余引文未动。
- H13：已替换。规则 28 单元格内引文「资本开支再上调」已替换为虚构引文「虚构公司绿谷科技资本开支继续上调」。其余内容未动。

## 3. 八个文件改动行数

改前行数与改后行数以 `wc -l` 计。改动行数以旧副本对照 `diff` 计（旧副本 md5 与改前 canonical 文件相同）。

| 文件 | 改前行数 | 改后行数 | 行数变化 | diff 改动行（删 + 增） |
|---|---|---|---|---|
| A | 82 | 64 | −18 | 26（删 22，增 4） |
| B | 238 | 157 | −81 | 119（删 100，增 19） |
| C | 79 | 79 | 0 | 12（删 6，增 6） |
| D | 96 | 79 | −17 | 21（删 19，增 2） |
| E | 45 | 45 | 0 | 6（删 3，增 3） |
| F | 51 | 51 | 0 | 8（删 4，增 4） |
| G | 77 | 77 | 0 | 表改写：7 栏 → 3 栏，10 行 |
| H | 434 | 434 | 0 | 26（删 13，增 13） |

- 文件 G 无 md5 相同的旧副本。表改写以行内栏位计。行数不变。
- 「（纯属构造）」标记出现次数：A 4 次，B 10 次，C 3 次，D 2 次，E 3 次，F 5 次，G 0 次（表改写无标记），H 19 次（13 处替换，多引文单元格每条虚构引文各带一个标记）。合计 46 次标记，对应 41 处替换。

## 4. 协调表处理结果（第 12.10 节）

- 6 个文件全部处理完成。处理方式：只删除种类栏。轮次、轮次日期、题号全部保留。题号旁的预测点日期保留在题号栏内（如 q15（20261119））。
- `verification-v1-round6/design/predictor-plan-vision6-round6.md`：分发表表头「题号（种类 / 玩家）」改为「题号」。11 行全部删除种类与玩家。完成。
- `verification-v1-round7/design/predictor-plan-vision7-round7.md`：分发表表头改为「题号」。4 行全部删除种类与玩家。完成。
- `verification-v1-round9/design/predictor-plan-vision9-round9.md`：分发表表头改为「题号」。6 行全部删除种类与玩家。完成。
- `verification-v1-round10/design/predictor-plan-vision10-round10.md`：分发表表头改为「题号」。16 行全部删除种类与玩家。角色表表头「题号 | 玩家 | 种类 | 扮演的决策者」改为「题号 | 玩家 | 扮演的决策者」。32 行全部删除种类栏。完成。
- `verification-v1-round6/design/experiment-vision6-round6.md`：焦点类别表删除种类栏，只留题数与 v5 题号。合计行保留为「合计 26 | A 集 13 道，B 集 13 道」。日期违规表删除种类栏，只留题号、玩家、晚了多少天。23 行全部删除种类栏。完成。
- `verification-v1-roleplay-pilot/design/roleplay-pilot-design.md`：分类表删除种类栏与题号栏，只留原型预测类别与题数。4 行加合计行全部处理。完成。
- 表格分隔行已同步栏数。全部 6 个文件复核：表内无「q数字（种类 / 玩家）」写法。表头无种类栏。
- 6 个文件行数不变。改动只在表内栏位。

## 5. 封存的旧副本清单

- 以下旧副本全部未改写。以下旧副本全部未删除。以下旧副本全部含泄漏例题。以下旧副本是历史记录。以下旧副本不得再发给预测员。
- 清单按文件名分组。md5 为清理执行时的实测值。canonical 文件不在本清单内。

### kind-boundary-rules.md（旧副本 10 个）

- `/home/hatch/workspace/verification-v1-baseline88/design/kind-boundary-rules.md` — md5 `60d44603c3878ded7ec54538ef2c0427`
- `/home/hatch/workspace/verification-v1-roleplay-pilot/design/kind-boundary-rules.md` — md5 `60d44603c3878ded7ec54538ef2c0427`
- `/home/hatch/workspace/verification-v1-round6/design/kind-boundary-rules.md` — md5 `60d44603c3878ded7ec54538ef2c0427`
- `/home/hatch/workspace/verification-v1-round7/design/kind-boundary-rules.md` — md5 `60d44603c3878ded7ec54538ef2c0427`
- `/home/hatch/workspace/verification-v1-round8/design/kind-boundary-rules.md` — md5 `60d44603c3878ded7ec54538ef2c0427`
- `/home/hatch/workspace/verification-v1-round9/design/kind-boundary-rules.md` — md5 `60d44603c3878ded7ec54538ef2c0427`
- `/home/hatch/workspace/verification-v1-s5patch/design/kind-boundary-rules.md` — md5 `60d44603c3878ded7ec54538ef2c0427`
- `/home/hatch/workspace/verification-v1-testset/design/kind-boundary-rules.md` — md5 `60d44603c3878ded7ec54538ef2c0427`
- `/home/hatch/workspace/verification-v1-walkforward/design/kind-boundary-rules.md` — md5 `509cbd3601a18d9dd383266ef164d0d9`
- `/home/hatch/workspace/verification-v1-weakest-link/design/kind-boundary-rules.md` — md5 `60d44603c3878ded7ec54538ef2c0427`

### method-roleplay.md（旧副本 3 个）

- `/home/hatch/workspace/verification-v1-roleplay-pilot/design/method-roleplay.md` — md5 `bd11ebf729d3d02817975289440a20b9`
- `/home/hatch/workspace/verification-v1-round10/design/method-roleplay.md` — md5 `c226b5d49903331536852924f134da6d`
- `/home/hatch/workspace/verification-v1-round9/design/method-roleplay.md` — md5 `f16a2c80a861719cd1d37bb00f609330`

### method-vision6-datacenter-capex-boundary.md（旧副本 6 个）

- `/home/hatch/workspace/verification-v1-roleplay-pilot/design/method-vision6-datacenter-capex-boundary.md` — md5 `146944240b54bbca872f7d2cf96e0a29`
- `/home/hatch/workspace/verification-v1-round10/design/method-vision6-datacenter-capex-boundary.md` — md5 `146944240b54bbca872f7d2cf96e0a29`
- `/home/hatch/workspace/verification-v1-round6/design/method-vision6-datacenter-capex-boundary.md` — md5 `146944240b54bbca872f7d2cf96e0a29`
- `/home/hatch/workspace/verification-v1-round7/design/method-vision6-datacenter-capex-boundary.md` — md5 `146944240b54bbca872f7d2cf96e0a29`
- `/home/hatch/workspace/verification-v1-round8/design/method-vision6-datacenter-capex-boundary.md` — md5 `146944240b54bbca872f7d2cf96e0a29`
- `/home/hatch/workspace/verification-v1-round9/design/method-vision6-datacenter-capex-boundary.md` — md5 `146944240b54bbca872f7d2cf96e0a29`

### method-vision6-forward-guidance-steps.md（旧副本 6 个）

- `/home/hatch/workspace/verification-v1-roleplay-pilot/design/method-vision6-forward-guidance-steps.md` — md5 `8e46f611bac0e6d62db0442ea3f9863e`
- `/home/hatch/workspace/verification-v1-round10/design/method-vision6-forward-guidance-steps.md` — md5 `10ed4c00193482c832ff81ccabf3ace7`
- `/home/hatch/workspace/verification-v1-round6/design/method-vision6-forward-guidance-steps.md` — md5 `8e46f611bac0e6d62db0442ea3f9863e`
- `/home/hatch/workspace/verification-v1-round7/design/method-vision6-forward-guidance-steps.md` — md5 `8e46f611bac0e6d62db0442ea3f9863e`
- `/home/hatch/workspace/verification-v1-round8/design/method-vision6-forward-guidance-steps.md` — md5 `79d29deafd3696971d30c4453c2657d4`
- `/home/hatch/workspace/verification-v1-round9/design/method-vision6-forward-guidance-steps.md` — md5 `10ed4c00193482c832ff81ccabf3ace7`

### method-vision6-overseas-leasing-weight.md（旧副本 5 个）

- `/home/hatch/workspace/verification-v1-roleplay-pilot/design/method-vision6-overseas-leasing-weight.md` — md5 `a0572041ad973007669a6d3e6677d782`
- `/home/hatch/workspace/verification-v1-round6/design/method-vision6-overseas-leasing-weight.md` — md5 `a0572041ad973007669a6d3e6677d782`
- `/home/hatch/workspace/verification-v1-round7/design/method-vision6-overseas-leasing-weight.md` — md5 `a0572041ad973007669a6d3e6677d782`
- `/home/hatch/workspace/verification-v1-round8/design/method-vision6-overseas-leasing-weight.md` — md5 `a0572041ad973007669a6d3e6677d782`
- `/home/hatch/workspace/verification-v1-round9/design/method-vision6-overseas-leasing-weight.md` — md5 `a0572041ad973007669a6d3e6677d782`

### roleplay-pilot-test-scenarios.md（旧副本 0 个）


### search-boundary-tightened.md（旧副本 3 个）

- `/home/hatch/workspace/verification-v1-roleplay-pilot/design/search-boundary-tightened.md` — md5 `d780ed4bb00a0449fdc209eb1b63d161`
- `/home/hatch/workspace/verification-v1-round10/design/search-boundary-tightened.md` — md5 `d780ed4bb00a0449fdc209eb1b63d161`
- `/home/hatch/workspace/verification-v1-weakest-link/design/search-boundary-tightened.md` — md5 `d780ed4bb00a0449fdc209eb1b63d161`

### semantic-kinds.md（旧副本 27 个）

- `/home/hatch/workspace/verification-nn/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-r2-agent/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-r2-composite/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-r2-search/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-r3-boring/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-r3-theme/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-r3-thin/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-r4-capex/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-r4-exception/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-r4-project/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-r5-date/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-r5-sample/design/semantic-kinds.md` — md5 `23f058d2a89aba4c38f9388e520012d8`
- `/home/hatch/workspace/verification-r5-thin/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-baseline88/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-guidance/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-roleplay-pilot/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-round10/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-round11/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-round6/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-round7/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-round8/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-round9/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-s5patch/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-testset-complete/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-testset/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-walkforward/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`
- `/home/hatch/workspace/verification-v1-weakest-link/design/semantic-kinds.md` — md5 `dddf8750f210fe229372c7cb5113dde5`

旧副本合计 60 个。

## 6. 扫描脚本与扫描结果

- 扫描脚本路径：`/tmp/phase4-cleanup-scan.py`。脚本不在仓库内。脚本可复现。脚本读 `~/workspace/verification/testset-v7.json`（215 道，43 种）。
- 扫描分四部分。Part 1：215 道题的事件名与动作字段全文作子串扫描。Part 2：同行内题号加种类指认扫描。种类 token 包括种类 slug 与种类中文特征词。Part 3：替换文本本身内的真实公司名扫描。只扫插入的替换文本，不扫同行未动的原文。Part 4：8 个文件内剩余题号清单。

| 部分 | 扫描内容 | 命中数 | 结论 |
|---|---|---|---|
| Part 1 | 事件名与动作字段全文 | 0 | 通过 |
| Part 2 | 同行题号加种类指认 | 7（5 个不同行） | 不通过，见下 |
| Part 3 | 替换文本内的真实公司名 | 0 | 通过 |
| Part 4 | 剩余题号清单 | 见第 7 节 | 清单 |

- H10 例外说明：H10 替换块与 q61 的动作字段的最长公共子串是「Megaspeed 」，即关键词本身加一个空格。与 q61 的事件名的最长公共子串是「 M」。除关键词本身外，无 8 字以上重合。例外成立。
- H5 说明：替换引文「分阶段募资到手」与「募资已到账」文本与原引文相同。原因是协议第 12.9 节的虚构动作本身就是这两个短语。q2 的动作字段是「分阶段募资到手。绿鞋后合计口径见本轮说明」。q4 的动作字段是「募资已到账。现金垫最厚」。引文只是动作前缀。Part 1 确认无全文重合。
- 复核结论：按任务的字面标准（全文扫描 0 命中），复核不通过。失败项是 Part 2 的 5 个不同行。5 行全部在 41 处范围之外。5 行全部在例题块之外。执行规则只许替换例题本身。周围正文一字不动。所以 5 行未改。失败项列在第 7 节。协调员定夺 5 行的处理方式。

## 7. 复核失败项（Part 2 的 5 个不同行）

- 失败项 1：文件 B 第 118 行。更正记录。「q10 例题原先写“Q3 电话会，CFO 说 2024 年资本开支将上升”，是错的。」题号 q10 与种类「资本开支」同行。位置在更正记录，不在例题块内。
- 失败项 2：文件 B 第 134 行。更正记录。「q19 例题原先直接写了事件数字（Q3 现金资本开支 759 亿美元）。」题号 q19 与种类「资本开支」同行。数字「759 亿美元」是 q19 事件数字的片段。位置在更正记录，不在例题块内。
- 失败项 3：文件 B 第 144 行。更正记录。「q18 例题原先写“Q1 资本开支同比涨 91%”，是错的。」题号 q18 与种类「资本开支」同行。位置在更正记录，不在例题块内。
- 失败项 4：文件 D 第 5 行。导语。「第 5 轮试跑：海外租赁 1 道题（q67，BYTE，S5 4-1），两批都是 0/1。」题号 q67 与种类「海外租赁」同行。位置在「它修什么」导语，不在例题块内。
- 失败项 5：文件 G 第 20 行。表下注释。「注意：q5 是已知的难推题（轮次之前没有先兆，BIS 规则 11 月 16 日才公布……）。」题号 q5 与「BIS」同行。q5 的种类是 bis_rule。位置在表下注释，不在总览表内。
- 其余剩余题号（Part 4 清单）不含种类指认。文件 B 第 67 行 q14、第 96–97 行 q16、第 123 行 q11、第 126 行 q12、第 128 行 q13、第 131 行 q16、第 137 行 q17 只有题号，无种类词。文件 G 总览表 10 行只有题号与决策者角色，无种类词。文件 G 第 64 行 q5 只有题号，无种类词。
- 文件 B 第 131 行另含事件数字片段「73.5 亿元」。文件 B 第 67 行另含趋势片段「115→140→190 亿美元」。两处只有题号加数字片段，无种类词。Part 1 确认两处不是事件名或动作字段全文。

## 8. 其他残留观察（不在 41 处内，未改动，提请协调员定夺）

- 观察 1：文件 E 的种类表内仍有 3 行与 E1–E3 相同的事件加种类写法。spacex_xai 行写「Grok 4 发布算 spacex_xai，不算 colossus」。wenxin 行写「文心 4.5 开源算 wenxin，不算 open_source」。pangu 行写「盘古 5.5 算 pangu，不算 ascend」。3 行无题号。3 行不是事件名或动作字段全文。机械扫描不命中。语义上仍指认答案。是否清理，由协调员定夺。
- 观察 2：文件 H 规则 11 单元格仍含引文「BIS 远程规则收紧」。该引文是 q7 动作字段「BIS 远程规则收紧。火山引擎海外单受限」的前缀。协议审计只列 H4 为 q5。引文未列入 41 处。Part 1 确认无全文重合。是否清理，由协调员定夺。
- 观察 3：文件 H 规则 10、11、12、14、15、16、24、26、27、28 单元格内仍有未泄漏的棋盘动作原文引文。审计确认这些引文不是题集原题。Part 1 确认无全文重合。引文保留原样。
- 观察 4：文件 F 的 F5 替换句含「证监会」。「证监会」是真实监管机构名，不是公司名。协议第 12.7 节原文如此。Part 3 的公司名表不含监管机构名。是否改写，由协调员定夺。
- 观察 5：文件 H 的 H1 替换句含「SEC」。「SEC」是规则 1 本身的匹配关键词。协议第 12.9 节原文如此。是否改写，由协调员定夺。
- 观察 6：文件 G 的「原型格式」一节仍写「cls 按上表“原型预测类别”一栏填」。总览表已删除原型预测类别栏。该句现无所指。是否改写，由协调员定夺。
- 观察 7：第 12.10 节的 6 个文件表外仍有种类加题号的文字映射。round10 预测员计划「按原型预测类别」一段与「资本开支 8 道」一段。round9 预测员计划「数据中心 3 道」「资本开支 10 道」一段。round6 实验设计焦点类别一段与「capex 8 道（q10, 11, …）」一段。round10 预测员计划角色表后「角色按种类定」一段。试点设计文档「按原型的 4 个预测类别分」一句。协议第 12.10 节只要求删除表里的种类栏。表外文字未动。是否清理，由协调员定夺。
- 观察 8：第 12.10 节文件的重复副本未处理。`predictor-plan-vision6-round6.md` 在 round7、round8、round9、round10、roleplay-pilot 工作区的副本仍含种类栏。`predictor-plan-vision7-round7.md` 在 round8、round9、round10 工作区的副本仍含种类栏。`predictor-plan-vision9-round9.md` 在 round10 工作区的副本仍含种类栏。`experiment-vision6-round6.md` 在 round7、round8、round9、round10、roleplay-pilot 工作区的副本仍含种类栏。任务只要求改对应轮次工作区的各一份。重复副本的 md5 见第 4 节后的核查记录：round6 计划已改本 md5 `6ed131c368acee5d4e1e89d2c3d1ace0`，其余副本 md5 `2c6f5d6ad9410ec4c0ca48ffa310a920`；round7 计划已改本 md5 `ab3013f737c6fb334d49f7d8f38f067c`，其余副本 md5 `5ff5b420bedeb6a1892e033024545eea`；round9 计划已改本 md5 `0117bbe8df95d327d8e5eef590cfb3df`，round10 副本 md5 `931894b77f9dd8b7df8a8f3f2c4fbaae`；round6 实验设计已改本 md5 `b4467c4161542da3cc76936d5b92c92a`，其余副本 md5 `dc08e3961d3f7ac5a361e3b89d349c3c`。
- 观察 9：文件 B 第 1 步 (b) 仍写「三年 3800 亿元计划、1500 亿元人民币年度计划（路透匿名信源，字节曾否认）」。该句在规则步骤内，不在例题块内。数字与 q15、q17 的事件数字相同，但不是事件名或动作字段全文。Part 1 确认无全文重合。是否清理，由协调员定夺。

## 9. 未碰的文件

- 题集 `~/workspace/verification/testset-v7.json` 未碰。data.json 未碰。预测账本 `forecasts/ledger.json` 未碰。
- 旧轮次副本全部未碰。封存清单见第 5 节。旧副本 60 个。
- 其他任何文件未碰。仓库内只有 `design/semantic-kinds.md` 被改动。git 未提交。改动留给协调员统一提交。
- artifact 工具未调用。

## 10. 执行过程记录

- 替换前逐处核对协议第 11 节原文位置。41 处原文全部找到。41 处原文全部与协议描述一致。无猜测替换。
- 替换中只改例题本身。规则步骤、判断逻辑、周围正文一字未动。例外：第 12.10 节按协议要求删除表栏。第 12.10 节的表栏删除只动表内栏位。
- 第 12.10 节表处理脚本在执行中修过 3 处脚本问题。角色表正则漏配含数字的种类（v3、r1）。实验设计焦点表分隔行被当作数据行。试点设计表正则用了半角右括号。3 处问题全部在写入前由断言拦住。已改本以断言计数复核：计划表 11、4、6、16 行，角色表 32 行，焦点表 10 行，违规表 24 行，试点分类表 4 行加合计行。表头与分隔行已同步栏数。
- 扫描脚本初版 Part 3 把整行当作替换块扫，报出 49 个命中。49 个命中全部是同行未动的原文。Part 3 已修正为只扫插入的替换文本本身。修正后 Part 3 为 0 命中。

## 11. 协调员追加清理（2026-11-25，第 5 项失败项与第 8 节观察的处理）

- 追加原因：复核 Part 2 的 5 行失败项与第 8 节的 9 项观察属于同一类泄漏（题号加种类、事件加种类）。协议第 12.1 节的复核标准是全文扫描 0 命中。复核不通过，不开跑。追加清理执行该标准本身，不是扩大范围。
- 追加清理分两批，共 30 处，全部精确替换（每处在文件里恰好命中一次），规则步骤与判断逻辑未动。
- 第一批 21 处：文件 B 规则步骤里的 q14 举例、两节更正记录整节（8 条，按题号写的答案细节全部改写为通用表述，只留教训）、第 1 步 (b) 的 3800 亿与 1500 亿数字（改写为题集里没有的 4600 亿与 5200 亿）、例题标题里的“（v5 题号）”；文件 D 导语的 q67；文件 G 表下注释的 q5 与悬空的“原型预测类别”引用；文件 E 种类表里与 E1–E3 相同的 3 行事件加种类写法（改写为与 E1–E3 相同的虚构例子）；文件 H 规则 11 单元格里 q7 动作前缀引文（改写为虚构引文）；6 个协调表文件正文里的种类加题号映射（第 7 轮计划、第 9 轮计划、第 10 轮计划、第 6 轮实验设计的子集 M、子集 Q、子集 N、增益分解、试点设计文档各 1 处）。
- 第二批 9 处：窗口扫描（前后各 1 行）新发现的跨行映射。第 6 轮实验设计的增益分解（capex 与 q16、q19 相邻、energy 与 q37 相邻）、按种类分的期望（bis_rule、megaspeed、sec_probe 各带题号）、违规分析（q7、q30、q31 带种类）；第 7 轮计划的分子样本（q16、q19）；第 9 轮与第 10 轮计划的旧注段落（q19 的 759 亿美元、q14 的 200 亿美元事件数字片段）。
- 追加清理后复核：扫描脚本 Part 1 为 0，Part 2 为 0。Part 3 仍报 4 处命中，全部是文件 E 第 26、27 行同行未动的种类定义文字（“文心产品线：文心发布、文心更新、文心开源。只认 BIDU。”“盘古模型线：盘古发布、盘古开源。只认 HUAWEI。”），扫描器按整行扫。只取本次插入的替换文本本身复核，真实公司名为 0。H 规则 11 新引文与题集全部事件名与动作字段的最长公共子串为 4 字，低于 8 字标准。
- 窗口扫描（前后各 1 行）最终剩余 2 处，均为裸题号状态说明，种类已不再挂接，留作记录：第 10 轮计划第 52 行“q7 单独报告”（相邻行只写“非 capex 24 道”，未写 q7 的种类）；第 6 轮实验设计第 84 行“q7 和 q30 有日期违规”（种类挂接在第 294–298 行，已改写为通用表述，无法对应哪道题是哪个种类）。
- 第 8 节观察的最终处理：观察 1、2、6、7、9 已清理（见上）。观察 3（非题集原题的棋盘动作引文）保留。观察 4（F5 的“证监会”）与观察 5（H1 的“SEC”）保留，理由是协议第 12 节原文如此，且“证监会”与“SEC”是通用监管机构名与规则本身的匹配关键词，不指认任何一题。观察 8（协调表文件的重复副本）不处理，封存清单见第 5 节的旧副本逻辑：重复副本是历史记录，不得再发给预测员。
- 追加清理脚本：`/tmp/phase4-residual-cleanup.py`（21 处）、`/tmp/phase4-residual-cleanup-2.py`（9 处）。两脚本均在 /tmp 内，不在仓库内。
- 本节之后，方法文件泄漏复核通过：事件名与动作字段全文 0 命中，同行题号加种类 0 命中，插入文本真实公司名 0 命中。复核标准见协议第 12.1 节。
