# AI Native Standard Workspace

本仓库是“AI 原生标准工作区”产品的 V0.1 草案源码。它不属于任何业务项目，也不绑定特定项目或 AI 平台。

产品的主交付物是一个全文本、版本化、自包含的 Bootstrap Skill。AI 使用该 Skill 将标准模板展开到空目录；展开后的工作区携带自己的 Skills、规范、Schema、事实管理、项目适配、诊断接入和校验能力。

## 当前能力

- 定义 AI 平台尽量无关的标准工作区结构和生命周期。
- 定义宿主环境、项目插件、诊断能力和任务事实模型。
- 提供 Bootstrap、初始化、环境扫描、项目适配、诊断配置、Doctor、任务创建和升级 Skills。
- 提供可复制的 V0.1 工作区模板。
- 提供 Bootstrap 安全校验、安装 Release 收据、结构 Doctor 与升级影响预览。
- 提供版本化工具能力种子知识，用于环境事实采集和非绑定式优化建议。
- 提供工作区实践反馈、标准提案与版本演进的受控闭环。

## 产品分层

```text
Bootstrap Skill
  -> 展开标准工作区
  -> 初始化宿主环境事实
  -> 接入并适配项目
  -> 配置项目能力插件
  -> 编译 AI 规则
  -> Doctor 通过后进入 READY
```

运行能力由以下部分组合：

```text
通用工作流内核
+ 当前机器能力
+ 通用技术适配器
+ 项目插件
+ 项目实例事实
+ 项目能力插件
+ 当前任务状态
```

## 目录说明

- `skills/`：Bootstrap Skill 主体；其 `assets/workspace-v0.1/skills/` 中包含展开后工作区自己的运行时 Skills。
- `specs/`：工作区、序列化、任务、事实、项目插件、诊断、AGENTS 和升级协议。
- `schemas/`：机器可读的基础 JSON Schema。
- `facts/`：产品决策、可复用能力种子知识及仅供源码溯源的观察事实。
- `docs/`：产品愿景、架构、生命周期、维护说明、路线图和完整会话总结。
- `scripts/`：产品构建与校验脚本。
- `tests/`：Bootstrap、Schema 和目录结构验证。
- `CHANGELOG.md`：产品发行级变化；不会替代任务 memory 或设计事实。

## 当前阶段

V0.1 重点是把设计固定成可审查、可验证的文本产品骨架。标准与 Assets 不绑定某个 AI 平台；确定性 Bootstrap 脚本当前只支持 POSIX `sh` 宿主。自更新、跨版本 Migration、完整 AGENTS 编译器和其他宿主平台引导器暂时只定义协议，不在本轮实现生产版本。

## 使用方向

1. 使用 `skills/bootstrap-standard-workspace` 将模板展开到空目录。
2. 在新工作区中使用 `initialize-standard-workspace` 建立宿主环境事实。
3. 使用 `adapt-project-workspace` 接入代码镜像、远端和项目插件。
4. 按需使用 `configure-project-diagnostics` 配置诊断能力。
5. 运行 `standard-workspace-doctor`，通过后将工作区标记为 `READY`。
6. 在任务结束或定期复盘时使用 `extract-standard-feedback` 生成脱敏候选；由标准仓库审核后再形成下一版本。

## 仓库与发行物

`std-workspace` 本身是独立标准 Git 仓库，是规范、Schema、文档和构建逻辑的源码真相源。正式分发物则是由该仓库构建出的 `bootstrap-standard-workspace` Skill ZIP；两者不是并列的两套产品。

```text
std-workspace Git repository
  -> build + validate
  -> bootstrap-standard-workspace Skill
  -> expand into an empty directory
  -> self-hosted standard workspace
```

根级 `docs/session-summary.md` 只保存产品形成过程，不进入 Bootstrap Skill ZIP；发行物只携带通用规范、通用产品文档和可复用种子知识。

运行 `scripts/build-bootstrap-assets.sh` 可将仓库级 Specs、Schemas、文档和设计事实同步进 Bootstrap Skill；运行 `scripts/validate-product.sh` 执行结构校验。公开发行前仍需明确选择正式许可证。
