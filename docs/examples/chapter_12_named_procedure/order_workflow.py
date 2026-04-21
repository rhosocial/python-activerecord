# docs/examples/chapter_12_named_procedure/order_workflow.py
"""
复杂订单处理工作流示例 - 展示命名过程的流程图功能。

该过程包含:
- 条件分支(库存检查)
- 并行执行(库存预留 + 通知)
- 条件回滚(支付失败)
"""
from typing import Optional

from rhosocial.activerecord.backend.named_query import (
    Procedure,
    ProcedureContext,
    ParallelStep,
)


class OrderProcessingProcedure(Procedure):
    """订单处理完整工作流。

    流程:
    1. 查询订单详情
    2. 检查库存(库存不足则终止)
    3. 并行: 预留库存 + 发送通知
    4. 处理支付(失败则回滚库存)
    5. 创建订单记录
    6. 更新库存(最终确认)
    """

    order_id: int
    user_id: int
    amount: float = 0.0

    def run(self, ctx: ProcedureContext) -> None:
        ctx.log(f"开始处理订单 {self.order_id}", "INFO")

        ctx.execute(
            "examples.queries.get_order",
            params={"order_id": self.order_id},
            bind="order",
        )

        order = ctx.scalar("order", "status")
        if order is None:
            ctx.log(f"订单 {self.order_id} 不存在", "ERROR")
            ctx.abort("OrderProcessingProcedure", f"Order {self.order_id} not found")

        ctx.log(f"订单状态: {order}", "DEBUG")

        ctx.execute(
            "examples.queries.check_inventory",
            params={"order_id": self.order_id},
            bind="inventory",
        )

        available = ctx.scalar("inventory", "available")
        if not available or available < 1:
            ctx.log("库存不足,终止处理", "WARNING")
            ctx.abort("OrderProcessingProcedure", "Insufficient inventory")

        ctx.parallel(
            ParallelStep(
                "examples.queries.reserve_inventory",
                params={"order_id": self.order_id},
                bind="reserved",
            ),
            ParallelStep(
                "examples.queries.send_notification",
                params={"user_id": self.user_id, "type": "order_started"},
            ),
            max_concurrency=2,
        )

        ctx.execute(
            "examples.queries.process_payment",
            params={"order_id": self.order_id, "amount": self.amount},
            bind="payment",
        )

        payment_status = ctx.scalar("payment", "status")
        if payment_status != "success":
            ctx.log(f"支付失败: {payment_status}, 回滚库存", "ERROR")
            ctx.execute(
                "examples.queries.release_inventory",
                params={"order_id": self.order_id},
                output=True,
            )
            ctx.abort("OrderProcessingProcedure", f"Payment failed: {payment_status}")

        ctx.execute(
            "examples.queries.create_order_record",
            params={
                "order_id": self.order_id,
                "user_id": self.user_id,
                "amount": self.amount,
            },
            bind="order_record",
            output=True,
        )

        ctx.execute(
            "examples.queries.confirm_inventory",
            params={"order_id": self.order_id},
            output=True,
        )

        ctx.log(f"订单 {self.order_id} 处理完成", "INFO")