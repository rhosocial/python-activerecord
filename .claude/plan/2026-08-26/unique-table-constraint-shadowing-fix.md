# 表级 UNIQUE 约束被列级同名方法遮蔽 —— 修复记录

> **日期**: 2026-08-26
> **影响范围**: `backend.impl.sqlite`（仅；其余后端无此覆盖）
> **发现路径**: 下游 rhosocial-user 的 identity.federation 模块
> **状态**: 已修复，回归测试就位

---

## 1. 前因后果

### 1.1 如何发现

下游项目 rhosocial-user（本生态的 RBAC/身份框架）为外部身份链接表
`(tenant_id, provider, subject)` 声明 DDL 级 UNIQUE 约束后，
`create_all` 在 SQLite 上抛出：

```
TypeError: sequence item 0: expected str instance, tuple found
    at backend/dialect/mixins/ddl_column.py:145
      return " ".join(const_parts) if const_parts else "", tuple(params)
```

### 1.2 根因

**两个语义无关的方法共用同一个名字，且后者遮蔽前者：**

| 层 | 文件 | 签名 | 用途 | 返回 |
|---|---|---|---|---|
| 基础方言 | `backend/dialect/mixins/ddl_column.py:99` | `format_unique_constraint(t_const) -> str` | **表级**约束（`TableConstraintType.UNIQUE`） | `"UNIQUE (cols)"` |
| SQLite 实现 | `backend/impl/sqlite/mixins/ddl_column.py:102` | `format_unique_constraint(constraint) -> Tuple[str, tuple]` | **列级**约束（`ColumnConstraintType.UNIQUE` 单列内联 `UNIQUE`） | `" UNIQUE", ()` |

`format_table_constraint_sql` 分发器通过 `self.format_unique_constraint`
调用表级格式化器；MRO 使 SQLiteDialect 的**列级**实现胜出——返回的元组
`(str, ())` 被当作字符串塞进 `const_parts`，`" ".join(...)` 即崩。

### 1.3 影响面排查

- 全 impl 目录 grep：仅 SQLite 定义了该列级名（其余后端回落基础实现，
  故多后端矩阵中 MySQL/PG 等从未暴露此缺陷——这也解释了为何长期潜伏）；
- 同文件其它列级方法与表级分发器所调名字**均不同名**
  （`format_primary_key_constraint` vs `format_pk_constraint`、
  `format_check_constraint` vs `format_table_check_constraint`、
  `format_column_fk_constraint` vs `format_foreign_key_constraint`），
  UNIQUE 是唯一碰撞点；
- 长期潜伏原因：既有测试只覆盖列级 handler 本身，缺少
  "表级 UNIQUE 经 CreateTableExpression 全链路编译"的用例。

## 2. 修复方案

1. **重命名消除遮蔽**：SQLite 列级方法更名为
   `format_column_unique_constraint`（与其邻居
   `format_primary_key_constraint` / `format_check_constraint` 的命名
   家族风格一致），同步更新其 `ColumnConstraintType` 分派表引用；
   附注释说明两层级不可重名的签名差异。
2. **回归测试**（新增
   `tests/.../sqlite2/test_sqlite_dialect_table_constraints.py`）：
   - 表级 UNIQUE / PRIMARY KEY 经 `CreateTableExpression.to_sql()` 全链路
     编译产物断言（含命名 `CONSTRAINT "uq_demo_code"` 变体）；
   - 列级新名可达性断言；
   - **防复发守卫**：断言 `vars(SQLiteDialect)` 中不再出现
     `format_unique_constraint`。
3. 更新引用旧列级名的一处既有测试。

不采用的分案：在表分发器里做 str/tuple 归一化容错——能止血但会掩盖
"两层同名异形"的设计问题，且其余后端无此需求。

## 3. 修复后效果

### 3.1 直接效果（最小复现前后对比）

```
修复前: TableConstraintType.UNIQUE -> TypeError: sequence item 0:
        expected str instance, tuple found
修复后: TableConstraintType.UNIQUE ->
        CREATE TABLE "demo" ("id" INTEGER, "code" TEXT NOT NULL,
                             UNIQUE ("code"))
        TableConstraintType.PRIMARY_KEY -> （行为不变）
```

### 3.2 测试证据

| 套件 | 结果 |
|---|---|
| 核心 sqlite2 目录（128 项，含新增 7 项回归） | ✅ 全绿 |
| 新增回归文件 test_sqlite_dialect_table_constraints.py | ✅ 7/7 |
| 更新后的列级约束测试文件 | ✅ 24/24 |
| 核心全量套件 | ⚠️ 见 §3.5 环境注意事项 |

### 3.3 下游联动收益

rhosocial-user 的 federation 模块随即恢复 DDL 级 UNIQUE 声明：
其 8 项联邦测试全绿，全套件 183 passed。应用层守卫保留——SQL 标准
对 NULL 的 UNIQUE 语义是"互异"，NULL-tenant（独立部署形态）下的重复
链接仍需应用层拦截，两层防护互补。

### 3.4 兼容性说明

- 仅重命名 SQLite 内部受保护用途的方法 + 更新一处测试引用，
  无公共 API 变化；
- 其它六个后端实现未定义该列级名，行为零变化。

### 3.5 环境注意事项（与本次修复无关的既有问题）

本机沙箱中核心全量套件存在**与 DDL 无关的既有阻塞**：

1. `feature/worker/test_worker_pool.py` 的进程池用例
   （crash_and_restart / kill_on_dead_process 等 4 项）在未修改的基线
   上同样挂起/失败——子进程编排类用例对本沙箱的进程控制语义敏感；
   该目录已被本次验证显式排除。
2. 排除 worker 后再次运行，于 `feature/relation/test_redis_cache.py`
   （Redis 未安装，优雅跳过）之后仍有未知尾段阻塞，两轮分别推进至
   46% 与 97%，**期间零失败、零 DDL/约束相关错误**。
3. 结论：上述现象在修复前后行为一致（worker 用例在含/不含修复的两种
   树状态下均复现），与本重命名无因果关联。建议后续单独排查沙箱的
   子进程/信号语义。

### 3.6 逐后端审计矩阵（2026-08-26 补充）

对全部九个后端实现仓库做两层核验：

**静态层**：grep 九个 `src/rhosocial/activerecord/backend/impl/*/`
——除 SQLite 外，没有任何后端定义表分发器所调用的四个名字
（format_pk_constraint / format_unique_constraint /
format_table_check_constraint / format_foreign_key_constraint），
也没有后端整体覆盖 format_table_constraint_sql。故其余后端一律继承
基础方言的正确实现。

**动态层**：以命名空间合并 PYTHONPATH + DBAPI 桩加载各方言类并实际
编译 TableConstraintType.UNIQUE：

| 后端 | 结果 | 说明 |
|---|---|---|
| sqlite | ✅ | 本修复直接验证 |
| firebird / bigquery / snowflake / mariadb / sqlserver / oracle | ✅ | 编译通过 |
| clickhouse | ⚠️ 设计如此 | 方言显式抛 UnsupportedFeatureError：不支持 UNIQUE 表约束（能力矩阵声明，非缺陷） |
| mysql / postgres | ◐ 未能在本机动态验证 | 方言模块顶层深入导入驱动子模块，桩机制无法完全模拟；由静态层结论 + 两后端自有 CI 中复合主键约束（同一分发器路径）长期绿灯背书 |

结论：该遮蔽缺陷为 SQLite 独有；其余全部后端继承共享基类实现，
行为一致正确。
