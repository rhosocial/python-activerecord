import pytest
from pydantic import ValidationError
from src.rhosocial.activerecord.backend.errors import ValidationError as DBValidationError

from .fixtures.models import validated_user  # needed as fixture, do not remove.


@pytest.fixture
def validated_user_data():
    """提供有效的用户测试数据"""
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'age': 25
    }

def test_field_validation(validated_user):
    """Test Pydantic field validation"""
    # Test username validation
    with pytest.raises(ValidationError) as exc_info:
        validated_user(username="ab", email="valid@example.com")  # Too short
    assert "username" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        validated_user(username="x" * 51, email="valid@example.com")  # Too long
    assert "username" in str(exc_info.value)

    # Test email validation
    with pytest.raises(ValidationError) as exc_info:
        validated_user(username="validuser", email="invalid-email")
    assert "email" in str(exc_info.value)

    # Test age validation
    with pytest.raises(ValidationError) as exc_info:
        validated_user(username="validuser", email="valid@example.com", age=-1)
    assert "age" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        validated_user(username="validuser", email="valid@example.com", age=151)
    assert "age" in str(exc_info.value)


def test_business_rule_validation(validated_user):
    """Test custom business rule validation"""
    # Test age restriction rule
    user = validated_user(
        username="younguser",  # Changed to comply with alphanumeric requirement
        email="young@example.com",
        age=12
    )

    with pytest.raises(DBValidationError) as exc_info:
        user.save()
    assert "at least 13 years old" in str(exc_info.value)

    # Test valid age
    user.age = 13
    assert user.save() == 1


def test_validation_on_update(validated_user, validated_user_data):
    """Test validation during record updates"""
    # Create valid user
    user = validated_user(**validated_user_data)
    user.save()

    # Test invalid update
    user.email = "invalid-email-format"
    with pytest.raises(DBValidationError):
        user.save()

    # Verify record remains unchanged
    fresh_user = validated_user.find_one(user.id)
    assert fresh_user.email == validated_user_data['email']

    # Test valid update
    user.email = "new-valid@example.com"
    assert user.save() == 1


def test_null_field_validation(validated_user):
    """Test validation of nullable fields"""
    # Test with null age (should be valid as age is optional)
    user = validated_user(
        username="testuser",  # Changed to comply with alphanumeric requirement
        email="test@example.com"
    )
    assert user.save() == 1

    # Verify null field was saved correctly
    saved_user = validated_user.find_one(user.id)
    assert saved_user.age is None


def test_multiple_validation_errors(validated_user):
    """Test handling of multiple validation errors"""
    with pytest.raises(ValidationError) as exc_info:
        validated_user(
            username="a",  # Too short
            email="invalid-email",  # Invalid format
            age=200  # Too high
        )

    error_str = str(exc_info.value)
    assert "username" in error_str
    assert "email" in error_str
    assert "age" in error_str