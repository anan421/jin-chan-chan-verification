# 第 6 轮：删掉不可识别的 c_rule 项，加识别诊断（审计改法 6，P1）

分支：`loop/round-6-drop-crule`，从 main（72fc739）分出。不含第 5 轮改动。第 5 轮分支保留在 git 里，不删除。

## 问题（plain 语言）

收益函数里有一项合规成本：系数 c_rule，特征 f_rule。

f_rule 对一切合法动作恒为 0。没有一条合法动作有合规成本。

一个恒为 0 的特征，梯度恒为 0。拟合时它学不到任何东西。它的值只随归一化移动。

但它却是权重向量里最大的一项：第一次真拟合 c_rule = 0.894，第二次 0.890。权重向量被一个没有信息的参数主导。

同时 w_hp、w_gold、w_pos 被压到接近 0。它们的真实大小看不见。

审计的改法：二选一。有证据的合法合规成本写入 f_rule，带证据指针。无证据则删项。

决定：删项。无证据。没有许可申请成本、法律费用之类的定价证据。

## 改了什么

### `rules/payoff-model.json`（live，占位 v2）

只删 c_rule。其他占位参数一个没动（w_hp 1.0、w_gold 1.0、c_lever 5.0、w_pos 1.0、temperature 1.0、discount 1.0、hp_exponent 1.0）。

- `parameters` 删 `c_rule`（原值 10.0）。
- 五档 `player_types[*].parameters` 各删 `c_rule`（原值 10.0）。
- `utility_form` 删 `− c_rule * compliance_cost`。
- A4 改成墓碑：`parameter` 为 `c_rule (removed)`，正文写明已删、原因“未识别”、f_rule 恒为 0、有证据时带证据指针加回来。
- `note` / `note_zh` 追加第 6 轮删除记录。version 仍为 2。

### `fit.py`（特征构造与拟合报告）

- `WEIGHT_NAMES` 从 5 项减到 4 项：`["w_hp", "w_gold", "c_lever", "w_pos"]`。
- `INIT_W` 从 `(1.0, 1.0, 5.0, 10.0, 1.0)` 减到 `(1.0, 1.0, 5.0, 1.0)`。
- `phi_of()` 从 5 元组减到 4 元组：`(f_hp, f_gold, -f_lever, f_pos)`。恒为 0 的分量已删。
- `argmax_kind()`、`utilities()`、`perceptron()` 按 4 维算。L2 归一化不再含 c_rule。
- `weights_block()` 不再写 `c_rule`。拟合输出的两份文件（`payoff-model-fitted.json`、`payoff-model-fitted-v1.json`）全局与分档参数里都没有 c_rule。
- v1 投影的 `utility_form` 同步删项。
- 新增 `identification_diagnostics()`：每项的梯度非零比例。定义：拟合窗里有候选集的决策中，记录种类与预测种类在该特征上不同、且该决策是一次错判（只有错判才更新权重）的占比。0 表示该特征没有任何识别信号，不得留在权重向量里。
- 拟合报告（`fit-report.json`）新增 `identification` 块：每项梯度非零比例、bootstrap 零值占比（B = 50，整轮重采样）、`money_term_identified` 与 `verdict`。`fit` 块（两份拟合输出文件里）也带同一块诊断。
- 报告 `notes`：c_rule 删除说明；若 w_gold 的 bootstrap 零值占比 ≥ 0.5，追加“金钱项未识别”。

### `predict.py`（效用函数）

- `utility()` 删掉 `− params["c_rule"] * compliance` 这一项。`compliance` 参数保留（调用点不动），但被忽略，不按 0 定价。
- 模块文档与 `utility()` 文档同步改公式，注明第 6 轮删除。

### `backtest.py`

未改。它不直接引用 c_rule，只读 `payoff_model.utility_form` 写进报告。已实测通过。

### `ensemble.py` / `classify.py`

未改。`ensemble.py` 各成员的权重字典里仍有 `c_rule` 键（成员立场快照），新 `utility()` 直接忽略多余键。已实测：同一 trace 下，main（72fc739，旧代码 + 旧 payoff）与本分支（新代码 + 新 payoff）的集成输出逐项相同——270/270 个（成员，玩家）众数条目相同，分布 0 项不同。旧的 `runs/2026-11-21_115508/ensemble-report.json` 与本次不同，那是第 4 轮之前的旧 trace 与旧期望增量造成的，与本轮无关。`classify.py` 不读 payoff 文件，不受影响。

### 设计稿

- `design/fitting-layer.md`：第一节占位值表、四项特征与 φ、感知机初值、第八节诚实边界同步更新。历史拟合记录里的 c_rule 数值保留（那是当时的真实记录）。
- `design/prediction-layer.md`、README.md：收益公式删合规成本项。

### 不动的东西

页面、`data.json`、`check.py`、Lean 检查路径一律未动。`data.json` 里仍有旧的 payoff 快照（含 c_rule），那是页面的数据快照，禁区内不改。

## c_rule / f_rule 引用清单与处理

全仓库 grep（除 `runs/`、`archive/` 历史记录外）：

| 位置 | 处理 |
|---|---|
| `rules/payoff-model.json` 参数与五档参数 | 已删 |
| `rules/payoff-model.json` A4 | 墓碑，写明已删与原因 |
| `rules/payoff-model.json` `utility_form` | 已删该项 |
| `fit.py` 特征构造、权重表、归一化、输出块 | 已删；只剩删除说明文字 |
| `predict.py` `utility()` 与文档公式 | 已删该项；只剩删除说明文字 |
| `ensemble.py` 成员权重字典与两处注释 | 保留（成员立场快照，效用函数已忽略）；实测输出逐项相同 |
| `design/prediction-layer.md`、`README.md` 公式 | 已删该项 |
| `design/fitting-layer.md` 定义段 | 已删该项并加诊断说明；历史记录保留 |
| `prediction-audit-2026-11-21.md`、`STATUS.md`、旧设计稿 | 历史记录，保留 |
| `data.json` payoff 快照 | 禁区，不动 |

