# Standard Workspace Specification V0.1

## 1. 目的

定义 Bootstrap Skill 展开后的最小工作区结构、生命周期、状态和文件所有权。目录结构是规范表现，Manifest 和 Schema 才是机器判断依据。

## 2. 必需入口

- `AI_WORKSPACE.md`：平台无关的 AI 入口。
- `AGENTS.md`：Codex 等支持 AGENTS 的适配入口。
- `.ai-workspace/workspace.toml`：工作区身份和当前状态。
- `.ai-workspace/versions.lock`：发行版及各 Schema 版本。
- `.ai-workspace/release-manifest.json`：当前已安装 Release 的完整性清单和升级收据。
- `skills/`：工作区运行时 Skills。

## 3. 标准目录

```text
environment/   宿主环境事实和快照
project/       项目实例、项目插件和能力配置
mirror/        主线或参考代码镜像
remotes/       仓库远端和默认分支登记
requirements/  需求、缺陷、诊断和 Review 任务档案
workspaces/    隔离开发工作区
diagnostics/   非任务专属诊断配置、Provider 和知识
tools/         项目或工作区确定性工具
knowledge/     经确认的可复用知识
docs/          项目和工作区文档
memory/        工作区级会话与演进记忆
```

## 4. 生命周期

允许状态：

```text
CREATED
ENVIRONMENT_INITIALIZED
PROJECT_ATTACHED
PROJECT_ADAPTED
DIAGNOSTICS_CONFIGURED
READY
DEGRADED
PAUSED
ARCHIVED
```

Bootstrap 完成后只能进入 `CREATED`。只有 Doctor 通过后才能进入 `READY`。

## 5. 文件所有权

- `distribution`：由发行版维护，升级可通过 Migration 替换。
- `generated`：由结构化事实编译，禁止作为唯一人工编辑源。
- `workspace`：由用户、项目或任务维护，升级必须保留。

Manifest 必须能够判断所有受升级影响文件的所有权。

V0.1 使用 `.ai-workspace/distribution.manifest` 列出可做逐字节校验和修复的不可变发行路径，并用 `.ai-workspace/ownership.toml` 描述完整所有权。运行时会变化的 `workspace.toml`、`versions.lock`、`AGENTS.md`、环境事实和诊断策略不得进入逐字节修复清单；其发行初值保存在 `.ai-workspace/templates/`。

V0.1 同时使用 `.ai-workspace/release-manifest.json` 作为已安装 Release 收据。它必须符合 Release Manifest Schema V0.1，记录 `schema_version = 0.1`、产品 `release_version`，并列出发行资产内除该清单自身外的每个普通文件及其 `path`、first-match `owner` 和 SHA-256。该清单不自哈希，候选副本由 Bootstrap Skill 外层 `checksums/workspace-v0.1.sha256` 保护；升级事务必须在其余文件、版本锁和验证门禁全部成功后，最后原子替换该收据，替换后不得再修改工作区文件。

所有权规则按文件顺序执行 `first-match`；具体文件规则必须位于较宽目录规则之前。没有匹配时默认为 `workspace`。`.ai-workspace/distribution.manifest` 中的每个路径必须拥有完全同名的 `distribution` 规则，目录子项另用 `/**` 规则覆盖；Release 清单则按同一 first-match 规则解析每个普通文件。

## 6. 默认安全状态

- 远端动作默认禁止。
- 诊断未配置时只允许本地代码和已有文件分析。
- 环境初始化不得直接安装工具或修改 Shell。
- 项目未适配前不得推断分支、发布、诊断或写入规则。
- Bootstrap 不覆盖非空目录。

## 7. 平台适配

结构化策略是真相源。`AGENTS.md`、`CLAUDE.md` 等是编译适配文件；平台不支持自动读取时，必须显式读取 `AI_WORKSPACE.md`。
