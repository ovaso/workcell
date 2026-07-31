---
name: start-standard-task
description: 在标准工作区中创建并推进机器可读的需求、缺陷、诊断、Review 或研究任务，建立任务档案、标准生命周期、模块 edit/verify/reference 角色、授权、风险、计划、证据和隔离工作区。用于开始新任务、把收件箱事项转为可执行任务、恢复暂停任务，或在实施前重新确认范围和模块职责时。
---

# Start Standard Task

把用户请求转成可追踪、可暂停、可并行且默认不扩大权限的任务。`requirements/<task-id>/task.toml` 是任务状态真相源。

## 启动前置

1. 读取 `AI_WORKSPACE.md`、`.ai-workspace/workspace.toml`、项目插件、环境事实和相关项目规则。
2. 要求工作区处于 `READY`。若为 `DEGRADED`、`PAUSED` 或更早状态，先运行 `$standard-workspace-doctor` 并解决阻断，不通过创建任务绕过工作区门禁。
3. 检查同 ID 任务是否已经存在。存在时读取并恢复，禁止覆盖档案或重置生命周期。
4. 把本次用户请求作为授权边界。已安装工具、可访问远端或项目模块角色不自动授予写入、推送、部署或生产访问权限。

## 创建 INBOX 任务

1. 确认任务标题、类型、稳定 ID 和原始请求。类型使用 `requirement`、`defect`、`diagnostic`、`review`、`maintenance` 或 `research`。
2. 从 `.ai-workspace/templates/task.toml` 复制并填写 Manifest，创建 [task-contract.md](references/task-contract.md) 规定的最小目录。
3. 把用户原始描述写入 `requirement.md`，保留来源、附件和未确认项；不要把推断改写成用户事实。
4. 写入 `INBOX` 初始状态、`workflow.next_action` 与 `workflow.next_gate = "SCOPED"`。尚未确认的远端读取、源码写入和外部副作用继续由项目策略拒绝。

## 发现与定界

1. 在 `INBOX` 状态内执行已授权的本地只读发现。检查代码、Git、配置、项目知识和历史任务，区分事实、推断与待确认项。
2. 从项目插件读取仓库角色上限，再把模块 ID 放入当前任务的机器可读 `scope` 数组：
   - `edit`：当前任务明确允许修改的模块；
   - `verify`：只做契约、编译、测试和链路验证，不修改源文件；
   - `reference`：只读搜索和上下文参考。
   - `excluded`：本任务明确不处理的模块或范围。
3. 未登记模块或证据不足的模块默认 `reference` 并标记阻断。项目插件 `modules[].role` 是任务同名角色的上限：`reference` 不能扩大为 `verify/edit`，`verify` 不能扩大为 `edit`。
4. 向用户确认范围、排除项、模块角色、风险、环境和需要新增的授权。确认后推进到 `SCOPED`。

## 计划与 READY 门禁

1. 在 `plans/` 创建不可覆盖的版本化计划，记录代码基线、实现步骤、对应测试、兼容性、回滚和验证证据要求。
2. 把 `current_plan` 指向最新计划，完成计划确认后推进到 `PLANNED`。
3. 仅在明确授权后准备隔离 `workspaces/<task-id>/`、读取远端、创建分支或安装任务工具。每个动作分别记录授权和结果。
4. 按 [lifecycle-and-gates.md](references/lifecycle-and-gates.md) 检查范围、计划、模块、工作区、测试和写入授权门禁；全部通过后推进到任务 `READY`。
5. 不在本 Skill 中自动开始业务实现。只有用户继续要求实施时才进入 `IMPLEMENTING`。

## 并行协作

- 按模块或不重叠文件组拆分任务，在版本化计划或决策证据中记录负责方、角色、范围和状态。
- 同一模块或文件组同时只允许一个写入负责方；其他参与者使用 `verify` 或 `reference`。
- 子任务不能扩大父任务授权、模块角色或环境范围。
- 汇总者在接受结果前核对实际文件、Git diff、测试证据和任务 Manifest，不把代理口头结论当作完成证据。

## 状态更新规则

- 每次状态变化同时更新 `task.status`、`task.updated_at`、`workflow.next_action`、`workflow.next_gate`、门禁和决定证据，不得只修改 Markdown 说明。
- 不跳过生命周期状态；失败或测试反馈按标准状态回流。
- 暂停时写入 `PAUSED`，并用决定证据记录原状态、原因、恢复条件和未完成动作。
- 完成、`QC_READY`、`RELEASE_READY` 与归档按 [lifecycle-and-gates.md](references/lifecycle-and-gates.md) 执行，不用“代码已写完”替代验证证据。

## 完成输出

报告任务 ID、当前状态、任务目录、模块角色、已有授权、仍禁止的动作、当前计划、隔离工作区、风险、下一门禁和下一步。明确说明本轮是否修改了源码或外部状态。
