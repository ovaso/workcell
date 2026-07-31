# AGENTS

> 本文件是标准工作区的 AI 平台适配入口。结构化策略和事实位于 `.ai-workspace/`、`environment/` 与 `project/`；当两者冲突时，以安全策略和当前已验证事实为准。

## 默认规则

- 首先读取 `AI_WORKSPACE.md`、`.ai-workspace/workspace.toml` 和当前任务 Manifest。
- 当前状态为 `CREATED` 时，不得声称环境或项目已经初始化。
- 能力存在不代表获得操作授权。
- 默认只读、失败关闭；未登记或事实过期的目标禁止操作。
- 禁止输出、复制到报告或写入 memory 的凭证值。
- 禁止默认安装工具、修改 Shell、访问远端、覆盖非空目录或自动提交代码。
- 项目规则必须由 `adapt-project-workspace` 基于问询、事实和代码查证生成。
- 项目诊断规则必须由 `configure-project-diagnostics` 交互生成；未配置时只允许本地代码和已有文件分析。

## 生成内容

下方区域由标准工作区根据结构化策略重新编译。不要将手工编辑作为唯一规则来源。

<!-- ai-workspace:generated:start -->
### 当前诊断边界

- 诊断状态：未配置。
- 远端 Shell：禁止。
- 远端写入：禁止。
- 未登记端点与节点：禁止访问。
- 当前允许：读取本地代码、配置与已经存在的本地日志。
<!-- ai-workspace:generated:end -->
