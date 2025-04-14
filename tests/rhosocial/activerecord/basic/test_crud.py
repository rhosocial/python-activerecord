import time
import uuid
from decimal import Decimal
from datetime import date, time as dtime

import pydantic
import pytest

from src.rhosocial.activerecord.backend.errors import ValidationError, RecordNotFound, DatabaseError

from .fixtures.models import user_class, type_case_class, validated_user_class  # needed as fixture, do not remove.


def test_create_user(user_class):
    """Test creating a user record"""
    instance = user_class(username="Alice", email="alice@example.com", age=30, balance=Decimal("100.50"))
    rows = instance.save()
    assert rows == 1
    assert instance.id is not None
    assert instance.created_at is not None
    assert instance.updated_at is not None
    assert instance.is_active is True


def test_create_user_with_invalid_data(user_class):
    """Test creating a user record with invalid data"""
    with pytest.raises(pydantic.ValidationError):
        user = user_class(
            username='jo',  # too short
            email='invalid-email',  # invalid email format
            age=200,  # out of range
            balance=Decimal('100.999')  # exceeds decimal places
        )
        user.save()


def test_find_user(user_class):
    """Test finding a user record"""
    # Create a user
    user = user_class(
        username='jane_doe',
        email='jane@doe.com',
        age=25,
        balance=Decimal('200.00')
    )
    user.save()

    # Find by ID
    found = user_class.find_one(user.id)
    assert found is not None
    assert found.username == 'jane_doe'
    assert found.email == 'jane@doe.com'
    assert found.age == 25
    assert found.balance == Decimal('200.00')


def test_find_nonexistent_user(user_class):
    """Test finding a non-existent user record"""
    found = user_class.find_one(999)
    assert found is None

    with pytest.raises(RecordNotFound):
        user_class.find_one_or_fail(999)


def test_update_user(user_class):
    """Test updating a user record"""
    # Create a user
    user = user_class(
        username='bob_smith',
        email='bob@smith.com',
        age=40,
        balance=Decimal('300.00')
    )
    assert user.is_new_record is True
    user.save()
    assert user.is_new_record is False

    # Update fields
    original_created_at = user.created_at
    original_updated_at = user.updated_at
    time.sleep(0.1)
    assert user.is_dirty is False
    user.username = 'robert_smith'
    assert user.is_dirty is True
    user.age = 41
    rows = user.save()
    assert user.is_dirty is False

    assert rows == 1
    assert user.updated_at > user.created_at
    assert user.updated_at > original_updated_at

    # Reload to verify
    user.refresh()
    assert user.username == 'robert_smith'
    assert user.age == 41
    assert user.email == 'bob@smith.com'  # field not modified should remain unchanged
    assert user.created_at == original_created_at


def test_update_with_invalid_data(user_class):
    """Test updating a user record with invalid data"""
    user = user_class(
        username='alice_wonder',
        email='alice@wonder.com',
        age=28,
        balance=Decimal('400.00')
    )
    user.save()

    with pytest.raises(ValidationError):
        user.age = -1  # invalid age
        user.save()


def test_delete_user(user_class):
    """Test deleting a user record"""
    user = user_class(
        username='charlie_brown',
        email='charlie@brown.com',
        age=35,
        balance=Decimal('500.00')
    )
    assert user.is_new_record is True
    user.save()
    assert user.is_new_record is False

    # Delete record
    user_id = user.id
    rows = user.delete()
    assert rows == 1

    # Verify deleted
    assert user_class.find_one(user_id) is None


import time
import uuid
from decimal import Decimal
from datetime import date, time as dtime

import pydantic
import pytest

from src.rhosocial.activerecord.backend.errors import ValidationError, RecordNotFound, DatabaseError

from .fixtures.models import user_class, type_case_class, validated_user_class  # needed as fixture, do not remove.


def test_create_user(user_class):
    """Test creating a user record"""
    instance = user_class(username="Alice", email="alice@example.com", age=30, balance=Decimal("100.50"))
    rows = instance.save()
    assert rows == 1
    assert instance.id is not None
    assert instance.created_at is not None
    assert instance.updated_at is not None
    assert instance.is_active is True


