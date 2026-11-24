# 预测账本格式（Forecast Ledger Schema）

- 版本：`schema_version` 为 `1.0`
- 账本文件：`forecasts/ledger.json`
- 校验脚本：`scripts/validate_ledger.py`
- 状态：格式文档。本文件只定格式，不写预测内容。
- 依据：Phase 1 报告 `design/phase1-report-2026-11-24.md` 第 6 节。字段按任务文档第 6.1 节。类型枚举取任务文档第 7.2 节的五类预测任务。

## 1. 顶层结构

账本文件是一个 JSON 对象。它含五个顶层键。五个键全部必填。不接受其他顶层键。

| 键 | 类型 | 含义 |
| --- | --- | --- |
| `schema_version` | 字符串 | 格式版本。当前值固定为 `"1.0"`。格式改动时升版本。 |
| `meta` | 对象 | 账本元数据。含 `created`、`updated`、`note`。`created` 与 `updated` 是 ISO 8601 UTC 时间。`updated` 不早于 `created`。`note` 是字符串，可空。 |
| `forecasts` | 数组 | 预测记录。每条记录是当前版本的内容。数组为空表示账本尚无预测。 |
| `resolutions` | 数组 | 结算记录。每条记录引用一条已存在的预测。结算记录与预测记录分开存放。 |
| `versions` | 数组 | 版本链记录。每条记录保存一条预测某一个版本的完整内容。旧版本永不删除，永不改写。 |

## 2. 预测记录（forecasts 数组元素）

一条预测记录含 21 个字段。21 个字段全部必填。不接受其他字段。

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `forecast_id` | 字符串 | 预测编号。格式为 `S<赛季>-FC-<两位以上数字>`，例如 `S6-FC-01`。正则为 `^S[0-9]+-FC-[0-9]{2,}$`。账本内唯一。 |
| `proposition` | 字符串 | 命题。命题写清主语、动作、截止条件。命题不得含糊到无法结算。命题一经写入不得改写，只能追加新版本。 |
| `forecast_type` | 字符串 | 预测任务类型。枚举见第 3 节。 |
| `type` | 字符串 | 棋盘动作种类，例如 `policy_regulatory`。非空字符串。该字段保留棋盘的动作词汇，与 `forecast_type` 回答不同的问题：前者是这条预测关于哪类动作，后者是这是一类什么预测任务。 |
| `participants` | 数组 | 参与者。数组非空。元素是玩家代码字符串，例如 `NVDA`，或对象。对象必须含非空的 `player` 字段，可含 `persona`、`persona_role`、`role_in_forecast`。S6 可新增玩家，校验不按 `data.json` 玩家名单硬拦。 |
| `author` | 字符串 | 预测者。写人名或 agent 标识。结算者不得是预测者本人，见第 6 节。 |
| `agent` | 字符串或 null | 生成预测的 agent 标识。角色扮演预测写扮演角色。模型预测写模型 agent。无 agent 时写 `null`。结算者不得等于该字段，见第 6 节。 |
| `created_at` | 字符串 | 创建时间。ISO 8601 UTC 时间，例如 `2026-11-22T10:00:00Z`。创建后永不改写。 |
| `information_cutoff` | 字符串 | 信息截止时间。ISO 8601 UTC 时间。预测只用该时间之前的信息。信息截止时间不晚于创建时间。 |
| `resolution_deadline` | 字符串 | 结算截止时间。ISO 8601 UTC 时间。结算截止时间晚于创建时间。命题在该时间之前未兑现即按结算标准判未命中或无法判定。 |
| `probability` | 数字 | 概率。取值范围是 0 到 1，含 0 与 1。 |
| `resolution_criteria` | 字符串 | 结算标准。结算标准写清可观测的判定条件与判定依据来源。结算标准在创建时定死。事后改结算标准须追加新版本。 |
| `evidence_snapshot` | 数组 | 证据快照。每项格式见第 5 节。数组非空。 |
| `reasoning_summary` | 字符串 | 推理摘要。推理摘要写清从证据到概率的推理链。推理摘要非空。 |
| `assumptions` | 字符串数组 | 假设。假设逐条列出。无假设时写空数组。假设不得省略，不得藏进推理摘要。 |
| `counter_evidence` | 字符串数组 | 反证据。反证据逐条列出。无反证据时写空数组。反证据不得省略。 |
| `model_version` | 字符串 | 模型版本。非空字符串，例如 `payoff-model-v2`。无模型时写 `none`，不得留空。 |
| `method_version` | 字符串 | 方法版本。非空字符串，例如 `roleplay-v1`。 |
| `rule_version` | 字符串 | 规则版本。非空字符串，例如 `RV-2026.2`。规则版本取 `data.json` 与 trace 使用的规则编号。 |
| `world_state_version` | 字符串 | 世界状态版本。非空字符串。推荐格式为 trace 文件加短哈希，例如 `traces/trace-2026-11-24.json@0c938073`。世界状态版本指明预测出发的世界状态。 |
| `status` | 字符串 | 状态。枚举见第 3 节。 |

