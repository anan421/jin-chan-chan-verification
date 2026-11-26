# 第 16 轮开跑前提 2：打分脚本 verdict_from 判定措辞修复（2026-11-26）

- 状态：已修好。三例合成验证全部通过。第 15 轮真实数据重跑输出丢掉。
- 依据：第 15 轮审计 `round15-audit-2026-11-25.md` 第 7、14、15 节；协议 `phase4-control-experiment-protocol-2026-11-25.md` 第 5.2、6.1、6.2 节。
- 范围：只改 `/tmp/round16-scripts/` 里的两套脚本副本。第 15 轮工作区未动（`git status` 干净）。main 未动。

## 1. 根因

- 旧 `verdict_from` 的输入只有增益 `G`、原始增益 `G_raw`、新题增益 `G_new`、新种类增益、六条件通过与否、H4 通过与否。
- 它从不计算真新信息。真新信息是协议第 5.2 节的定义：对照组三批全错、实验组三批全对的题。协议第 6.2 节把它列为丢掉条件之一（真新信息少于 2 道即丢掉），也列为暂定条件之一（不少于 2 道）。
- 第 15 轮真新信息是 0 道（审计第 7 节直接数原始文件：原始 215 道与排除后 173 道都是 0 道）。旧函数走到最后的 else 分支，输出 `MIXED (helpful but below adoption threshold; stays tentative)`。
- 第 14 轮是同一个错误。本次修复后，两套脚本里不再有 `MIXED`、`stays tentative`、`NOT ADOPTED (H4 ... coordinator decides ...)` 这类措辞。判定只有三种：ADOPT、TENTATIVE、REMOVE。

## 2. 新判定逻辑（协议第 6.2 节）

- 真新信息：从打分输出里直接数，不从增益推断。主脚本从逐题表 `per_question` 的 `control_correct_batches_excluded42 == 0` 且 `exp_correct_batches_excluded42 == 3` 数（泄漏题已排除）。验证脚本从原始预测文件独立重数（不读逐题表）。
- 丢掉条件（任一满足即丢掉）：增益 `G <= 0`；增益只来自泄漏题（`G_raw > 0` 且 `G <= 0`）；新种类总增益小于 0（系统性帮倒忙）；真新信息少于 2 道。
- 采用条件：六个采用条件全过，且 H4 门过，且无丢掉条件。
- 暂定条件（三条全满足，但采用条件未全满足）：增益为正；真新信息不少于 2 道；无系统性帮倒忙（新种类总增益不小于 0）。
- 判定顺序：先算丢掉，再算采用，再算暂定。丢掉优先于采用：如果六条件全过但真新信息少于 2 道，判定是丢掉，不是采用。无第四种判定；另有一条防呆分支，理论上不可达，触发时按丢掉处理。
- 判定字符串：`ADOPT (...)`、`TENTATIVE (...)`、`REMOVE (discard condition met: ...; ...)`。字符串里写明丢掉原因。H4 单独失败时不强制丢掉：它只阻止采用；暂定字符串里会注明 H4 门失败。

## 3. 改了什么

### 主脚本 `score_round15.py`（文件名与第 15 轮一致）

- 模块 docstring 的判定规则段重写：写明新逻辑与三处口径说明（见第 5 节）。
- 新增 `count_genuine_new_info(ctrl_n, exp_n, leak_qids, n_exp_batches)`：按协议第 5.2 节数真新信息，返回（道数，题号清单）。
- 重写 `verdict_from`：新签名 `verdict_from(G, G_raw, new_kind_gain, six_pass, h4_pass, genuine_new_info)`，返回 `(verdict, adopt, remove, tentative, discard_reasons)`。`G_new` 参数已去掉（见第 5 节）。
- Headline 调用点：先算真新信息，再调 `verdict_from`。输出新增字段：`decision_rules.genuine_new_info`、`decision_rules.genuine_new_info_qids`、`decision_rules.discard_reasons`、`decision_rules.tentative`、`gains.genuine_new_info_excluded42`、`gains.genuine_new_info_qids_excluded42`。
- Leave-one-out 调用点（`compute_sensitivity`）：按剩余批次算真新信息（剩余对照组全错、剩余实验组全对），再调 `verdict_from`。每条 LOO 记录新增 `genuine_new_info`、`genuine_new_info_qids`、`discard_reasons`、`tentative`、`remove_any`。
- 其余打分逻辑未动：分数、增益、噪声带、六条件、H-15、McNemar、执行率、guards 均未改。

### 验证脚本 `score_round15_verify.py`（第二套，独立重算）

- 保持独立：不 import 主脚本。LEAK_42 另抄一份。真新信息从原始预测文件重数。
- 在 `main()` 内新增两个嵌套 helper：`_genuine_list`（从原始预测文件数真新信息）与 `_verdict_from`（与主脚本同规范、独立代码）。
- Headline 核对点：用 helper 重算判定，并核对主脚本输出的新字段（`genuine_new_info`、`genuine_new_info_qids`、`discard_reasons`、`tentative`、`remove_any`、`adopt_all_six_plus_H4`）。旧的 `adopt_all_six_plus_H4` 核对已改：旧核对只算六条件加 H4，新核对含丢掉条件（六条件全过但真新信息为 0 时，采用为假）。
- Leave-one-out 核对点：同理重算每条 LOO 记录的判定与真新信息，并核对新增字段。
- 其余核对逻辑未动。

## 4. 验证结果

### 三例合成用例（任务第 3 项）——全部通过

