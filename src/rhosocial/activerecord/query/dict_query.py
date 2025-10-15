# src/rhosocial/activerecord/query/dict_query.py
"""Dictionary query wrapper implementation."""
import logging
from typing import Generic, Any, List, Optional, Set, Dict, Tuple

from ..interface import ModelT, IQuery


class DictQuery(Generic[ModelT]):
    """Wrapper for queries that return dictionary results instead of models.

    This class provides a way to execute queries and retrieve results as dictionaries
    instead of model instances. It's particularly useful for:

    1. Retrieving only specific fields from a model
    2. Working with JOIN queries that might return columns not defined in the model
    3. Bypassing model validation when raw data access is needed

    For JOIN queries or complex aggregate queries, use the direct_dict=True parameter
    to bypass model instantiation entirely and get raw dictionary results directly
    from the database.
    """

    def __init__(self, query: IQuery[ModelT],
                 include: Optional[Set[str]] = None,
                 exclude: Optional[Set[str]] = None,
                 direct_dict: bool = False):
        """Initialize a dictionary query wrapper.

        Args:
            query: The underlying query instance
            include: Optional set of fields to include in results
            exclude: Optional set of fields to exclude from results
            direct_dict: If True, bypasses model instantiation entirely and returns
                         raw dictionaries from the database. Use this for JOIN queries
                         or when model validation would fail.
        """
        self._query = query  # Underlying query instance
        self._include = include  # Fields to include in result
        self._exclude = exclude  # Fields to exclude from result
        self._direct_dict = direct_dict  # Whether to bypass model instantiation

    def _to_dict(self, record: ModelT) -> Dict[str, Any]:
        """Convert model instance to dictionary.

        Applies include/exclude filters if specified.
        """
        return record.model_dump(
            include=self._include,
            exclude=self._exclude
        )

    def all(self) -> List[Dict[str, Any]]:
        """Return dictionary list of all results.

        If direct_dict=True was specified, retrieves results directly as dictionaries
        from the database, bypassing model instantiation and validation.

        Otherwise, instantiates models first, then converts them to dictionaries
        with the specified include/exclude filters.

        Returns:
            List of dictionaries representing query results

        Examples:
            # Standard usage - instantiates models first
            users = User.query().to_dict().all()

            # For JOIN queries - bypass model instantiation
            results = User.query()
                .join("JOIN orders ON users.id = orders.user_id")
                .select("users.id", "users.name", "orders.total")
                .to_dict(direct_dict=True)
                .all()
        """
        if self._direct_dict:
            # Bypass model instantiation and get raw dictionaries
            sql, params = self._query.build()
            self._query._log(
                logging.INFO,
                f"Executing direct dictionary query: {sql}, parameters: {params}"
            )
            return self._query.model_class.backend().fetch_all(sql, params)
        else:
            # Regular path - instantiate models first
            records = self._query.all()
            return [self._to_dict(record) for record in records]

    def one(self) -> Optional[Dict[str, Any]]:
        """Return dictionary of first result.

        If direct_dict=True was specified, retrieves the result directly as a dictionary
        from the database, bypassing model instantiation and validation.

        Otherwise, instantiates a model first, then converts it to a dictionary
        with the specified include/exclude filters.

        Returns:
            Dictionary representing the first result, or None if no results

        Examples:
            # Standard usage - instantiates model first
            user = User.query().where("id = ?", (1,)).to_dict().one()

            # For JOIN queries - bypass model instantiation
            result = User.query()
                .join("JOIN orders ON users.id = orders.user_id")
                .select("users.id", "users.name", "orders.total")
                .where("users.id = ?", (1,))
                .to_dict(direct_dict=True)
                .one()
        """
        if self._direct_dict:
            # Bypass model instantiation and get raw dictionary
            original_limit = self._query.limit_count
            self._query.limit(1)

            sql, params = self._query.build()
            self._query._log(
                logging.INFO,
                f"Executing direct dictionary query: {sql}, parameters: {params}"
            )

            # Reset limit to original value
            self._query.limit_count = original_limit

            return self._query.model_class.backend().fetch_one(sql, params)
        else:
            # Regular path - instantiate model first
            record = self._query.one()
            return self._to_dict(record) if record else None

    def to_sql(self) -> Tuple[str, tuple]:
        """Get the SQL statement and parameters for this query."""
        return self._query.to_sql()

    def __getattr__(self, name: str) -> Any:
        """Delegate other query methods to original query."""
        return getattr(self._query, name)
