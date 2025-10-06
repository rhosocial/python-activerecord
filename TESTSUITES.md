# 测试套件分离与兼容性报告规划

本文档详细说明了 `rhosocial-activerecord` 生态系统的测试策略，旨在确保代码质量、后端兼容性和框架的实际可用性。该策略的核心是将测试套件 (`testsuite`) 与具体的后端实现分离，并通过一套明确的协作机制来联动。

## 1. 测试框架的三个核心支柱

我们的测试策略建立在三个核心支柱之上，每个支柱都服务于不同的验证目的：

1.  **特性测试 (Feature Tests)**: 验证库的每一个独立功能点。这些是细粒度的单元测试，确保如 `where` 查询、`save` 方法、`BelongsTo` 关系等基础构建块按预期工作。

2.  **“真实世界”场景测试 (Real-world Scenarios)**: 模拟真实业务场景，验证多个特性在复杂交互下的正确性和健壮性。这确保了库不仅在理论上可行，在实际应用中也足够可靠。

3.  **性能基准测试 (Performance Benchmarks)**: 通过标准化的负载测试，衡量和比较不同数据库后端在执行常见操作时的性能表现，为技术选型和优化提供数据支持。

## 2. `testsuite` 包：标准化的测试契约

所有测试的“定义”都集中在 `rhosocial-activerecord-testsuite` 这个独立的Python包中。它不包含任何特定于数据库的实现，而是定义了一套所有后端都必须通过的“测试契约”。

### 2.1. `testsuite` 目录结构

为了清晰地组织这三类测试，`testsuite` 包将采用以下目录结构：

```
rhosocial-activerecord-testsuite/
└── src/
    └── rhosocial/
        └── activerecord/
            └── testsuite/
                ├── __init__.py             # 定义各测试类别的版本号
                ├── feature/                  # 特性测试
                │   ├── basic/
                │   ├── query/
                │   └── ...
                ├── realworld/                # 真实世界场景测试
                │   ├── fixtures/             # 场景相关的模型定义
                │   ├── ecommerce/
                │   └── ...
                ├── benchmark/                # 性能基准测试
                │   ├── fixtures/
                │   └── ...
                └── utils/                    # 测试辅助工具
                    └── schema_generator.py # Schema生成器脚本
```

### 2.2. 标记系统

`testsuite` 中的每个测试都会被赋予一个或多个 `pytest` 标记，以便于分类、选择性执行和报告生成。

-   `@pytest.mark.feature`: 标记所有特性测试。
-   `@pytest.mark.realworld`: 标记所有真实世界场景测试。
-   `@pytest.mark.benchmark`: 标记所有性能基准测试。
-   `@pytest.mark.scenario_ecommerce`: 标记特定的电子商务场景测试。
-   `@pytest.mark.feature_cte`: 标记特定的功能点测试。

## 3. 后端集成与协作机制

这是整个测试策略的核心。它定义了后端包（如 `rhosocial-activerecord-mysql`）如何与 `testsuite` 包协作。

### 3.1. 核心原则：责任分离

-   **`testsuite` 的责任**: 定义测试逻辑和业务模型。它 **不负责** 数据库的准备工作，如 `CREATE TABLE` 或数据填充。
-   **后端包的责任**: **完全负责“测试环境”**。它需要根据 `testsuite` 定义的场景，提供匹配的数据库Schema，并在适当的时机创建和销毁它们。

### 3.2. 协作流程：按场景动态准备Schema

`testsuite` 中的测试将通过依赖特定名称的 `pytest` 夹具（Fixture）来声明其所需的环境。后端包则负责实现这些夹具，从而实现按需、动态地搭建和销毁数据库环境。

**第一步: `testsuite` 声明环境依赖**

在 `testsuite` 中，一个测试模块（如电子商务场景的测试）会通过 `@pytest.mark.usefixtures("ecommerce_schema")` 声明它需要一个名为 `ecommerce_schema` 的环境。

```python
# rhosocial-activerecord-testsuite/realworld/ecommerce/test_checkout.py

import pytest

@pytest.mark.realworld
@pytest.mark.scenario_ecommerce
@pytest.mark.usefixtures("ecommerce_schema")
def test_create_order(ecommerce_models):
    User, Product, Order = ecommerce_models
    # ... 测试逻辑 ...
```

**第二步: 后端包提供夹具实现**

每个后端包必须在自己的 `tests/conftest.py` 文件中提供 `ecommerce_schema` 夹具的实现。这个夹具负责创建和销毁该场景所需的数据库表。

