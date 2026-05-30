# src/rhosocial/activerecord/base/bulk_operations.py
"""Bulk operations mixin for ActiveRecord models."""

import logging
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

from ..backend.errors import DatabaseError, BulkStateError, BulkValidationError
from ..backend.expression import Column, Literal
from ..backend.expression.predicates import InPredicate
from ..backend.options import BulkInsertOptions, BulkUpdateOptions, DeleteOptions, UpdateOptions
from ..interface import ModelEvent

if TYPE_CHECKING:
    from .base import BaseActiveRecord, AsyncBaseActiveRecord


class BulkOperationsMixin:
    """Mixin providing synchronous bulk operations for ActiveRecord models."""

    @classmethod
    def bulk_create(
        cls,
        records: List["BaseActiveRecord"],
        *,
        batch_size: Optional[int] = None,
    ) -> List["BaseActiveRecord"]:
        """
        Bulk insert multiple new records in a single operation.

        All records must be new (is_new_record == True). Validation and events
        are triggered per-record, but the actual INSERT is batched.

        Args:
            records: List of new model instances to insert.
            batch_size: If set, split into batches of this size.

        Returns:
            The same records list with primary keys populated.

        Raises:
            BulkStateError: If any record is not a new record.
            BulkValidationError: If any record fails validation.
            DatabaseError: On database errors.
        """
        if not records:
            return records

        backend = cls.backend()
        if not backend:
            raise DatabaseError("No backend configured")

        for i, record in enumerate(records):
            if not record.is_new_record:
                raise BulkStateError(
                    f"Record at index {i} is not a new record. bulk_create requires all records to be new."
                )

        validation_errors = []
        for i, record in enumerate(records):
            try:
                record.validate_fields()
            except Exception as e:
                validation_errors.append((i, str(e)))
        if validation_errors:
            raise BulkValidationError(validation_errors)

        for record in records:
            record._trigger_event(ModelEvent.BEFORE_INSERT)

        all_data = []
        for record in records:
            data = record._prepare_save_data()
            all_data.append(data)

        if not all_data:
            return records

        columns = list(cls._map_fields_to_columns(all_data[0]).keys())
        rows = []
        for data in all_data:
            mapped = cls._map_fields_to_columns(data)
            rows.append([mapped.get(col) for col in columns])

        supports_returning = backend.dialect.supports_returning_insert()
        returning_columns = [cls.primary_key()] if supports_returning else None
        column_mapping = cls.get_column_to_field_map()
        column_adapters = cls.get_column_adapters()

        def _do_batch(batch_rows, batch_records):
            opts = BulkInsertOptions(
                table=cls.table_name(),
                schema_name=cls.schema_name(),
                columns=columns,
                rows=batch_rows,
                column_adapters=column_adapters,
                column_mapping=column_mapping,
                returning_columns=returning_columns,
                auto_commit=False,
            )
            result = backend.bulk_insert(opts)

            if supports_returning and result.data:
                pk_field = cls._get_field_name(cls.primary_key())
                for j, row_data in enumerate(result.data):
                    if isinstance(row_data, dict) and pk_field in row_data:
                        setattr(batch_records[j], pk_field, row_data[pk_field])
            elif result.last_insert_id is not None:
                pk_field = cls._get_field_name(cls.primary_key())
                for j, rec in enumerate(batch_records):
                    if getattr(rec, pk_field, None) is None:
                        setattr(rec, pk_field, result.last_insert_id + j)

        with backend.transaction():
            if batch_size and batch_size > 0:
                for start in range(0, len(rows), batch_size):
                    end = start + batch_size
                    _do_batch(rows[start:end], records[start:end])
            else:
                _do_batch(rows, records)

        for record in records:
            record._is_from_db = True
            record.reset_tracking()
            record._trigger_event(ModelEvent.AFTER_INSERT)

        return records

    @classmethod
    def bulk_update(
        cls,
        records: List["BaseActiveRecord"],
        fields: List[str],
        *,
        batch_size: Optional[int] = None,
    ) -> int:
        """
        Bulk update multiple existing records in a single operation.

        Uses CASE WHEN pattern to update all records in one SQL statement.

        Args:
            records: List of existing model instances to update.
            fields: List of field names to update.
            batch_size: If set, split into batches of this size.

        Returns:
            Number of affected rows.

        Raises:
            BulkStateError: If any record is a new record.
            BulkValidationError: If any record fails validation.
            ValueError: If fields list is empty or contains invalid field names.
        """
        if not records:
            return 0

        if not fields:
            raise ValueError("fields parameter must not be empty")

        model_field_names = set(cls.model_fields.keys())
        invalid_fields = [f for f in fields if f not in model_field_names]
        if invalid_fields:
            raise ValueError(f"Invalid field names: {invalid_fields}")

        backend = cls.backend()
        if not backend:
            raise DatabaseError("No backend configured")

        for i, record in enumerate(records):
            if record.is_new_record:
                raise BulkStateError(
                    f"Record at index {i} is a new record. bulk_update requires all records to be persisted."
                )

        validation_errors = []
        for i, record in enumerate(records):
            try:
                record.validate_fields()
            except Exception as e:
                validation_errors.append((i, str(e)))
        if validation_errors:
            raise BulkValidationError(validation_errors)

        for record in records:
            record._trigger_event(ModelEvent.BEFORE_UPDATE)

        for record in records:
            record._prepare_save_data()

        pk_column = cls.primary_key()
        pk_field = cls._get_field_name(pk_column)
        pk_values = [getattr(r, pk_field) for r in records]

        field_values = {}
        for field_name in fields:
            col_name = cls._get_column_name(field_name)
            field_values[col_name] = [getattr(r, field_name) for r in records]

        total_affected = 0

        def _do_batch(batch_pk_values, batch_field_values):
            opts = BulkUpdateOptions(
                table=cls.table_name(),
                schema_name=cls.schema_name(),
                pk_column=pk_column,
                pk_values=batch_pk_values,
                field_values=batch_field_values,
                auto_commit=False,
            )
            result = backend.bulk_update(opts)
            return result.affected_rows

        with backend.transaction():
            if batch_size and batch_size > 0:
                for start in range(0, len(pk_values), batch_size):
                    end = start + batch_size
                    batch_pks = pk_values[start:end]
                    batch_fv = {col: vals[start:end] for col, vals in field_values.items()}
                    total_affected += _do_batch(batch_pks, batch_fv)
            else:
                total_affected = _do_batch(pk_values, field_values)

        for record in records:
            record.reset_tracking()
            record._trigger_event(ModelEvent.AFTER_UPDATE)

        return total_affected

    @classmethod
    def bulk_delete(cls, records: List["BaseActiveRecord"]) -> int:
        """
        Bulk delete multiple existing records in a single operation.

        Args:
            records: List of existing model instances to delete.

        Returns:
            Number of affected rows.

        Raises:
            BulkStateError: If any record is a new record.
        """
        if not records:
            return 0

        backend = cls.backend()
        if not backend:
            raise DatabaseError("No backend configured")

        for i, record in enumerate(records):
            if record.is_new_record:
                raise BulkStateError(
                    f"Record at index {i} is a new record. bulk_delete requires all records to be persisted."
                )

        for record in records:
            record._trigger_event(ModelEvent.BEFORE_DELETE)

        pk_column = cls.primary_key()
        pk_field = cls._get_field_name(pk_column)
        pk_values = [getattr(r, pk_field) for r in records]

        dialect = backend.dialect
        pk_col_expr = Column(dialect, pk_column)
        where_predicate = InPredicate(dialect, pk_col_expr, Literal(dialect, pk_values))

        is_soft_delete = hasattr(records[0], "prepare_delete")

        with backend.transaction():
            if is_soft_delete:
                data = records[0].prepare_delete()
                update_opts = UpdateOptions(
                    table=cls.table_name(),
                    schema_name=cls.schema_name(),
                    data=data,
                    where=where_predicate,
                )
                result = backend.update(update_opts)
            else:
                delete_opts = DeleteOptions(
                    table=cls.table_name(),
                    schema_name=cls.schema_name(),
                    where=where_predicate,
                )
                result = backend.delete(delete_opts)

        affected_rows = result.affected_rows
        if affected_rows > 0:
            for record in records:
                if not is_soft_delete:
                    setattr(record, pk_field, None)
                record.reset_tracking()
                record._trigger_event(ModelEvent.AFTER_DELETE)

        return affected_rows


