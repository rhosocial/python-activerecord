# Standard: Adding a New Generic Test Case to the `testsuite`

This document aims to establish a standard, repeatable process for the `rhosocial-activerecord` ecosystem to add new generic test cases to the `python-activerecord-testsuite` project, with implementation provided by specific backend projects (e.g., `python-activerecord`).

Adhering to this specification is crucial for ensuring the stability of the test architecture and avoiding hard-to-debug circular dependencies and environment issues.

## General Rules: Comments and Documentation Standards

When adding any new code, please follow these commenting guidelines:

1.  **First-Line Path Comment**: All newly created `.py` and `.sql` files must include a path comment on the first line. This path should start from the root of their respective projects (e.g., `src/` or `tests/`), without including the project's own directory name (e.g., `python-activerecord/`).
2.  **Comprehensive Docstrings**:
    -   **Test Case Files**: Should include a clear `docstring` explaining the purpose of the test file.
    -   **Test Functions**: Each `test_*` function should include a concise `docstring` describing its testing objective.
    -   **Fixture and Helper Classes**: All newly added fixture classes (e.g., models, type adapters) and functions should have comprehensive comments explaining their role and usage.

## Core Principles

Before proceeding, it is essential to understand and strictly adhere to the following core principles. These principles are valuable lessons learned from past mistakes.

### 1. Framework Stability Principle
**The framework is stable and should not be modified.** The core code of `python-activerecord` (`src/rhosocial/activerecord`) and the core logic of `python-activerecord-testsuite` are considered stable and correct.

-   **DO NOT**: Modify any core framework files (e.g., `backend.py`, `base.py`, `type_adapter.py`, etc.) to make your new tests pass.
-   **CONSEQUENCE**: This is considered a "catastrophic modification." If a test fails, 99% of the time the issue lies with your test case, fixture definition, or Provider implementation. If you genuinely suspect a framework bug, it should be reported rather than fixed by the test implementer during the test creation process.

### 2. Test Environment Isolation Principle
The test environment of backend projects (e.g., `python-activerecord`) relies on `PYTHONPATH`, not on `pip`'s editable mode installation.

-   **DO NOT**: Execute `pip install -e .` for the backend project (`python-activerecord`) itself within its virtual environment.
-   **CONSEQUENCE**: This will lead to confusing and incorrect `ModuleNotFoundError` or `ImportError` errors during module discovery and import by `pytest`. The correct practice is to **only** temporarily append `PYTHONPATH=src` when executing `pytest`.

### 3. Fixture Organization Principle
To avoid import issues, related fixture classes (such as test models and their dependent custom type adapters) should be placed within the same file.

-   **DO NOT**: Disperse multiple fixture classes required for a test scenario (e.g., `MyModel` and `MyAdapter`) across multiple files within the `fixtures` directory.
-   **CONSEQUENCE**: Due to the fact that test directories (especially the `fixtures` directory) are not treated as standard Python packages (**IT IS FORBIDDEN TO ADD `__init__.py` TO THEM**), relative or absolute imports between files will fail during `pytest`'s test collection phase.
-   **DO**: Place the definitions of `MyModel` and `MyAdapter` within the same `.../fixtures/my_feature_models.py` file.

### 4. Provider Import Pattern Principle
In the Provider implementation of the backend (e.g., `tests/providers/query.py`), the "import on demand" pattern must be used.

-   **DO NOT**: Import test-specific model classes at the top level of the `provider.py` file.
-   **DO**: Import the required model *inside* the specific `setup_*_fixtures` method that uses it.
-   **CONSEQUENCE**: This will cause fatal circular dependencies during the test collection phase (`testsuite` loads `provider` -> `provider` loads models from `testsuite`), leading to test framework crashes.

## Complete Execution Steps

The following outlines the complete and correct two-phase process for adding a new test case.

### Phase One: In the `python-activerecord-testsuite` Project

This phase defines "what should be tested."

#### Step 1.1: Create Fixture Model and Helper Classes

In the `src/rhosocial/activerecord/testsuite/feature/<category>/fixtures/` directory, create a new Python file (e.g., `annotated_adapter_models.py`).

-   **Note**: Place all auxiliary classes required for this test scenario (e.g., `ListToStringAdapter`) and model classes (e.g., `SearchableItem`) within this **single file**.