def test_create_user_with_invalid_data(user_class):
    """Test creating a user record with invalid data"""
    with pytest.raises(pydantic.ValidationError):
        user = user_class(
            username='jo',  # too short
            email='invalid-email',  # invalid email format
            age=200,  # out of range
            balance=Decimal('100.999')  # exceeds decimal places
        )
        user.save()


def test_find_user(user_class):
    """Test finding a user record"""
    # Create a user
    user = user_class(
        username='jane_doe',
        email='jane@doe.com',
        age=25,
        balance=Decimal('200.00')
    )
    user.save()

    # Find by ID
    found = user_class.find_one(user.id)
    assert found is not None
    assert found.username == 'jane_doe'
    assert found.email == 'jane@doe.com'
    assert found.age == 25
    assert found.balance == Decimal('200.00')


def test_find_nonexistent_user(user_class):
    """Test finding a non-existent user record"""
    found = user_class.find_one(999)
    assert found is None

    with pytest.raises(RecordNotFound):
        user_class.find_one_or_fail(999)


def test_update_user(user_class):
    """Test updating a user record"""
    # Create a user
    user = user_class(
        username='bob_smith',
        email='bob@smith.com',
        age=40,
        balance=Decimal('300.00')
    )
    assert user.is_new_record is True
    user.save()
    assert user.is_new_record is False

    # Update fields
    original_created_at = user.created_at
    original_updated_at = user.updated_at
    time.sleep(0.1)
    assert user.is_dirty is False
    user.username = 'robert_smith'
    assert user.is_dirty is True
    user.age = 41
    rows = user.save()
    assert user.is_dirty is False

    assert rows == 1
    assert user.updated_at > user.created_at
    assert user.updated_at > original_updated_at

    # Reload to verify
    user.refresh()
    assert user.username == 'robert_smith'
    assert user.age == 41
    assert user.email == 'bob@smith.com'  # field not modified should remain unchanged
    assert user.created_at == original_created_at


def test_update_with_invalid_data(user_class):
    """Test updating a user record with invalid data"""
    user = user_class(
        username='alice_wonder',
        email='alice@wonder.com',
        age=28,
        balance=Decimal('400.00')
    )
    user.save()

    with pytest.raises(ValidationError):
        user.age = -1  # invalid age
        user.save()


def test_delete_user(user_class):
    """Test deleting a user record"""
    user = user_class(
        username='charlie_brown',
        email='charlie@brown.com',
        age=35,
        balance=Decimal('500.00')
    )
    assert user.is_new_record is True
    user.save()
    assert user.is_new_record is False

    # Delete record
    user_id = user.id
    rows = user.delete()
    assert rows == 1

    # Verify deleted
    assert user_class.find_one(user_id) is None


def test_save_after_delete(user_class):
    """Test saving a user record after it has been deleted"""
    # Create a user
    user = user_class(
        username='deleted_user',
        email='deleted@example.com',
        age=45,
        balance=Decimal('600.00')
    )
    user.save()
    user_id = user.id

    # Delete the user
    rows = user.delete()
    assert rows == 1
    assert user_class.find_one(user_id) is None

    # Check state after deletion
    # Important: After deletion, the record should be considered new
    # This ensures proper behavior when reusing deleted model instances
    assert user.is_new_record, "After deletion, a record should be considered new to ensure proper recreation"
    # The record should not be dirty, as no changes have been made after deletion
    assert not user.is_dirty, "After deletion, a record should be clean since tracking state is reset"

    # Attempt to save the user again
    rows = user.save()
    assert rows == 1
    assert user.id is not None
    assert user.id != user_id  # Should have a new ID
    assert user.is_new_record is False

    # Verify the user exists in the database
    found = user_class.find_one(user.id)
    assert found is not None
    assert found.username == 'deleted_user'
    assert found.email == 'deleted@example.com'


