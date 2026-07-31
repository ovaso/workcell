# 生命周期

## 工作区生命周期

```text
EMPTY
  -> CREATED
  -> ENVIRONMENT_INITIALIZED
  -> PROJECT_ATTACHED
  -> PROJECT_ADAPTED
  -> DIAGNOSTICS_CONFIGURED（可选）
  -> READY
  -> DEGRADED / PAUSED
  -> ARCHIVED
```

### EMPTY -> CREATED

Bootstrap 只向空目录展开标准 Assets，写入发行来源并进行结构校验，不扫描环境、不联网、不接入项目。

### CREATED -> ENVIRONMENT_INITIALIZED

采集命令、工具链、环境变量和网络事实，形成首个环境快照和能力建议。

### ENVIRONMENT_INITIALIZED -> PROJECT_ATTACHED

确认单仓或多仓，引入项目代码镜像，登记远端和已有规范、文档、知识与需求资料。

### PROJECT_ATTACHED -> PROJECT_ADAPTED

通过交互问询、代码发现和事实验证生成项目插件，建立模块、分支、构建、测试、Review、发布和风险模型。

### PROJECT_ADAPTED -> DIAGNOSTICS_CONFIGURED

按需交互配置诊断目标、Provider、安全边界、端点、标识和采集流程。未配置时必须失败关闭远端诊断。

### READY

只有环境、项目、策略、AI 规则和 Doctor 全部通过后才能进入 READY。

## 任务生命周期

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

允许任一活动状态显式进入 `PAUSED`。发现和修复属于状态内动作：范围发现发生在 `INBOX -> SCOPED`，反馈修复发生在 `DEV_FEEDBACK / TEST_FEEDBACK` 中。项目插件可以增加状态转换门禁，但不得创建互不兼容的项目专属状态名。

## 标准演进闭环

任务完成或定期复盘后，可在明确授权下从当前工作区生成脱敏反馈候选。候选留在工作区，直到用户明确交给标准仓库；标准仓库导入后先形成提案，再经审核、实现、全量验证和升级影响评估进入新 Release。该闭环不改变工作区主生命周期，也不授予自动上传、自动采纳或自动升级权限。