#### Step 1.2: Create Generic Test Case

In the `src/rhosocial/activerecord/testsuite/feature/<category>/` directory, create a new test file (e.g., `test_annotated_adapter_queries.py`).

-   **Note**:
    -   The test class should be pure, containing only `test_*` methods.
    -   **DO NOT** include any setup or teardown logic (especially `@pytest.fixture(autouse=True)`) within the test class. Environment preparation and cleanup are entirely handled by the Provider and fixtures in `conftest.py`.
    -   Ensure the `ActiveRecord` import path is correct: `from rhosocial.activerecord.model import ActiveRecord`.

#### Step 1.3: Update Provider Interface

Open the `src/rhosocial/activerecord/testsuite/feature/<category>/interfaces.py` file. In the `IProvider` interface you are extending, add a new abstract method (e.g., `setup_annotated_query_fixtures`).

#### Step 1.4: Define `testsuite` Fixture

Open the `src/rhosocial/activerecord/testsuite/feature/<category>/conftest.py` file and add a new fixture.

-   **Note**: You **MUST** imitate the pattern of existing fixtures (e.g., `order_fixtures`).
    1.  Obtain the Provider **class** via `get_provider_registry().get_provider("...")`.
    2.  Instantiate the Provider: `provider = provider_class()`.
    3.  Call the setup method: `fixtures = provider.setup_..._fixtures(request.param)`.
    4.  `yield fixtures`.
    5.  Call the cleanup method: `provider.cleanup_after_test(request.param)`.

### Phase Two: In the Backend Project (e.g., `python-activerecord`)

This phase defines "how to run the test."

#### Step 2.1: Implement Provider Method

Open the `tests/providers/<category>.py` file and implement the abstract method you added in `interfaces.py` for the Provider class.

-   **Note**: You **MUST** import the model *inside* the function (`from rhosocial.activerecord.testsuite.feature.<category>.fixtures... import ...`) to avoid circular dependencies.

#### Step 2.2: Create Database Schema

In the `tests/rhosocial/activerecord_test/feature/<category>/schema/` directory, create a corresponding `.sql` file for your new model.

-   **Note**: If your model inherits from mixins like `TimestampMixin`, **DO NOT FORGET** to add the `created_at` and `updated_at` fields to the `CREATE TABLE` statement; otherwise, it will result in an `OperationalError`.

#### Step 2.3: Create "Bridge" Test File

In the `tests/rhosocial/activerecord_test/feature/<category>/` directory, create a "bridge" file with the same name as the test file in the `testsuite`.

-   **Note**: This file **MUST** strictly follow the format of other bridge files in the same directory. It should contain only two imports:
    1.  Import the fixture name from the `testsuite`'s `conftest`.
    2.  Wildcard import all test cases from the `testsuite`'s test file.
    -   **DO NOT** add any other logic.
    -   **Complete Comments**: Add a comprehensive `docstring` and `IMPORTANT` comment blocks to the file, consistent with the style of other bridge files in the same directory.

### Phase Three: Execution and Debugging

#### Step 3.1: Execute Tests

Execute tests from the root directory of the **backend project** (`python-activerecord`).

-   **Correct Command**: `PYTHONPATH=src pytest -v tests/rhosocial/activerecord_test/feature/<category>/test_my_feature.py`
-   **Incorrect Commands**:
    -   **DO NOT** execute `pytest` directly within the `testsuite` project.
    -   **DO NOT** manually add the `tests` directory to `PYTHONPATH`.

#### Step 3.2: Debugging

If tests fail:
1.  **Enable Logging**: Temporarily add `logging.basicConfig(level=logging.DEBUG)` to the test file in the `testsuite`.
2.  **Isolate Tests**: Use `pytest -k <test_name>` to run failing test cases individually for analysis.
3.  **Analyze Errors**: If the error points to the core framework (e.g., a `ValueError` from the `sqlite3` driver), **DO NOT** attempt to modify the framework. This usually means your test **setup** is incorrect (e.g., the model inherits from a Mixin incompatible with the current test environment). You should modify the **test itself** (e.g., remove `TimestampMixin`) to work around the issue, rather than modifying the framework to suit your test.
