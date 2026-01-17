# 安装指南 (Installation)

开始使用 `rhosocial-activerecord` 非常简单。

## 环境要求

*   Python 3.8+
*   Pydantic V2

## 通过 pip 安装

```bash
pip install rhosocial-activerecord
```

## 从源码安装

如果你想使用最新的开发版本：

```bash
git clone https://github.com/rhosocial/python-activerecord.git
cd python-activerecord
pip install .
```

## 验证安装

你可以通过检查版本号来验证安装是否成功：

```python
from importlib.metadata import version
print(version("rhosocial_activerecord"))
```
