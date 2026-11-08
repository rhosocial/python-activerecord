# 列数据剖面 (Column Data Profiles)

[数据库内省](../introspection.md) 所描述的内容是读取 schema 目录：报告数据库说自己的对象是什么。本页这三个方法再往前一步，问的是一列里实际装的是什么。

DDL 是承诺：一个类型、一个可空性，有时还有一个默认值。行才是现实，而两者不一致之处才是信号：声明为 `NOT NULL` 却装着空值的列、声明为 `TEXT` 却全是数字的列、没有声明任何键但某一列在每一行上都唯一的表。

## 三个问题，分开问

| 方法 | 它问什么 |
|------|----------|
| `list_column_data_profiles(table_name, schema=None)` | 这张表每一列装的是什么：空值、基数、极值，以及依据多少行 |
| `sample_column_values(table_name, column_name, limit=100, schema=None)` | 这一列出现过哪些值，各自出现得多重 |
| `estimate_join_coverage(left_table, left_column, right_table, right_column, schema=None)` | 一列的值域有多少出现在另一列里 |

之所以是三次调用而不是一次，是因为它们的代价相差几个数量级。值列表要扫一遍一列；连接覆盖要扫两张表里的两列；剖面一般而言最便宜，但便宜多少取决于它的数字从哪来，而 `source` 会说出这一点。混进同一个方法里，每个调用方都要为自己没要的那部分付账，而最便宜的那个问题——每张表都要问的那个——付账次数最多。

## ColumnDataProfile

以下是声明形态，与库中实际的类一致：

```python
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from rhosocial.activerecord.backend.introspection.types import ProfileSource


@dataclass
class ColumnDataProfile:
    schema: Optional[str] = None
    table_name: str = ""
    column_name: str = ""
    null_fraction: Optional[float] = None    # share of rows holding NULL, 0.0 .. 1.0
    distinct_count: Optional[int] = None     # distinct non-null values
    min_value: Optional[Any] = None          # the driver's own Python value
    max_value: Optional[Any] = None
    row_count: Optional[int] = None          # rows the figures were computed over
    source: Optional[ProfileSource] = None   # where the figures came from
    collected_at: Optional[str] = None       # as the collecting engine spells it
    extra: Dict[str, Any] = field(default_factory=dict)
```

地址槽携带这份剖面说的是哪张表、哪一列；`extra` 携带该后端自己的探针在公共槽之外报告的东西，它的键与含义归那个后端。

### None 表示"未测量"

每一个槽都可能是 `None`，而 `None` 表示**未测量**，永远不是零：一个不保存某项数字的后端会如实说没有，而不是报一个它从未数过的零。

零在两个数值槽上都是真实答案。`null_fraction` 为 `0.0` 说明该列没有空值；`distinct_count` 为 `0` 说明它除了空值什么都没有。`None` 两者都不说明，所以把它读成 `0.0` 的代码会得出"该列没有空值"的结论，尽管根本没人看过。

### min_value 与 max_value 是驱动原生值

它们是 `Any`，因为它们是驱动返回的值，不是字符串：文本列的最大值是字典序最大的那个，时间戳列的最大值是一个 datetime，整数列的最大值是一个 int。把它们转成文本，会逼每个消费方把本来已经拿到的东西再解析一遍，还会丢掉值本身携带的排序关系。

所以"最小"是什么意思，取决于这一列声明成了什么，而剖面不会重复那份声明：要把极值放在列清单旁边读，由 `IntrospectionColumnInfo.data_type`（或它的 `parsed_data_type`）说明是哪种比较产生了它们。声明类型不同的两份剖面，即使在数字上看起来都是数值，比较的也不是同一个量。

### row_count 让计数变成占比

`distinct_count` 说明有多少个不同的非空值；`row_count` 说明这个计数是在多少行上取的。两者合起来才给出真正重要的比例：一列的 distinct 计数等于它的行数，说明该列在每一行上都不同，那就是 schema 从未声明过的候选键。

