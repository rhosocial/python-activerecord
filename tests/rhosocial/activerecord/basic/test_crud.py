import time
import uuid
from decimal import Decimal
from datetime import date, time as dtime

import pydantic
import pytest

from src.rhosocial.activerecord.backend.errors import ValidationError, RecordNotFound, DatabaseError

from .fixtures.models import user_class, type_case_class, validated_user_class  # needed as fixture, do not remove.


def test_create_user(user_class):
    """测试创建用户记录"""
    instance = user_class(username="Alice", email="alice@example.com", age=30, balance=Decimal("100.50"))
    rows = instance.save()
    assert rows == 1
    assert instance.id is not None
    assert instance.created_at is not None
    assert instance.updated_at is not None
    assert instance.is_active is True


def test_create_user_with_invalid_data(user_class):
    """测试创建带无效数据的用户记录"""
    with pytest.raises(pydantic.ValidationError):
        user = user_class(
            username='jo',  # 太短
            email='invalid-email',  # 无效的email格式
            age=200,  # 超出范围
            balance=Decimal('100.999')  # 超出小数位数
        )
        user.save()


def test_find_user(user_class):
    """测试查找用户记录"""
    # 创建用户
    user = user_class(
        username='jane_doe',
        email='jane@doe.com',
        age=25,
        balance=Decimal('200.00')
    )
    user.save()

    # 通过ID查找
    found = user_class.find_one(user.id)
    assert found is not None
    assert found.username == 'jane_doe'
    assert found.email == 'jane@doe.com'
    assert found.age == 25
    assert found.balance == Decimal('200.00')


def test_find_nonexistent_user(user_class):
    """测试查找不存在的用户记录"""
    found = user_class.find_one(999)
    assert found is None

    with pytest.raises(RecordNotFound):
        user_class.find_one_or_fail(999)


def test_update_user(user_class):
    """测试更新用户记录"""
    # 创建用户
    user = user_class(
        username='bob_smith',
        email='bob@smith.com',
        age=40,
        balance=Decimal('300.00')
    )
    assert user.is_new_record is True
    user.save()
    assert user.is_new_record is False

    # 更新字段
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

    # 重新加载验证
    user.refresh()
    assert user.username == 'robert_smith'
    assert user.age == 41
    assert user.email == 'bob@smith.com'  # 未修改的字段保持不变
    assert user.created_at == original_created_at


def test_update_with_invalid_data(user_class):
    """测试使用无效数据更新用户记录"""
    user = user_class(
        username='alice_wonder',
        email='alice@wonder.com',
        age=28,
        balance=Decimal('400.00')
    )
    user.save()

    with pytest.raises(ValidationError):
        user.age = -1  # 无效的年龄
        user.save()


def test_delete_user(user_class):
    """测试删除用户记录"""
    user = user_class(
        username='charlie_brown',
        email='charlie@brown.com',
        age=35,
        balance=Decimal('500.00')
    )
    assert user.is_new_record is True
    user.save()
    assert user.is_new_record is False

    # 删除记录
    user_id = user.id
    rows = user.delete()
    assert rows == 1

    # 验证已删除
    assert user_class.find_one(user_id) is None


def test_bulk_operations(user_class):
    """测试批量操作"""
    # 批量创建
    users = [
        user_class(username=f'user_{i}',
                   email=f'user_{i}@example.com',
                   age=20 + i,
                   balance=Decimal(f'{100 + i}.00'))
        for i in range(5)
    ]
    for user in users:
        user.save()

    # 批量查询
    found_users = user_class.query().order_by('age').all()
    assert len(found_users) == 5
    assert [u.age for u in found_users] == [20, 21, 22, 23, 24]

    # 条件查询
    young_users = user_class.query().where('age < ?', (22,)).all()
    assert len(young_users) == 2


def test_dirty_tracking(user_class):
    """测试脏数据跟踪"""
    user = user_class(
        username='track_user',
        email='track@example.com',
        age=30,
        balance=Decimal('100.00')
    )

    # 新记录应该不是脏的
    assert not user.is_dirty and user.is_new_record
    assert 'username' not in user.dirty_fields
    assert 'email' not in user.dirty_fields

    user.save()
    # 保存后应该是干净的
    assert not user.is_dirty and not user.is_new_record
    assert len(user.dirty_fields) == 0

    # 修改后应该是脏的
    user.username = 'new_track_user'
    assert user.is_dirty
    assert 'username' in user.dirty_fields
    assert 'email' not in user.dirty_fields


