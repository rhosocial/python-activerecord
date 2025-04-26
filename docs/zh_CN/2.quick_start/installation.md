# 安装指南

本指南介绍如何安装rhosocial ActiveRecord及其依赖项。

## 系统要求

在安装rhosocial ActiveRecord之前，请确保您的系统满足以下要求：

- **Python**: 3.8或更高版本
- **Pydantic**: 2.10+（适用于Python 3.8），2.11+（适用于Python 3.9+）
- **SQLite**: 3.25+（如果使用内置的SQLite后端）

> **注意**：您可以使用以下命令检查SQLite版本：
> ```shell
> python3 -c "import sqlite3; print(sqlite3.sqlite_version);"
> ```

## 安装方法

### 基本安装

要安装带有SQLite支持的核心包：

```bash
pip install rhosocial-activerecord
```

这提供了使用SQLite作为数据库后端所需的一切。

### 可选数据库后端

rhosocial ActiveRecord通过可选包支持多种数据库后端：

> **注意**：这些可选数据库后端目前正在开发中，可能尚未完全稳定，不建议在生产环境中使用。

```bash
# MySQL支持
pip install rhosocial-activerecord[mysql]

# MariaDB支持
pip install rhosocial-activerecord[mariadb]

# PostgreSQL支持
pip install rhosocial-activerecord[pgsql]

# Oracle支持
pip install rhosocial-activerecord[oracle]

# SQL Server支持
pip install rhosocial-activerecord[mssql]
```

### 完整安装

要安装所有数据库后端：

```bash
pip install rhosocial-activerecord[databases]
```

要安装包括数据库迁移在内的所有功能：

```bash
pip install rhosocial-activerecord[all]
```

## 版本兼容性

### Pydantic兼容性

- **Pydantic 2.10.x**: 兼容Python 3.8至3.12
- **Pydantic 2.11.x**: 兼容Python 3.9至3.13（包括自由线程模式）

> **注意**：根据Python官方开发计划（[PEP 703](https://peps.python.org/pep-0703/)），自由线程模式将在未来几年内保持实验性质，不建议在生产环境中使用，尽管Pydantic和rhosocial ActiveRecord都支持它。

## 验证安装

安装完成后，您可以通过运行以下代码验证rhosocial ActiveRecord是否正确安装：

```python
import rhosocial.activerecord
print(rhosocial.activerecord.__version__)
```

这应该会打印已安装包的版本号。

## 下一步

现在您已经安装了rhosocial ActiveRecord，请继续阅读[基本配置](basic_configuration.md)以了解如何设置您的第一个数据库连接。