`row_count` 数的是什么取决于来源，这也是两个槽必须同行的原因：对聚合而言是整张表，对取样而言是样本大小（此时比例是对整体的估计），对估计而言是收集器自己对行数的估计。

## ProfileSource

### 没有来源的数字不是事实

同一个 `null_fraction`，可能是从统计目录读到的采样估计，也可能是用全表扫描换来的精确计数，两者都以一个 float 落进同一个槽。分不清这两者的读者，读到的并不是 `0.3`：那到底是"大约三分之一的行走过空值，取自某次没人记日期的统计刷新"，还是"三百万行里正好百分之三十，刚刚数的"？两个都是有用的答案，但它们不是同一个事实，而且其中一个可能已经放了几个月。所以来源跟着数字一起走；没有它，探针交回的就是类型未知的数字，并引诱出算术上成立、语义上无意义的比较，比如把估计和聚合一平均。这就是为什么这个槽是本族承重的那一部分；它描述的是同一份剖面里那些数字的整体，而不是逐个槽的标志位。

### 四个来源

`ESTIMATE` 表示这些数字读自引擎自己维护的统计目录：便宜，一次查询而不是扫一遍行，而且可能陈旧，因为数据变化时没有任何东西会重算它。`AGGREGATE` 表示它们是在被问到时从行算出来的：对本次查询看到的那些行精确，代价是与表大小成正比的时间，描述的是调用那一刻的数据。

`SAMPLE` 表示它们是在行的子集上算出来的。`row_count` 是样本大小，分数只在样本能代表整体的程度上描述整体。样本说的是取了哪些行；它不承诺取样方法，需要知道方法的读者不该从数字里去猜。

`UNKNOWN` 表示引擎答了，但没说这个数字是怎么产生的。这本身就是值得记录的事实：没有出处，而不是可以假设它精确的许可。槽为 `None` 又是另一回事：那一行压根没带来源，是沉默，而不是一句明确的"我不说"。

### ESTIMATE 与 collected_at 同行

`ESTIMATE` 携带 `collected_at`，即统计目录里的数字所描述的那一刻：七个月前的 `null_fraction` 和今天的不是同一个事实。它是文本，写法就是收集它的引擎的写法，core 不跨引擎归一化日期格式。`AGGREGATE` 的数字就是调用那一刻的，所以这个槽不是必需的；`SAMPLE` 用它说明样本是什么时候取的。

一份 `source` 是 `ESTIMATE`、而 `collected_at` 为 `None` 的剖面仍然告诉你这是一个估计，但没告诉你是哪一刻的估计；任何取决于新鲜度的判断，都应当把它当作不可用。

某个后端对某个探针报告哪一种来源、甚至是否回答这个探针，属于该后端自己的文档；本页只说明 core 契约的含义。

## ColumnValueFrequency

```python
@dataclass
class ColumnValueFrequency:
    value: Optional[Any] = None
    count: Optional[int] = None
    frequency: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)
```

一个该列真的装着的值，以及它的权重。`count` 是装着它的行数，`frequency` 是它在行中的占比。两者都是可选的，因为引擎只报其中一个，而换算要用到一个库里并不掌握的行数：手里有剖面 `row_count` 的调用方可以自己除，而替它除的库得先猜分母。

列表比请求的 `limit` 短，是正确答案，因为 `limit` 是上限：一个只保留固定大小"最常见值"列表的引擎，返回的就是它保留的那些，补齐到上限等于编造值。`value` 完全可以是 `None`，因为 NULL 是值域的成员，而且常常是最有意思的那个；内省里其余清单遇到没有地址的行会当作坏行跳过，这里"为空即跳过"的规则不适用。

## JoinCoverage

```python
@dataclass
class JoinCoverage:
    left_schema: Optional[str] = None
    left_table: str = ""
    left_column: str = ""
    right_schema: Optional[str] = None
    right_table: str = ""
    right_column: str = ""
    left_coverage: Optional[float] = None    # share of left's distinct values found on the right
    right_coverage: Optional[float] = None   # share of right's distinct values found on the left
    extra: Dict[str, Any] = field(default_factory=dict)
```

