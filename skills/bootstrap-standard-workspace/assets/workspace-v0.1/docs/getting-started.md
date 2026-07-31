# 初始化指南

## 1. 确认初始状态

检查 `.ai-workspace/workspace.toml` 的状态为 `CREATED`，并确认 Bootstrap 没有覆盖既有目录。

## 2. 建立环境事实

使用 `initialize-standard-workspace` 和 `inspect-host-environment`。扫描只记录命令、工具链、环境变量名称与敏感分类、经授权的网络探测结果；不得把凭证值写入文件。

## 3. 接入项目

使用 `adapt-project-workspace`。先问询目标和边界，再读取代码、构建文件、Git 配置与已有文档，生成项目插件、项目实例和证据索引。不得从示例或历史项目直接继承事实。

## 4. 配置诊断（可选）

使用 `configure-project-diagnostics`。必须先确认禁止事项、目标类型、部署模型、Observability、关联标识、证据保存和脱敏规则；生成策略后再编译 `AGENTS.md` 诊断硬约束。

## 5. Doctor 与 READY

运行 `standard-workspace-doctor`。只有必需事实、策略、结构和版本均通过时，才可将工作区标记为 `READY`。
