---
name: integrate-workspace-feedback
description: 在标准源码仓库中校验用户明确导入的脱敏工作区反馈，并生成可审查的标准演进提案。用于汇总多个工作区实践、判断候选归属和准备下个版本；不用于自动采纳、修改发行 Assets、发布或升级工作区。
---

# Integrate Workspace Feedback

在 `std-workspace` 源码仓库处理用户明确放入 `evolution/inbox/` 的反馈报告。该收件箱本地且 Git 忽略；提案才可进入可审查历史。

## 导入流程

1. 读取 `specs/workspace-evolution-spec-v0.1.md` 与报告对应 Schema。
2. 确认报告由用户明确提供，且只包含脱敏 JSON；不得扫描其他目录、联网或收集工作区内容。
3. 运行 `scripts/integrate_feedback.py REPORT.json`，只处理 `standard-candidate`。`local` 和 `project-plugin` 候选必须留在原工作区。
4. 审查生成的 `evolution/proposals/<report-id>.md`：来源数、反例、证据强度、兼容性、所有权、受影响文件、迁移与测试计划必须完整。
5. 报告或提案不等同于采纳。只有用户确认后才可另行修改 Specs、Schemas、Skills、Assets、版本或发行物。

## 安全与完整性

- 拒绝包含 URL、绝对路径或常见凭证标记的报告；检查只是兜底，人工脱敏确认仍不可省略。
- 拒绝覆盖已有提案或复用提案 ID。
- 一个报告不能自行证明跨工作区共性；在提案中保留“待聚合”状态，直到独立来源达到规范门槛。
- 详细门槛与版本规则见 [evolution-protocol.md](references/evolution-protocol.md)。