-   **Schema文件组织**: 建议后端包的 `tests/schemas/` 目录结构与 `testsuite` 的测试目录结构保持一致，便于管理。

    ```
    rhosocial-activerecord-mysql/
    └── tests/
        ├── schemas/
        │   ├── realworld/
        │   │   └── ecommerce.sql
        │   └── feature/
        │       └── basic.sql
        └── conftest.py
    ```

-   **夹具实现 (`conftest.py`)**:

    ```python
    # rhosocial-activerecord-mysql/tests/conftest.py
    import pytest

    @pytest.fixture(scope="module") # 作用域设为 module，为每个测试模块准备一次环境
    def ecommerce_schema(db_connection): # 依赖一个通用的数据库连接夹具
        # 1. 测试前：执行SQL文件，创建表
        with open("tests/schemas/realworld/ecommerce.sql") as f:
            db_connection.execute(f.read())
        print("\nECOMMERCE SCHEMA CREATED")

        yield # 执行该模块下的所有测试

        # 2. 测试结束后：销毁表
        db_connection.execute("DROP TABLE IF EXISTS orders, products, customers;")
        print("\nECOMMERCE SCHEMA DROPPED")
    ```

### 3.3. 辅助工具：标准Schema生成器

为了方便新后端包的开发者，`testsuite` 包将提供一个命令行工具，用于根据模型定义生成一份标准的、通用的SQL Schema。

-   **目的**: 减少开发者手动编写 `CREATE TABLE` 语句的初始工作量。
-   **使用方式**:
    ```bash
    # 生成电子商务场景的schema模板
    python -m rhosocial.activerecord.testsuite.utils.schema_generator --scenario ecommerce > tests/schemas/realworld/ecommerce.sql
    ```
-   **重要提示**: 此工具生成的SQL是基于通用SQL标准的 **模板**。开发者仍需根据其特定数据库的方言（如数据类型、自增主键语法等）进行手动调整。

### 3.4. 可选执行机制

为保持后端包本地测试的纯粹性，`testsuite` 的执行是可选的。

-   **命令行触发**: 引入 `--run-testsuite` 参数。只有当开发者执行 `pytest --run-testsuite` 时，才会运行 `testsuite` 中的测试。
-   **动态跳过**: 后端包的 `conftest.py` 中将包含 `pytest_collection_modifyitems` 钩子。如果未提供 `--run-testsuite` 参数，该钩子会自动取消选择（deselect）所有来自 `testsuite` 的测试项。
-   **依赖检查**: 钩子还会检查 `rhosocial-activerecord-testsuite` 是否已安装。如果未安装，将向用户显示清晰的警告信息。

## 4. 新后端接入与认证标准

为了确保生态中所有数据库后端实现的质量和一致性，我们为新后端接入定义了清晰的测试通过标准。

-   **强制要求 (Mandatory)**: **通过所有“特性测试”**。这是后端被认证为“兼容”的最低标准。报告中将为此计算一个 **兼容性得分** (`通过的特性测试数 / 特性测试总数`)。

-   **推荐要求 (Recommended)**: **通过所有“真实世界场景测试”**。这表明后端不仅功能完备，而且在模拟真实业务的复杂交互下表现稳定，是高质量实现的标志。

-   **可选要求 (Optional)**: **执行“性能基准测试”**。这部分测试不影响兼容性认证，其结果主要用于性能评估和技术选型，供开发者和用户按需运行和参考。

## 5. 版本控制与兼容性管理

由于 `testsuite` 包和后端包是独立版本和发布的，必须有一套明确的机制来管理它们之间的兼容性。

### 5.1. 独立版本线策略

为了更精确地反映不同测试类别的演进速度和兼容性，`testsuite` 内部将对三个核心支柱进行独立的版本管理。包的主版本号将与“特性测试”版本保持一致。

-   **特性测试 (Feature Tests)**:
    -   **版本**: 与 `rhosocial-activerecord` **核心库的版本号保持同步**。例如，当核心库为 `v1.2.0` 时，对应的特性测试版本也为 `v1.2.0`。这确保了功能和测试的紧密耦合。

-   **真实世界场景测试 (Real-world Scenarios)**:
    -   **版本**: 拥有 **独立的语义化版本号** (如 `1.0.0`, `1.1.0`)。
    -   **更新**: 仅当新增场景（如“金融”）或现有场景（如“电商”）的模型、业务逻辑发生不兼容变更时，才提升其主版本或次版本。

-   **性能基准测试 (Performance Benchmarks)**:
    -   **版本**: 同样拥有 **独立的语义化版本号** (如 `1.0.0`, `1.0.1`)。
    -   **更新**: 仅当新增或修改基准测试用例（如调整数据量、改变测试算法）时更新。

