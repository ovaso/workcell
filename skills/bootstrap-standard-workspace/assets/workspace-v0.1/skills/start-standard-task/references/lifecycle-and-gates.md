# 任务生命周期与门禁

## 唯一状态机

```text
INBOX
  -> SCOPED
  -> PLANNED
  -> READY
  -> IMPLEMENTING
  -> VERIFYING
  -> DEV_FEEDBACK / TEST_FEEDBACK
  -> QC_READY
  -> RELEASE_READY
  -> DONE
  -> ARCHIVED
```

任一活动状态可以显式进入 `PAUSED`。发现是 `INBOX` 内动作；修复是 `DEV_FEEDBACK` 或 `TEST_FEEDBACK` 内动作，不为这些动作创建额外状态。

## 转换门禁

### INBOX -> SCOPED

- 原始需求、任务类型、稳定 ID 和项目插件引用已记录。
- 已完成必要的代码、配置和项目事实发现。
- `scope.edit/verify/reference/excluded` 无重复且未扩大项目角色。
- 用户已确认包含项、排除项、未知项和安全边界。

### SCOPED -> PLANNED

- `current_plan` 指向不可覆盖的版本化计划。
- 计划覆盖每个 `edit` 模块及匹配测试、验证、兼容性和回滚。
- 旧计划已进入 `superseded_plans`。
- `plan` 证据与计划门禁已记录。

### PLANNED -> READY

- 范围和当前计划门禁为 `passed`，或有明确决定证据的 `waived`。
- 所需隔离工作区、分支、工具和环境快照已验证。
- 必要的源码写入、远端读取或诊断动作已获得当前任务授权。
- 并行写入范围不重叠，失败关闭条件明确。

### READY -> IMPLEMENTING

- 用户明确要求开始实施。
- 当前代码基线仍与计划一致；漂移时留在或退回适当的前置状态重新定界。
- 所有写入都位于 `scope.edit`。

### IMPLEMENTING -> VERIFYING

- 计划内变更已完成或明确记录未完成项。
- diff 与 `scope.edit` 一致，没有范围外写入。
- 匹配测试和验证清单完整。

### VERIFYING -> DEV_FEEDBACK / TEST_FEEDBACK / QC_READY

- 开发环境反馈进入 `DEV_FEEDBACK`；测试环境反馈进入 `TEST_FEEDBACK`。
- 在对应反馈状态内完成定位、修复和回归，再返回 `VERIFYING`。
- 所有必要验证通过且残余风险可接受时进入 `QC_READY`。
- 无法运行关键验证不得进入 `QC_READY`，除非有明确 `waived` 门禁和决定证据。

### QC_READY -> RELEASE_READY

- 独立 Review 和项目专项门禁通过。
- 变更、测试、数据库、配置、兼容性、回滚和发布顺序材料齐全。
- 发布前仍需要的人工动作已列出，未授权动作没有被执行。

### RELEASE_READY -> DONE

- 任务定义的交付目标已经完成。
- 最终代码、测试、Review、发布或决定证据可追溯。
- 不存在失败门禁或未处理阻断问题。

### DONE -> ARCHIVED

- 最终提交、分支、环境和交付摘要可追溯。
- 工作区无未保存改动、未处理提交或未归档证据。
- 删除、压缩或迁移隔离工作区已单独获得确认；归档任务档案不等于删除源码副本。

## PAUSED

用 `decision` 证据记录暂停前状态、原因、恢复条件和未完成动作。恢复时回到暂停前状态并重新检查对应门禁，不得跳到更后的状态。

## 禁止行为

- 不允许从 `INBOX` 直接进入 `IMPLEMENTING`。
- 不允许通过只改 `task.status` 绕过 `workflow.next_gate` 和门禁证据。
- 不允许把反馈修复包装成新状态名。
- 不允许从反馈状态直接进入 `DONE`。
- `ARCHIVED` 默认不可变；恢复应创建明确恢复决定或新任务。
