---
name: extract-standard-feedback
description: 从标准工作区中已授权的任务、控制面和项目材料提炼脱敏实践反馈，生成可审核的通用能力、规范或约束候选包。用于任务结束后的复盘、定期工作区总结，或准备向标准仓库提交实践反馈时；不用于自动上传、自动采纳或修改标准。
---

# Extract Standard Feedback

将当前工作区实践转为 `feedback/candidates/` 下的机器可读候选报告。报告是待审核信号，不是标准变更，也不替代任务、项目和环境事实。

## 收集边界

1. 读取 `AI_WORKSPACE.md`、工作区策略和当前任务授权；默认只读取任务记录与工作区控制面。
2. 需要读取项目文档、代码或配置时，先取得本次明确授权，并在报告中声明 `approved-project-material`。
3. 默认排除凭证、私密变量、远端内容、完整日志、业务数据、原始代码、项目名、仓库/宿主路径和端点。无法可靠脱敏时停止，不生成报告。
4. 不联网、不上传、不读取其他工作区、不修改标准仓库或当前任务状态。

## 提炼与归类

1. 只记录可验证的摩擦、重复约束、能力缺口或兼容性问题；区分观察与已确认结论。
2. 为每项候选选择范围：`local`、`project-plugin` 或 `standard-candidate`。项目术语、环境偏好和一次性经验不能标为 `standard-candidate`。
3. 为每项候选写入最小脱敏证据摘要、发生次数和反例。`standard-candidate` 通常要求多个独立工作区；单个已确认的安全、完整性或兼容性缺陷除外。
4. 使用 `scripts/new_feedback_report.py` 创建报告，再运行 `scripts/validate_feedback_report.py`。详细字段见 [feedback-contract.md](references/feedback-contract.md)。

## 输出与交接

1. 报告写入 `feedback/candidates/<report-id>.json`，禁止覆盖已有报告。
2. 同时用简短 Markdown 向用户说明来源类别、候选数量、被排除内容、各候选范围和仍待确认项。
3. 只有用户明确要求时，才将脱敏报告交给标准仓库维护者；由 `$integrate-workspace-feedback` 生成提案。不得把“交接”解释为自动采纳或升级。
