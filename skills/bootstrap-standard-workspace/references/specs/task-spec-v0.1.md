# Standard Task Specification V0.1

## 1. 目的

需求、缺陷、诊断、Review、维护和研究都表示为独立任务实例。任务 Manifest 是当前状态的唯一机器可读入口；计划、memory、Git 和日志是证据，不得再由它们反向猜测任务状态。

## 2. 稳定 ID 与展示名称

每个任务同时维护：

- `id`：用于目录、分支、命令和关联的稳定机器 ID；
- `display_name`：面向个人阅读的名称，可使用中文；
- `title`：本次任务的简短目标。

目录和分支由 `id` 派生，禁止在多处手工维护不一致的副本。

V0.1 机器 ID 只使用小写 ASCII 字母、数字、点、下划线和连字符；中文、空格及其他展示字符放入 `display_name`。项目插件可以定义分支前缀，但不得改变任务 ID 本身。

## 3. 生命周期

```text
INBOX
→ SCOPED
→ PLANNED
→ READY
→ IMPLEMENTING
→ VERIFYING
→ DEV_FEEDBACK / TEST_FEEDBACK
→ QC_READY
→ RELEASE_READY
→ DONE
→ ARCHIVED
```

任何活动状态均可显式进入 `PAUSED`。状态迁移必须记录下一步与下一道门禁，不能只改状态字段。

## 4. 模块角色

- `edit`：当前任务允许修改的模块。
- `verify`：只用于契约、构建或链路验证的模块。
- `reference`：只读参考模块。
- `excluded`：本任务明确不处理的模块或范围。

并行代理的写入所有权必须落在 `edit` 范围内，且同一文件不得被多个代理同时拥有。

## 5. 计划与历史

- `current_plan` 明确指向当前生效计划。
- 新计划不得原地覆盖旧版本；旧计划进入 `superseded_plans`。
- 计划只描述预期工作、验证和风险；执行事实写入变更记录和证据。
- memory 可帮助恢复会话，但不是任务状态的真相源。

## 6. 门禁与证据

门禁状态为 `pending / passed / failed / waived / not-applicable`。任何 `passed` 或 `waived` 都应引用证据或决定记录。

证据类型至少包括：需求、计划、代码、测试、日志、指标、追踪、Review、决策和发布材料。原始日志应通过 Manifest 记录来源、时间窗口、关联标识、脱敏和保留策略。

## 7. 安全边界

任务授权只能缩小或临时开放已登记的项目能力，不能绕过核心禁止事项。环境具备某个命令、项目配置了某个 Provider，均不自动构成当前任务授权。

## 8. 目录建议

```text
requirements/<task-id>/
├── task.toml
├── requirement.md
├── plans/
├── decisions/
├── changes/
├── evidence/
├── logs/
├── reviews/
└── memory/
```

是否创建全部子目录由任务类型决定；`task.toml` 必须始终存在。
