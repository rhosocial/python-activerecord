# 集合运算、EXPLAIN和JOIN的完整使用示例

from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.query import ActiveQuery
from rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat
from datetime import datetime, timedelta

# ============================================================================
# 模型定义
# ============================================================================

class User(ActiveRecord):
    __table_name__ = 'users'
    id: int
    name: str
    email: str
    department: str
    status: str
    created_at: datetime
    salary: float

class Order(ActiveRecord):
    __table_name__ = 'orders'
    id: int
    user_id: int
    product_id: int
    amount: float
    order_date: datetime
    status: str

class Product(ActiveRecord):
    __table_name__ = 'products'
    id: int
    name: str
    category: str
    price: float
    stock: int

class Employee(ActiveRecord):
    __table_name__ = 'employees'
    id: int
    name: str
    department: str
    position: str
    salary: float
    hire_date: datetime

class Contractor(ActiveRecord):
    __table_name__ = 'contractors'
    id: int
    name: str
    department: str
    hourly_rate: float


# ============================================================================
# 第一部分：EXPLAIN在集合运算中的使用
# ============================================================================

def example_explain_basic_union():
    """基础UNION的执行计划分析"""
    # 活跃用户
    active_users = User.query().where('status = ?', ('active',))
    # 高级用户
    premium_users = User.query().where('status = ?', ('premium',))
    
    # 获取UNION的执行计划（默认TEXT格式）
    plan = active_users.union(premium_users).explain().all()
    print("基础UNION执行计划:")
    print(plan)
    
    # 使用EXPLAIN ANALYZE（实际执行并显示统计）
    plan_analyze = active_users.union(premium_users) \
        .explain(type=ExplainType.ANALYZE).all()
    print("\nUNION的ANALYZE执行计划:")
    print(plan_analyze)
    
    return plan

def example_explain_complex_set_operation():
    """复杂集合运算的执行计划分析"""
    # 三个查询组件
    dept_a = Employee.query().where('department = ?', ('A',))
    dept_b = Employee.query().where('department = ?', ('B',))
    high_salary = Employee.query().where('salary > ?', (80000,))
    
    # 复杂集合运算：(A ∪ B) ∩ 高薪
    complex_query = dept_a.union(dept_b).intersect(high_salary)
    
    # 获取不同格式的执行计划
    
    # JSON格式（便于程序解析）
    plan_json = complex_query.explain(format=ExplainFormat.JSON).all()
    print("JSON格式执行计划:", plan_json)
    
    # VERBOSE模式（更详细的信息）
    plan_verbose = complex_query.explain(
        type=ExplainType.VERBOSE
    ).all()
    print("VERBOSE执行计划:", plan_verbose)
    
    # BUFFERS信息（PostgreSQL）
    try:
        plan_buffers = complex_query.explain(
            type=ExplainType.BUFFERS
        ).all()
        print("BUFFERS执行计划:", plan_buffers)
    except:
        print("当前数据库不支持EXPLAIN BUFFERS")
    
    return plan_json

def example_explain_with_aggregation():
    """带聚合的集合运算执行计划"""
    # 2023年订单
    orders_2023 = Order.query() \
        .where('YEAR(order_date) = ?', (2023,)) \
        .select('user_id', 'amount')
    
    # 2024年订单
    orders_2024 = Order.query() \
        .where('YEAR(order_date) = ?', (2024,)) \
        .select('user_id', 'amount')
    
    # UNION后聚合
    combined = orders_2023.union(orders_2024, all=True) \
        .group_by('user_id') \
        .sum('amount', 'total_amount') \
        .having('SUM(amount) > ?', (5000,))
    
    # 分析聚合查询的执行计划
    plan = combined.explain(type=ExplainType.ANALYZE).aggregate()
    print("聚合集合运算的执行计划:", plan)
    
    return plan


# ============================================================================
# 第二部分：集合运算作为子查询参与JOIN
# ============================================================================

def example_set_operation_as_join_subquery():
    """集合运算结果作为子查询参与JOIN"""
    # 创建特殊用户集合（活跃 ∪ 高级）
    active = User.query().where('status = ?', ('active',)).select('id', 'name')
    premium = User.query().where('status = ?', ('premium',)).select('id', 'name')
    special_users = active.union(premium)
    
    # 方法1：使用as_subquery()参与JOIN
    orders_with_special = Order.query() \
        .inner_join(
            special_users.as_subquery('su'),
            'orders.user_id = su.id'
        ) \
        .select('orders.*', 'su.name as user_name') \
        .all()
    
    print("特殊用户的订单（INNER JOIN）:", orders_with_special)
    
    # 方法2：使用join_on()自定义条件
    orders_custom = Order.query() \
        .join_on(
            special_users.as_subquery('special'),
            'orders.user_id = special.id AND orders.amount > ?',
            params=(100,)
        ) \
        .all()
    
    return orders_with_special

