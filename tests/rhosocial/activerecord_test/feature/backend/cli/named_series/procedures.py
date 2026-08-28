# tests/rhosocial/activerecord_test/feature/backend/cli/named_series/procedures.py
"""Named procedure fixtures (named-procedure layer).

Procedures orchestrate named queries from ``queries``.  They are imported by
the CLI resolver by FQN and require the tables created by the migrations.
"""

from rhosocial.activerecord.backend.named_expression.procedure import (
    Procedure,
    ProcedureContext,
    AsyncProcedure,
    AsyncProcedureContext,
    ParallelStep,
)

QUERIES = "rhosocial.activerecord_test.feature.backend.cli.named_series.queries"


class SeedUsersProcedure(Procedure):
    """Insert N users, then verify the stored count matches.

    Exercises: execute + bind, scalar extraction, conditional abort.
    """

    user_count: int = 3

    def run(self, ctx: ProcedureContext) -> None:
        for i in range(self.user_count):
            ctx.execute(
                f"{QUERIES}.insert_user",
                params={"name": f"user{i}", "email": f"user{i}@example.com"},
            )
        ctx.execute(f"{QUERIES}.list_users", bind="users")
        rows = list(ctx.rows("users"))
        ctx.log(f"Stored {len(rows)} users", "INFO")
        if len(rows) < self.user_count:
            ctx.abort("SeedUsersProcedure", f"Expected {self.user_count}, got {len(rows)}")


class SeedPostsParallelProcedure(Procedure):
    """Insert a user, then insert posts in parallel, then count.

    Exercises: parallel execution + bind + scalar.
    """

    user_count: int = 2
    posts_per_user: int = 2

    def run(self, ctx: ProcedureContext) -> None:
        for i in range(self.user_count):
            ctx.execute(
                f"{QUERIES}.insert_user",
                params={"name": f"u{i}", "email": f"u{i}@ex.com"},
                bind="user",
            )
        steps = [
            ParallelStep(
                f"{QUERIES}.insert_post",
                params={"title": f"post-{i}", "user_id": i % max(self.user_count, 1) + 1},
            )
            for i in range(self.posts_per_user)
        ]
        ctx.parallel(*steps, max_concurrency=2)
        ctx.execute(f"{QUERIES}.count_posts", bind="count")
        total = ctx.scalar("count", "total")
        ctx.log(f"Total posts: {total}", "INFO")
        if total < self.posts_per_user:
            ctx.abort("SeedPostsParallelProcedure", f"Expected {self.posts_per_user}, got {total}")


class AsyncSeedUsersProcedure(AsyncProcedure):
    """Async variant of SeedUsersProcedure."""

    user_count: int = 3

    async def run(self, ctx: AsyncProcedureContext) -> None:
        for i in range(self.user_count):
            await ctx.execute(
                f"{QUERIES}.insert_user",
                params={"name": f"auser{i}", "email": f"auser{i}@example.com"},
            )
        await ctx.execute(f"{QUERIES}.list_users", bind="users")
        rows = [row async for row in ctx.rows("users")]
        await ctx.log(f"Stored {len(rows)} users", "INFO")
        if len(rows) < self.user_count:
            await ctx.abort("AsyncSeedUsersProcedure", f"Expected {self.user_count}, got {len(rows)}")
