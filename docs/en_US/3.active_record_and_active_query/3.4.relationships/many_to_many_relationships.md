# Many-to-Many Relationships

Many-to-many relationships represent a connection between two models where multiple records in the first model can be associated with multiple records in the second model. In rhosocial ActiveRecord, many-to-many relationships are typically implemented using an intermediate join table and a combination of `HasMany` relationships.

## Overview

A many-to-many relationship occurs when multiple records in one model can be associated with multiple records in another model. Examples include:

- Students and courses (a student can take many courses, and a course can have many students)
- Products and categories (a product can belong to many categories, and a category can contain many products)
- Users and roles (a user can have many roles, and a role can be assigned to many users)

In database design, many-to-many relationships are implemented using a join table (also called a pivot or junction table) that contains foreign keys to both related tables.

## Implementing Many-to-Many Relationships

In rhosocial ActiveRecord, there are two main approaches to implementing many-to-many relationships:

1. **Using an explicit join model**: Define a separate model for the join table and use two one-to-many relationships
2. **Using a through relationship**: Use a more direct approach with a special configuration (❌ NOT IMPLEMENTED in the current version)

### Using an Explicit Join Model

This approach involves creating three models: the two main models and a join model that connects them.

#### Example: Students and Courses

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
    
    # Define relationship with Enrollment model
    enrollments: ClassVar[HasMany['Enrollment']] = HasMany(
        foreign_key='student_id',
        inverse_of='student'
    )
    
    # Helper method to get all courses for this student
    def courses(self):
        from .course import Course  # Import here to avoid circular imports
        enrollments = self.enrollments()
        course_ids = [enrollment.course_id for enrollment in enrollments]
        return Course.find_all().where(id__in=course_ids).all()

class Course(IntegerPKMixin, ActiveRecord):
    __table_name__ = "courses"
    
    id: Optional[int] = None
    title: str
    description: str
    
    # Define relationship with Enrollment model
    enrollments: ClassVar[HasMany['Enrollment']] = HasMany(
        foreign_key='course_id',
        inverse_of='course'
    )
    
    # Helper method to get all students for this course
    def students(self):
        from .student import Student  # Import here to avoid circular imports
        enrollments = self.enrollments()
        student_ids = [enrollment.student_id for enrollment in enrollments]
        return Student.find_all().where(id__in=student_ids).all()

class Enrollment(IntegerPKMixin, ActiveRecord):
    __table_name__ = "enrollments"
    
    id: Optional[int] = None
    student_id: int  # Foreign key to Student
    course_id: int   # Foreign key to Course
    enrollment_date: datetime
    
    # Define relationships with Student and Course models
    student: ClassVar[BelongsTo['Student']] = BelongsTo(
        foreign_key='student_id',
        inverse_of='enrollments'
    )
    
    course: ClassVar[BelongsTo['Course']] = BelongsTo(
        foreign_key='course_id',
        inverse_of='enrollments'
    )
```

## Using Many-to-Many Relationships

### Adding a Relationship

To enroll a student in a course:

```python
# Get a student and a course
student = Student.find_by(name="John Doe")
course = Course.find_by(title="Introduction to Python")

# Create an enrollment
enrollment = Enrollment(
    student_id=student.id,
    course_id=course.id,
    enrollment_date=datetime.now()
)
enrollment.save()
```

### Retrieving Related Records

To get all courses for a student:

```python
student = Student.find_by(name="John Doe")
courses = student.courses()

for course in courses:
    print(f"Course: {course.title}")
```

To get all students for a course:

```python
course = Course.find_by(title="Introduction to Python")
students = course.students()

for student in students:
    print(f"Student: {student.name}")
```

### Removing a Relationship

To remove a student from a course:

```python
# Find the enrollment to remove
enrollment = Enrollment.find_by(
    student_id=student.id,
    course_id=course.id
)

# Delete the enrollment
if enrollment:
    enrollment.delete()
```

## Eager Loading

When working with many-to-many relationships, you can use eager loading to optimize performance:

```python
# Eager load enrollments when fetching students
students = Student.find_all().with_("enrollments").all()

# For each student, eager load courses
for student in students:
    enrollments = student.enrollments()
    course_ids = [enrollment.course_id for enrollment in enrollments]
    courses = Course.find_all().where(id__in=course_ids).all()
    print(f"Student: {student.name}")
    for course in courses:
        print(f"  Course: {course.title}")
```

## Advanced Usage: Additional Data in Join Table

One advantage of using an explicit join model is that you can store additional data about the relationship. For example, in the student-course relationship, you might want to store the enrollment date, grade, or other information:

```python
# Create an enrollment with additional data
enrollment = Enrollment(
    student_id=student.id,
    course_id=course.id,
    enrollment_date=datetime.now(),
    grade="A",
    completed=False
)
enrollment.save()

# Query based on the additional data
honor_students = Enrollment.find_all().where(
    grade__in=["A", "A+"]
).all()

for enrollment in honor_students:
    student = enrollment.student()
    course = enrollment.course()
    print(f"Honor student {student.name} in {course.title}")
```

## Best Practices

1. **Use meaningful names for join models**: Instead of generic names like "UserRole", use names that describe the relationship, like "Enrollment" or "Membership".

2. **Add indexes to foreign keys**: Make sure to add database indexes to the foreign key columns in the join table to improve query performance.

3. **Consider using transactions**: When creating or removing relationships that involve multiple database operations, use transactions to ensure data consistency.

4. **Implement helper methods**: Add helper methods to your models to make working with many-to-many relationships more intuitive, as shown in the examples above.

5. **Be mindful of N+1 query problems**: Use eager loading when appropriate to avoid performance issues when accessing related records.

## Conclusion

Many-to-many relationships are a powerful feature in database design and are well-supported in rhosocial ActiveRecord through the use of join models. By following the patterns described in this document, you can implement complex relationships between your models while maintaining clean, readable code and good performance.