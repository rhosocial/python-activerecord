# 电商数据分析综合示例：双11活动分析
# 结合集合运算、CTE、JOIN、聚合、窗口函数、EXPLAIN等所有功能

from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.query import ActiveQuery
from rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat
from datetime import datetime, timedelta
from decimal import Decimal

# ============================================================================
# 电商业务模型定义
# ============================================================================

class User(ActiveRecord):
    """用户表 - 包含买家和卖家"""
    __table_name__ = 'users'
    id: int
    username: str
    email: str
    user_type: str  # 'buyer', 'seller', 'both'
    vip_level: int  # 0-5, 0表示普通用户
    register_date: datetime
    last_login: datetime
    account_balance: Decimal
    points: int  # 积分
    city: str
    province: str

class Product(ActiveRecord):
    """商品表"""
    __table_name__ = 'products'
    id: int
    name: str
    category: str  # '电子产品', '服装', '食品', '图书', '家居'
    brand: str
    price: Decimal
    cost: Decimal  # 成本
    stock: int
    seller_id: int  # 卖家ID
    listing_date: datetime
    rating: float  # 1-5评分
    sales_count: int  # 销量

class Order(ActiveRecord):
    """订单表"""
    __table_name__ = 'orders'
    id: int
    order_no: str
    buyer_id: int
    seller_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    total_amount: Decimal
    discount_amount: Decimal  # 优惠金额
    actual_amount: Decimal  # 实付金额
    order_date: datetime
    status: str  # 'pending', 'paid', 'shipped', 'completed', 'cancelled', 'refunded'
    payment_method: str  # 'alipay', 'wechat', 'card', 'points'
    shipping_address: str

class CartItem(ActiveRecord):
    """购物车项"""
    __table_name__ = 'cart_items'
    id: int
    user_id: int
    product_id: int
    quantity: int
    added_date: datetime

class Review(ActiveRecord):
    """商品评价"""
    __table_name__ = 'reviews'
    id: int
    order_id: int
    product_id: int
    user_id: int
    rating: int  # 1-5
    comment: str
    review_date: datetime
    helpful_count: int  # 有用数

class Coupon(ActiveRecord):
    """优惠券"""
    __table_name__ = 'coupons'
    id: int
    code: str
    type: str  # 'percentage', 'fixed', 'buy_one_get_one'
    value: Decimal
    min_purchase: Decimal  # 最低消费
    valid_from: datetime
    valid_until: datetime
    usage_limit: int
    used_count: int

class UserCoupon(ActiveRecord):
    """用户优惠券"""
    __table_name__ = 'user_coupons'
    id: int
    user_id: int
    coupon_id: int
    obtained_date: datetime
    used_date: datetime
    order_id: int  # 使用的订单


# ============================================================================
# 场景1：双11活动用户分析 - 综合运用所有功能
# ============================================================================

