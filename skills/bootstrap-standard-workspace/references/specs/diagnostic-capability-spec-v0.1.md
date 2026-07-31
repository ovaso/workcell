# Diagnostic Capability Specification V0.1

## 1. 定义

诊断能力用于收集、关联和分析某个软件目标的运行事实。它是项目能力插件，不默认等于服务器排查。

## 2. 目标类型

```text
local-cli
desktop-app
local-process
library
batch-job
baremetal-service
container
kubernetes
distributed-system
observability-backed
hybrid
```

## 3. 配置前置

用户提出配置项目诊断能力时必须进入交互问询。第一组问题只确认安全与权限边界，并立即编译进入项目级 AI 规则。

问询顺序：

1. 绝对禁止和允许事项；
2. 目标类型；
3. 部署、运行和环境模型；
4. 日志、指标、Trace、崩溃或本地状态来源；
5. 业务关联标识；
6. 采集、复现、脱敏、保存和保留流程。

## 4. 事实来源

```text
user-declared
code-discovered
config-discovered
endpoint-verified
runtime-observed
historical
```

安全禁止事项和用户确认的权限优先级最高。可达不代表授权。

## 5. Provider 接口

```text
discover
questionnaire
requirements
validate
plan
collect
poll
correlate
sanitize
index
summarize
health
```

## 6. 结构化文件

聚合真相源固定为：

```text
project/diagnostics/diagnostic-profile.toml
```

目标、Provider 和知识的详细资源可放在：

```text
diagnostics/targets/
diagnostics/providers/
diagnostics/knowledge/
```

聚合文件记录 `schema_version`、profile、失败关闭策略、目标、Provider、关联标识、逐动作授权、事实和证据保留规则。项目插件只引用该能力，不复制诊断事实。

profile 状态为 `unconfigured / configuring / draft / verified / degraded / stale / disabled`。只有 `verified` 可以支撑工作区状态 `DIAGNOSTICS_CONFIGURED`。

## 7. 执行条件

```text
环境能力满足
AND Provider 支持
AND 项目策略允许
AND 当前任务授权
```

任一条件不满足时失败关闭。

授权必须收窄到动作、目标和环境，并记录来源、确认时间及可选失效时间。笼统的 `diagnostics = true` 不构成授权。

## 8. AGENTS 联动

结构化诊断策略是真相源。禁止登录、禁止远程 Shell、只读采集、凭证保护、允许端点和事实过期停止条件必须编译进入项目级 AI 规则文件。

## 9. 未配置状态

诊断状态为 `unconfigured` 时：

- 只允许分析本地代码和已有文件；
- 禁止所有远端诊断动作；
- 禁止使用未登记端点、目录、节点和 Provider。
