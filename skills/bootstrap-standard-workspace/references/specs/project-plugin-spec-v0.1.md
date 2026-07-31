# Project Plugin Specification V0.1

## 1. 定义

项目插件是标准工作区内部的项目适配协议，不等同于任何 AI 平台 Plugin。它描述项目稳定差异；当前机器路径、密钥和动态 Git 状态属于项目实例。

## 2. 最小内容

- 项目标识、显示名称和插件版本。
- 单仓库或多仓库模型。
- 仓库、模块、默认分支和模块角色。
- 技术栈与通用适配器组合。
- 构建、测试、Review、发布和回滚规则。
- 项目高风险链路与知识入口。
- 启用的项目能力插件。
- 与工作流和能力插件 API 的兼容版本。

V0.1 的规范文件为 `project/plugin/project-plugin.json`，使用 `.ai-workspace/schemas/project-plugin.schema.json` 校验。绝对本地路径、当前分支、dirty/ahead/behind、环境绑定和端点引用只进入项目实例，不进入可复用插件。

## 3. 模块角色

- `edit`：任务可修改。
- `verify`：只做契约、编译和链路验证。
- `reference`：只读参考。

角色由任务进一步收窄，不能由任务无授权扩大。

## 4. 证据分层

项目插件必须把以下集合分开：

- `facts`：由用户声明、代码、Git 或配置直接确认的事实；
- `inferences`：引用事实 ID 的推断；
- `policies`：带明确来源的项目规则或用户限制；
- `unresolved_questions`：冲突或尚未确认的事项。

不得从一次问询直接生成可查证的代码事实，也不得把推断写成策略。

## 5. 工作流命令

构建、测试、验证、Review、发布、回滚和关闭流程使用声明式 `argv` 数组与相对工作目录，禁止保存未经审查的 Shell 拼接字符串。

适配过程本身支持以下标准阶段：

```text
discover
scope
prepare
context
plan
verify
diagnose
review
release
close
```

优先使用声明式配置；复杂行为才增加脚本或项目专属 Skill。

## 6. 生成流程

项目适配必须结合：

1. 用户交互确认；
2. 代码、Git 和配置只读发现；
3. 安全允许范围内的事实验证；
4. 冲突事实的明确裁决。

不得把历史文档直接提升为当前事实。