`testsuite` 包的 `__init__.py` 将会定义这些版本：
```python
# rhosocial/activerecord/testsuite/__init__.py
__version__ = "1.2.5"  # 包的整体版本，与特性测试版本同步
__feature_version__ = "1.2.5"
__realworld_version__ = "1.1.0"
__benchmark_version__ = "1.0.2"
```

### 5.2. 后端包的责任

-   **明确依赖**: 每个后端包的维护者 **必须** 在其项目的依赖项中，明确指定其兼容的 `testsuite` 版本范围。这个版本号主要锚定的是 **特性测试** 的版本。

    **示例: `pyproject.toml`**
    ```toml
    [project.optional-dependencies]
    test = [
      "pytest",
      "rhosocial-activerecord-testsuite >=1.2,<1.3" # 声明与 testsuite 特性集 1.2.x 兼容
    ]
    ```

-   **`testsuite` 不保证向后兼容**: `testsuite` 的主要职责是驱动生态系统的发展，因此它不保证其 **MAJOR** 版本之间的兼容性。后端包需要自行跟进 `testsuite` 的演进，并更新自己的Schema和测试配置。

### 5.3. 报告中的版本信息

为了保证测试结果的可追溯性，所有生成的兼容性报告的页眉或标题中，都必须包含本次测试所使用的 `testsuite` 的 **所有相关版本号**。

**示例控制台报告标题:**
```
================== Backend Compatibility Report ==================
Test Suite Version: 1.2.5
- Features: v1.2.5
- Real-world: v1.1.0
- Benchmark: v1.0.2
==================================================================
```

## 6. 报告的演进

最终的兼容性报告将整合所有三个支柱的测试结果，提供一个全面的视图。

### 6.1. 多场景报告策略

为了适应不同的执行环境，报告生成将通过命令行参数控制，提供不同格式和详细程度的输出。

-   **执行场景**:
    1.  **本地命令行 (Manual CLI)**: 开发者手动执行测试，需要最直观、详细的报告。
    2.  **持续集成 (CI/CD)**: 自动化流水线执行，需要简洁、适合日志输出的报告。
    3.  **IDE内部执行**: 在IDE（如PyCharm, VSCode）中运行，开发者通常关注即时的失败/通过信息，不需要额外的报告文件。

-   **命令行参数控制**:
    -   我们将引入一个自定义的 `pytest` 参数，例如 `--compat-report`。
    -   `pytest --compat-report=html`: 生成一份详细的HTML格式兼容性报告。
    -   `pytest --compat-report=console`: 在测试运行结束后，在控制台打印一份简洁的兼容性矩阵。
    -   **默认行为**: 如果不提供此参数，则不生成任何额外的兼容性报告，仅显示标准的 `pytest` 输出，这最适合IDE环境。

### 6.2. 报告格式与细节

兼容性矩阵的内容和形式将根据输出格式自适应调整。

1.  **HTML报告 (`--compat-report=html`)**:
    -   **视觉丰富**: 使用CSS和JavaScript实现美观、易读的布局。
    -   **交互性**: 矩阵中的 ⚠️ 和 ❌ 标记可以点击，展开显示所有被跳过（Skipped）的测试用例及其详细原因。
    -   **层次感**: 可以将功能特性进行分类（如：查询、关系、字段等），并提供折叠/展开功能。

2.  **控制台报告 (`--compat-report=console`)**:
    -   **简洁明了**: 输出一个纯文本的、固定宽度的表格，适合在CI日志中查看。
    -   **关键信息**: 只保留核心的“功能特性”、“支持状态”和简短的“备注”。过长的跳过原因将被截断。

### 6.3. 最终报告结构（示例）

| 类别 | 名称 | 支持状态/得分 | 备注/性能指标 |
| :--- | :--- | :---: | :--- |
| **功能特性 (v1.2.5)** | **兼容性得分** | **95%** | 190/200 tests passed |
| | CTE | ✅ | |
| | Window Functions | ⚠️ | `GROUPS` 模式未实现 |
| **真实世界场景 (v1.1.0)** | **电子商务 (E-commerce)** | ✅ | 完整通过订单创建、支付、发货流程测试。 |
| | **金融 (Finance)** | ⚠️ | 高并发转账测试中出现死lock (Deadlock) 失败。 |
| **性能基准 (v1.0.2)** | **Bulk Insert (10k)** | `1.23s` | `mean` |
| | **Complex Join (1k)** | `5.67s` | `mean` |

```