def analyze_double11_comprehensive():
    """
    双11活动综合分析：识别高价值用户、分析购买行为、优化营销策略
    
    业务场景：
    1. 识别活跃买家（最近30天有购买）和VIP用户的并集
    2. 分析这些用户的购买偏好
    3. 找出最受欢迎的商品类别
    4. 计算不同用户群体的贡献度
    5. 生成营销建议
    """
    
    print("=" * 80)
    print("双11活动综合分析 - 展示所有高级查询功能")
    print("=" * 80)
    
    # 设置时间范围
    double11_start = datetime(2024, 11, 1)
    double11_end = datetime(2024, 11, 11)
    last_30_days = datetime.now() - timedelta(days=30)
    
    # ========== 步骤1：使用集合运算识别目标用户群体 ==========
    print("\n【步骤1：识别目标用户群体】")
    
    # 活跃买家：最近30天有购买
    active_buyers = Order.query() \
        .where('order_date > ?', (last_30_days,)) \
        .where('status IN (?, ?, ?)', ('paid', 'shipped', 'completed')) \
        .select('DISTINCT buyer_id as id') \
        .group_by('buyer_id') \
        .having('COUNT(*) >= ?', (2,))  # 至少2单
    
    # VIP用户：VIP等级3以上
    vip_users = User.query() \
        .where('vip_level >= ?', (3,)) \
        .where('user_type IN (?, ?)', ('buyer', 'both')) \
        .select('id')
    
    # 高消费用户：单笔订单超过1000元
    high_spenders = Order.query() \
        .where('actual_amount > ?', (1000,)) \
        .select('DISTINCT buyer_id as id')
    
    # 使用集合运算组合用户群体
    # 目标用户 = (活跃买家 ∪ VIP用户) ∩ 高消费用户
    target_users = active_buyers.union(vip_users).intersect(high_spenders)
    
    # 查看执行计划
    plan = target_users.explain(type=ExplainType.ANALYZE).all()
    print(f"目标用户识别执行计划：\n{plan[:500]}...")  # 只显示前500字符
    
    # ========== 步骤2：使用CTE分析用户购买力 ==========
    print("\n【步骤2：分析用户购买力分层】")
    
    # 创建用户消费统计CTE
    user_spending_cte = Order.query() \
        .where('order_date BETWEEN ? AND ?', (double11_start, double11_end)) \
        .select('buyer_id') \
        .group_by('buyer_id') \
        .sum('actual_amount', 'total_spent') \
        .count('*', 'order_count') \
        .avg('actual_amount', 'avg_order_value')
    
    # 创建用户分层CTE（使用CASE表达式）
    user_tier_query = User.query() \
        .with_cte('user_spending', user_spending_cte) \
        .with_cte('target_users', target_users) \
        .from_cte('user_spending') \
        .inner_join('target_users', 'user_spending.buyer_id = target_users.id') \
        .case(
            'user_spending.total_spent',
            [
                ('> 10000', "'钻石用户'"),
                ('> 5000', "'黄金用户'"),
                ('> 1000', "'白银用户'"),
            ],
            "'青铜用户'",
            'user_tier'
        ) \
        .select(
            'user_spending.buyer_id',
            'user_spending.total_spent',
            'user_spending.order_count',
            'user_spending.avg_order_value'
        ) \
        .group_by('user_tier') \
        .count('*', 'tier_count') \
        .sum('total_spent', 'tier_total') \
        .order_by('tier_total DESC')
    
    tier_analysis = user_tier_query.aggregate()
    print("用户分层分析结果：")
    for tier in tier_analysis:
        print(f"  {tier['user_tier']}: {tier['tier_count']}人，总消费￥{tier['tier_total']}")
    
    # ========== 步骤3：复杂JOIN分析商品表现 ==========
    print("\n【步骤3：商品销售表现分析】")
    
    # 分析双11期间各类商品的表现
    # 使用多表JOIN获取完整信息
    product_performance = Order.query() \
        .where('order_date BETWEEN ? AND ?', (double11_start, double11_end)) \
        .inner_join('products', 'orders.product_id = products.id') \
        .left_join('reviews', 'orders.id = reviews.order_id') \
        .inner_join(
            target_users.as_subquery('tu'),
            'orders.buyer_id = tu.id'
        ) \
        .select(
            'products.category',
            'products.brand',
            'COUNT(DISTINCT orders.id) as order_count',
            'SUM(orders.quantity) as total_quantity',
            'SUM(orders.actual_amount) as revenue',
            'AVG(reviews.rating) as avg_rating',
            'COUNT(DISTINCT orders.buyer_id) as unique_buyers'
        ) \
        .group_by('products.category', 'products.brand') \
        .having('COUNT(DISTINCT orders.id) > ?', (10,)) \
        .order_by('revenue DESC') \
        .limit(20)
    
    # 使用窗口函数添加排名
    ranked_products = product_performance \
        .window_expr(
            'ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC)',
            'category_rank'
        ) \
        .window_expr(
            'SUM(revenue) OVER (PARTITION BY category)',
            'category_total'
        ) \
        .window_expr(
            'revenue / SUM(revenue) OVER (PARTITION BY category) * 100',
            'category_share'
        )
    
    print("TOP商品类别表现：")
    results = ranked_products.aggregate()
    for product in results[:10]:
        print(f"  {product['category']} - {product['brand']}: ")
        print(f"    销售额：￥{product['revenue']}")
        print(f"    类别内排名：{product['category_rank']}")
        print(f"    类别份额：{product['category_share']:.1f}%")
    
    # ========== 步骤4：购物车转化分析（集合运算） ==========
    print("\n【步骤4：购物车转化率分析】")
    
    # 有购物车的用户
    cart_users = CartItem.query() \
        .where('added_date > ?', (double11_start,)) \
        .select('DISTINCT user_id as id')
    
    # 实际下单的用户
    ordered_users = Order.query() \
        .where('order_date BETWEEN ? AND ?', (double11_start, double11_end)) \
        .select('DISTINCT buyer_id as id')
    
    # 转化用户 = 购物车用户 ∩ 下单用户
    converted_users = cart_users.intersect(ordered_users)
    
    # 未转化用户 = 购物车用户 - 下单用户
    abandoned_cart_users = cart_users.except_(ordered_users)
    
    # 统计转化率
    total_cart = cart_users.count()
    total_converted = converted_users.count()
    total_abandoned = abandoned_cart_users.count()
    
    conversion_rate = (total_converted / total_cart * 100) if total_cart > 0 else 0
    
    print(f"购物车转化分析：")
    print(f"  添加购物车用户：{total_cart}")
    print(f"  成功转化用户：{total_converted}")
    print(f"  流失用户：{total_abandoned}")
    print(f"  转化率：{conversion_rate:.2f}%")
    
    # ========== 步骤5：优惠券效果分析（聚合+JOIN） ==========
    print("\n【步骤5：优惠券使用效果分析】")
    
    coupon_analysis = UserCoupon.query() \
        .where('used_date BETWEEN ? AND ?', (double11_start, double11_end)) \
        .inner_join('coupons', 'user_coupons.coupon_id = coupons.id') \
        .inner_join('orders', 'user_coupons.order_id = orders.id') \
        .select('coupons.type as coupon_type') \
        .group_by('coupons.type') \
        .count('*', 'usage_count') \
        .sum('orders.discount_amount', 'total_discount') \
        .sum('orders.actual_amount', 'total_revenue') \
        .avg('orders.actual_amount', 'avg_order_value') \
        .aggregate()
    
    print("优惠券效果：")
    for coupon in coupon_analysis:
        roi = (coupon['total_revenue'] / coupon['total_discount']) if coupon['total_discount'] > 0 else 0
        print(f"  {coupon['coupon_type']}类型：")
        print(f"    使用次数：{coupon['usage_count']}")
        print(f"    总优惠：￥{coupon['total_discount']}")
        print(f"    带来收入：￥{coupon['total_revenue']}")
        print(f"    ROI：{roi:.2f}")
    
    # ========== 步骤6：递归CTE分析用户推荐链 ==========
    print("\n【步骤6：用户推荐链分析（递归CTE）】")
    
    # 假设有推荐关系表
    referral_base = User.query() \
        .where('referrer_id IS NULL') \
        .select('id', 'username', '0 as level', 'id as root_id')
    
    referral_recursive = """
        SELECT u.id, u.username, r.level + 1, r.root_id
        FROM users u
        JOIN referral_tree r ON u.referrer_id = r.id
        WHERE r.level < 5
    """
    
    try:
        referral_analysis = Order.query() \
            .with_recursive_cte('referral_tree', referral_base, referral_recursive) \
            .from_cte('referral_tree') \
            .inner_join('orders', 'referral_tree.id = orders.buyer_id') \
            .where('orders.order_date BETWEEN ? AND ?', (double11_start, double11_end)) \
            .select('referral_tree.level') \
            .group_by('referral_tree.level') \
            .count('DISTINCT referral_tree.id', 'user_count') \
            .sum('orders.actual_amount', 'total_revenue') \
            .aggregate()
        
        print("推荐链层级分析：")
        for level in referral_analysis:
            print(f"  第{level['level']}层：{level['user_count']}人，贡献￥{level['total_revenue']}")
    except:
        print("  （递归CTE示例，需要referrer_id字段）")
    
    # ========== 步骤7：实时热销商品（复杂嵌套查询） ==========
    print("\n【步骤7：实时热销商品追踪】")
    
    # 最近1小时热销
    last_hour = datetime.now() - timedelta(hours=1)
    
    # 创建多个时间段的查询
    morning_sales = Order.query() \
        .where('HOUR(order_date) BETWEEN ? AND ?', (6, 12)) \
        .where('DATE(order_date) = ?', (datetime.now().date(),)) \
        .select('product_id', 'SUM(quantity) as qty', "'morning' as period")
        .group_by('product_id')
    
    afternoon_sales = Order.query() \
        .where('HOUR(order_date) BETWEEN ? AND ?', (12, 18)) \
        .where('DATE(order_date) = ?', (datetime.now().date(),)) \
        .select('product_id', 'SUM(quantity) as qty', "'afternoon' as period")
        .group_by('product_id')
    
    evening_sales = Order.query() \
        .where('HOUR(order_date) BETWEEN ? AND ?', (18, 24)) \
        .where('DATE(order_date) = ?', (datetime.now().date(),)) \
        .select('product_id', 'SUM(quantity) as qty', "'evening' as period")
        .group_by('product_id')
    
    # 合并各时段数据
    all_periods = morning_sales.union(afternoon_sales, all=True).union(evening_sales, all=True)
    
    # 分析各时段热销商品
    period_analysis = Product.query() \
        .inner_join(
            all_periods.as_subquery('ps'),
            'products.id = ps.product_id'
        ) \
        .select(
            'ps.period',
            'products.category',
            'products.name',
            'ps.qty',
            'RANK() OVER (PARTITION BY ps.period ORDER BY ps.qty DESC) as period_rank'
        ) \
        .where('period_rank <= ?', (5,))  # 每个时段TOP 5
    
    # 查看执行计划（JSON格式）
    plan_json = period_analysis.explain(
        type=ExplainType.ANALYZE,
        format=ExplainFormat.JSON
    ).all()
    
    print("热销商品时段分析执行计划（JSON格式摘要）")
    # 实际应用中可以解析JSON获取详细信息
    
    # ========== 步骤8：综合营销建议生成 ==========
    print("\n【步骤8：智能营销建议】")
    
    # 基于以上分析生成建议
    recommendations = []
    
    # 1. 基于转化率
    if conversion_rate < 30:
        recommendations.append("购物车转化率偏低，建议：")
        recommendations.append("  - 发送购物车提醒推送")
        recommendations.append("  - 提供限时优惠券")
        recommendations.append("  - 优化结算流程")
    
    # 2. 基于用户分层
    recommendations.append("\n针对不同用户层级的策略：")
    recommendations.append("  钻石用户：提供专属客服和定制化推荐")
    recommendations.append("  黄金用户：推送会员升级优惠")
    recommendations.append("  白银用户：发放满减优惠券刺激消费")
    
    # 3. 基于商品表现
    recommendations.append("\n商品策略：")
    recommendations.append("  - 增加热销品类库存")
    recommendations.append("  - 对低评分商品进行质量改进")
    recommendations.append("  - 捆绑销售互补商品")
    
    print("营销建议：")
    for rec in recommendations:
        print(rec)
    
    return {
        'target_users': target_users,
        'conversion_rate': conversion_rate,
        'tier_analysis': tier_analysis,
        'product_performance': results[:5] if results else []
    }


