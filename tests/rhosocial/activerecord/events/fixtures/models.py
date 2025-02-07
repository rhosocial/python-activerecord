from typing import Optional, Dict, List, Tuple

from pydantic import Field

from src.rhosocial.activerecord.interface import ModelEvent
from src.rhosocial.activerecord import ActiveRecord
from src.rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin
from tests.rhosocial.activerecord.utils import create_active_record_fixture


class EventTestModel(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """用于测试事件机制的模型类"""
    __table_name__ = "event_tests"

    id: Optional[int] = None
    name: str
    status: str = Field(default="draft")
    revision: int = Field(default=1)
    content: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._event_logs = []  # 用于记录事件触发历史

    def log_event(self, event: ModelEvent, **kwargs):
        """记录事件触发历史"""
        self._event_logs.append((event, kwargs))

    def get_event_logs(self) -> List[Tuple[ModelEvent, Dict]]:
        """获取事件历史"""
        return self._event_logs.copy()

    def clear_event_logs(self):
        """清空事件历史"""
        self._event_logs.clear()


# 创建测试夹具
event_test_model = create_active_record_fixture(EventTestModel)