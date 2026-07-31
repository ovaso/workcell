---
name: upgrade-standard-workspace
description: 安全预览并升级标准 AI 工作区的发行版、Schema、运行时 Skills 和生成适配文件，同时完整保护用户、项目和任务内容。用于检查或应用稳定 Release 升级、执行 Migration、升级后验证或回滚，以及用户要求更新工作区标准版本时；强制先校验来源、生成影响预览、建立可恢复快照并取得明确确认。
---

# Upgrade Standard Workspace

把升级视为受控迁移，不视为文件覆盖。只替换 `distribution`，重新编译 `generated`，完整保留 `workspace`。

## 强制边界

- 只接受不可变稳定 Release、明确版本和完整文件哈希；不得把 `main`、最新提交或未校验目录作为自动升级目标。
- 默认只检查和预览。下载、写入、覆盖、删除、迁移、切换版本和回滚分别需要相应授权。
- 当前机器具备 Git、网络、解压或复制能力不等于获得这些动作的授权。
- 不在 Skill 执行期间原地覆盖正在运行的 Skill。把候选版本放入临时或并列目录，验证后再切换。
- 当前安装收据固定为 `.ai-workspace/release-manifest.json`。它不自哈希，必须先用匹配 Release 的 Bootstrap 外层 checksum 验证其可信来源。
- 缺少当前文件清单、候选清单、所有权、Migration 链、校验值或恢复方案时失败关闭。

## 预检与预览

1. 读取 `AI_WORKSPACE.md`、`.ai-workspace/workspace.toml`、`.ai-workspace/versions.lock`、`.ai-workspace/release-manifest.json` 和文件所有权；先确认安装收据符合 Schema V0.1，且未把自身列入 `files`。
2. 运行 `$standard-workspace-doctor` 获取升级前基线。已有错误必须先解释；不得用升级顺带覆盖未知问题。
3. 获取用户指定的候选 Release。联网或下载前先确认授权，随后验证版本、来源、Manifest、SHA-256 和可用签名。
4. 选择从当前版本到目标版本的连续 Migration；存在跳跃、降级或不兼容 Schema 时停止。
5. 运行只读预览脚本：

   ```bash
     python3 skills/upgrade-standard-workspace/scripts/preview_upgrade.py \
       --workspace /absolute/workspace \
       --current-manifest /absolute/workspace/.ai-workspace/release-manifest.json \
       --candidate-root /absolute/candidate-release \
       --candidate-manifest /absolute/candidate-release/.ai-workspace/release-manifest.json \
       --json
   ```

6. 按 [upgrade-protocol.md](references/upgrade-protocol.md) 展示新增、替换、删除、重新生成、保留、所有权变化、冲突，以及固定排在最后的 `replace-receipt`。预览脚本不应用任何文件。
7. 对发行文件的本地修改、未知现有文件、所有权变化、缺失候选文件和哈希不符保持阻断；不得自动选择“以新版为准”。

## 快照与确认

1. 选择能够真实恢复的快照方式：完整文件快照，或可信 VCS 检查点加所有受影响、未跟踪和工作区元数据文件的补充快照。
2. 把快照放在不会被本次升级覆盖的位置，生成内容清单和校验值，并实际验证可读取。
3. 向用户展示目标版本、Migration、准确文件影响、冲突处理、生成文件重建、快照位置、回滚步骤和预计外部动作。
4. 等待用户对这份具体计划明确确认。较早的“请升级”不能替代影响预览后的确认。

## 应用升级

1. 在并列暂存目录验证候选发行内容，记录升级事务日志。
2. 按 Migration 顺序操作：
   - 仅替换未被用户修改的 `distribution`；
   - 通过编译器重建 `generated`，不把候选生成文件直接当真相源；
   - 不覆盖、删除或移动 `workspace`；新增工作区模板只能作为可选 seed；
   - 对已确认的冲突使用用户选定策略，并在事务日志中逐项记录。
3. 每步后验证路径仍位于工作区内、哈希符合计划、用户内容仍存在。发现计划外影响立即停止。
4. 完成 Migration 后重编译 AI 适配文件，再运行完整 `$standard-workspace-doctor` 和发行校验。
5. 只有全部验证通过后才更新 `.ai-workspace/versions.lock` 和当前发行指针。
6. 将候选 `.ai-workspace/release-manifest.json` 与已通过外层 checksum 验证的候选字节再次比较，然后原子替换当前安装收据。该替换必须是升级事务的最后一次工作区写入；失败时按升级失败回滚。

## 失败与回滚

- 任一步失败都停止后续 Migration，不尝试带病继续。
- 默认按已验证快照回滚本次已应用动作，再次运行 Doctor。
- 若用户要求保留失败现场，先确认并保持工作区 `DEGRADED`，明确哪些能力失败关闭。
- 不删除候选版本、快照或事务日志，直到用户确认升级稳定并授权清理。

## 完成输出

报告原版本、目标版本、Release 校验、Migration、实际文件动作、保留的用户内容、冲突决策、快照与回滚位置、Doctor 结果和当前生命周期状态。明确说明未执行的下载、删除、自更新或外部动作。