## 拟合诊断（只作诊断，不升 live）

运行：`python3 fit.py traces/trace-latest.json --payoff rules/payoff-model.json --fit-seasons 1,2,3 --out-dir runs/fit-round-6-2026-11-21 --bootstrap 50 --seed 20261121`，exit 0。

拟合窗 S1–S3，n = 126 条决策；有候选集 92 条；错判 84 条。

共享拟合（α = 1.0、γ = 1.0、τ = 0.25，违规率 0.936508）：权重 w_hp 0.127033、w_gold 0.0、c_lever 0.987113、w_pos 0.097317。v1 投影与共享拟合相同。

对比第二次真拟合（fit-2026-11-21-02，5 维）：w_hp 0、w_gold 0、c_lever 0.445106、c_rule 0.890213、w_pos 0.096961。删掉 c_rule 后，w_hp 从 0 升到 0.127，第一次看得见真实大小。这就是审计要的效果。

识别诊断（`runs/fit-round-6-2026-11-21/fit-report.json` 的 `identification` 块）：

| 项 | 梯度非零比例 | bootstrap 零值占比 |
|---|---|---|
| w_hp | 0.913043 | 0.62 |
| w_gold | 0.913043 | 0.68 |
| c_lever | 0.0 | 0.0 |
| w_pos | 0.391304 | 0.64 |

结论：

- **金钱项未识别。**w_gold 的 bootstrap 零值占比 0.68 ≥ 0.5。报告 `notes` 与 `verdict` 已按审计原话写明“金钱项未识别”，不得称模型已拟合。本轮不做采用评估（hold-out 门控未跑；拟合输出只在运行目录）。
- w_hp 与 w_pos 的 bootstrap 零值占比也 ≥ 0.5（0.62、0.64）。只有 c_lever 在 bootstrap 里稳定（0.0）。
- 新发现：c_lever 的梯度非零比例也是 0.0。拟合窗里，记录种类与预测种类在杠杆特征上从不不同。它的拟合值 0.987 基本是占位初值经归一化剩下的，不是学出来的。c_rule 删掉了，但同类的归一化假象还在 c_lever 身上。这不在本轮改动范围，记在这里，待下一轮处理。

## 验收对照（基线 runs/2026-11-21_134835/，hold-out S4–S5，n = 234，M1 分母 83）

删项的口径：f_rule 对一切合法动作恒为 0，live 占位 c_rule = 10.0，所以删掉这一项不会改变任何一次预测的数值。测试集数字与基线逐项相同是预期结果，不是失败。

| 指标 | 基线 | 本轮（runs/2026-11-21_140227/） | 变化 |
|---|---|---|---|
| M1 | 1.2%（1/83） | 1.2%（1/83） | 相同 |
| M2 | 35.47% | 35.47% | 相同 |
| M3 | 25.21% | 25.21% | 相同 |
| M4 | 54.70% | 54.70% | 相同 |
| M5 | 91.88% | 91.88% | 相同 |
| M6 校准度（阈值 < 0.2） | 0.922，不通过 | 0.922，不通过 | 相同 |
| 退化率 | 0.000（0/18） | 0.000（0/18） | 相同 |
| 测试窗预测熵 | 1.7693 比特 | 1.7693 比特 | 相同 |
| 测试窗最大种类占比 | 46.2%（claude 108/234） | 46.2%（claude 108/234） | 相同 |
| v3 预测次数 | 5 | 5 | 相同 |
| 测试窗预测分布 | capex 15、llama 90、colossus 1、open_source 8、r1 7、v3 5、claude 108 | 逐项相同 | 相同 |
| 实时预测众数 | claude 12、llama 4、r1 2 | claude 12、llama 4、r1 2 | 相同 |
| 实时预测众数熵 | 1.224394 比特 | 1.224394 比特 | 相同 |

形式化检验：`./run.sh --predict` exit 0，总体 pass，预测章 opinion（`runs/2026-11-21_140227/merged-report.md`）。

收敛情况：实时预测最好回应 20 次迭代跑满，未收敛，cycle = True。第 4 轮的收敛回归仍在。本轮不改最好回应动态，如实报告。

## 变好还是没变好

按本轮的“变好”口径：变好了，但变好的地方在拟合诊断，不在 live 预测上。

- 权重向量不再含无信息参数。c_rule 已删，不再参与 L2 归一化。
- w_hp 的真实大小第一次看得见（0 → 0.127）。
- 识别诊断已产出并如实报告，包括不好看的部分：金钱项未识别（0.68），w_hp、w_pos 同样不稳定，c_lever 的 0.987 是归一化假象。
- live 预测数字逐项不变。预测本身没有变好，也没有变差。

## 还差什么

- c_lever 的梯度非零比例为 0.0：它的值不是学出来的。下一轮须处理（审计改法里没有单独一项，属本轮诊断的新发现）。
- 金钱项未识别：w_gold bootstrap 零值占比 0.68。模型仍不能说已拟合。
- M6 校准度 0.922，仍不通过（阈值 < 0.2）。
- 收敛回归仍在：实时最好回应 20 次迭代跑满、cycle = True。
- 拟合输出未升 live（按 hold-out 门控，本轮不做采用评估）。
