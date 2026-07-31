# 仓库维护说明

## 真相源

`std-workspace` 是产品源码仓库。以下根目录内容由人工维护：

- `docs/`
- `specs/`
- `schemas/`
- `facts/`
- `skills/bootstrap-standard-workspace` 中 Bootstrap 专属协议与脚本
- `skills/bootstrap-standard-workspace/assets/workspace-v0.1` 中非同步生成的工作区资产

以下目录由 `scripts/build-bootstrap-assets.sh` 从根级真相源生成，不直接编辑：

- Bootstrap `references/specs/`
- Bootstrap `references/schemas/`
- Bootstrap `references/product-docs/`
- Bootstrap `references/product-facts/`
- 工作区资产 `.ai-workspace/specs/`
- 工作区资产 `.ai-workspace/schemas/`
- 工作区资产 `docs/standard/`
- 工作区资产 `knowledge/tool-capabilities.toml`
- 工作区资产 `.ai-workspace/release-manifest.json`
- Bootstrap `checksums/workspace-v0.1.sha256`

同步采用发行白名单：`references/product-docs/` 只携带通用产品文档，`references/product-facts/` 只携带可复用决策和种子知识。`docs/session-summary.md` 属于源码仓库的设计溯源，不得进入 Skill ZIP 或展开后的标准工作区。

## 本地验证

```text
scripts/build-bootstrap-assets.sh
tests/run.sh
```

源码仓库构建基线为 POSIX `sh`、Python 3.11+ 与 Node.js；仅打包 ZIP 时需要 `zip`。这些是产品维护工具，不是 Bootstrap 展开目标或新工作区的默认环境要求。

验证过程必须离线，不安装依赖，不修改父工作区，不生成 Python cache。测试覆盖 Schema 示例、TOML 映射、运行时脚本、Skill 元数据、Bootstrap 空目录创建、拒绝非空目录、发行文件漂移、Doctor 和 ZIP 完整性。

## 版本同步

发布前同时核对：

- `VERSION`
- `product.toml`
- Bootstrap `bundle.toml`
- 工作区 `.ai-workspace/workspace.toml`
- 工作区 `.ai-workspace/versions.lock`
- 各 Schema 与 API 版本
- `CHANGELOG.md`

版本变化必须先更新根真相源，再重建自包含 Skill；不得只修改同步副本。

## 打包

```text
scripts/package-bootstrap-skill.sh
```

产物默认写入 `dist/`，包括 Skill ZIP 与 SHA-256。ZIP 是正式分发候选，Git 仓库仍是源码维护形态。

## Release 门禁

正式公开发行前必须：

1. 选择并确认正式许可证；
2. 指定唯一公开仓库；
3. 从不可变 Tag 构建；
4. 运行全部测试；
5. 检查无凭证、绝对宿主路径、缓存和二进制文件；
6. 校验 ZIP SHA-256；
7. 确认自更新仍为禁用，除非其独立安全协议已经完成。

本仓库禁止自动提交、推送、打 Tag 或发布。