def test_bulk_operations(user_class):
    """Test bulk operations"""
    # Bulk create
    users = [
        user_class(username=f'user_{i}',
                   email=f'user_{i}@example.com',
                   age=20 + i,
                   balance=Decimal(f'{100 + i}.00'))
        for i in range(5)
    ]
    for user in users:
        user.save()

    # Bulk query
    found_users = user_class.query().order_by('age').all()
    assert len(found_users) == 5
    assert [u.age for u in found_users] == [20, 21, 22, 23, 24]

    # Conditional query
    young_users = user_class.query().where('age < ?', (22,)).all()
    assert len(young_users) == 2


def test_dirty_tracking(user_class):
    """Test dirty data tracking"""
    user = user_class(
        username='track_user',
        email='track@example.com',
        age=30,
        balance=Decimal('100.00')
    )

    # New record should not be dirty
    assert not user.is_dirty and user.is_new_record
    assert 'username' not in user.dirty_fields
    assert 'email' not in user.dirty_fields

    user.save()
    # Should be clean after saving
    assert not user.is_dirty and not user.is_new_record
    assert len(user.dirty_fields) == 0

    # Should be dirty after modification
    user.username = 'new_track_user'
    assert user.is_dirty
    assert 'username' in user.dirty_fields
    assert 'email' not in user.dirty_fields


def test_type_case_crud(type_case_class):
    """Test CRUD operations with various field types"""
    from datetime import datetime

    # Create test record
    case = type_case_class(
        username='type_test',
        email='type@test.com',
        tiny_int=127,
        small_int=32767,
        big_int=9223372036854775807,
        float_val=3.14,
        double_val=3.141592653589793,
        decimal_val=Decimal('123.4567'),
        char_val='fixed',
        varchar_val='variable',
        text_val='long text content',
        date_val=datetime.now().date(),
        time_val=datetime.now().time(),
        timestamp_val=datetime.now().timestamp(),
        blob_val=b'binary data',
        json_val={'key': 'value'},
        array_val=[1, 2, 3]
    )

    # Save and verify
    rows = case.save()
    assert rows == 1
    assert case.id is not None

    # Find and verify
    found = type_case_class.find_one(case.id)
    assert found is not None
    assert isinstance(found.id, uuid.UUID)
    assert found.tiny_int == 127
    assert found.small_int == 32767
    assert found.big_int == 9223372036854775807
    assert abs(found.float_val - 3.14) < 1e-6
    assert abs(found.double_val - 3.141592653589793) < 1e-10
    assert found.decimal_val == Decimal('123.4567')
    assert found.char_val == 'fixed'
    assert found.varchar_val == 'variable'
    assert found.text_val == 'long text content'
    assert isinstance(found.date_val, date)
    assert isinstance(found.time_val, dtime)
    assert isinstance(found.timestamp_val, float)
    assert found.blob_val == b'binary data'
    assert found.json_val == {'key': 'value'}
    assert found.array_val == [1, 2, 3]


def test_validated_user_crud(validated_user_class):
    """Test CRUD operations with a validated user model"""
    # Test with valid data
    user = validated_user_class(
        username='valid_user',
        email='valid@domain.com',
        age=30,
        credit_score=750,
        status='active'
    )
    rows = user.save()
    assert rows == 1

    # Test invalid username (contains numbers)
    with pytest.raises(ValidationError):
        user = validated_user_class(
            username='user123',
            email='valid@domain.com',
            credit_score=750,
            status='active'
        )
        user.save()

    # Test invalid email address
    with pytest.raises(pydantic.ValidationError):
        user = validated_user_class(
            username='valid_user',
            email='@example.com',
            credit_score=750,
            status='active'
        )
        user.save()

    # Test invalid credit score
    with pytest.raises(ValidationError):
        user = validated_user_class(
            username='valid_user',
            email='valid@domain.com',
            credit_score=900,  # out of range
            status='active'
        )
        user.save()

    # Test invalid status
    with pytest.raises(pydantic.ValidationError):
        user = validated_user_class(
            username='valid_user',
            email='valid@domain.com',
            credit_score=750,
            status='unknown'  # not in allowed status list
        )
        user.save()

    # Test update validation
    user = validated_user_class(
        username='valid_user',
        email='valid@domain.com',
        credit_score=750,
        status='active'
    )
    user.save()

    # Valid update
    user.credit_score = 800
    user.status = 'suspended'
    rows = user.save()
    assert rows == 1

    # Invalid update: username contains numbers
    with pytest.raises(ValidationError):
        user.username = 'valid123'
        user.save()

    # Invalid update: credit score out of range
    with pytest.raises(ValidationError):
        user.credit_score = 200
        user.save()

    # Invalid update: invalid status
    with pytest.raises(ValidationError):
        user.status = 'deleted'
        user.save()

    # Reload to verify last valid state
    user.refresh()
    assert user.username == 'valid_user'
    assert user.credit_score == 800
    assert user.status == 'suspended'


