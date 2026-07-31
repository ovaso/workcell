# AGENTS

> 本文件由标准工作区根据结构化策略编译。安全策略和当前已验证事实优先于历史文档。

## 默认规则

- 首先读取 `AI_WORKSPACE.md`、`.ai-workspace/workspace.toml` 和当前任务 Manifest。
- 能力存在不代表获得操作授权。
- 默认只读、失败关闭；未登记或事实过期的目标禁止操作。
- 禁止输出、复制到报告或写入 memory 的凭证值。
- 禁止默认安装工具、修改 Shell、访问远端、覆盖非空目录或自动提交代码。

<!-- ai-workspace:generated:start -->
### 当前诊断边界

- 诊断状态：未配置。
- 远端 Shell：禁止。
- 远端写入：禁止。
- 当前允许：读取本地代码、配置与已经存在的本地日志。
<!-- ai-workspace:generated:end -->