注：上表列出 21 行，其中 `author` 与 `agent` 是任务书第 6.1 节之外补的两个字段。补这两个字段的原因只有一个：结算者分离规则需要一个可比的预测者标识。`author` 必填，`agent` 可为 null。`forecast_type` 与 `type` 是任务书第 6.1 节的 `forecast_type` 字段拆出的两个字段：`forecast_type` 用任务书第 7.2 节的五类预测任务，`type` 保留棋盘动作种类。字段名 `information_cutoff` 与 `resolution_deadline` 用任务书第 6.1 节原文，不加 `_at` 后缀。

## 3. 枚举值

### 3.1 预测类型（`forecast_type`）

| 值 | 中文 | 含义 |
| --- | --- | --- |
| `active_action` | 主动行为 | 某玩家主动做的动作。 |
| `external_event` | 外部事件 | 玩家控制之外的事件。 |
| `reaction` | 反应 | 某玩家对另一事件的反应。 |
| `impact` | 影响 | 事件对血量、金币、段位的影响。 |
| `state` | 状态 | 某时点的世界状态。 |

### 3.2 预测状态（`status`）

| 值 | 中文 | 含义 |
| --- | --- | --- |
| `open` | 未到期 | 无结算记录，或最新结算记录的状态是尚未到期。 |
| `resolved` | 已结算 | 最新结算记录的状态是命中、未命中、无法判定或结算存在争议。 |
| `void` | 作废 | 预测在结算前撤回。作废的预测不得再有结算记录。作废本身是一次版本变更，须追加新版本。 |

预测状态与最新结算记录一致。校验脚本核对这一致性。

### 3.3 证据核验结果（`verification_result`）

| 值 | 中文 | 含义 |
| --- | --- | --- |
| `verified` | 已核验 | 摘录内容与来源原文一致，来源真实可查。 |
| `unverified` | 未核验 | 来源已记录，内容尚未逐字核对。 |
| `contradicted` | 被反驳 | 来源原文不支持摘录主张，或来源本身不可信。 |

核验结果为 `contradicted` 的证据项不得作为支撑主张的唯一证据。

已核验须同时有来源地址与发布时间，校验脚本强制这一条。来源地址可写完整 URL，也可写可定位的出版标识（机构加日期加主题），或内部文档路径。不得猜测 URL。无来源时来源地址写 `null`，发布时间写 `null`，核验结果只能是 `unverified`。引用内部文档路径的已核验项，校验脚本只报警告：内部文档是主张的出处，不是独立核验，须人工确认它是一手来源。摘录是主张摘要，不是逐字引用；逐字引用须注明。

## 4. 版本链（versions 数组元素）

预测发布后不得直接覆盖原始内容。判断变化时追加新版本。旧版本保留并关联。

