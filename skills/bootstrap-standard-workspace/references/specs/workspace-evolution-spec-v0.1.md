# Standard Workspace Evolution Specification V0.1

## 1. 边界

工作区实践可以产生标准演进候选，但标准仓库仍是唯一真相源。反馈导出、导入、提案、采纳和发布必须分离；工作区不得自动修改标准仓库、联网回传反馈或触发升级。

反馈只记录已脱敏的抽象结论和最小证据摘要。禁止包含项目名称、仓库或宿主机路径、远端地址、凭证、业务数据、完整日志、原始代码或未授权材料。

## 2. 反馈报告

`feedback-report.schema.json` 定义可交换的 JSON 报告。工作区将报告写入 `feedback/candidates/`，该目录归 `workspace` 所有；报告不是任务、项目或环境事实的替代品。

- `redaction_confirmed` 必须为 `true`；无法确认时不得导出。
- `source_fingerprint` 是工作区本地生成的不可逆指纹，只用于跨报告去重与独立来源计数；不得携带工作区、项目或人员标识。
- `authorized_sources` 只声明获授权来源类别，不记录文件路径或内容。
- 每项候选必须标注范围、可信度、发生次数和最小证据摘要。
- `standard-candidate` 仅表示可供审核，绝不表示已经成为标准。

## 3. 归属与采纳

| 范围 | 处理 |
| --- | --- |
| `local` | 留在工作区知识或策略，不导入标准。 |
| `project-plugin` | 由项目插件维护，不进入通用 Assets。 |
| `standard-candidate` | 可导入标准仓库并生成提案，仍需审核。 |

通用化提案必须至少有两个独立工作区的证据，或有一个经确认的安全、完整性或兼容性缺陷。一次实践、项目术语、环境偏好和未验证推断不得升级为通用约束。

## 4. 集成与版本

维护者将用户明确提供的报告放入本地、Git 忽略的 `evolution/inbox/`。`integrate-workspace-feedback` 先校验 Schema、脱敏声明、范围和重复 ID，再写入可审查的 `evolution/ledger/evidence.json`，按规范化候选 ID 去重并以唯一 `source_fingerprint` 计算独立工作区证据；随后生成 `evolution/proposals/` 的不可覆盖 Change Set 提案。它不直接修改产品定义。

审核后的采纳才可修改 Specs、Schemas、Skills 或 Assets，并必须同步 Assets、运行完整验证、评估升级影响、更新版本与发行记录。补丁版只用于无行为变化修复，兼容新增使用次版本，破坏 Schema、状态机、所有权或默认安全语义的变化使用主版本并要求 Migration。
