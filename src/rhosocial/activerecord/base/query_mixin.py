# src/rhosocial/activerecord/base/query_mixin.py
"""QueryMixin class providing query functionality for ActiveRecord."""

from typing import TYPE_CHECKING
from ..interface import IActiveRecord, IActiveQuery
from ..query import ActiveQuery

if TYPE_CHECKING:
    from ..query import ActiveQuery


class QueryMixin(IActiveRecord):
    """Mixin class providing query functionality for ActiveRecord models.

    Provides:
    - Query builder interface
    - Custom query class support
    """

    __query_class__ = ActiveQuery

    @classmethod
    def query(cls) -> 'IActiveQuery':
        """
        Create a new query instance configured for this model class.

        This method serves as the primary entry point for building database queries
        against this model. It returns a fresh query object that is pre-configured
        with the model's table information and can be chained with various query
        methods to build complex queries.

        The method uses the model's configured query class (stored in __query_class__)
        to create the appropriate query instance. This allows for customization of
        query behavior by changing the query class.

        The returned query object supports a fluent interface with methods like:
        - where(), select(), order_by(), limit()
        - join(), left_join()
        - aggregate functions like count(), sum_()
        - eager loading with with_()

        Args:
            cls: The model class for which to create the query (implicit from @classmethod)

        Returns:
            IActiveQuery: A new query instance configured for this model class.
                         The query is ready to be chained with additional methods
                         or executed with methods like all(), one(), first(), etc.

        Note:
            Each call to this method returns a new query instance, so queries
            are not shared between calls. This allows multiple independent queries
            to be built simultaneously.

        Example:
            ```python
            # Simple query
            users = User.query().all()

            # Chained query
            active_users = User.query().where(User.c.is_active == True).order_by(User.c.username).all()

            # Complex query with joins
            posts_with_authors = Post.query().join(User, on=(Post.c.user_id == User.c.id)).select(Post.c.title, User.c.username).all()

            # Query with eager loading
            users_with_posts = User.query().with_('posts').where(User.c.status == 'active').all()
            ```
        """
        return cls.__query_class__(cls)