# ============================================================================
# 场景2：实时库存预警系统
# ============================================================================

def realtime_inventory_alert():
    """
    实时库存预警：结合多种查询技术监控库存状态
    """
    print("\n" + "=" * 80)
    print("实时库存预警系统")
    print("=" * 80)
    
    # 低库存商品
    low_stock = Product.query() \
        .where('stock < ?', (10,)) \
        .select('id', 'name', 'stock')
    
    # 高销量商品（最近7天）
    week_ago = datetime.now() - timedelta(days=7)
    high_demand = Order.query() \
        .where('order_date > ?', (week_ago,)) \
        .group_by('product_id') \
        .sum('quantity', 'total_sold') \
        .having('SUM(quantity) > ?', (100,)) \
        .select('product_id as id')
    
    # 需要补货的商品 = 低库存 ∩ 高销量
    restock_urgent = low_stock.intersect(high_demand)
    
    # 获取详细信息
    alert_products = Product.query() \
        .inner_join(
            restock_urgent.as_subquery('urgent'),
            'products.id = urgent.id'
        ) \
        .left_join(
            Order.query()
                .where('order_date > ?', (week_ago,))
                .group_by('product_id')
                .sum('quantity', 'week_sales')
                .as_subquery('sales'),
            'products.id = sales.product_id'
        ) \
        .select(
            'products.*',
            'sales.week_sales',
            'products.stock / (sales.week_sales / 7.0) as days_remaining'
        ) \
        .order_by('days_remaining ASC') \
        .all()
    
    print("紧急补货清单：")
    for product in alert_products[:10]:
        print(f"  {product['name']}：")
        print(f"    当前库存：{product['stock']}")
        print(f"    周销量：{product['week_sales']}")
        print(f"    预计售罄：{product['days_remaining']:.1f}天")


# ============================================================================
# 主执行函数
# ============================================================================

if __name__ == "__main__":
    try:
        # 执行双11综合分析
        results = analyze_double11_comprehensive()
        
        # 执行库存预警
        realtime_inventory_alert()
        
        print("\n" + "=" * 80)
        print("所有分析完成！")
        print("=" * 80)
        
        # 展示最终统计
        print("\n【分析总结】")
        print(f"目标用户群体规模：{results['target_users'].count()}人")
        print(f"购物车转化率：{results['conversion_rate']:.2f}%")
        print(f"用户分层数：{len(results['tier_analysis'])}层")
        print(f"热销商品类别：{len(results['product_performance'])}个")
        
    except Exception as e:
        print(f"\n分析过程中出现错误：{e}")
        print("请确保数据库连接正常并且表结构存在")