def example_left_join_with_set_operation():
    """LEFT JOIN与集合运算结合"""
    # 高价值员工：高薪 ∩ 老员工
    high_salary = Employee.query() \
        .where('salary > ?', (100000,)) \
        .select('id', 'name', 'department')
    
    senior = Employee.query() \
        .where('hire_date < ?', (datetime.now() - timedelta(days=365*5),)) \
        .select('id', 'name', 'department')
    
    valuable_employees = high_salary.intersect(senior)
    
    # 所有订单LEFT JOIN高价值员工（显示哪些订单是高价值员工创建的）
    orders_analysis = Order.query() \
        .left_join(
            valuable_employees.as_subquery('ve'),
            'orders.user_id = ve.id'
        ) \
        .select(
            'orders.*',
            'COALESCE(ve.name, "Regular Customer") as employee_type'
        ) \
        .all()
    
    print("订单分析（区分高价值员工）:", orders_analysis)
    
    # 获取执行计划
    plan = Order.query() \
        .left_join(
            valuable_employees.as_subquery('ve'),
            'orders.user_id = ve.id'
        ) \
        .explain() \
        .all()
    
    print("LEFT JOIN执行计划:", plan)
    
    return orders_analysis


# ============================================================================
# 第三部分：所有JOIN类型的完整示例
# ============================================================================

def example_all_join_types():
    """演示所有JOIN类型与集合运算的结合"""
    
    # 准备数据：活跃用户集合
    active_users = User.query() \
        .where('status = ?', ('active',)) \
        .union(
            User.query().where('status = ?', ('premium',))
        )
    
    # 1. INNER JOIN - 只返回匹配的行
    inner_result = Order.query() \
        .inner_join(
            active_users.as_subquery('au'),
            'orders.user_id = au.id'
        ) \
        .select('orders.id', 'au.name') \
        .limit(5) \
        .all()
    print("INNER JOIN结果:", inner_result)
    
    # 2. LEFT JOIN - 返回左表所有行
    left_result = Order.query() \
        .left_join(
            active_users.as_subquery('au'),
            'orders.user_id = au.id'
        ) \
        .select('orders.id', 'au.name') \
        .limit(5) \
        .all()
    print("LEFT JOIN结果:", left_result)
    
    # 3. RIGHT JOIN - 返回右表所有行（注意：不是所有数据库都支持）
    try:
        right_result = active_users.as_subquery('au') \
            .right_join('orders', 'au.id = orders.user_id') \
            .select('orders.id', 'au.name') \
            .limit(5) \
            .all()
        print("RIGHT JOIN结果:", right_result)
    except:
        print("当前数据库不支持RIGHT JOIN")
    
    # 4. FULL OUTER JOIN - 返回两表所有行（注意：MySQL、SQLite不支持）
    try:
        full_result = Order.query() \
            .full_join(
                active_users.as_subquery('au'),
                'orders.user_id = au.id'
            ) \
            .select('orders.id', 'au.name') \
            .limit(5) \
            .all()
        print("FULL OUTER JOIN结果:", full_result)
    except:
        print("当前数据库不支持FULL OUTER JOIN")
    
    # 5. CROSS JOIN - 笛卡尔积（慎用，结果集很大）
    # 获取所有产品类别与部门的组合
    categories = Product.query() \
        .select('DISTINCT category') \
        .union(
            Product.query().select("'Special' as category")
        )
    
    departments = Employee.query() \
        .select('DISTINCT department')
    
    cross_result = categories.as_subquery('c') \
        .cross_join(departments.as_subquery('d')) \
        .select('c.category', 'd.department') \
        .limit(10) \
        .all()
    print("CROSS JOIN结果（前10个组合）:", cross_result)
    
    return {
        'inner': inner_result,
        'left': left_result,
        'cross': cross_result
    }


# ============================================================================
# 第四部分：复杂场景 - 多重JOIN与集合运算
# ============================================================================