def test_type_case_crud(type_case_class):
    """测试各种字段类型的CRUD操作"""
    from datetime import datetime

    # 创建测试记录
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

    # 保存并验证
    rows = case.save()
    assert rows == 1
    assert case.id is not None

    # 查找并验证
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
    """测试带验证的用户模型的CRUD操作"""
    # 测试有效数据
    user = validated_user_class(
        username='valid_user',
        email='valid@domain.com',
        age=30,
        credit_score=750,
        status='active'
    )
    rows = user.save()
    assert rows == 1

    # 测试无效用户名（包含数字）
    with pytest.raises(ValidationError):
        user = validated_user_class(
            username='user123',
            email='valid@domain.com',
            credit_score=750,
            status='active'
        )
        user.save()

    # 测试无效email地址
    with pytest.raises(pydantic.ValidationError):
        user = validated_user_class(
            username='valid_user',
            email='@example.com',
            credit_score=750,
            status='active'
        )
        user.save()

    # 测试无效信用分数
    with pytest.raises(ValidationError):
        user = validated_user_class(
            username='valid_user',
            email='valid@domain.com',
            credit_score=900,  # 超出范围
            status='active'
        )
        user.save()

    # 测试无效状态
    with pytest.raises(pydantic.ValidationError):
        user = validated_user_class(
            username='valid_user',
            email='valid@domain.com',
            credit_score=750,
            status='unknown'  # 不在允许的状态列表中
        )
        user.save()

    # 测试更新验证
    user = validated_user_class(
        username='valid_user',
        email='valid@domain.com',
        credit_score=750,
        status='active'
    )
    user.save()

    # 有效更新
    user.credit_score = 800
    user.status = 'suspended'
    rows = user.save()
    assert rows == 1

    # 无效更新：用户名包含数字
    with pytest.raises(ValidationError):
        user.username = 'valid123'
        user.save()

    # 无效更新：信用分数超出范围
    with pytest.raises(ValidationError):
        user.credit_score = 200
        user.save()

    # 无效更新：无效状态
    with pytest.raises(ValidationError):
        user.status = 'deleted'
        user.save()

    # 重新加载验证最后的有效状态
    user.refresh()
    assert user.username == 'valid_user'
    assert user.credit_score == 800
    assert user.status == 'suspended'


def test_transaction_crud(user_class):
    """测试事务中的CRUD操作"""
    # 成功的事务
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

    # 验证事务成功
    saved_user = user_class.find_one(user.id)
    assert saved_user is not None
    assert saved_user.balance == Decimal('1500.00')

    # 失败的事务
    with pytest.raises(ValidationError):
        with user_class.transaction():
            user = user_class(
                username='transaction_user2',
                email='transaction2@example.com',
                age=36,
                balance=Decimal('2000.00')
            )
            user.save()

            # 这应该触发回滚
            user.age = -1
            user.save()

    # 验证事务回滚
    found = user_class.query().where('username = ?', ('transaction_user2',)).one()
    assert found is None


def test_refresh_record(validated_user_class):
    """测试记录刷新功能"""
    user = validated_user_class(
        username='refresh_user',
        email='refresh@example.com',
        age=40,
        balance=Decimal('100.00'),
        credit_score=100,
    )
    user.save()

    # 使用另一个实例更新数据
    another_instance = validated_user_class.find_one(user.id)
    another_instance.username = 'refreshed_user'
    another_instance.save()

    # 刷新原始实例
    user.refresh()
    assert user.username == 'refreshed_user'

    # 尝试刷新未保存的记录
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
    """测试查询方法"""
    # 创建测试数据
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

    # 测试 find_by_pk
    found = validated_user_class.find_one(users[0].id)
    assert found is not None
    assert found.username == 'query_user_0'

    # 测试 find_one_or_fail
    found = validated_user_class.find_one_or_fail(users[1].id)
    assert found.username == 'query_user_1'

    with pytest.raises(RecordNotFound):
        validated_user_class.find_one_or_fail(9999)

    # 测试查询构建器
    query_results = (validated_user_class.query()
                     .where('age >= ?', (31,))
                     .order_by('age')
                     .all())
    assert len(query_results) == 2
    assert query_results[0].username == 'query_user_1'
    assert query_results[1].username == 'query_user_2'

    # 测试聚合查询
    count = validated_user_class.query().count()
    assert count == 3

    # avg_age = validated_user_class.query().select('AVG(age) as avg_age').one()  # TODO: 暂时不支持聚合查询，留待日后改进。
    # assert avg_age['avg_age'] == 31  # 30 + 31 + 32 / 3