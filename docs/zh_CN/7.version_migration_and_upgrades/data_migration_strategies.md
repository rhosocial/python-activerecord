# 数据迁移策略

## 介绍

数据迁移是在存储系统、格式或应用程序之间传输数据的过程。在rhosocial ActiveRecord的上下文中，数据迁移通常伴随着模式变更，或在不同数据库系统之间过渡时发生。本文档概述了有效规划和执行数据迁移的策略。

## 数据迁移类型

### 1. 与模式相关的数据迁移

这些迁移发生在模式变更需要数据转换时：

- **列重命名**：将数据从旧列移动到新列
- **数据重构**：更改数据的组织方式（例如，规范化或反规范化表）
- **数据类型转换**：将数据从一种类型转换为另一种类型
- **默认值填充**：用默认值或计算值填充新列

### 2. 系统迁移

这些迁移涉及在不同系统之间移动数据：

- **数据库平台迁移**：从一个数据库系统迁移到另一个
- **应用程序迁移**：将数据从一个应用程序过渡到另一个
- **版本升级**：在主要版本升级期间移动数据

## 迁移规划

### 1. 评估和规划

- **数据清单**：编目所有需要迁移的数据
- **依赖关系映射**：识别数据实体之间的关系
- **数量分析**：估计数据量以规划性能考虑因素
- **验证策略**：定义如何在迁移前、迁移中和迁移后验证数据

### 2. 风险管理

- **备份策略**：确保迁移前进行全面备份
- **回滚计划**：定义明确的程序，以便在需要时撤销更改
- **测试方法**：为迁移过程创建测试策略
- **停机规划**：估计并沟通任何所需的停机时间

## 实施技术

### 使用迁移脚本

rhosocial ActiveRecord的迁移框架可以处理数据迁移和模式变更：

```python
from rhosocial.activerecord.migration import Migration

class MigrateUserNames(Migration):
    """将full_name拆分为first_name和last_name。"""
    
    def up(self):
        # 添加新列
        self.add_column('user', 'first_name', 'string', length=100, null=True)
        self.add_column('user', 'last_name', 'string', length=100, null=True)
        
        # 迁移数据
        self.execute("""
            UPDATE user 
            SET first_name = SUBSTRING_INDEX(full_name, ' ', 1),
                last_name = SUBSTRING_INDEX(full_name, ' ', -1)
            WHERE full_name IS NOT NULL
        """)
        
        # 如果适当，使列不可为空
        self.change_column('user', 'first_name', 'string', length=100, null=False)
        self.change_column('user', 'last_name', 'string', length=100, null=False)
        
        # 可选地移除旧列
        self.remove_column('user', 'full_name')
    
    def down(self):
        # 添加回原始列
        self.add_column('user', 'full_name', 'string', length=200, null=True)
        
        # 恢复数据
        self.execute("""
            UPDATE user
            SET full_name = CONCAT(first_name, ' ', last_name)
        """)
        
        # 移除新列
        self.remove_column('user', 'first_name')
        self.remove_column('user', 'last_name')
    }
```

### 使用ActiveRecord模型

对于更复杂的迁移，您可以直接使用ActiveRecord模型：

```python
from rhosocial.activerecord.migration import Migration
from app.models import OldUser, NewUser

class MigrateUserData(Migration):
    """将用户数据迁移到新结构。"""
    
    def up(self):
        # 为新表创建模式
        self.create_table('new_user', [
            self.column('id', 'integer', primary_key=True, auto_increment=True),
            self.column('username', 'string', length=64, null=False),
            self.column('email', 'string', length=255, null=False),
            self.column('profile_data', 'json', null=True),
            self.column('created_at', 'datetime'),
            self.column('updated_at', 'datetime')
        ])
        
        # 使用模型进行复杂数据转换
        batch_size = 1000
        offset = 0
        
        while True:
            old_users = OldUser.find().limit(batch_size).offset(offset).all()
            if not old_users:
                break
                
            for old_user in old_users:
                new_user = NewUser()
                new_user.username = old_user.username
                new_user.email = old_user.email
                
                # 复杂转换 - 将配置文件字段合并为JSON
                profile_data = {
                    'address': old_user.address,
                    'phone': old_user.phone,
                    'preferences': {
                        'theme': old_user.theme,
                        'notifications': old_user.notifications_enabled
                    }
                }
                new_user.profile_data = profile_data
                
                new_user.created_at = old_user.created_at
                new_user.updated_at = old_user.updated_at
                new_user.save()
                
            offset += batch_size
    
    def down(self):
        self.drop_table('new_user')
```

### 批处理

对于大型数据集，批处理至关重要：

```python
def migrate_large_table(self):
    # 获取总计数以跟踪进度
    total = self.execute("SELECT COUNT(*) FROM large_table")[0][0]
    
    batch_size = 5000
    processed = 0
    
    while processed < total:
        # 处理一批
        self.execute(f"""
            INSERT INTO new_large_table (id, name, transformed_data)
            SELECT id, name, UPPER(data) AS transformed_data
            FROM large_table
            ORDER BY id
            LIMIT {batch_size} OFFSET {processed}
        """)
        
        processed += batch_size
        print(f"已处理 {processed}/{total} 条记录")
```

## 性能优化

### 1. 索引策略

- **临时删除索引**：在批量数据加载期间删除非主键索引
- **加载后创建索引**：在数据加载后添加索引
- **优化查询索引**：确保迁移中使用的查询具有适当的索引

### 2. 事务管理

- **批量事务**：在批次而不是单个记录周围使用事务
- **保存点**：对于非常大的事务，使用保存点以避免回滚开销

### 3. 资源管理

- **连接池**：配置适当的连接池设置
- **内存管理**：监控和优化迁移期间的内存使用
- **并行处理**：考虑对独立数据集进行并行处理

## 验证和测试

### 1. 数据验证

- **迁移前验证**：在迁移前验证源数据
- **迁移后验证**：迁移后验证数据完整性
- **对账报告**：生成比较源数据和目标数据的报告

### 2. 测试方法

- **演练**：首先在测试环境中执行迁移
- **子集测试**：使用代表性数据子集进行测试
- **性能测试**：使用类似生产的数据量测量迁移性能

## 处理特殊情况

### 1. 处理遗留数据

- **数据清洗**：在迁移前清洗和规范化数据
- **处理NULL值**：为NULL或缺失值定义策略
- **数据类型不兼容**：规划类型转换边缘情况

### 2. 持续运营要求

- **零停机迁移**：无需服务中断即可迁移的策略
- **双写模式**：在过渡期间同时写入新旧系统
- **增量迁移**：以较小、可管理的增量迁移数据

## 结论

有效的数据迁移需要仔细规划、适当的技术和彻底的验证。通过遵循本文档中概述的策略，您可以在应用程序发展过程中最小化风险并确保成功的数据转换。

请记住，每个迁移场景都是独特的，您应该根据特定需求、数据量和系统约束调整这些策略。