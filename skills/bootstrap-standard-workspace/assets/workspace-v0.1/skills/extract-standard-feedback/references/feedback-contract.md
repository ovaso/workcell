# 反馈报告契约

报告必须符合 `.ai-workspace/schemas/feedback-report.schema.json`。

- `feedback.id` 是稳定报告 ID；不使用工作区、项目或人员标识。
- `redaction_confirmed` 只能在人工检查脱敏后设为 `true`。
- `authorized_sources` 是来源类别，不得记录路径、URL 或原文。
- `evidence[].summary` 是最小抽象说明，不得包含原始日志、代码或业务数据。
- `scope = standard-candidate` 只表示提交审核的资格，不能暗示已采纳。

导出前运行：

```bash
python3 skills/extract-standard-feedback/scripts/validate_feedback_report.py feedback/candidates/<report-id>.json
```