def example_multiple_joins_with_set_operations():
    """多重JOIN与集合运算的复杂场景"""
    
    # 场景：分析订单、用户和产品的关系
    # 其中用户来自集合运算，产品也来自集合运算
    
    # 特殊用户：活跃或VIP
    special_users = User.query() \
        .where('status = ?', ('active',)) \
        .union(User.query().where('status = ?', ('vip',))) \
        .select('id', 'name', 'department')
    
    # 热门产品：高销量或高评分
    hot_products = Product.query() \
        .where('stock < ?', (10,)) \
        .union(Product.query().where('price > ?', (1000,))) \
        .select('id', 'name as product_name', 'category')
    
    # 复杂的多重JOIN
    analysis = Order.query() \
        .inner_join(
            special_users.as_subquery('u'),
            'orders.user_id = u.id'
        ) \
        .inner_join(
            hot_products.as_subquery('p'),
            'orders.product_id = p.id'
        ) \
        .select(
            'orders.id as order_id',
            'orders.amount',
            'u.name as user_name',
            'u.department',
            'p.product_name',
            'p.category'
        ) \
        .where('orders.amount > ?', (500,)) \
        .order_by('orders.amount DESC') \
        .limit(20)
    
    # 获取执行计划
    plan = analysis.explain(type=ExplainType.ANALYZE).all()
    print("复杂多重JOIN的执行计划:", plan)
    
    # 执行查询
    results = analysis.all()
    print("分析结果（前20条）:", results)
    
    return results


# ============================================================================
# 第五部分：性能优化案例
# ============================================================================

def example_optimized_join_strategies():
    """JOIN性能优化策略示例"""
    
    # 策略1：使用CTE减少重复计算
    high_value_users = User.query() \
        .where('salary > ?', (100000,)) \
        .union(User.query().where('status = ?', ('vip',)))
    
    # 将集合运算结果转为CTE
    query_with_cte = Order.query() \
        .with_cte('high_users', high_value_users) \
        .join('JOIN high_users ON orders.user_id = high_users.id') \
        .select('orders.*', 'high_users.name')
    
    # 比较执行计划
    plan_direct = Order.query() \
        .inner_join(
            high_value_users.as_subquery('hu'),
            'orders.user_id = hu.id'
        ) \
        .explain().all()
    
    plan_cte = query_with_cte.explain().all()
    
    print("直接JOIN的执行计划:", plan_direct)
    print("使用CTE的执行计划:", plan_cte)
    
    # 策略2：先过滤再JOIN（减少JOIN的数据量）
    # 不好的做法：先JOIN再过滤
    bad_query = Order.query() \
        .inner_join('users', 'orders.user_id = users.id') \
        .where('users.status = ?', ('active',)) \
        .where('orders.amount > ?', (1000,))
    
    # 好的做法：先过滤再JOIN
    filtered_users = User.query() \
        .where('status = ?', ('active',)) \
        .select('id', 'name')
    
    filtered_orders = Order.query() \
        .where('amount > ?', (1000,))
    
    good_query = filtered_orders \
        .inner_join(
            filtered_users.as_subquery('u'),
            'orders.user_id = u.id'
        )
    
    # 比较执行计划
    print("不优化的执行计划:")
    print(bad_query.explain(type=ExplainType.COSTS).all())
    
    print("优化后的执行计划:")
    print(good_query.explain(type=ExplainType.COSTS).all())
    
    return {'bad': bad_query, 'good': good_query}


# ============================================================================
# 第六部分：特殊场景处理
# ============================================================================

def example_handling_database_differences():
    """处理不同数据库的差异"""
    
    # 获取数据库类型
    backend = User.backend()
    db_type = backend.__class__.__name__
    
    print(f"当前数据库: {db_type}")
    
    # 准备集合运算
    q1 = User.query().where('status = ?', ('active',))
    q2 = User.query().where('status = ?', ('inactive',))
    
    if 'MySQL' in db_type:
        # MySQL特定处理
        if backend.version < (8, 0, 31):
            print("MySQL版本低于8.0.31，INTERSECT和EXCEPT将被模拟")
            # Handler会自动处理
        
        # MySQL支持的JOIN hint
        query = Order.query() \
            .join('JOIN /*+ BKA(users) */ users ON orders.user_id = users.id')
    
    elif 'SQLite' in db_type:
        # SQLite不支持RIGHT JOIN和FULL JOIN
        print("SQLite不支持RIGHT JOIN和FULL OUTER JOIN")
        
        # 使用LEFT JOIN替代RIGHT JOIN
        query = Order.query() \
            .left_join('users', 'orders.user_id = users.id')
    
    elif 'PostgreSQL' in db_type:
        # PostgreSQL支持所有标准功能
        print("PostgreSQL支持所有SQL标准的集合运算和JOIN类型")
        
        # 可以使用LATERAL JOIN（PostgreSQL特性）
        subquery = q1.except_(q2).limit(10)
        query = Order.query() \
            .join(f'JOIN LATERAL {subquery.as_subquery("u")} ON TRUE')
    
    else:
        # 通用处理
        query = Order.query() \
            .inner_join('users', 'orders.user_id = users.id')
    
    # 执行并获取计划
    plan = query.explain().all()
    print(f"{db_type}的执行计划:", plan)
    
    return query


