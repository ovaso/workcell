# 升级协议

## 发行清单

预览脚本使用 JSON 清单：

```json
{
  "schema_version": "0.1",
  "release_version": "0.2.0",
  "files": [
    {
      "path": "skills/example/SKILL.md",
      "owner": "distribution",
      "sha256": "64-character-lowercase-hex"
    }
  ]
}
```

该 JSON 是不可变稳定 Release 及其安装收据使用的完整性清单，固定安装在 `.ai-workspace/release-manifest.json`，包含 Schema 版本、发行版本、所有权和文件哈希。它不等同于 `.ai-workspace/distribution.manifest`：后者只是 Doctor 和修复流程用于核对 distribution 路径与所有权的纯路径 allowlist，不能传给升级预览脚本，也不能用当前工作区文件的哈希临时补造成 Release 清单。

- `schema_version` 必须为 `0.1`，只允许 `schema_version`、`release_version`、`files` 三个顶层字段。
- `path` 必须是无 `..` 的工作区相对文件路径。
- `owner` 只允许 `distribution`、`generated`、`workspace`。
- 每个路径只出现一次。
- `files` 必须与发行资产内全部普通文件完全对应，但必须排除 `.ai-workspace/release-manifest.json` 自身。
- 候选清单中的实际文件必须与 `sha256` 一致。
- 当前清单的哈希用于判断发行文件是否被本地修改，不能用当前文件重新计算后覆盖记录。

清单自身不自哈希，避免形成递归摘要。候选收据的可信字节由 Bootstrap Skill 外层 `checksums/workspace-v0.1.sha256`（以及未来可选的 Release 签名）保护；调用预览前必须完成该外层校验。预览脚本还会确认 `--current-manifest` 与工作区安装收据逐字节一致、`--candidate-manifest` 与候选目录安装收据逐字节一致，并拒绝候选目录中的未列入文件。

## 所有权处理

| 所有权 | 升级动作 |
|---|---|
| `distribution` | 仅在当前文件仍匹配已安装发行哈希时新增、替换或删除；本地修改形成冲突。 |
| `generated` | 从新的结构化事实和策略重新编译；候选文件只可作为编译器输入或验证样例。 |
| `workspace` | 始终保留；新版内容只能作为可选 seed，由用户决定是否采用。 |

所有权变化必须由显式 Migration 解释并在确认中单列。没有 Migration 时保持冲突。

## 预览动作

- `add`：新增发行文件，目标路径原先不存在。
- `replace`：当前发行文件未修改，候选内容变化。
- `remove`：旧发行文件未修改，候选清单已移除。
- `unchanged`：当前与候选哈希相同。
- `preserve`：保留工作区文件。
- `offer-seed`：目标不存在时提供新的工作区模板，但不自动写入。
- `regenerate`：升级后从真相源重新生成。
- `replace-receipt`：其余动作和验证全部成功后，最后原子替换安装收据；不得提前执行。
- `conflict`：本地修改、未知占用、所有权变化、缺失文件或哈希不符。

预览出现 `conflict` 时 `safe_to_apply` 必须为 `false`。

## 快照要求

快照至少覆盖：

- `.ai-workspace` 下的身份、版本、清单、状态和升级事务数据；
- 所有计划新增、替换、删除或重新生成的现有文件；
- 受影响父目录中的未知和未跟踪用户文件；
- 所有被 Migration 修改的 `workspace` 元数据；
- 当前发行指针或安装目录链接。

仅记录 Git commit 不足以保护未跟踪文件、嵌套仓库、外部符号链接目标和不受 Git 管理的工作区数据。选择 VCS 快照时必须补齐这些内容。

快照收据记录时间、工作区、当前版本、文件清单、哈希、存放位置和恢复命令。无法验证恢复路径时停止升级。

## 确认内容

在应用前要求用户确认以下完整事实：

1. 当前版本和目标不可变 Release；
2. Migration 链和不可逆步骤；
3. 文件动作数量与逐项冲突决策；
4. `workspace` 内容保护结论；
5. 快照收据和回滚命令；
6. 是否需要下载、联网、删除、切换符号链接或重启任何外部进程；
7. 升级后验证和失败处理。

计划变化、候选内容变化或快照失败后，原确认失效，必须重新预览和确认。

## 安装收据提交

`.ai-workspace/release-manifest.json` 不按普通 `distribution` 文件参与 `files` 比较，而由预览单列 `replace-receipt`。应用阶段必须：

1. 保持旧收据不变，完成其余文件动作、Migration、生成文件重建和验证；
2. 更新版本锁与发行指针；
3. 再次校验候选收据与已认证候选 Release 中的字节一致；
4. 原子替换收据，作为事务最后一次工作区写入；
5. 若替换失败，判定升级失败并执行回滚，不得保留“新版本、旧收据”的混合状态。

收据替换成功后，不得再运行会写入工作区的生成、格式化、迁移或修复动作。

## 自更新

V0.1 只定义协议。未建立唯一正式仓库、稳定 Tag、不可变 Release、完整校验和可信切换机制前：

- 可以在授权后检查版本；
- 可以在授权后下载到并列目录；
- 禁止默认自动应用；
- 禁止正在运行的 Skill 覆盖自身；
- 禁止以最新分支提交替代 Release。
