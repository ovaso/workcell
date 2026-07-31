# 诊断配置契约

## 真相源

```text
project/diagnostics/diagnostic-profile.toml
.ai-workspace/schemas/diagnostic-profile.schema.json
.ai-workspace/templates/diagnostic-profile.toml
.ai-workspace/policies/diagnostics.toml
diagnostics/targets/
diagnostics/providers/
diagnostics/knowledge/
```

Profile 是项目诊断配置真相源，必须符合 V0.1 Schema。策略文件保存工作区当前失败关闭边界；`AGENTS.md` 是由这些结构化内容编译出的平台适配结果。任务专属证据放入对应 `requirements/<task-id>/`，不放入长期 Profile。

## Profile 状态

聚合文件顶层必须包含 `schema_version = "0.1"`。Profile 状态只使用：

- `unconfigured`：尚未完成问询，只允许本地代码和已有文件分析；
- `configuring`：已确认安全边界，正在问询、查证或形成候选配置；
- `draft`：正在配置或仍有未验证关键事实，不能据此开放远端动作；
- `verified`：完成强制问询、代码查证、获授权事实验证和门禁；
- `degraded`：原已验证能力出现部分失效或冲突，只保留仍被完整证明且获授权的只读能力；
- `stale`：依赖事实已过期或发生漂移，受影响动作失败关闭；
- `disabled`：显式关闭全部 Provider。

`verified` 必须同时满足 `profile.configured_by_interview = true` 并记录 `verified_at`。只有 `verified` 能支撑工作区状态 `DIAGNOSTICS_CONFIGURED`；不得使用 `configured` 作为完成态。

## policies 表

```toml
[policies]
default_action = "deny"
remote_shell = "deny"       # deny | ask | allow
remote_write = "deny"       # deny | ask | allow
credential_output = "deny"
unknown_target = "deny"
allowed_collection_modes = ["local-read"]
forbidden_actions = []
```

`default_action`、`credential_output` 和 `unknown_target` 必须为 `deny`。`allow` 只表达项目级上限，仍需要当前任务授权；生产、写入、重启、部署、删除和数据回放必须单独确认。

采集模式只使用：`local-read`、`local-process-inspect`、`file-copy-read-only`、`api-read-only`、`observability-query`、`remote-command-read-only`。

## targets 数组

每个目标至少记录：

```toml
[[targets]]
id = "service-test"
type = "container"
environment = "test"
fact_status = "code-verified"
endpoint_refs = []
log_locations = []
```

目标类型只使用 Schema 枚举：`local-cli`、`desktop-app`、`local-process`、`library`、`batch-job`、`baremetal-service`、`container`、`kubernetes`、`distributed-system`、`observability-backed`、`hybrid`。

事实状态只使用 `declared`、`code-verified`、`endpoint-verified`、`runtime-observed`、`stale`。在任务证据或诊断知识中补充事实来源、代码位置、观测时间、敏感级别、可信度和过期条件；历史材料本身不能得到 verified 状态。

`endpoint_refs` 保存端点引用，不保存凭证或带凭证 URL。`log_locations` 必须与目标类型和环境一致。

复杂目标的详细发现资料可以保存到 `diagnostics/targets/`，但 `project/diagnostics/diagnostic-profile.toml` 始终是唯一聚合真相源。

## providers 数组

```toml
[[providers]]
id = "local-files"
kind = "local-files"
enabled = true
authorization = "task-scoped"
target_refs = ["service-test"]
credential_refs = []
```

Provider 类型只使用：`local-files`、`local-process`、`file-transfer`、`remote-command`、`container-runtime`、`kubernetes-api`、`logs-api`、`metrics-api`、`traces-api`、`custom`。

授权只使用 `denied`、`read-only`、`ask-each-time`、`task-scoped`。即使 Provider `enabled = true`，仍必须满足：环境能力、Provider 接口、项目策略、目标事实有效和当前任务授权。

凭证仅保存引用，例如 `env://NAME`、`keychain://...`、`file-ref://...`、`vault://...`。不得验证时打印值。

复杂 Provider 的详细配置可以保存到 `diagnostics/providers/`，并由聚合 Profile 引用或汇总。Provider 文件不能形成第二个项目诊断聚合状态。

## authorizations 与 facts

`authorizations` 保存用户确认的动作、目标、环境、只读或任务级模式、来源、确认时间和过期时间。它只能收窄核心与项目策略，不能覆盖禁止项。

`facts` 保存声明、代码查证、配置查证、端点验证和运行观测事实及其证据、观测时间、可信度、敏感级别和过期条件。可复用的详细知识放入 `diagnostics/knowledge/`，但必须由 Profile 中的事实记录建立来源关系。

## correlations 与 retention

`correlations` 记录可跨日志、指标、Trace 和任务证据使用的业务关联标识，并用 `sensitive` 标记敏感值。至少一个来源才能建立关联。

`retention.evidence_directory` 使用安全工作区相对路径；设置保留天数时不得超出用户确认范围。`redaction_required` 默认保持 true。

## 动作判定

每个诊断动作都计算：

```text
环境事实证明能力存在
AND Provider 明确支持该动作
AND Profile 允许目标、环境和采集模式
AND 核心与项目策略允许
AND 当前任务明确授权
AND 依赖事实未过期
```

任一未知、冲突或过期值都拒绝动作。连通成功和凭证可用不能扩大授权。

## 完成门禁

- 已完成强制问询，Profile 标记 `configured_by_interview = true`。
- 已通过代码和配置查证建立目标模型。
- 获授权验证的事实有当前证据；未验证事实不支撑远端动作。
- Profile 符合 `.ai-workspace/schemas/diagnostic-profile.schema.json`。
- 未保存凭证值，默认动作和未知目标保持拒绝。
- Profile 与 `.ai-workspace/policies/diagnostics.toml` 一致。
- 诊断硬约束已重新编译到生效的 AI 指令。
- 最小 dry run 未越权、未写入目标且结果可审计。
- `$standard-workspace-doctor` 通过。

任一门禁失败时保持 `unconfigured`、`configuring`、`draft`、`degraded` 或 `stale`，禁止受影响的远端动作。只有 `verified` Profile 才能支持工作区进入 `DIAGNOSTICS_CONFIGURED`。
