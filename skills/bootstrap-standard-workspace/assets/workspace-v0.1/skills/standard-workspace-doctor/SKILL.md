---
name: standard-workspace-doctor
description: 对标准 AI 工作区执行只读优先的结构、安装 Release 收据与发行文件哈希、Manifest、生命周期、Skill、任务角色、诊断安全和文件所有权健康检查。用于初始化或适配后验收、进入 READY 前门禁、任务启动前检查、升级前后验证、配置漂移排查，以及用户要求检查、诊断或修复标准工作区时。
---

# Standard Workspace Doctor

先用确定性只读检查建立事实，再给出最小修复建议。Doctor 不因“发现了修复方法”而获得写入权限。

## 默认执行

1. 定位包含 `AI_WORKSPACE.md` 与 `.ai-workspace/workspace.toml` 的工作区根目录。找不到时停止，不把普通项目目录误判为标准工作区。
2. 读取 `AI_WORKSPACE.md`、`.ai-workspace/workspace.toml`、`.ai-workspace/versions.lock`、`.ai-workspace/release-manifest.json`、项目与诊断配置；不读取凭证值。
3. 运行只读检查脚本：

   ```bash
   python3 skills/standard-workspace-doctor/scripts/doctor.py /absolute/workspace/path --json
   ```

4. 根据 [checks.md](references/checks.md) 补充脚本无法判断的代码、Git、生成链路和外部事实检查。所有外部验证仍需相应授权。
5. 按严重程度报告问题、证据路径、影响、失败关闭范围和建议动作。
6. 仅当没有 `ERROR` 时判定结构门禁通过。存在未解决授权、过期事实或无法验证的关键条件时，不得把工作区标记为 `READY`。

## 只读边界

- 不自动创建缺失文件、不改 Manifest、不格式化、不删除、不安装工具、不联网、不更新 Git 引用、不启动服务。
- 不执行配置中登记的诊断 Provider；Doctor 只验证其声明和本地可见结构。端点健康检查必须由用户授权，并由诊断流程执行。
- 不把警告静默降级。无法解析真相源、生命周期非法、任务角色越权、诊断默认放行或所有权冲突均作为错误。
- 不跟随未知符号链接扫描工作区外内容。

## 修复模式

只有用户明确要求修复后才进入修复模式：

1. 把每项修复分为纯生成、工作区配置变更、用户内容变更和外部动作。
2. 先展示准确文件影响和拟执行命令；涉及覆盖、删除、迁移或外部状态时先建立可恢复快照并再次确认。
3. 一次只处理已授权问题，保留未知和项目自有内容。
4. 修复后重新运行完整 Doctor。不得通过手工把状态改成 `READY` 来绕过错误。

## 输出格式

先给结论：`PASS`、`PASS_WITH_WARNINGS` 或 `FAIL`。随后按 `ERROR`、`WARN`、`INFO` 列出检查代码、路径、事实证据和建议。最后说明：

- 当前工作区生命周期状态；
- 哪些能力被失败关闭；
- 是否满足进入 `READY` 的条件；
- 是否执行了任何修改；
- 如需修复，哪些动作仍等待授权。