def test_transaction_crud(user_class):
    """Test CRUD operations in transactions"""
    # Successful transaction
    with user_class.transaction():
        user = user_class(
            username='transaction_user',
            email='transaction@example.com',
            age=35,
            balance=Decimal('1000.00')
        )
        user.save()

        user.balance = Decimal('1500.00')
        user.save()

    # Verify transaction succeeded
    saved_user = user_class.find_one(user.id)
    assert saved_user is not None
    assert saved_user.balance == Decimal('1500.00')

    # Failed transaction
    with pytest.raises(ValidationError):
        with user_class.transaction():
            user = user_class(
                username='transaction_user2',
                email='transaction2@example.com',
                age=36,
                balance=Decimal('2000.00')
            )
            user.save()

            # This should trigger rollback
            user.age = -1
            user.save()

    # Verify transaction rolled back
    found = user_class.query().where('username = ?', ('transaction_user2',)).one()
    assert found is None


def test_refresh_record(validated_user_class):
    """Test record refresh functionality"""
    user = validated_user_class(
        username='refresh_user',
        email='refresh@example.com',
        age=40,
        balance=Decimal('100.00'),
        credit_score=100,
    )
    user.save()

    # Update data with another instance
    another_instance = validated_user_class.find_one(user.id)
    another_instance.username = 'refreshed_user'
    another_instance.save()

    # Refresh original instance
    user.refresh()
    assert user.username == 'refreshed_user'

    # Try to refresh an unsaved record
    new_user = validated_user_class(
        username='new_user',
        email='new@example.com',
        age=40,
        balance=Decimal('100.00'),
        credit_score=100,
    )
    with pytest.raises(DatabaseError):
        new_user.refresh()


def test_query_methods(validated_user_class):
    """Test query methods"""
    # Create test data
    users = [
        validated_user_class(
            username=f'query_user_{i}',
            email=f'query{i}@example.com',
            age=30 + i,
            balance=Decimal(f'{100 * (i + 1)}.00'),
            credit_score=100,
        )
        for i in range(3)
    ]
    for user in users:
        user.save()

    # Test find_by_pk
    found = validated_user_class.find_one(users[0].id)
    assert found is not None
    assert found.username == 'query_user_0'

    # Test find_one_or_fail
    found = validated_user_class.find_one_or_fail(users[1].id)
    assert found.username == 'query_user_1'

    with pytest.raises(RecordNotFound):
        validated_user_class.find_one_or_fail(9999)

    # Test query builder
    query_results = (validated_user_class.query()
                     .where('age >= ?', (31,))
                     .order_by('age')
                     .all())
    assert len(query_results) == 2
    assert query_results[0].username == 'query_user_1'
    assert query_results[1].username == 'query_user_2'

    # Test aggregate queries
    count = validated_user_class.query().count()
    assert count == 3

    # avg_age = validated_user_class.query().select('AVG(age) as avg_age').one()  # TODO: Aggregate queries not supported yet, to be improved in the future.
    # assert avg_age['avg_age'] == 31  # 30 + 31 + 32 / 3