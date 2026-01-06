# OpenStrategy

> **策略资产的标准运行时与分发平台**
>
> *The Standard Runtime & Distribution Platform for Strategy Assets.*

---

## 📖 简介 (Introduction)

在数据合成、算法交易、科学计算等领域，我们经常面临**"过程资产碎片化"**的挑战：代码写在 Notebook 里、依赖环境难以复现、硬编码的路径导致无法迁移、业务逻辑与计算基础设施耦合过深。

**OpenStrategy** 是一个旨在解决这些问题的现代化框架。它定义了一套标准的策略包规范（OpenSynth Package），通过**渐进式沙箱**技术，让你的策略代码实现 **Write Once, Run Anywhere**。我们希望无论是在笔记本电脑、Slurm 集群还是 Kubernetes 上，OpenStrategy 都能保证执行的一致性。

### 核心理念

1.  **标准化 (Standardization)**: 统一输入（Input）、输出（Output）与参数（Args）接口。
2.  **隔离性 (Isolation)**: 基于 `uv` 和虚拟文件系统（VFS）的强隔离环境，杜绝依赖冲突。
3.  **解耦 (Decoupling)**: 业务逻辑只关注过程处理，平台负责资源调度与环境构建。

---

## 🚀 快速开始 (Quick Start)

### 1. 安装

```bash
pip install openstrategy
```

### 2. 创建策略

使用脚手架初始化一个标准的策略项目：

```bash
openstrategy create hello-strategy
cd hello-strategy
```

这将生成以下结构：
```text
hello-strategy/
├── openstrategy.yaml  # 策略元数据
├── runtime.yaml       # 依赖定义
└── src/
    └── main.py        # 业务逻辑
```

### 3. 编写逻辑

OpenStrategy 让你专注于业务逻辑。编辑 `src/main.py`：

```python
from dataclasses import dataclass
from openstrategy.core.context import Context
from openstrategy.core.args import StrategyArgs

# 1. 定义强类型参数
@dataclass
class Params(StrategyArgs):
    message: str = "Hello OpenStrategy"
    repeat: int = 1

# 2. 实现入口函数
def run(ctx: Context, args: Params):
    print(f"🚀 Task ID: {ctx.task_id}")
    
    # 使用 VFS 写入结果
    output_path = ctx.outputs / "result.txt"
    with open(output_path, "w") as f:
        for i in range(args.repeat):
            f.write(f"{args.message} - {i}\n")
            print(f"[{i}] Processed.")
```

### 4. 运行策略

无需手动配置虚拟环境，OpenStrategy 会自动处理。

```bash
# 基本运行
openstrategy run .

# 通过 CLI 覆盖参数 (支持点号语法)
openstrategy run . strategy.message="Custom Msg" strategy.repeat=5

# 指定计算资源
openstrategy run . platform.cpu=4 platform.gpu=1
```

### 5. 打包分发

将策略打包为 `.ops` 文件，方便分享或部署。

```bash
openstrategy pack . -o release_v1.ops
```

---

## 🤝 贡献指南 (Contributing)

我们非常欢迎社区贡献！

1.  **Executors**: 编写适配 Slurm, Ray 或 Kubernetes 的执行器插件。
2.  **Builders**: 增加对 Docker 或 Singularity 容器构建的支持。
3.  **Strategies**: 提交通用的过程策略。
4.  **Docs**: 编写项目文档。

详情请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。