一条版本链记录含 7 个字段。7 个字段全部必填。不接受其他字段。

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `forecast_id` | 字符串 | 预测编号。引用 `forecasts` 里已存在的预测编号。 |
| `version` | 整数 | 版本号。从 1 开始，同一预测编号下连续递增，不跳号。 |
| `supersedes` | 整数或 null | 上一版本号。第 1 版写 `null`。第 n 版（n 大于 1）写 `n - 1`。 |
| `superseded_by` | 整数或 null | 下一版本号。最新版写 `null`。非最新版写 `n + 1`。 |
| `created_at` | 字符串 | 该版本写入时间。ISO 8601 UTC 时间。第 1 版的写入时间等于预测记录的 `created_at`。后一版本不早于前一版本。 |
| `change` | 字符串 | 变更说明。变更说明写清本版改了什么、为什么改。非空。 |
| `content` | 对象 | 该版本的完整预测内容。`content` 含第 2 节的 21 个字段，逐条遵守同一规则。`content` 不含版本号，版本号只存在版本链记录上。 |

版本链规则：

- 每条预测至少有一个版本链记录，即第 1 版。
- `forecasts` 数组里的记录必须与该预测最新版本的 `content` 逐字段相等。`forecasts` 数组只存当前版本，不存历史。
- `content` 里的 `created_at` 在各版本之间保持不变。创建时间是预测的出生时间，不是版本的写入时间。
- `superseded_by` 必须指向存在的更新版本。指向不存在版本的链是断链，校验失败。
- 版本链记录一经写入不得改写。改写旧版本内容只能用追加新版本实现。

## 5. 证据快照（evidence_snapshot 数组元素）

每条预测的 `evidence_snapshot` 至少含一项。每一项含 6 个字段。6 个字段全部必填。不接受其他字段。主张只存指针不够，内容摘录是必填项。

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `source_url` | 字符串或 null | 来源地址。完整 URL，或可定位的出版标识（机构、日期、主题），或内部文档路径。不得猜测 URL。无来源时写 `null`。 |
| `publisher` | 字符串 | 发布机构。发布机构是非空字符串，例如 `BIS`、`Anthropic`。 |
| `published_at` | 字符串或 null | 发布时间。ISO 8601 日期或 UTC 时间。来源只给日期时写日期。未知时写 `null`。 |
| `retrieved_at` | 字符串 | 获取时间。ISO 8601 UTC 时间。获取时间不早于发布时间，不晚于该版本写入时间。 |
| `excerpt` | 字符串 | 支撑主张的内容摘录。本账本的摘录是主张摘要，不是逐字引用；逐字引用须注明。内容摘录非空。只给链接不给摘录的证据项无效。 |
| `verification_result` | 字符串 | 核验结果。枚举见第 3.3 节。已核验须同时有来源地址与发布时间。 |

结算记录的 `outcome_evidence` 用同一格式。同一格式保证结算证据与预测证据可互相核对。

## 6. 结算记录（resolutions 数组元素）

一条结算记录含 11 个字段。其中 9 个字段必填，2 个字段有条件必填。结算记录不接受其他字段。

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `forecast_id` | 字符串 | 预测编号。引用 `forecasts` 里已存在的预测编号。引用不存在的预测编号时校验失败。 |
| `actual_outcome` | 布尔或 null | 实际结果。`true` 表示命题发生，`false` 表示命题未发生。状态是命中或未命中时必填布尔值。状态是结算存在争议时可填主张的结果，也可填 `null`。其他状态填 `null`。 |
| `resolved_at` | 字符串或 null | 结算时间。ISO 8601 UTC 时间。状态是尚未到期时填 `null`。其他状态必填。结算时间不早于预测创建时间。 |
| `outcome_evidence` | 数组 | 结果证据。格式与第 5 节相同。状态是尚未到期时可为空数组。其他状态非空。 |
| `resolution_status` | 字符串 | 结算状态。枚举见第 7 节。 |
| `resolver` | 字符串 | 结算者。结算者是非空字符串。结算者不得是预测者本人：`resolver` 不得等于该预测的 `author` 字段，也不得等于该预测的 `agent` 字段（`agent` 为 `null` 时只比 `author`）。 |
| `dispute_status` | 字符串 | 争议状态。枚举见第 7 节。 |
| `score` | 数字或 null | 得分。得分是 Brier 分。状态是命中或未命中时必填。其他状态填 `null`。得分取值范围是 0 到 1。得分必须等于 `(probability - actual_outcome)^2`，误差不大于 `0.0001`。概率取 `forecast_version` 指定的版本，无指定时取最新版本。 |
| `review` | 布尔 | 是否争议复核。默认 `false`。同一预测编号的第一条结算记录必须是 `false`。此后的结算记录必须是 `true`，并填 `review_reason`。 |
| `review_reason` | 字符串或 null | 复核原因。`review` 为 `true` 时必填，非空。`review` 为 `false` 时填 `null`。 |
| `forecast_version` | 整数或 null | 结算依据的预测版本号。结算依据的版本须在该预测的版本链里存在。无指定时取结算时的最新版本。建议结算时明确指定，避免事后版本变更改写得分依据。 |

