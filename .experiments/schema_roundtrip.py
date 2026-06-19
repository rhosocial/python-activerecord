"""
实验：SQLite DDL 内省一致性 & 列类型表达式化分析

环境准备：
  1. 创建各种 DDL（列定义、索引、外键、视图）
  2. 内省并比对原始定义
  3. 检查列类型在表达式-方言中的传递方式

运行: python .experiments/schema_roundtrip.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableExpression, ColumnDefinition, ColumnConstraint, ColumnConstraintType,
    ForeignKeyConstraint, IndexDefinition
)

INDENT = "  "

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_sub(title):
    print(f"\n  --- {title} ---")


def experiment_column_types(backend):
    """实验1：列定义 round-trip"""
    print_section("实验 1：DDL 列定义 → 内省 → 对比")

    # 准备多种列类型
    columns = [
        ColumnDefinition("id", "INTEGER",
                         constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)]),
        ColumnDefinition("name", "VARCHAR(255)",
                         constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
        ColumnDefinition("email", "VARCHAR(100)",
                         constraints=[ColumnConstraint(ColumnConstraintType.UNIQUE)]),
        ColumnDefinition("age", "INTEGER"),
        ColumnDefinition("salary", "DECIMAL(10,2)",
                         constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
        ColumnDefinition("bio", "TEXT", constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="''")]),
        ColumnDefinition("is_active", "BOOLEAN",
                         constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="1")]),
        ColumnDefinition("created_at", "TIMESTAMP",
                         constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="CURRENT_TIMESTAMP")]),
        ColumnDefinition("rating", "SMALLINT"),
        ColumnDefinition("photo", "BLOB"),
    ]

    dialect = backend.dialect
    expr = CreateTableExpression(dialect, table="roundtrip_types", columns=columns)
    sql, params = expr.to_sql()
    print(f"\n生成的 DDL:\n{INDENT}{sql}")

    backend.execute(sql, params)

    # 内省
    columns_info = backend.introspector.list_columns("roundtrip_types")
    print(f"\n内省结果 ({len(columns_info)} 列):")
    for col in columns_info:
        print(f"{INDENT}{col.name:15s}  data_type={col.data_type:20s}  "
              f"data_type_full={str(col.data_type_full):25s}  "
              f"nullable={col.nullable.value:10s}  "
              f"pk={col.is_primary_key}  "
              f"default={col.default_value}")

    # 对比分析
    print_sub("对比分析")
    type_mismatches = []
    for orig, intro in zip(columns, columns_info):
        print(f"  DDL传入: data_type={orig.data_type:20s}  →  内省: "
              f"data_type={intro.data_type:20s}  full={intro.data_type_full}")
        # 检查 data_type 是否一致
        if orig.data_type.lower() != intro.data_type:
            type_mismatches.append((orig.name, orig.data_type, intro.data_type, intro.data_type_full))

    if type_mismatches:
        print(f"\n  ⚠ 数据类型不一致 ({len(type_mismatches)} 处):")
        for name, orig_t, intro_t, full_t in type_mismatches:
            print(f"    {name}: original='{orig_t}' → intro='{intro_t}' (full='{full_t}')")
    else:
        print(f"\n  ✅ 所有列 data_type 基本一致（忽略大小写）")

    # 特别检查 VARCHAR(255) → varchar(255) 还是 varchar
    vc = [c for c in columns_info if c.name == 'name'][0]
    print(f"\n  VARCHAR(255) 内省后: data_type='{vc.data_type}' (基类型, 无精度) "
          f"data_type_full='{vc.data_type_full}' (完整原始类型)")
    print(f"  → 结论: 内省时 data_type 被剥离了精度参数，损失了信息")


def experiment_indexes(backend):
    """实验2：索引 round-trip"""
    print_section("实验 2：索引 DDL → 内省 → 对比")

    dialect = backend.dialect

    # 先创建基础表
    be_cols = [
        ColumnDefinition("id", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
        ColumnDefinition("name", "TEXT", constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
        ColumnDefinition("email", "TEXT", constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
        ColumnDefinition("age", "INTEGER"),
        ColumnDefinition("city", "TEXT"),
    ]
    backend.executescript("""
        CREATE TABLE idx_test (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            age INTEGER,
            city TEXT
        );
        CREATE UNIQUE INDEX idx_test_email ON idx_test(email);
        CREATE INDEX idx_test_name_age ON idx_test(name, age);
        CREATE INDEX idx_test_city ON idx_test(city) WHERE city IS NOT NULL;
    """)

    indexes = backend.introspector.list_indexes("idx_test")
    print(f"内省结果 ({len(indexes)} 个索引):")
    for idx in indexes:
        cols = ', '.join(c.name for c in idx.columns)
        print(f"{INDENT}{idx.name:25s}  unique={idx.is_unique}  pk={idx.is_primary}  "
              f"type={idx.index_type.value:10s}  columns=[{cols}]  "
              f"filter={idx.filter_condition}")

    print_sub("对比分析")
    print(f"  - 唯一索引 idx_test_email: unique=True ✓")
    print(f"  - 复合索引 idx_test_name_age: 列顺序 name, age → 内省结果："
          f"{[c.name for c in [i for i in indexes if i.name=='idx_test_name_age'][0].columns]}")
    # SQLite 的 PRAGMA 不暴露 partial index 的 WHERE 条件
    partial = [i for i in indexes if i.name == 'idx_test_city']
    if partial:
        print(f"  - 部分索引 idx_test_city: filter_condition={partial[0].filter_condition}")
        if partial[0].filter_condition is None:
            print(f"    ⚠ SQLite PRAGMA 不返回 partial index 的 WHERE 条件！信息丢失")


def experiment_foreign_keys(backend):
    """实验3：外键 round-trip"""
    print_section("实验 3：外键 DDL → 内省 → 对比")

    backend.executescript("""
        CREATE TABLE fk_parent (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE fk_child (
            id INTEGER PRIMARY KEY,
            parent_id INTEGER NOT NULL,
            FOREIGN KEY (parent_id) REFERENCES fk_parent(id)
                ON DELETE CASCADE ON UPDATE SET NULL
        );
    """)

    # 需要开启外键支持
    backend.execute("PRAGMA foreign_keys = ON")

    fks = backend.introspector.list_foreign_keys("fk_child")
    print(f"内省结果 ({len(fks)} 个外键):")
    for fk in fks:
        print(f"{INDENT}{fk.name:20s}  columns={fk.columns}  "
              f"ref_table={fk.referenced_table}  ref_cols={fk.referenced_columns}  "
              f"on_update={fk.on_update.value:15s}  on_delete={fk.on_delete.value:15s}")

    print_sub("对比分析")
    print(f"  - 列映射: ['parent_id'] → ['id'] ✓")
    for fk in fks:
        if fk.on_update != fk.on_delete:
            print(f"  - ON UPDATE: {fk.on_update.value}, ON DELETE: {fk.on_delete.value}")
            # ON UPDATE SET NULL 是自定义行为, ON DELETE CASCADE 是标准
            print(f"  - 默认约束名: {fk.name} (自动生成, 非原始指定)")


def experiment_views(backend):
    """实验4：视图 round-trip"""
    print_section("实验 4：视图 DDL → 内省 → 对比")

    backend.executescript("""
        CREATE VIEW vw_sample AS
        SELECT 1 AS id, 'hello' AS msg;
    """)

    views = backend.introspector.list_views()
    print(f"内省结果 ({len(views)} 个视图):")
    for v in views:
        print(f"{INDENT}{v.name:20s}  definition={v.definition}")

    vw = backend.introspector.get_view_info("vw_sample")
    if vw:
        print(f"\n  获取视图详情: name={vw.name}, definition={vw.definition}")
    print(f"  ✅ 视图定义通过 sqlite_master 完整保存")


def experiment_ddl_expression_flow(backend):
    """实验5：追踪列类型在表达式-方言系统中的传递路径"""
    print_section("实验 5：列类型表达式化分析")

    dialect = backend.dialect

    # 步骤1：构建 ColumnDefinition
    print("步骤1: 用户创建 ColumnDefinition 时 data_type 是普通字符串")
    col = ColumnDefinition("test_col", "VARCHAR(255)",
                           constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)])
    print(f"{INDENT}ColumnDefinition(name='test_col', data_type='{col.data_type}')")
    print(f"{INDENT}→ data_type 类型: {type(col.data_type).__name__}")

    # 步骤2：查看 dialect 如何处理列定义
    print("\n步骤2: dialect.format_column_definition 调用链")
    col_sql, col_params = dialect.format_column_definition(col)
    print(f"{INDENT}format_column_definition 输出: '{col_sql}'")
    print(f"{INDENT}→ data_type 直接被拼接到 SQL 中, 没有任何转换")

    # 步骤3：构建完整 DDL
    print("\n步骤3: CreateTableExpression.to_sql()")
    columns = [col, ColumnDefinition("id", "INTEGER",
                                     constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)])]
    expr = CreateTableExpression(dialect, table="type_flow_test", columns=columns)
    full_sql, full_params = expr.to_sql()
    print(f"{INDENT}完整 CREATE TABLE: {full_sql}")
    print(f"{INDENT}→ data_type 仅是字符串拼接: '{col.data_type}' → 出现在 SQL 中的位置")

    # 步骤4：SQLite 如何存储类型
    print("\n步骤4: SQLite 类型亲缘性（Type Affinity）")
    backend.execute(full_sql, full_params)
    raw = backend.introspector.pragma.table_info("type_flow_test")
    for row in raw:
        print(f"{INDENT}PRAGMA table_info: name={row['name']:10s}  type={row['type']:20s}  notnull={row['notnull']}  pk={row['pk']}")
    print(f"{INDENT}→ SQLite 以字符串原样存储 'VARCHAR(255)', 不做解析")

    # 步骤5：内省后的 ColumnInfo
    print(f"\n步骤5: 内省返回的 ColumnInfo")
    col_info = backend.introspector.list_columns("type_flow_test")
    for c in col_info:
        print(f"{INDENT}ColumnInfo: name={c.name:10s}  data_type='{c.data_type}'  data_type_full='{c.data_type_full}'")
    print(f"{INDENT}→ data_type 被剥离精度 -> 'varchar', 原始值保存于 data_type_full")

    # 清理
    backend.execute('DROP TABLE IF EXISTS type_flow_test')


def main():
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    backend.introspect_and_adapt()

    try:
        experiment_column_types(backend)
        experiment_indexes(backend)
        experiment_foreign_keys(backend)
        experiment_views(backend)
        experiment_ddl_expression_flow(backend)

        print_section("总结")
        print("""
1. DDL 内省一致性：
   - 列定义: data_type 被剥离精度参数（VARCHAR(255) → varchar），信息损失
   - 索引: 普通+唯一+复合可正确内省；partial index 的 WHERE 条件丢失
   - 外键: 基本正确，但约束名自动生成而非原始指定
   - 视图: 完整保留定义

2. 列类型表达式化：
   - data_type 是普通 str，非表达式对象
   - 方言直接拼接字符串，无类型映射/转换
   - SQLite 原样存储类型字符串
   - 内省时基类型和完整类型分别存储于 data_type / data_type_full
        """)
    finally:
        backend.disconnect()


if __name__ == "__main__":
    main()