它回答的是没有外键、而两列看起来仍可连接时消费方会问的问题：`orders.customer_ref` 和 `customers.code` 都在那里，但只有数据能说它们是否对得上。答案是两个分数，每个都是某一列去重后的非空值中、也在另一侧出现的比例。

### 两侧都给，因为关系不对称

每个订单的客户都可能存在，而大多数客户从未下过单：一个 `1.0` 的 `left_coverage` 旁边放着一个低得多的 `right_coverage`，两个数字同时为真。只给一个相似度分数，就得选报哪一侧、丢掉另一侧，而两者支持不同的结论：左侧比例高，说明从左往右连接时每个左值都能找到匹配；右侧比例低，说明这个关系是有选择性的，大多数右值从未被引用。

### None 不是 0.0

`0.0` 是一个测量结果：两个值域完全不相交。`None` 是那一侧没有测量；方法自己的返回值遵循同一条规则，只是高一层：用 `None` 代替一个 `JoinCoverage`，表示根本没有产生测量，调用方必须能把它和"测量出来是零重叠"区分开。`(0.0, 0.0)` 说两列毫无共同值；`None` 说什么都没学到。

### 两侧都排除 NULL

NULL 是值的缺席，不是值域的成员。把它算作成员，会让每一个可空列都和每一个别的可空列"重叠"，也会让没有客户的订单匹配上某个东西。两侧都排除之后，覆盖度描述的是实际存在的那些值之间的关系。

### 是证据，不是证明

两个分数都是估计：引擎可能取样，排序规则也没有归一，所以两个字符串比较方式不同的列，报出的重叠可能低于在单一排序规则下数据本身能支持的程度。

比例高说明两个值集合一致，不说明其中一个引用另一个。两列可能因为无关的原因共享同一个值域：地址和仓库上都有邮编，订单和发票上都有年份。覆盖度让一个连接值得一试，但不让这个连接正确；后者要靠声明，或者靠数据自身的行为。

## 用法

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.introspection.types import ProfileSource

backend = SQLiteBackend(database=":memory:")
backend.connect()
introspector = backend.introspector

# One call profiles every column of the table.
profiles = introspector.list_column_data_profiles("orders")

for profile in profiles:
    print(f"{profile.column_name}: nulls={profile.null_fraction}, "
          f"distinct={profile.distinct_count}, rows={profile.row_count}, "
          f"source={profile.source}")
    if profile.source is ProfileSource.ESTIMATE:
        print(f"  collected {profile.collected_at}")
```

结果是一个列表，表里每一列一项；列名来自 `list_columns` 返回的同一份清单，所以只要后端能读到这一列，它就会拿到一份剖面，即使关于它什么都没测。它的形状就是上面的 dataclass：

```python
# Every slot of one profile, as plain data.
print(profiles[0])
```

另外两个是单独的调用，用在需要它们的时候。在异步内省器上，同样这三个方法用同样的名字，await 即可。

```python
coverage = introspector.estimate_join_coverage(
    "orders", "customer_ref",
    "customers", "code",
)
if coverage is None:
    print("not measured")
else:
    print(f"orders -> customers: {coverage.left_coverage}")
    print(f"customers -> orders: {coverage.right_coverage}")
```

## 代价

值列表和重叠测量都很贵，而后者是整个内省系统里最贵的东西：它要读两张表里的两列来比较各自的值域，也就是一次双重扫描。所以它只活在一次显式调用的后面，也没有任何东西会隐式触发它：为一张表做剖面时不会顺带测任何连接覆盖，列出表时不会，schema 差异比较走过时也不会要它。

剖面自己的价格，就是它 `source` 所报告的那些东西的价格：从引擎已经维护的目录里得来的数字便宜，从行里聚合出来的不便宜。这三种答案与其他内省结果一样会被缓存，键就是提问时的表、列、`limit` 与 schema；改了 `limit` 就是另一个键，要再付一次。而且每个答案描述的都是取值那一刻的数据——一份缓存里的剖面可能比它所描述的行更旧。