## 7. 结算枚举值

### 7.1 结算状态（`resolution_status`）

| 值 | 中文 | 含义 |
| --- | --- | --- |
| `hit` | 命中 | 命题发生，结算标准满足。 |
| `miss` | 未命中 | 命题未发生，或结算截止时间已过仍未兑现。 |
| `not_yet_due` | 尚未到期 | 未到结算截止时间，尚无结果。 |
| `indeterminate` | 无法判定 | 结算标准无法判定，证据不足或命题本身不可判定。 |
| `disputed` | 结算存在争议 | 结算结果有人质疑，争议未解决。得分暂不记，争议解决后由复核记录改写。 |

### 7.2 争议状态（`dispute_status`）

| 值 | 中文 | 含义 |
| --- | --- | --- |
| `none` | 无争议 | 无争议。 |
| `open` | 争议中 | 争议未解决。 |
| `resolved` | 争议已解决 | 争议已解决，复核记录已写入。 |

一致性规则：`dispute_status` 为 `open` 当且仅当 `resolution_status` 为 `disputed`。`dispute_status` 为 `resolved` 时，该预测编号下必须存在一条 `review` 为 `true` 的结算记录。

## 8. 追加式写入流程

1. 新预测写入 `forecasts` 数组，同时在 `versions` 数组追加第 1 版。两处内容一致。
2. 判断变化时，先在 `versions` 数组追加新版，再把 `forecasts` 数组里的记录改成新版内容。旧版记录不动。
3. 结算时，在 `resolutions` 数组追加结算记录。结算记录不改 `forecasts` 数组里的概率与命题。结算后把 `forecasts` 数组里该预测的 `status` 改为 `resolved`。该改动本身是一次版本变更，须追加新版本。
4. 争议复核时，在 `resolutions` 数组追加 `review` 为 `true` 的新记录。旧结算记录不动。
5. 任何一步只追加，不改写已写入的版本链记录与结算记录。改写须用 git 历史核对，见第 9 节。

## 9. 校验规则

校验脚本是 `scripts/validate_ledger.py`。校验失败时退出码非零，并写明记录与字段。校验规则如下：

