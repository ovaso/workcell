# AI Instruction Generation Specification V0.1

## 1. 真相源

AI 指令文件不是唯一事实源。工作区策略、项目插件、诊断策略和用户覆盖是结构化真相源。

## 2. 标准分区

生成文件至少区分：

```text
GENERATED CORE
USER MANAGED
GENERATED PROJECT
GENERATED DIAGNOSTICS
```

每个生成区记录来源版本和配置哈希。Doctor 必须发现生成区被手工改写的情况。

## 3. 平台无关入口

`AI_WORKSPACE.md` 保存平台无关的工作区入口、强制读取顺序和状态。平台适配器可以生成 `AGENTS.md`、`CLAUDE.md` 等文件。

## 4. 编译优先级

```text
核心安全硬约束
> 用户明确限制
> 项目安全规则
> 诊断硬约束
> 项目工作流规则
> 平台表现形式
```

平台适配不能放宽上层约束。

## 5. 实时诊断更新

用户确认新的诊断禁止事项后，应先更新结构化策略，再原子重编译诊断生成区。失败时保留旧的、更严格规则。

## 6. 升级

升级重新编译 generated 区，保留 user managed 区。禁止用完整模板覆盖用户编辑内容。

