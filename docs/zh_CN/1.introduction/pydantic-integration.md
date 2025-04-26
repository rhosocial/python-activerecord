# Pydantic 集成优势

rhosocial ActiveRecord 与 Pydantic 的紧密集成提供了显著的优势，值得特别关注：

## 1. 无缝生态系统集成

rhosocial ActiveRecord 模型可以直接与其他基于 Pydantic 的库和框架一起使用：

- **FastAPI**：模型可以用作请求/响应模式，无需转换
- **Pydantic Settings**：使用相同验证的配置管理
- **数据验证库**：适用于 pydantic-extra-types、email-validator 等
- **模式生成**：自动 OpenAPI 模式生成
- **数据转换**：使用 model_dump() 和 parse_obj() 进行简单的模型转换

## 2. 高级类型验证

rhosocial ActiveRecord 继承了 Pydantic 的强大验证能力：

- **复杂类型**：支持嵌套模型、联合类型、字面量和泛型
- **自定义验证器**：字段级和模型级验证函数
- **约束类型**：最小/最大值、字符串模式、长度约束
- **强制转换**：在可能的情况下自动类型转换
- **错误处理**：详细的验证错误消息

## 3. 模式演变和文档

- **JSON 模式生成**：将模型定义导出为 JSON 模式
- **自动文档**：模型是自文档化的，包含字段描述
- **模式管理**：使用版本字段跟踪模型更改
- **数据迁移**：在模式版本之间转换

## 4. 实际开发优势

- **IDE 集成**：更好的类型提示和自动完成
- **测试**：带验证的更精确模拟对象
- **错误预防**：在运行时捕获数据问题，防止它们到达数据库
- **代码重用**：对数据库访问、API 端点和业务逻辑使用相同的模型

## 集成示例

以下是 rhosocial ActiveRecord 模型如何与 FastAPI 应用程序无缝集成的示例：

```python
from fastapi import FastAPI
from activerecord import ActiveRecord
from typing import List, Optional
from pydantic import EmailStr

# 使用 Pydantic 风格的类型注释定义 ActiveRecord 模型
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: Optional[int] = None
    name: str
    email: EmailStr
    is_active: bool = True
    
    class Config:
        schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "is_active": True
            }
        }

app = FastAPI()

# 直接使用 ActiveRecord 模型作为 FastAPI 响应模型
@app.get("/users/", response_model=List[User])
async def read_users():
    return User.query().where("is_active = ?", (True,)).all()

# 使用 ActiveRecord 模型进行请求验证
@app.post("/users/", response_model=User)
async def create_user(user: User):
    # 用户已由 Pydantic 验证
    user.save()
    return user
```

这种无缝集成在没有额外转换层或辅助库的情况下，无法通过其他 ORM 实现。