- 顶层结构：五个顶层键齐全，无多余键。`schema_version` 等于 `"1.0"`。`meta` 的 `updated` 不早于 `created`。
- 编号唯一：`forecast_id` 在 `forecasts` 数组里唯一，格式符合正则。
- 必填字段：预测记录 21 个字段齐全，版本链记录 7 个字段齐全，结算记录按第 6 节齐全，证据项 6 个字段齐全。空字符串视同缺失。`source_url` 与 `published_at` 可为 `null`，见第 5 节。
- 概率范围：`probability` 是数字，不含布尔值，取值在 0 到 1 之间。
- 时间顺序：信息截止时间不晚于创建时间。结算截止时间晚于创建时间。证据获取时间不早于发布时间，不晚于版本写入时间。结算时间不早于预测创建时间。
- 枚举值：`forecast_type`、`type`、`status`、`verification_result`、`resolution_status`、`dispute_status` 全部落在第 3 节与第 7 节的枚举内。`type` 是非空字符串。
- 结算引用：结算记录引用的 `forecast_id` 必须存在。结算记录引用的 `forecast_version` 必须在版本链里存在。
- 结算不重复：同一 `forecast_id` 的第一条结算记录 `review` 必须是 `false`。此后的结算记录 `review` 必须是 `true`，并填复核原因。
- 结算者分离：结算记录的 `resolver` 不得等于该预测的 `author` 字段，也不得等于该预测的 `agent` 字段。
- 得分一致：`score` 非空当且仅当结算状态是命中或未命中。`score` 必须等于 Brier 分，误差不大于 `0.0001`。
- 状态一致：预测状态与最新结算记录一致，见第 3.2 节。作废的预测不得有结算记录。
- 版本链自洽：同一预测编号的版本号从 1 连续递增。`supersedes` 与 `superseded_by` 互相吻合。`superseded_by` 指向存在的更新版本。`forecasts` 数组里的记录与最新版本 `content` 逐字段相等。各版本 `content` 的 `created_at` 相同。
- 证据摘录：每个证据项的 `excerpt` 非空。只存指针的证据项校验失败。已核验的证据项须同时有来源地址与发布时间；引用内部文档路径的已核验项只报警告，须人工确认。
- Git 历史核对（可选，`--git`）：校验脚本读 git 历史里每一次提交的 `forecasts/ledger.json`。历史里出现过的版本链记录，在当前账本里必须原样存在。历史快照被改写或删除时校验失败。账本文件尚未入库时跳过该项检查并打印警告。

## 10. 格式示例（非真实预测）

下例只演示格式。编号 `S6-FC-99` 是格式示例编号。命题是格式示例命题。下例不是真实预测，不得当作预测迁入账本。

```json
{
"schema_version": "1.0",
"meta": {
"created": "2026-11-24T00:00:00Z",
"updated": "2026-11-24T00:00:00Z",
"note": "格式示例，非真实预测。"
},
"forecasts": [
{
"forecast_id": "S6-FC-99",
"proposition": "某玩家在 2026-12-31 之前发布新模型。",
"forecast_type": "external_event",
"type": "model_release",
"participants": ["OAI"],
"author": "roleplay-agent",
"agent": "example-persona",
"created_at": "2026-11-22T10:00:00Z",
"information_cutoff": "2026-11-22T10:00:00Z",
"resolution_deadline": "2026-12-31T23:59:59Z",
"probability": 0.7,
"resolution_criteria": "发布机构官网或官方账号在截止时间前宣布新模型上线。",
"evidence_snapshot": [
{
"source_url": "https://example.com/evidence",
"publisher": "Example Publisher",
"published_at": "2026-11-21",
"retrieved_at": "2026-11-22T09:00:00Z",
"excerpt": "来源原文的关键句摘录。",
"verification_result": "verified"
}
],
"reasoning_summary": "推理摘要。",
"assumptions": ["假设一。"],
"counter_evidence": ["反证据一。"],
"model_version": "payoff-model-v2",
"method_version": "roleplay-v1",
"rule_version": "RV-2026.2",
"world_state_version": "traces/trace-2026-11-24.json@0c938073",
"status": "resolved"
}
],
"resolutions": [
{
"forecast_id": "S6-FC-99",
"actual_outcome": true,
"resolved_at": "2026-11-23T10:00:00Z",
"outcome_evidence": [
{
"source_url": "https://example.com/outcome",
"publisher": "Example Publisher",
"published_at": "2026-11-23",
"retrieved_at": "2026-11-23T09:00:00Z",
"excerpt": "结果证据摘录。",
"verification_result": "verified"
}
],
"resolution_status": "hit",
"resolver": "independent-settler",
"dispute_status": "none",
"score": 0.09,
"review": false,
"review_reason": null,
"forecast_version": 2
}
],
"versions": [
{
"forecast_id": "S6-FC-99",
"version": 1,
"supersedes": null,
"superseded_by": 2,
"created_at": "2026-11-22T10:00:00Z",
"change": "首版。",
"content": {}
},
{
"forecast_id": "S6-FC-99",
"version": 2,
"supersedes": 1,
"superseded_by": null,
"created_at": "2026-11-23T10:00:00Z",
"change": "概率由 0.6 改为 0.7，结算状态改为已结算。",
"content": {}
}
]
}
```

