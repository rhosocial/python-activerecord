# 开发流程

本文档概述了为rhosocial ActiveRecord贡献代码的开发流程。

## 入门

1. **Fork仓库**：
   - 访问[rhosocial ActiveRecord仓库](https://github.com/rhosocial/python-activerecord)
   - 点击"Fork"按钮创建自己的副本

2. **克隆你的Fork**：
   ```bash
   git clone https://github.com/YOUR-USERNAME/python-activerecord.git
   cd python-activerecord
   ```

3. **设置开发环境**：
   ```bash
   python -m venv venv
   source venv/bin/activate  # 在Windows上: venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

4. **创建分支**：
   ```bash
   git checkout -b feature/your-feature-name
   ```
   使用能反映你所做更改的描述性分支名称。

## 编码标准

为rhosocial ActiveRecord贡献代码时，请遵循以下标准：

- **遵循PEP 8**：遵守[PEP 8](https://www.python.org/dev/peps/pep-0008/)风格指南
- **有意义的命名**：使用描述性的变量、函数和类名
- **文档**：为所有函数、类和模块编写文档字符串
- **类型提示**：在适当的地方包含类型提示
- **专注的函数**：保持函数专注于单一职责
- **测试覆盖**：为新功能编写测试

## 测试

所有代码贡献都应包含测试：

1. **编写测试**：
   - 为任何新功能添加测试
   - 确保现有测试通过你的更改

2. **运行测试**：
   ```bash
   python -m pytest
   ```

3. **检查覆盖率**：
   ```bash
   python -m pytest --cov=rhosocial
   ```

## 提交更改

1. **提交你的更改**：
   ```bash
   git commit -m "添加功能：简短描述"
   ```
   编写清晰、简洁的提交消息，解释你的更改做了什么。

2. **推送到你的Fork**：
   ```bash
   git push origin feature/your-feature-name
   ```

3. **创建Pull Request**：
   - 在GitHub上转到你的fork
   - 点击"New Pull Request"
   - 选择你的分支并提供更改描述
   - 引用任何相关问题

## 代码审查流程

提交pull request后：

1. 维护者将审查你的代码
2. 自动测试将运行以验证你的更改
3. 你可能会被要求进行调整
4. 一旦获得批准，你的更改将被合并

## 持续集成

rhosocial ActiveRecord使用GitHub Actions进行持续集成。当你提交pull request时，自动测试将运行以验证你的更改。

## 版本控制实践

- 保持提交专注于单一更改
- 在提交pull request之前rebase你的分支
- 尽可能避免合并提交

## 仓库发布惯例

1. **常设分支**：
   - 仓库维护两个常设分支：`main`和`docs`。
   - 非常设分支包括具体发布主版本分支和特性分支。

2. **分支创建规则**：
   - 开发新特性或修正已存在问题时，始终基于`main`分支或具体发布主版本分支创建新分支。
   - 开发成熟后合并到目标分支。
   - 推荐的分支命名规则：
     - 特性分支以`feature-`开头，后接GitHub的issue编号
     - 问题修正分支以`issue-`开头，后接GitHub的issue编号

3. **版本发布流程**：
   - 所有版本发布采用顺序方式，每次发布主版本都基于`main`分支。
   - 发布后立即分出主版本分支。
   - `main`分支会常设持续集成，且特性分支尝试合入`main`分支时会自动触发持续集成。
   - 持续集成通过是合入`main`分支的必要条件。

4. **文档分支管理**：
   - `docs`分支基于`main`分支，且定期从`main`分支同步更改，保证最新状态。
   - `docs`分支只负责接收主开发版本的文档更新。
   - 合入更改后会及时向`main`同步。

## 沟通

如果你在开发过程中有问题：

- 在相关issue上评论
- 在GitHub Discussions中开始讨论
- 联系维护者

感谢你为rhosocial ActiveRecord做出贡献！