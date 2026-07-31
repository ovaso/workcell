# AI Native Standard Workspace

这是由 `bootstrap-standard-workspace` 创建的个人 AI 原生标准工作区。它提供通用工作流和事实协议，但尚未代表当前机器或任何项目的真实状态。

## 首次使用

1. 让 AI 读取 `AI_WORKSPACE.md` 与 `.ai-workspace/workspace.toml`。
2. 使用 `initialize-standard-workspace` 完成初始化并建立宿主环境事实。
3. 使用 `adapt-project-workspace` 接入代码、远端和项目规则。
4. 如项目需要诊断能力，使用 `configure-project-diagnostics` 完成交互式配置。
5. 使用 `standard-workspace-doctor` 检查事实、策略和结构；通过后才能进入 `READY`。

## 重要边界

- 初始状态为 `CREATED`，所有项目事实均未建立。
- 本机存在某个命令，不代表允许用它访问外部系统。
- 未配置诊断能力时，只允许分析本地代码和已有文件。
- 结构化事实与策略是真相源，`AGENTS.md` 等平台文件是编译适配结果。
- `requirements/` 保存任务档案，`workspaces/` 保存隔离执行目录，`mirror/` 保存只读参考镜像。

详细入口见 `AI_WORKSPACE.md`，标准协议见 `.ai-workspace/specs/`。
