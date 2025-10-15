# 多对多关系

多对多关系表示两个模型之间的连接，其中第一个模型中的多条记录可以与第二个模型中的多条记录相关联。在rhosocial ActiveRecord中，多对多关系通常通过中间连接表和`HasMany`关系的组合来实现。

## 概述

当一个模型中的多条记录可以与另一个模型中的多条记录相关联时，就会出现多对多关系。例如：

- 学生和课程（一个学生可以选修多门课程，一门课程可以有多个学生）
- 产品和类别（一个产品可以属于多个类别，一个类别可以包含多个产品）
- 用户和角色（一个用户可以拥有多个角色，一个角色可以分配给多个用户）

在数据库设计中，多对多关系通过连接表（也称为中间表或交叉表）实现，该表包含指向两个相关表的外键。

## 实现多对多关系

在rhosocial ActiveRecord中，有两种主要方法来实现多对多关系：

1. **使用显式连接模型**：为连接表定义一个单独的模型，并使用两个一对多关系
2. **使用through关系**：使用更直接的方法和特殊配置（❌ 未实现）

### 使用显式连接模型

这种方法涉及创建三个模型：两个主要模型和一个连接它们的连接模型。

#### 示例：学生和课程

```python
from typing import ClassVar, Optional, List
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany

class Student(IntegerPKMixin, ActiveRecord):
    __table_name__ = "students"
    
    id: Optional[int] = None
    name: str
    email: str
    
    # 定义与Enrollment模型的关系
    enrollments: ClassVar[HasMany['Enrollment']] = HasMany(
        foreign_key='student_id',
        inverse_of='student'
    )
    
    # 获取该学生所有课程的辅助方法
    def courses(self):
        from .course import Course  # 在这里导入以避免循环导入
        enrollments = self.enrollments()
        course_ids = [enrollment.course_id for enrollment in enrollments]
        return Course.find_all().where(id__in=course_ids).all()

class Course(IntegerPKMixin, ActiveRecord):
    __table_name__ = "courses"
    
    id: Optional[int] = None
    title: str
    description: str
    
    # 定义与Enrollment模型的关系
    enrollments: ClassVar[HasMany['Enrollment']] = HasMany(
        foreign_key='course_id',
        inverse_of='course'
    )
    
    # 获取该课程所有学生的辅助方法
    def students(self):
        from .student import Student  # 在这里导入以避免循环导入
        enrollments = self.enrollments()
        student_ids = [enrollment.student_id for enrollment in enrollments]
        return Student.find_all().where(id__in=student_ids).all()

class Enrollment(IntegerPKMixin, ActiveRecord):
    __table_name__ = "enrollments"
    
    id: Optional[int] = None
    student_id: int  # 指向Student的外键
    course_id: int   # 指向Course的外键
    enrollment_date: datetime
    
    # 定义与Student和Course模型的关系
    student: ClassVar[BelongsTo['Student']] = BelongsTo(
        foreign_key='student_id',
        inverse_of='enrollments'
    )
    
    course: ClassVar[BelongsTo['Course']] = BelongsTo(
        foreign_key='course_id',
        inverse_of='enrollments'
    )
```

## 使用多对多关系

### 添加关系

将学生注册到课程：

```python
# 获取一个学生和一门课程
student = Student.find_by(name="张三")
course = Course.find_by(title="Python入门")

# 创建注册记录
enrollment = Enrollment(
    student_id=student.id,
    course_id=course.id,
    enrollment_date=datetime.now()
)
enrollment.save()
```

### 检索相关记录

获取学生的所有课程：

```python
student = Student.find_by(name="张三")
courses = student.courses()

for course in courses:
    print(f"课程: {course.title}")
```

获取课程的所有学生：

```python
course = Course.find_by(title="Python入门")
students = course.students()

for student in students:
    print(f"学生: {student.name}")
```

### 移除关系

将学生从课程中移除：

```python
# 查找要移除的注册记录
enrollment = Enrollment.find_by(
    student_id=student.id,
    course_id=course.id
)

# 删除注册记录
if enrollment:
    enrollment.delete()
```

## 预加载

在处理多对多关系时，可以使用预加载来优化性能：

```python
# 获取学生时预加载注册记录
students = Student.find_all().with_("enrollments").all()

# 对每个学生，预加载课程
for student in students:
    enrollments = student.enrollments()
    course_ids = [enrollment.course_id for enrollment in enrollments]
    courses = Course.find_all().where(id__in=course_ids).all()
    print(f"学生: {student.name}")
    for course in courses:
        print(f"  课程: {course.title}")
```

## 高级用法：连接表中的附加数据

使用显式连接模型的一个优点是可以存储有关关系的附加数据。例如，在学生-课程关系中，您可能想要存储注册日期、成绩或其他信息：

```python
# 创建带有附加数据的注册记录
enrollment = Enrollment(
    student_id=student.id,
    course_id=course.id,
    enrollment_date=datetime.now(),
    grade="A",
    completed=False
)
enrollment.save()

# 基于附加数据进行查询
honor_students = Enrollment.find_all().where(
    grade__in=["A", "A+"]
).all()

for enrollment in honor_students:
    student = enrollment.student()
    course = enrollment.course()
    print(f"优秀学生 {student.name} 在 {course.title} 课程中")
```

## 最佳实践

1. **为连接模型使用有意义的名称**：不要使用像"UserRole"这样的通用名称，而是使用描述关系的名称，如"Enrollment"（注册）或"Membership"（会员资格）。

2. **为外键添加索引**：确保在连接表的外键列上添加数据库索引，以提高查询性能。

3. **考虑使用事务**：在创建或删除涉及多个数据库操作的关系时，使用事务确保数据一致性。

4. **实现辅助方法**：在模型中添加辅助方法，使多对多关系的使用更加直观，如上面的示例所示。

5. **注意N+1查询问题**：在适当的时候使用预加载，以避免访问相关记录时出现性能问题。

## 结论

多对多关系是数据库设计中的强大功能，在rhosocial ActiveRecord中通过使用连接模型得到了很好的支持。通过遵循本文档中描述的模式，您可以在模型之间实现复杂的关系，同时保持代码的清晰、可读性和良好的性能。