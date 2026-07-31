# AI Workspace Entry

## 启动顺序

每次进入本工作区时：

1. 读取 `.ai-workspace/workspace.toml` 和 `.ai-workspace/versions.lock`。
2. 读取 `.ai-workspace/policies/` 下当前策略。
3. 根据任务只加载相关的环境、项目、诊断和任务事实；不要默认读取全部历史。
4. 读取适用的项目插件与当前任务 Manifest。
5. 在执行写入、外部访问或诊断动作前校验授权。

## 真相与优先级

发生冲突时按以下顺序处理：

```text
安全禁止事项
> 用户对当前任务的明确授权
> 当前运行或端点验证事实
> 当前项目配置
> 项目插件声明
> 代码推导
> 历史计划、文档和 memory
```

不得用历史记录替代当前事实；不得选择权限更大或风险更高的解释。事实冲突、过期或缺失时，停止相关动作并请求确认或重新采集。

## 状态机

标准工作区按以下主路径演进：

```text
CREATED
→ ENVIRONMENT_INITIALIZED
→ PROJECT_ATTACHED
→ PROJECT_ADAPTED
→ DIAGNOSTICS_CONFIGURED（可选）
→ READY
```

只有 `standard-workspace-doctor` 通过后才能标记为 `READY`。发现关键事实漂移时标记为 `DEGRADED`，不要静默继续。

## 能力与授权

一个动作可执行必须同时满足：

```text
宿主环境具备能力
∧ Provider 支持该动作
∧ 项目策略允许
∧ 当前任务获得授权
```

命令、凭证或网络可用只是能力事实，不构成授权。默认禁止远端 Shell、远端写入、工具安装、Shell 修改、非空目录覆盖以及凭证输出。

## 文件职责

- `.ai-workspace/`：标准、Schema、策略、版本和状态控制面。
- `environment/`：当前宿主环境事实与历史快照。
- `project/`：项目插件、项目实例和项目能力配置。
- `requirements/`：需求、缺陷、诊断、Review 等任务档案。
- `mirror/`：项目主线或只读参考镜像。
- `workspaces/`：隔离的任务执行目录。
- `remotes/`：远端注册表，不直接保存凭证值。
- `diagnostics/`：跨任务诊断 Provider 和知识。
- `knowledge/`：已验证、可复用知识。
- `memory/`：工作区级演进记忆，不作为动态事实源。
- `feedback/`：工作区实践的脱敏反馈候选，不是已采纳标准。
- `skills/`：展开后工作区自己的运行时 Skills。

## 运行时 Skills

- `initialize-standard-workspace`：初始化身份和基础事实。
- `inspect-host-environment`：安全采集或刷新宿主环境事实。
- `adapt-project-workspace`：问询、查证并生成项目插件。
- `configure-project-diagnostics`：交互式配置诊断能力和硬约束。
- `standard-workspace-doctor`：检查结构、事实、状态与漂移。
- `start-standard-task`：建立机器可读任务和隔离边界。
- `upgrade-standard-workspace`：预览、备份并执行受控升级。
- `extract-standard-feedback`：从已授权实践生成脱敏反馈候选包。

平台若不支持自动发现 Skills，应显式读取相应 `SKILL.md` 后执行。