上例中两个 `content` 字段写 `{}` 是占位写法。真实账本里每个 `content` 必须是第 2 版的完整预测内容。第 2 版的 `content` 必须与 `forecasts` 数组里的记录逐字段相等。第 1 版的 `content` 是首版的完整预测内容。

## 11. 格式与账本统一记录（2026-11-24，协调员定夺）

格式文档初版与迁入路写出的账本字段名不一致，校验脚本按初版格式跑账本报 127 个错误。协调员按任务文档第 6.1 节原文定夺，以任务文档为准，格式文档与校验脚本按下列决定改过，账本已迁移到统一口径。迁移脚本是 `/tmp/migrate_ledger.py`。迁移前账本备份在 `/tmp/ledger-before-migration-2026-11-24.json`。

- `schema_version` 用 `"1.0"`。`meta` 补 `created` 与 `updated`。
- 时间字段用任务文档原文：`information_cutoff`、`resolution_deadline`，不加 `_at` 后缀。初版格式的 `_at` 后缀是格式路自加的，已改回。
- 结算字段用任务文档原文：`resolution_criteria`、`resolved_at`、`outcome_evidence`、`resolution_status`、`resolver`、`actual_outcome`。`score` 是数字（Brier 分），不是对象。`dispute_status` 用英文枚举（`none`）。
- 预测记录保留 `type`（棋盘动作种类），另加 `forecast_type`（任务书第 7.2 节五类预测任务）。四条预测的分类：FC-01 `external_event`（监管政策变化），FC-02 `state`（公司财务结果），FC-03 与 FC-04 `active_action`（公司主动行为）。
- `participants` 保留对象数组（含 `player`、`persona`）。`assumptions` 与 `counter_evidence` 由字符串改为单元素字符串数组，原文一字未改。
- `evidence_snapshot` 由对象改为证据项数组。旧 `facts` 的每条主张原样成为一项的 `excerpt`。21 条证据中 2 条标 `verified`（FC-01 的 BIS 远程接入规则与 FT 11-20 调查，项目已独立核实），其余 19 条标 `unverified`。摘录是主张摘要，不是逐字引用。
- 版本链补 `superseded_by` 与 `content`（完整快照）。第 1 版写入时间等于预测创建时间（2026-11-22），迁移日期记在 `meta` 与 git 历史里。
- 预测记录补 `author`（`roleplay-run-2026-11-22`）与 `agent`（`roleplay`）。结算者 `s6-daily-monitor` 与两者不同，结算者分离规则通过。
- 预测记录的 `settlement_status` 与 `hash` 已删除：前者与结算记录重复，后者计算方法无文档。结算记录的 `actual_result` 与 `recorded_at` 已删除：内容分别保留在 `outcome_evidence` 摘录与版本链写入时间里。
- 评分脚本的说法已订正：格式初版第 11 节称评分脚本只读 `settlements` 与 `version` 键，读代码证实是错的。评分脚本读 `resolutions`（回退）与 `schema_version`（回退），也读 `actual_outcome` 布尔值。迁移后的账本重跑评分，结果与迁移前完全一致：平均 Brier 分 0.1600，命中率 1/1。评分脚本逻辑未改，只改了文档说明。
- 校验器的一处局限已记下：结构规则（已核验须有来源与发布时间）拦不住“引用内部文档却标已核验”。校验器对这类项只报警告，语义判断须人工复核。

仍未解决：

- 任务文档第 6.1 节原文不在仓库内。本文件字段按任务书的字段清单与 Phase 1 报告第 6 节制定。任务书原文如有补充字段，格式版本须升到 `1.1` 并补字段。
- `forecasts` 数组里的记录与最新版本 `content` 的逐字段相等，由校验脚本核对。人工编辑账本时容易只改一处。写入账本的操作须成对改两处，或由写入脚本保证。
- 证据项的 `published_at` 允许只写日期。来源只给月份时，写 `YYYY-MM` 仍不在本格式内。月份精度的时间写法待定。
- 证据项的 `published_at` 允许只写日期。来源只给月份时，写 `YYYY-MM` 仍不在本格式内。月份精度的时间写法待定。
