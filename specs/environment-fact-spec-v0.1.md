# Environment Fact Specification V0.1

## 1. 首期范围

环境事实只覆盖：命令、工具链、环境变量和网络。未来扩展不得破坏现有事实元数据。

## 2. 事实类型

- `declared`：用户、工作区或项目声明。
- `discovered`：通过只读命令、文件或配置发现。
- `derived`：由多个事实推导。
- `runtime`：易变化的当前状态。

## 3. 通用元数据

每条事实至少记录：

```text
id
kind
source_type
source
observed_at
context
confidence
sensitivity
```

可选记录：`expires_at / supersedes / fingerprint / notes`。

## 4. 执行上下文

事实不得脱离上下文使用。建议上下文：

```text
system
login-shell
non-interactive-shell
ai-execution
workspace
project
task
```

## 5. 命令事实

记录命令名、可用性、解析路径、版本、探测方式和能力映射。存在命令不构成执行授权。

## 6. 工具链事实

区分声明版本、已安装版本和当前解析版本，并记录管理器与作用域。

## 7. 环境变量事实

敏感级别：

- `public`：V0.1 仍只保存名称和存在性；后续策略可显式允许无害值。
- `private`：保存存在性、来源和可选安全指纹。
- `secret`：只保存名称和可解析状态。
- `unknown`：按 `secret` 处理。

V0.1 禁止持久化环境变量原始值。

## 8. 网络事实

只允许探测明确允许清单中的目标。记录协议、目标引用、状态、探测方式、观测时间和 TTL。禁止扫描未知地址和端口。

## 9. 能力与建议

环境层把事实归一化为能力。项目或适配器声明 required/recommended/optional 能力，再生成缺失、降级或安装建议。建议不能自动转化为安装授权。

展开后的工作区携带 `knowledge/tool-capabilities.toml` 作为版本化种子知识。它描述已知命令的安全版本探测、能力映射和建议级别，不代表当前机器已经安装任何工具。环境事实刷新流程可以用它选择候选命令和生成建议；实际可用性始终以当前执行上下文的观测结果为准。
