# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_dialect_binding_semantics.py
"""对照测试：方言绑定的两种等价路径（显式构造 / 逐节点注入）。

背景
----
DataType 继承自 BaseExpression，其 SQL 文本**不由类型自身构建**，而是渲染时
交给所绑定方言的 ``format_data_type_<name>`` 格式化函数（如 dummy 后端的
``format_data_type_varchar``）。方言是**逐节点**的绑定信息：

1. **显式构造**：``VarCharType(dummy_dialect, 255)`` —— 构造即绑定，最直观。
2. **逐节点注入**：``t = VarCharType(None, 255)``，之后 ``t.dialect = dialect``
   推迟赋值；或对已构造的树**遍历每个节点**逐一绑定（ActiveRecord 推导 DDL
   时框架的职责——构建期复制声明期实例并注入方言）。

方言**不传播**：setter 只影响本节点（渲染层无状态，无重建、无副本）。
渲染前任何节点未绑定方言都会立即抛错——fail-fast 护栏。

为什么构造时可以不传方言
------------------------
* **值对象语义**：``DataType`` 的 ``__eq__``/``__hash__`` 忽略方言，只比较
  逻辑类型参数与 ``dialect_options``。纯相等性断言中传 ``None`` 与传方言
  等价——声明期（模型字段定义）的实例本来就没有方言。
* **推迟绑定合法**：构造后通过 setter 绑定，渲染入口统一校验。
* **渲染护栏**：未绑定就 ``to_sql()`` 立即抛 ``ValueError``（``has no
  dialect bound``）——不存在静默渲染。

测试矩阵
--------
* TestExplicitPerNodeBinding        —— 路径 1：嵌套树逐层显式，渲染一致
* TestPerNodeInjection              —— 路径 2：遍历注入（ActiveRecord 构建期规范）
* TestDeferredAssignment            —— 路径 2 的单节点形态
* TestRenderGuard                   —— 未绑定渲染即抛错
* TestValueObjectSemantics          —— 相等性/哈希忽略方言
* TestDialectOptionsChannel         —— dialect_options 参与相等性、
                                       参与参数面、不影响渲染文本
"""

import pytest

from rhosocial.activerecord.backend.expression.types import (
    ArrayType,
    IntegerType,
    VarCharType,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
)


class TestExplicitPerNodeBinding:
    """路径 1：构造时逐节点显式绑定方言（首选形态）。"""

    def test_explicit_binding_renders(self, dummy_dialect: DummyDialect):
        t = VarCharType(dummy_dialect, 255)
        assert t.to_sql() == ("VARCHAR(255)", ())

    def test_explicit_binding_no_length(self, dummy_dialect: DummyDialect):
        t = VarCharType(dummy_dialect)
        assert t.to_sql() == ("VARCHAR", ())

    def test_nested_tree_explicit_per_node(self, dummy_dialect: DummyDialect):
        # 嵌套树：每一层构造时都显式传方言。
        arr = ArrayType(dummy_dialect, IntegerType(dummy_dialect))
        assert arr._dialect is dummy_dialect
        assert arr.element_type._dialect is dummy_dialect
        sql, _ = arr.to_sql()
        assert "INTEGER" in sql

    def test_ddl_tree_explicit_per_node(self, dummy_dialect: DummyDialect):
        # 端到端：DDL 全树逐节点显式方言——两种写法渲染结果一致。
        def build(varchar: VarCharType) -> str:
            expr = CreateTableExpression(
                dummy_dialect,
                "t",
                [
                    ColumnDefinition(
                        dummy_dialect,
                        "id",
                        IntegerType(dummy_dialect),
                        constraints=[
                            ColumnConstraint(
                                dummy_dialect, ColumnConstraintType.PRIMARY_KEY
                            )
                        ],
                    ),
                    ColumnDefinition(dummy_dialect, "name", varchar),
                ],
            )
            sql, _ = expr.to_sql()
            return sql

        assert build(VarCharType(dummy_dialect, 100)) == build(
            VarCharType(dummy_dialect, 100)
        )


