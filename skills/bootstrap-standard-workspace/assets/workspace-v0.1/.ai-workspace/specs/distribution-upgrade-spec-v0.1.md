# Distribution and Upgrade Specification V0.1

## 1. 产品形态

```text
唯一 Git 源码仓库
-> 稳定 Tag
-> 校验与打包
-> Bootstrap Skill ZIP
-> 安装和展开
-> 独立标准工作区实例
```

## 2. 版本

至少独立维护：产品版本、工作区 Schema、Release Manifest Schema、环境事实 Schema、项目插件 API、诊断能力 API 和任务 Schema。

## 3. 发行要求

- Release 必须从稳定 Tag 构建。
- 发行物不可变。
- 确定性生成工作区内 `.ai-workspace/release-manifest.json`，覆盖资产内除自身外的全部普通文件，并记录 first-match 所有权和 SHA-256。
- 生成 Bootstrap 外层 SHA-256 清单，覆盖包括工作区 Release 清单在内的完整资产；工作区 Release 清单不得自哈希。
- 不得用 `main` 最新提交作为自动升级目标。
- 正式公开前必须选择许可证并完成第三方许可证清单。

## 4. 工作区升级

```text
验证当前安装收据与候选外层校验
-> 读取版本
-> 选择 Migration
-> 生成升级计划和文件影响
-> 用户确认
-> 创建可恢复快照
-> 执行 Migration
-> 重编译生成文件
-> Doctor
-> 更新版本锁和发行指针
-> 最后原子替换安装收据或回滚
```

升级预览必须直接使用当前工作区 `.ai-workspace/release-manifest.json` 作为 `--current-manifest`。候选清单必须符合相同 Schema，且由候选 Release 的外层 checksum 或签名建立信任。清单自身不出现在 `files` 中；预览和事务日志必须把它作为独立的 `replace-receipt` 末步动作。成功替换后禁止再执行生成、格式化或其他工作区写入；替换失败视为升级失败并进入回滚。

## 5. 自更新

自更新只在唯一仓库、生产标准和正式 Release 流程稳定后启用。默认允许自动检查，可配置自动下载，禁止默认自动应用。

不得在 Skill 正在执行时原地覆盖自身。新版本应安装到临时或并列目录，校验后再切换，并保留回滚能力。

## 6. 文件所有权

- `distribution` 可由 Migration 替换。
- `generated` 重新编译。
- `workspace` 完整保留。
