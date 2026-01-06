# 🛠️ 策略开发指南 (Strategy Development Guide)

在 OpenStrategy 中，一个策略（Strategy）不仅仅是代码，它是一个**自包含的资产**。为了确保它在任何机器上都能运行，你需要定义三个核心部分：

1.  **环境配置 (`runtime.yaml`)**: 定义“它的运行环境”。
2.  **元数据 (`openstrategy.yaml`)**: 定义“它叫什么”。
3.  **业务代码 (`src/main.py`)**: 定义“它做什么”。

---

## 1. 定义运行环境 (`runtime.yaml`)

OpenStrategy 使用声明式的 `runtime.yaml` 来管理依赖。引擎会自动根据此文件构建隔离的沙箱环境。

### 基础示例

```yaml
# runtime.yaml

# 构建后端: 目前推荐 "uv" (极速 Python 包管理器)，未来支持 "docker"
backend: "uv"

# Python 版本
python_version: "3.10"

# 依赖列表 (支持 PyPI 包名，可指定版本)
dependencies:
  - "requests>=2.28.0"
  - "numpy"
  - "pandas"
  - "torch --index-url https://download.pytorch.org/whl/cu118"  # 支持自定义索引
```

### 最佳实践

*   **锁定版本**: 尽量指定具体的版本号（如 `pandas==2.0.0`），以保证可复现性。
*   **最小化依赖**: 只列出必要的包，这能显著加快冷启动速度。

---

## 2. 定义元数据 (`openstrategy.yaml`)

这是策略的“身份证”，告诉引擎入口在哪里。

```yaml
# openstrategy.yaml

name: "my-team/data-processor"  # 格式: 组织/项目名
version: "0.1.0"                # 语义化版本
description: "清洗并转换原始日志数据"

# 入口定义
entry_module: "main"  # 对应 src/main.py
entry_point: "run"    # 对应 main.py 中的 run 函数
```

---

## 3. 编写业务代码 (`src/main.py`)

OpenStrategy 的核心哲学是**类型安全**和**文件系统隔离**。

### 3.1 引入必要模块

```python
from dataclasses import dataclass, field
from typing import List, Optional
from openstrategy.core.context import Context
from openstrategy.core.args import StrategyArgs
```

### 3.2 定义输入参数 (`StrategyArgs`)

不要使用 `argparse`。创建一个继承自 `StrategyArgs` 的 Dataclass。
**好处**：CLI 会自动生成参数检查，并允许用户通过 `strategy.xxx=yyy` 覆盖。

```python
@dataclass
class ProcessArgs(StrategyArgs):
    # 1. 必填参数 (没有默认值)
    source_url: str
    
    # 2. 可选参数 (有默认值)
    batch_size: int = 32
    enable_logging: bool = True
    
    # 3. 复杂类型 (List/Dict 需要使用 field)
    # ❌ 错误写法: columns: list = []
    # ✅ 正确写法:
    columns: List[str] = field(default_factory=lambda: ["id", "timestamp"])
```

### 3.3 编写执行逻辑 (`run` 函数)

入口函数必须接收 `ctx` 和 `args` 两个参数。

```python
def run(ctx: Context, args: ProcessArgs):
    """
    ctx: 上下文对象，包含路径信息和任务ID
    args: 上面定义的 ProcessArgs 实例，包含用户传入的参数
    """
    
    print(f"🚀 开始执行任务: {ctx.task_id}")
    print(f"⚙️ 参数配置: {args}")

    input_file = ctx.inputs / "data.csv"
    
    if not input_file.exists():
        print("⚠️ 未找到输入文件，生成模拟数据...")
    
    results = []
    for i in range(args.batch_size):
        results.append(f"Row {i} processed from {args.source_url}")
        
    output_path = ctx.outputs / "result.jsonl"
    
    with open(output_path, "w", encoding="utf-8") as f:
        import json
        for line in results:
            f.write(json.dumps({"res": line}) + "\n")
            
    print(f"✅ 结果已保存至: {output_path}")
```

---

## 4. 完整的目录结构示例

将以上所有内容组合，你的项目目录应如下所示：

```text
my-strategy/
├── openstrategy.yaml
├── runtime.yaml
├── Readme.md
└── src/
    ├── __init__.py
    └── main.py
```