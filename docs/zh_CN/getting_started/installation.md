# 安装指南 (Installation)

开始使用 `rhosocial-activerecord` 非常简单。本指南将详细介绍各种安装方式和环境配置。

## 环境要求

### Python 版本
*   **Python 3.8+** — 支持包括最新的 Python 3.14 以及自由线程版本 (3.13t, 3.14t)
*   **推荐版本**: Python 3.11+ 以获得最佳性能和功能支持

### 核心依赖
*   **Pydantic V2** — 数据验证和序列化框架
    *   Python 3.8: pydantic 2.10.6 (由于兼容性限制)
    *   Python 3.9+: pydantic 2.12+ (完整功能支持)

### 数据库要求
* **SQLite**: 3.25+ (内置支持)
  * 同步后端: 使用标准 `sqlite3` 模块（无需额外依赖）
  * 异步后端: 需要安装 `aiosqlite` 包（需单独安装）
* **其他数据库**: 需要安装对应的后端包
* MySQL/MariaDB: `rhosocial-activerecord-mysql`
* PostgreSQL: `rhosocial-activerecord-postgres`
* Oracle: `rhosocial-activerecord-oracle` (计划中)
* SQL Server: `rhosocial-activerecord-mssql` (计划中)

> ⚠️ **注意**: 异步 SQLite 后端需要 `aiosqlite` 包。它不包含在核心依赖中，如果您计划使用异步 SQLite，需要手动安装：
> ```bash
> pip install aiosqlite
> ```

## 通过 pip 安装

### 基础安装
```bash
pip install rhosocial-activerecord
```

### 安装特定数据库后端支持
```bash
# 安装 MySQL/MariaDB 支持
pip install rhosocial-activerecord[mysql]

# 安装 PostgreSQL 支持
pip install rhosocial-activerecord[postgres]

# 安装所有数据库支持
pip install rhosocial-activerecord[databases]

# 安装完整包（包括所有可选依赖）
pip install rhosocial-activerecord[all]
```

### 开发环境安装
如果你计划参与项目开发或运行测试：
```bash
# 安装开发依赖（格式化、类型检查、测试等）
pip install rhosocial-activerecord[dev,test]

# 安装文档构建依赖
pip install rhosocial-activerecord[docs]
```

## 从源码安装

如果你想使用最新的开发版本或者参与项目开发：

### 克隆仓库
```bash
git clone https://github.com/rhosocial/python-activerecord.git
cd python-activerecord
```

### 开发模式安装
```bash
# 开发模式安装（推荐用于开发）
pip install -e .

# 安装所有开发依赖
pip install -e .[dev,test,docs]
```

### 生产模式安装
```bash
# 生产模式安装
pip install .
```

## 虚拟环境推荐

强烈建议在虚拟环境中安装和使用 `rhosocial-activerecord`：

### 使用 venv
```bash
# 创建虚拟环境
python -m venv activerecord-env

# 激活虚拟环境
# Windows:
activerecord-env\Scripts\activate
# macOS/Linux:
source activerecord-env/bin/activate

# 安装 rhosocial-activerecord
pip install rhosocial-activerecord

# 使用完毕后退出虚拟环境
deactivate
```

### 使用 conda
```bash
# 创建虚拟环境
conda create -n activerecord-env python=3.11

# 激活虚拟环境
conda activate activerecord-env

# 安装 rhosocial-activerecord
pip install rhosocial-activerecord

# 使用完毕后退出虚拟环境
conda deactivate
```

## 验证安装

你可以通过多种方式验证安装是否成功：

### 检查版本号
```python
from importlib.metadata import version
print(version("rhosocial_activerecord"))
```

### 基本功能测试
```python
# 测试基本导入
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from typing import ClassVar

# 定义简单模型测试
class TestModel(ActiveRecord):
    __table_name__ = "test_table"
    name: str
    c: ClassVar[FieldProxy] = FieldProxy()

# 检查模型定义是否成功
print("ActiveRecord 模型定义成功")
print(f"模型类: {TestModel}")
```

### 检查依赖完整性
```bash
# 检查已安装的包
pip list | grep -E "(rhosocial|pydantic)"

# 检查 Python 版本兼容性
python --version
```

## 常见安装问题及解决方案

### 1. 依赖冲突
如果遇到依赖版本冲突：
```bash
# 升级 pip 到最新版本
pip install --upgrade pip

# 清理缓存后重试
pip cache purge
pip install rhosocial-activerecord
```

### 2. Python 3.8 兼容性问题
对于 Python 3.8 用户，请确保安装正确的依赖版本：
```bash
# Python 3.8 用户会自动安装兼容版本
pip install rhosocial-activerecord
```

### 3. 权限问题
如果遇到权限问题：
```bash
# 使用 --user 参数安装到用户目录
pip install --user rhosocial-activerecord

# 或者使用虚拟环境（推荐）
python -m venv myenv
source myenv/bin/activate  # Windows: myenv\Scripts\activate
pip install rhosocial-activerecord
```

### 4. 网络问题
如果下载速度慢或连接超时：
```bash
# 使用国内镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple rhosocial-activerecord

# 或者使用阿里云镜像
pip install -i https://mirrors.aliyun.com/pypi/simple/ rhosocial-activerecord
```

## 下一步

安装完成后，建议：

1. **阅读快速开始指南**: 查看 [快速开始](quick_start.md) 文档了解基本用法
2. **配置数据库**: 学习如何 [配置数据库连接](configuration.md)
3. **构建第一个应用**: 跟随 [第一个 CRUD 应用](first_crud.md) 教程

## 获取帮助

如果在安装过程中遇到问题：

1. **检查系统要求**: 确保满足最低 Python 和依赖版本要求
2. **查看错误日志**: 仔细阅读安装过程中的错误信息
3. **查阅文档**: 参考 [故障排除](troubleshooting.md) 文档
4. **提交问题**: 在 [GitHub Issues](https://github.com/rhosocial/python-activerecord/issues) 上提交问题

---

> 💡 **提示**: 建议定期更新到最新版本以获得新功能和安全修复:
> ```bash
> pip install --upgrade rhosocial-activerecord
> ```