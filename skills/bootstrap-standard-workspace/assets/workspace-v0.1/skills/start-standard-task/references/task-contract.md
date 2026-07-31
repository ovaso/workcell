# 任务契约

## 真相源与目录

```text
requirements/<task-id>/
  task.toml
  requirement.md
  plans/
  decisions/
  changes/
  evidence/
  logs/
  reviews/
  memory/
workspaces/<task-id>/
  ...仅在任务准备隔离代码时创建...
```

按任务类型创建必要子目录；`task.toml` 必须存在。它是状态真相源，且必须符合 `.ai-workspace/schemas/task.schema.json`。创建时使用 `.ai-workspace/templates/task.toml`，不要维护第二套字段。

全部任务内容属于 `workspace` 所有权，发行升级不得覆盖。

## task 表

记录稳定 `id`、展示名称、标题、任务类型、标准 `status`、项目插件引用和时间。任务 ID 用于目录、分支和关联；展示名称可以使用中文。

任务类型仅使用：`requirement`、`defect`、`diagnostic`、`review`、`maintenance`、`research`。

## scope 表

模块角色由四个唯一字符串数组表示：

```toml
[scope]
edit = ["service-app"]
verify = ["service-api"]
reference = ["shared-library"]
excluded = ["deployment"]
```

角色权限顺序为：

```text
excluded / reference < verify < edit
```

- `edit`：当前任务允许修改的模块；不自动包含提交、推送、发布或外部写入。
- `verify`：只做契约、构建、测试和链路验证，不修改源文件。
- `reference`：只读检索与上下文参考。
- `excluded`：明确不处理，用于阻止任务无证据扩散。

项目插件 `project/plugin/project-plugin.json` 中 `modules[].role` 是上限，角色同样只使用 `edit`、`verify`、`reference`。任务只能收窄，不能扩大；一个模块只能出现在一个 scope 数组中。`task.project_plugin_ref` 应指向该 JSON，例如：

```toml
[task]
project_plugin_ref = "project/plugin/project-plugin.json"
```

## workflow 表

- `current_plan` 指向当前生效的版本化计划；没有计划时使用空字符串或 null。
- 新计划使用新文件，把旧路径追加到 `superseded_plans`，禁止原地覆盖。
- `next_action` 和 `next_gate` 必须与当前状态相符。
- `branch` 从稳定任务 ID 派生；不得在多个文档手工维护不同分支值。

## gates 与 evidence

门禁状态只使用 `pending`、`passed`、`failed`、`waived`、`not-applicable`。`passed` 或 `waived` 应提供 `evidence_refs`。

证据类型只使用：`requirement`、`plan`、`code`、`test`、`log`、`metric`、`trace`、`review`、`decision`、`release`。证据引用必须说明实际位置和观测时间；不得把 memory 或口头结论当作状态真相源。

任务 Manifest 当前不保存凭证或笼统的能力开关。当前动作是否允许，必须同时读取核心策略、项目插件策略、诊断配置和本次用户授权。能力存在不等于授权。

## 并行写入

在计划或 `decisions/` 证据中登记参与者、模块、文件组和只读或写入模式，并把决定文件加入 `evidence`。同一时间只允许一个参与者拥有同一文件的写入权；参与者不得超出 `scope.edit`。

并行安排是协作边界，不改变项目角色、任务范围或用户授权。