# ============================================================================
# 第七部分：递归CTE与集合运算
# ============================================================================

def example_recursive_cte_with_set_operations():
    """递归CTE与集合运算的结合（高级）"""
    
    # 递归查询组织层级
    # 基础：顶级员工
    base = Employee.query() \
        .where('position = ?', ('CEO',)) \
        .select('id', 'name', 'department', '1 as level')
    
    # 递归部分：下属员工
    recursive_part = """
        SELECT e.id, e.name, e.department, h.level + 1
        FROM employees e
        JOIN hierarchy h ON e.manager_id = h.id
        WHERE h.level < 5
    """
    
    # 额外的特殊员工（通过集合运算添加）
    special = Employee.query() \
        .where('position = ?', ('Board Member',)) \
        .select('id', 'name', 'department', '0 as level')
    
    # 组合：特殊员工 ∪ 层级结构
    combined = special.union(base)
    
    # 创建递归CTE并JOIN
    full_query = Order.query() \
        .with_recursive_cte(
            'hierarchy',
            combined,  # 使用集合运算结果作为基础
            recursive_part
        ) \
        .join('JOIN hierarchy h ON orders.user_id = h.id') \
        .select('orders.*', 'h.name', 'h.level') \
        .order_by('h.level', 'orders.amount DESC')
    
    # 分析执行计划
    plan = full_query.explain(
        type=ExplainType.VERBOSE,
        format=ExplainFormat.JSON
    ).all()
    
    print("递归CTE与集合运算的执行计划:", plan)
    
    return full_query


# ============================================================================
# 第八部分：窗口函数与集合运算后的JOIN
# ============================================================================

def example_window_functions_after_set_operations():
    """在集合运算结果上使用窗口函数"""
    
    # 合并多年数据
    sales_2022 = Order.query() \
        .where('YEAR(order_date) = ?', (2022,)) \
        .select('user_id', 'amount', '2022 as year')
    
    sales_2023 = Order.query() \
        .where('YEAR(order_date) = ?', (2023,)) \
        .select('user_id', 'amount', '2023 as year')
    
    sales_2024 = Order.query() \
        .where('YEAR(order_date) = ?', (2024,)) \
        .select('user_id', 'amount', '2024 as year')
    
    # 三年数据UNION
    all_sales = sales_2022.union(sales_2023).union(sales_2024, all=True)
    
    # 在结果上应用窗口函数
    ranked_sales = User.query() \
        .inner_join(
            all_sales.as_subquery('s'),
            'users.id = s.user_id'
        ) \
        .select(
            'users.name',
            's.year',
            's.amount',
            'ROW_NUMBER() OVER (PARTITION BY s.year ORDER BY s.amount DESC) as rank',
            'SUM(s.amount) OVER (PARTITION BY users.id) as total_by_user'
        ) \
        .where('s.amount > ?', (100,))
    
    # 获取执行计划
    plan = ranked_sales.explain().all()
    print("窗口函数执行计划:", plan)
    
    results = ranked_sales.limit(20).all()
    print("排名结果（前20）:", results)
    
    return results


# ============================================================================
# 主执行函数
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("集合运算、EXPLAIN和JOIN的完整示例")
    print("=" * 80)
    
    # 第一部分：EXPLAIN
    print("\n【第一部分：EXPLAIN在集合运算中的使用】")
    example_explain_basic_union()
    example_explain_complex_set_operation()
    example_explain_with_aggregation()
    
    # 第二部分：集合运算作为子查询
    print("\n【第二部分：集合运算作为子查询参与JOIN】")
    example_set_operation_as_join_subquery()
    example_left_join_with_set_operation()
    
    # 第三部分：所有JOIN类型
    print("\n【第三部分：所有JOIN类型的完整示例】")
    example_all_join_types()
    
    # 第四部分：复杂场景
    print("\n【第四部分：多重JOIN与集合运算】")
    example_multiple_joins_with_set_operations()
    
    # 第五部分：性能优化
    print("\n【第五部分：性能优化案例】")
    example_optimized_join_strategies()
    
    # 第六部分：数据库差异
    print("\n【第六部分：处理数据库差异】")
    example_handling_database_differences()
    
    # 第七部分：递归CTE
    print("\n【第七部分：递归CTE与集合运算】")
    try:
        example_recursive_cte_with_set_operations()
    except Exception as e:
        print(f"递归CTE示例失败: {e}")
    
    # 第八部分：窗口函数
    print("\n【第八部分：窗口函数与集合运算】")
    example_window_functions_after_set_operations()
    
    print("\n" + "=" * 80)
    print("所有示例执行完成！")