class AsyncBulkOperationsMixin:
    """Mixin providing asynchronous bulk operations for ActiveRecord models."""

    @classmethod
    async def bulk_create(
        cls,
        records: List["AsyncBaseActiveRecord"],
        *,
        batch_size: Optional[int] = None,
    ) -> List["AsyncBaseActiveRecord"]:
        """
        Bulk insert multiple new records asynchronously in a single operation.

        Args:
            records: List of new model instances to insert.
            batch_size: If set, split into batches of this size.

        Returns:
            The same records list with primary keys populated.

        Raises:
            BulkStateError: If any record is not a new record.
            BulkValidationError: If any record fails validation.
            DatabaseError: On database errors.
        """
        if not records:
            return records

        backend = cls.backend()
        if not backend:
            raise DatabaseError("No backend configured")

        for i, record in enumerate(records):
            if not record.is_new_record:
                raise BulkStateError(
                    f"Record at index {i} is not a new record. bulk_create requires all records to be new."
                )

        validation_errors = []
        for i, record in enumerate(records):
            try:
                record.validate_fields()
            except Exception as e:
                validation_errors.append((i, str(e)))
        if validation_errors:
            raise BulkValidationError(validation_errors)

        for record in records:
            record._trigger_event(ModelEvent.BEFORE_INSERT)

        all_data = []
        for record in records:
            data = record._prepare_save_data()
            all_data.append(data)

        if not all_data:
            return records

        columns = list(cls._map_fields_to_columns(all_data[0]).keys())
        rows = []
        for data in all_data:
            mapped = cls._map_fields_to_columns(data)
            rows.append([mapped.get(col) for col in columns])

        supports_returning = backend.dialect.supports_returning_insert()
        returning_columns = [cls.primary_key()] if supports_returning else None
        column_mapping = cls.get_column_to_field_map()
        column_adapters = cls.get_column_adapters()

        async def _do_batch(batch_rows, batch_records):
            opts = BulkInsertOptions(
                table=cls.table_name(),
                schema_name=cls.schema_name(),
                columns=columns,
                rows=batch_rows,
                column_adapters=column_adapters,
                column_mapping=column_mapping,
                returning_columns=returning_columns,
                auto_commit=False,
            )
            result = await backend.bulk_insert(opts)

            if supports_returning and result.data:
                pk_field = cls._get_field_name(cls.primary_key())
                for j, row_data in enumerate(result.data):
                    if isinstance(row_data, dict) and pk_field in row_data:
                        setattr(batch_records[j], pk_field, row_data[pk_field])
            elif result.last_insert_id is not None:
                pk_field = cls._get_field_name(cls.primary_key())
                for j, rec in enumerate(batch_records):
                    if getattr(rec, pk_field, None) is None:
                        setattr(rec, pk_field, result.last_insert_id + j)

        async with backend.transaction():
            if batch_size and batch_size > 0:
                for start in range(0, len(rows), batch_size):
                    end = start + batch_size
                    await _do_batch(rows[start:end], records[start:end])
            else:
                await _do_batch(rows, records)

        for record in records:
            record._is_from_db = True
            record.reset_tracking()
            record._trigger_event(ModelEvent.AFTER_INSERT)

        return records

    @classmethod
    async def bulk_update(
        cls,
        records: List["AsyncBaseActiveRecord"],
        fields: List[str],
        *,
        batch_size: Optional[int] = None,
    ) -> int:
        """
        Bulk update multiple existing records asynchronously in a single operation.

        Args:
            records: List of existing model instances to update.
            fields: List of field names to update.
            batch_size: If set, split into batches of this size.

        Returns:
            Number of affected rows.

        Raises:
            BulkStateError: If any record is a new record.
            BulkValidationError: If any record fails validation.
            ValueError: If fields list is empty or contains invalid field names.
        """
        if not records:
            return 0

        if not fields:
            raise ValueError("fields parameter must not be empty")

        model_field_names = set(cls.model_fields.keys())
        invalid_fields = [f for f in fields if f not in model_field_names]
        if invalid_fields:
            raise ValueError(f"Invalid field names: {invalid_fields}")

        backend = cls.backend()
        if not backend:
            raise DatabaseError("No backend configured")

        for i, record in enumerate(records):
            if record.is_new_record:
                raise BulkStateError(
                    f"Record at index {i} is a new record. bulk_update requires all records to be persisted."
                )

        validation_errors = []
        for i, record in enumerate(records):
            try:
                record.validate_fields()
            except Exception as e:
                validation_errors.append((i, str(e)))
        if validation_errors:
            raise BulkValidationError(validation_errors)

        for record in records:
            record._trigger_event(ModelEvent.BEFORE_UPDATE)

        for record in records:
            record._prepare_save_data()

        pk_column = cls.primary_key()
        pk_field = cls._get_field_name(pk_column)
        pk_values = [getattr(r, pk_field) for r in records]

        field_values = {}
        for field_name in fields:
            col_name = cls._get_column_name(field_name)
            field_values[col_name] = [getattr(r, field_name) for r in records]

        total_affected = 0

        async def _do_batch(batch_pk_values, batch_field_values):
            opts = BulkUpdateOptions(
                table=cls.table_name(),
                schema_name=cls.schema_name(),
                pk_column=pk_column,
                pk_values=batch_pk_values,
                field_values=batch_field_values,
                auto_commit=False,
            )
            result = await backend.bulk_update(opts)
            return result.affected_rows

        async with backend.transaction():
            if batch_size and batch_size > 0:
                for start in range(0, len(pk_values), batch_size):
                    end = start + batch_size
                    batch_pks = pk_values[start:end]
                    batch_fv = {col: vals[start:end] for col, vals in field_values.items()}
                    total_affected += await _do_batch(batch_pks, batch_fv)
            else:
                total_affected = await _do_batch(pk_values, field_values)

        for record in records:
            record.reset_tracking()
            record._trigger_event(ModelEvent.AFTER_UPDATE)

        return total_affected

    @classmethod
    async def bulk_delete(cls, records: List["AsyncBaseActiveRecord"]) -> int:
        """
        Bulk delete multiple existing records asynchronously in a single operation.

        Args:
            records: List of existing model instances to delete.

        Returns:
            Number of affected rows.

        Raises:
            BulkStateError: If any record is a new record.
        """
        if not records:
            return 0

        backend = cls.backend()
        if not backend:
            raise DatabaseError("No backend configured")

        for i, record in enumerate(records):
            if record.is_new_record:
                raise BulkStateError(
                    f"Record at index {i} is a new record. bulk_delete requires all records to be persisted."
                )

        for record in records:
            record._trigger_event(ModelEvent.BEFORE_DELETE)

        pk_column = cls.primary_key()
        pk_field = cls._get_field_name(pk_column)
        pk_values = [getattr(r, pk_field) for r in records]

        dialect = backend.dialect
        pk_col_expr = Column(dialect, pk_column)
        where_predicate = InPredicate(dialect, pk_col_expr, Literal(dialect, pk_values))

        is_soft_delete = hasattr(records[0], "prepare_delete")

        async with backend.transaction():
            if is_soft_delete:
                data = records[0].prepare_delete()
                update_opts = UpdateOptions(
                    table=cls.table_name(),
                    schema_name=cls.schema_name(),
                    data=data,
                    where=where_predicate,
                )
                result = await backend.update(update_opts)
            else:
                delete_opts = DeleteOptions(
                    table=cls.table_name(),
                    schema_name=cls.schema_name(),
                    where=where_predicate,
                )
                result = await backend.delete(delete_opts)

        affected_rows = result.affected_rows
        if affected_rows > 0:
            for record in records:
                if not is_soft_delete:
                    setattr(record, pk_field, None)
                record.reset_tracking()
                record._trigger_event(ModelEvent.AFTER_DELETE)

        return affected_rows
