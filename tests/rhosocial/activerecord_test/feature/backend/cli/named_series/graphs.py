# tests/rhosocial/activerecord_test/feature/backend/cli/named_series/graphs.py
"""Named procedure-graph fixtures (named-procedure-graph layer).

Graphs wire named queries from ``queries`` into DAGs with dependencies.
They are resolved by the CLI by FQN and require the tables created by the
migrations.
"""

from rhosocial.activerecord.backend.named_expression import (
    ProcedureGraph,
    StepNode,
    GraphTransactionMode,
)

QUERIES = "rhosocial.activerecord_test.feature.backend.cli.named_series.queries"


def seed_and_report_graph(dialect, params=None):
    """Insert a user, a post, then count posts.

    Topology:
        insert_user
            -> insert_post
                -> count_posts
    """
    user_name = (params or {}).get("user_name", "graph_user")
    user_email = (params or {}).get("user_email", "graph@example.com")
    post_title = (params or {}).get("post_title", "graph_post")
    return (
        ProcedureGraph(transaction_mode=GraphTransactionMode.AUTO)
        | StepNode.query(
            "insert_user",
            f"{QUERIES}.insert_user",
            params={"name": user_name, "email": user_email},
            label="Insert the user",
        )
        | StepNode.query(
            "insert_post",
            f"{QUERIES}.insert_post",
            params={"title": post_title, "user_id": 1},
            depends_on=["insert_user"],
            label="Insert a post for the user",
        )
        | StepNode.query(
            "count_posts",
            f"{QUERIES}.count_posts",
            depends_on=["insert_post"],
            bind_output={"rows[0].total": "total_posts"},
            label="Count all posts",
        )
    )


def conditional_graph(dialect, params=None):
    """Graph whose middle step runs only when a threshold is met.

    Topology:
        count_posts
            -> check_threshold (conditional)
                -> list_posts
    """
    threshold = (params or {}).get("threshold", 1)
    return (
        ProcedureGraph(transaction_mode=GraphTransactionMode.AUTO)
        | StepNode.query(
            "count_posts",
            f"{QUERIES}.count_posts",
            bind_output={"rows[0].total": "total_posts"},
        )
        | StepNode.query(
            "check_threshold",
            f"{QUERIES}.list_posts",
            depends_on=["count_posts"],
            condition="${total_posts} > " + str(threshold),
            label="Proceed only if posts exceed threshold",
        )
    )