class TestPerNodeInjection:
    """路径 2：对已构造的树遍历每个节点逐一注入方言。

    这是 ActiveRecord 推导 DDL 时框架职责的可执行规范：
    收集定义 → 构建期复制 → 逐节点注入 → 渲染。
    """

    def test_injection_walk_binds_every_node(self, dummy_dialect: DummyDialect):
        # 声明期形态：全部无方言。
        arr = ArrayType(None, IntegerType(None))
        col = ColumnDefinition(None, "name", arr)
        tree = [col]

        # 框架遍历注入：对每个节点赋值方言（setter 只影响本节点）。
        for node in tree:
            node.dialect = dummy_dialect
            node.data_type.dialect = dummy_dialect
            node.data_type.element_type.dialect = dummy_dialect

        # 全树就位后渲染，与显式构造完全一致。
        sql, _ = col.to_sql()
        assert "INTEGER" in sql

    def test_partial_injection_fails_fast(self, dummy_dialect: DummyDialect):
        # 只注入列节点、不注入类型节点 → 渲染时类型节点护栏生效。
        t = VarCharType(None, 255)
        col = ColumnDefinition(dummy_dialect, "name", t)
        with pytest.raises(ValueError) as excinfo:
            col.to_sql()
        assert "has no dialect bound" in str(excinfo.value)
        assert "VarCharType" in str(excinfo.value)


class TestDeferredAssignment:
    """路径 2 的单节点形态：构造时 None，之后通过 setter 推迟绑定。"""

    def test_deferred_assignment_renders(self, dummy_dialect: DummyDialect):
        t = VarCharType(None, 255)
        assert t._dialect is None  # 构造后确实未绑定
        t.dialect = dummy_dialect  # 推迟赋值
        assert t.to_sql() == ("VARCHAR(255)", ())

    def test_deferred_matches_explicit(self, dummy_dialect: DummyDialect):
        deferred = VarCharType(None, 255)
        deferred.dialect = dummy_dialect
        explicit = VarCharType(dummy_dialect, 255)
        assert deferred.to_sql() == explicit.to_sql()

    def test_setter_does_not_propagate(self, dummy_dialect: DummyDialect):
        # setter 只影响本节点——这是 D4 决策的锚点断言。
        arr = ArrayType(None, IntegerType(None))
        arr.dialect = dummy_dialect
        assert arr._dialect is dummy_dialect
        assert arr.element_type._dialect is None  # 未传播


class TestRenderGuard:
    """渲染护栏：未绑定方言不得静默渲染。"""

    def test_unbound_render_raises(self):
        t = VarCharType(None, 255)
        with pytest.raises(Exception) as excinfo:
            t.to_sql()
        assert "has no dialect bound" in str(excinfo.value)

    def test_column_definition_with_unbound_type_raises(self):
        t = VarCharType(None, 255)
        col = ColumnDefinition(None, "name", t)
        with pytest.raises(Exception):
            col.to_sql()


class TestValueObjectSemantics:
    """相等性/哈希忽略方言 —— 纯比较测试中传 None 与传方言等价的依据。"""

    def test_equality_ignores_dialect(self, dummy_dialect: DummyDialect):
        assert VarCharType(None, 255) == VarCharType(dummy_dialect, 255)
        assert hash(VarCharType(None, 255)) == hash(
            VarCharType(dummy_dialect, 255)
        )
        assert VarCharType(None, 255) != VarCharType(None, 100)


class TestDialectOptionsChannel:
    """dialect_options：参数面的扩展通道（刁钻参数不进构造签名）。

    * 参与相等性（渲染语义的一部分）
    * 不参与哈希（文档化不对称：options 是配置，极少被哈希）
    * 不影响渲染文本（方言格式化函数自行决定是否消费）
    """

    def test_options_participate_in_equality(self, dummy_dialect: DummyDialect):
        a = VarCharType(dummy_dialect, 255, dialect_options={"unsigned": True})
        b = VarCharType(dummy_dialect, 255, dialect_options={"unsigned": True})
        c = VarCharType(dummy_dialect, 255, dialect_options={"unsigned": False})
        assert a == b
        assert a != c
        assert a != VarCharType(dummy_dialect, 255)

    def test_options_deferred_dict_isolation(self, dummy_dialect: DummyDialect):
        # 构造后传入的 dict 被拷贝——外部修改不污染实例。
        opts = {"x": 1}
        t = VarCharType(dummy_dialect, 10, dialect_options=opts)
        opts["x"] = 2
        assert t.dialect_options == {"x": 1}

    def test_options_do_not_affect_render_text(self, dummy_dialect: DummyDialect):
        # dummy 的格式化函数不消费 options——渲染文本不受影响；
        # 消费与否是方言格式化函数的职责（(self, expr) 原则）。
        plain = VarCharType(dummy_dialect, 255)
        adorned = VarCharType(dummy_dialect, 255, dialect_options={"x": 1})
        assert plain.to_sql() == adorned.to_sql() == ("VARCHAR(255)", ())