| 用例 | 输入 | 预期 | 实际 |
|---|---|---|---|
| (a) 采用 | 增益 +12、真新信息 3 道、无帮倒忙、六条件全过、H4 过 | ADOPT | ADOPT |
| (b) 暂定 | 增益 +5、真新信息 3 道、无帮倒忙、六条件未全过 | TENTATIVE | TENTATIVE |
| (c) 丢掉 | 增益 +3、真新信息 0 道 | REMOVE | REMOVE |

### 第 15 轮真实数据重跑——通过

- 方法：沙盒 `/tmp/r16replay/`（符号链接读第 15 轮题集与预测文件，输出写 /tmp，未写第 15 轮工作区）。修复后的主脚本重算第 15 轮全部 186 个预测文件。
- 分数与原版逐项一致：对照组 77/73/79、实验组 77/83/79；排除后对照组 64/61/66、实验组 64/71/66；增益原始与排除后均为 +3.33；噪声带 7；门槛 11；McNemar p 为 1.0、0.0063、1.0；H-15 为 FALSIFIED。diff 只差判定相关字段。
- 判定：`REMOVE (discard condition met: no genuine new info (0 < 2); method does not enter baseline)`。`remove_any` 由 False 变 True。真新信息 0 道，与审计第 7 节一致。
- 修复后的验证脚本对该输出：`VERIFY PASS`，exit 0。两套独立实现在判定上一致。

### 补充测试——全部通过

- `test_verdict_from_fix.py`：第 15 轮数字、三例、10 个边界用例（增益为 0/为负、只来自泄漏题、新种类帮倒忙、真新信息 1 道/2 道、六条件全过但真新信息为 0、H4 失败的两种情形、增益超门槛但 McNemar 失败），以及 192 组输入的穷举：判定集合恒为 {ADOPT, TENTATIVE, REMOVE}，无 MIXED。
- `test_verify_helper_and_loo.py`：从验证脚本文件里用 AST 抽出嵌套 helper 直接跑，三例通过；主脚本与验证脚本的判定函数在 192 组穷举输入上 0 处不一致；验证脚本的 `_genuine_list` 在第 15 轮真实预测文件上数为 0，把 q122 的 C3 记录由 arr 改为 chatgpt 后数为 [122]，主脚本的计数函数结果相同；主脚本 LOO 路径强制指定 C1、E2 为 flagged 批后，两条 LOO 记录均为 REMOVE（真新信息 0 道，增益分别为 +3.50、+1.33）。
- 复跑命令：`python3 test_verdict_from_fix.py`、`python3 test_verify_helper_and_loo.py`（均 exit 0）。

## 5. 口径说明（需协调员知晓的三处判断）

1. `G_new <= 0` 不再是丢掉条件。协议第 6.2 节的丢掉清单里没有这一条，旧代码多加了它。本次按协议字面去掉。`G_new` 仍在输出里报告（`G_new_excluded42`），只不参与判定。如需恢复为第五条丢掉条件，改一行即可。
2. 暂定条件 1 按任务简报写为“增益为正”，未加协议原文的“但未超噪声带”上限。后果：增益已超门槛、但因另一条件（如 McNemar）未过采用时，判定为 TENTATIVE 而非 REMOVE（无丢掉条件满足）。如需严格口径，协调员定夺。
3. H4 门单独失败不是丢掉条件。六条件全过但 H4 失败、且暂定三条满足时，判定为 TENTATIVE（字符串注明 H4 失败、采用被阻止）。旧的 `NOT ADOPTED (coordinator decides ...)` 已删除，不再把判定推给协调员。
4. “无系统性帮倒忙”按新种类总增益判断（小于 0 为帮倒忙），与审计第 15 节口径一致：单个种类小跌（如 musk_table −0.33）不算系统性帮倒忙。

## 6. T 匹配空格归一化（任务第 4 项）——已确认，两套脚本均已有

- 主脚本 `has_trigger_line`：匹配前做 `ev.replace(" ", "")`，再查 `"30天内无触发事件"`。`"30 天内无触发事件"` 与 `"30天内无触发事件"` 计为相同。
- 验证脚本 `_trig_ok`：同一写法，`ev.replace(" ", "")` 后查 `"30天内无触发事件"`。
- 功能测试：主脚本 `has_trigger_line` 对带空格与不带空格两种写法均返回 True，无触发文本返回 False。
- 说明：规则 T 已在第 15 轮移除，T 计数只是 legacy 上报，不参与 H-15。本次未改归一化代码，只确认并测试。

## 7. 第 16 轮使用方法与注意事项

- 文件：`/tmp/round16-scripts/score_round15.py`、`/tmp/round16-scripts/score_round15_verify.py`（文件名与第 15 轮一致）。测试：`test_verdict_from_fix.py`、`test_verify_helper_and_loo.py`。说明：本文件。
- 放入第 16 轮工作区时，须像往轮一样把 `RUN` / `PRED_DIR` / `SCORE_PATH` 指向第 16 轮运行目录（本次未改路径常量，因第 16 轮运行目录名尚未定夺）。判定字符串已去掉轮次字样，可直接用于第 16 轮。
- 验证脚本现在要求输出含新字段（`genuine_new_info` 等），须与修复后的主脚本配对使用；对旧版输出跑新版验证脚本会因缺字段而报错，这是预期的版本配对关系。
- 未端到端验证的一点：验证脚本的 LOO 判定核对块只在有 flagged 批时运行。第 15 轮无 flagged 批，故该块未在重跑里走过；它已在单元层验证（helper 抽出直跑 + 主脚本 LOO 路径实测）。第 16 轮如有 flagged 批，该块会首次实跑。
