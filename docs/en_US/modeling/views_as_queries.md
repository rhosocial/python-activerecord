# Views as Queries

**A view is a query.** `CREATE VIEW v AS SELECT ...` stores nothing but a query, and a
framework that modelled views as tables would have to invent a name, a lifecycle, and an
introspection story for what is already an expression you can hold in a variable.

So this framework does not provide view models. Express the view as an encapsulated
`ActiveQuery` instead.

> A **materialized view** is different: it has an entity, a name, a storage cost and a
> refresh cycle. That is a real thing to model, and it is handled separately — see
> [Read-Only Models](readonly_models.md) for the read-only half.

---

## 1. A View Is a Reusable Query

Start from the model, preset the parts that define the view, and return the query:

```python
from rhosocial.activerecord.model import ActiveRecord

class Order(ActiveRecord):
    __table_name__ = "orders"
    id: int
    status: str
    total: float
    created_at: str

def open_orders():
    """The 'open orders' view: status filter and ordering, nothing else."""
    return Order.query().where(Order.c.status == "open").order_by(Order.c.created_at.desc())

rows = open_orders().limit(50).all()
total = open_orders().count()
```

This is a view, parameterised. The same view shape with a parameter is something a SQL
view cannot express:

```python
def orders_since(cutoff):
    return (
        Order.query()
        .where(Order.c.status == "open", Order.c.created_at >= cutoff)
        .order_by(Order.c.created_at.desc())
    )
```

One definition, any window. Naming a database view `open_orders_since` would mean a new
object per cutoff.

---

## 2. The Three Usual Shapes

### Filtering

```python
def paid_orders():
    return Order.query().where(Order.c.status == "paid")
```

### Aggregating

Two models, one grouping. `aggregate()` returns rows rather than model instances:

```python
def revenue_by_customer(Customer, Order):
    return (
        Order.query()
        .join(Customer, on=Order.c.customer_id == Customer.c.id)
        .select(Customer.c.name, functions.sum(Order.c.total))
        .group_by(Customer.c.name)
        .aggregate()
    )

for row in revenue_by_customer(Customer, Order):
    print(row["name"], row[list(row)[1]])
```

### Projecting

Narrowing the column set — note the explicit alias, which keeps the result keyable:

```python
def order_summary():
    return Order.query().select(Order.c.id, Order.c.status.as_("state")).limit(20)
```

> **Careful with `SELECT *` across a join.** Two tables commonly both have an `id`, and a
> bare `SELECT *` emits both under the same name; the row mapping keeps the last one. When
> you join, narrow the projection with `select()`.

---

## 3. Getting Typed Instances

A plain `ActiveQuery` hands back whatever its `model_class` is. When the shape you want is
*not* the table's shape, declare a model for it and let the query supply the rows:

```python
class OrderSummary(ActiveRecord):
    __table_name__ = "orders"
    __primary_key__ = None                 # not addressable by key
    id: int
    state: str
    total: float

def open_order_summaries():
    return OrderSummary.query().select(
        OrderSummary.c.id,
        OrderSummary.c.status.as_("state"),
        OrderSummary.c.total,
    ).where(OrderSummary.c.status == "open")
```

The model supplies the field names and types; the query supplies the projection. A model
mapped onto a stored result set — a materialized view, an external table — uses exactly
this shape with `__table_name__` pointing at the stored object instead.

---

## 4. When You Should Still Create a Database View

A Python query is not always the right answer. Reach for `CREATE VIEW` when:

| Need | Why the database view wins |
| --- | --- |
| **Shared across processes** | several services need the same definition |
| **A permission boundary** | grant `SELECT` on the view, not on the base tables |
| **The planner needs it** | an indexed or filtered view can be optimised server-side |
| **Legacy consumers** | tools that cannot be changed to emit the query |

Creating one is available through the DDL layer — see [DDL Views](ddl_views.md). You then
have two ways to read it: keep using the encapsulated query (usually better, because it is
parameterised), or point a model at the stored object.

---

## 5. Why Not `__table_name__ = "the_view"`

Pointing `__table_name__` at an existing view does work, and for a materialized view that
is the intended shape. For an ordinary view it is a worse deal:

- the framework cannot know the view is updatable, so it cannot decide whether writes are
  legal — that judgement would need introspection, which would break the "no I/O at import"
  property that model metadata depends on
- the model implies a stable shape that the view definition can change underneath it
- the same definition cannot be reused with different parameters

None of that makes it wrong for a materialized view, where the object *is* a stored
relation. It makes it wrong for a plain view, which is only a query wearing a name.

---

## See Also

- [Read-Only Models](readonly_models.md) — refusing writes, and read-only models
- [Keyless Models](keyless_models.md) — models without a primary key
- [DDL Views](ddl_views.md) — creating views through the DDL layer
- [Derived Fields](derived_fields.md) — computed values in the SELECT list
