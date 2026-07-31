---
name: configure-project-diagnostics
description: 通过强制交互问询、代码查证和事实验证，为标准工作区配置项目诊断目标、Provider、安全边界与采集流程。用于首次启用或重新配置本地 CLI、桌面应用、本地进程或批任务、裸机服务、容器、Kubernetes、Observability 或混合系统诊断，以及端点、凭证引用、权限、部署模型或诊断流程发生变化时。
---

# Configure Project Diagnostics

为项目建立可审查、可验证、默认拒绝的诊断能力。把结构化配置作为真相源；能力存在不代表获得操作授权。

## 强制边界

- 先读取 `AI_WORKSPACE.md`、`.ai-workspace/workspace.toml`、项目插件、环境事实和现有诊断配置。
- 仅在工作区至少完成 `PROJECT_ADAPTED` 后配置诊断；否则停止并转回项目适配。
- 每次首次配置或安全边界变化时都进行显式交互问询。历史文档、旧配置和工具可用性不能替代用户确认。
- 在用户回答第一组安全问题前，不探测远端、不验证端点、不读取凭证、不启动复现、不执行采集。
- 按以下条件逐项判定动作：环境能力满足、Provider 支持、项目策略允许、当前任务明确授权。任一条件未知或不满足即拒绝。
- 只保存凭证引用，不保存 token、密码、私钥或 kubeconfig 内容。
- 将未配置、验证失败、事实过期或权限冲突视为失败关闭。此时只允许分析本地代码和已有文件。

## 配置流程

1. 读取 [questionnaire.md](references/questionnaire.md)，提出第一组安全与权限问题并等待明确回答。
2. 立即把确认的禁止项、默认动作、环境边界和授权有效期写入预览；先让用户核对，不执行诊断动作。
3. 根据目标类型读取 [target-profiles.md](references/target-profiles.md) 中对应章节，继续询问运行、部署、证据来源、关联标识、脱敏和保留要求。
4. 对项目代码和配置进行只读查证：定位启动入口、日志配置、遥测 SDK、健康检查、崩溃处理、容器或集群清单、业务关联标识和环境选择逻辑。
5. 区分声明与事实。为每项事实记录来源、证据、观测时间、敏感级别、可信度和过期条件。不得把历史文档直接提升为当前运行事实。
6. 仅在用户已授权对应验证动作时执行最小只读验证。优先本地静态检查；远端元数据、端点探测、采样采集或轮询分别取得授权。
7. 选择满足要求的 Provider，验证其 `discover/questionnaire/requirements/validate/plan/collect/poll/correlate/sanitize/index/summarize/health` 能力。缺少必要能力时停止，不临时绕过策略。
8. 按 [configuration-contract.md](references/configuration-contract.md) 生成配置变更预览，列出 `project/diagnostics/diagnostic-profile.toml`、诊断策略、未验证事实、过期条件和禁止动作。
9. 获得用户对预览的明确确认后，写入符合 Schema 的诊断 Profile 和 `.ai-workspace/policies/diagnostics.toml`；让项目插件的诊断 capability 引用 `project/diagnostics/diagnostic-profile.toml`，再重新编译项目级 AI 适配规则，使硬约束进入实际生效的 `AGENTS.md` 等入口。
10. 执行配置校验和一次获授权的最小 dry run。不得用成功连通性推导额外授权。
11. 运行 `$standard-workspace-doctor`。只有配置、生成规则和 Doctor 均通过后，才把工作区推进到 `DIAGNOSTICS_CONFIGURED`；是否进入 `READY` 仍由完整 Doctor 门禁决定。

## 代码与事实查证要求

- 给出每个代码结论的仓库、文件和符号位置。
- 给出每个运行事实的目标、环境、来源、验证方式和观测时间。
- 对代码声明与运行事实冲突的情况把 Profile 保持为 `draft` 或标记为 `stale`；关键能力受影响时将工作区标记为 `DEGRADED`，请求裁决或继续验证。
- 对生产、写操作、远程 Shell、重启、扩缩容、部署、删除、配置变更和数据回放保持单独授权，不把“允许诊断”解释为这些权限。

## 完成输出

报告已配置目标和 Provider、有效授权、明确禁止项、代码证据、已验证事实、未验证或已过期事实、dry run 结果、Doctor 结果以及仍被失败关闭的动作。不要输出凭证值。
