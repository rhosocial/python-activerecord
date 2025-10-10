# Heterogeneous Data Source Integration

> **❌ NOT IMPLEMENTED**: The heterogeneous data source integration functionality described in this document is **not implemented**. This documentation describes planned functionality and is provided for future reference only. Current users should handle integration at the application level. This feature may be developed in future releases with no guaranteed timeline. Cross-database operations described here cannot achieve true cross-database atomicity.

This document explains how rhosocial ActiveRecord can be used to integrate data from different types of database systems, allowing you to work with heterogeneous data sources in a unified way.

## Overview

Heterogeneous data source integration refers to the ability to work with multiple different types of databases or data storage systems within a single application. rhosocial ActiveRecord provides tools and patterns to make this integration seamless, allowing you to:

- Query data from different database systems using a consistent API
- Join or combine data from different sources
- Maintain data consistency across heterogeneous systems
- Build applications that leverage the strengths of different database technologies

## Integration Approaches

### Model-Based Integration

The most common approach to heterogeneous data source integration in rhosocial ActiveRecord is through model-based integration, where different models connect to different data sources:

```python
from rhosocial.activerecord import ActiveRecord, ConnectionManager

# Configure connections to different database systems
ConnectionManager.configure('mysql_conn', {
    'driver': 'mysql',
    'host': 'mysql.example.com',
    'database': 'customer_data',
    'username': 'user',
    'password': 'password'
})

ConnectionManager.configure('postgres_conn', {
    'driver': 'postgresql',
    'host': 'postgres.example.com',
    'database': 'analytics',
    'username': 'user',
    'password': 'password'
})

# Define models that use different connections
class Customer(ActiveRecord):
    __connection__ = 'mysql_conn'
    __tablename__ = 'customers'

class AnalyticsEvent(ActiveRecord):
    __connection__ = 'postgres_conn'
    __tablename__ = 'events'
```

With this approach, you can work with both models in the same application code, even though they connect to different database systems.

### Service Layer Integration

For more complex integration scenarios, you might implement a service layer that coordinates operations across multiple data sources:

```python
class CustomerAnalyticsService:
    def get_customer_with_events(self, customer_id):
        # Get customer from MySQL database
        customer = Customer.find(customer_id)
        if not customer:
            return None
            
        # Get related events from PostgreSQL database
        events = AnalyticsEvent.where(customer_id=customer_id).all()
        
        # Combine the data
        result = customer.to_dict()
        result['events'] = [event.to_dict() for event in events]
        
        return result
```

### Data Federation

rhosocial ActiveRecord also supports data federation patterns, where you can create virtual models that combine data from multiple sources:

```python
class CustomerWithEvents:
    @classmethod
    def find(cls, customer_id):
        # Create a composite object from multiple data sources
        customer = Customer.find(customer_id)
        if not customer:
            return None
            
        result = cls()
        result.id = customer.id
        result.name = customer.name
        result.email = customer.email
        result.events = AnalyticsEvent.where(customer_id=customer_id).all()
        
        return result
```

## Working with Different Database Types

### Handling Type Differences

Different database systems may have different data types and type conversion rules. rhosocial ActiveRecord handles most common type conversions automatically, but you may need to be aware of some differences:

```python
# PostgreSQL-specific JSON operations
class Configuration(ActiveRecord):
    __connection__ = 'postgres_conn'
    __tablename__ = 'configurations'
    
    def get_setting(self, path):
        # Uses PostgreSQL's JSON path extraction
        return self.query_value("settings->>'{}'\:\:text".format(path))

# MySQL-specific operations
class LogEntry(ActiveRecord):
    __connection__ = 'mysql_conn'
    __tablename__ = 'logs'
    
    @classmethod
    def recent_by_type(cls, log_type):
        # Uses MySQL's date functions
        return cls.where("log_type = ? AND created_at > DATE_SUB(NOW(), INTERVAL 1 DAY)", log_type).all()
```

### Database-Specific Features

You can leverage database-specific features while still maintaining a clean abstraction:

```python
class Product(ActiveRecord):
    __connection__ = 'postgres_conn'
    __tablename__ = 'products'
    
    @classmethod
    def search_by_text(cls, query):
        # Uses PostgreSQL's full-text search capabilities
        return cls.where("to_tsvector('english', name || ' ' || description) @@ to_tsquery('english', ?)", query).all()

class UserActivity(ActiveRecord):
    __connection__ = 'mysql_conn'
    __tablename__ = 'user_activities'
    
    @classmethod
    def get_recent_activities(cls, user_id):
        # Uses MySQL's specific syntax
        return cls.where("user_id = ? ORDER BY created_at DESC LIMIT 10", user_id).all()
```

## Integration with Non-Relational Data Sources

While rhosocial ActiveRecord is primarily designed for relational databases, you can integrate with non-relational data sources through custom adapters or by using hybrid approaches:

```python
# Example of a service that integrates relational and document database data
class UserProfileService:
    def __init__(self):
        self.mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
        self.profiles_collection = self.mongo_client["user_db"]["profiles"]
    
    def get_complete_user_profile(self, user_id):
        # Get basic user data from relational database
        user = User.find(user_id)
        if not user:
            return None
            
        # Get extended profile from MongoDB
        profile_data = self.profiles_collection.find_one({"user_id": user_id})
        
        # Combine the data
        result = user.to_dict()
        if profile_data:
            result.update({
                'preferences': profile_data.get('preferences', {}),
                'activity_history': profile_data.get('activity_history', []),
                'extended_attributes': profile_data.get('attributes', {})
            })
            
        return result
```

## Best Practices for Heterogeneous Data Integration

### 1. Define Clear Boundaries

Clearly define which data belongs in which system and why. Avoid duplicating data across systems unless necessary for performance or availability reasons.

### 2. Use Consistent Identifiers

Ensure that entities shared across systems use consistent identifiers to make joining and relating data easier.

### 3. Handle Transactions Carefully

Be aware that transactions cannot span different database systems automatically. Implement compensating transactions or saga patterns for operations that need to update multiple systems atomically.

### 4. Consider Performance Implications

Joining data across different database systems can be expensive. Consider strategies like:

- Periodic data synchronization
- Caching frequently accessed cross-database data
- Denormalizing some data to avoid frequent cross-database operations

### 5. Monitor and Log Integration Points

Integration points between different data systems are common sources of errors and performance issues. Implement thorough logging and monitoring at these boundaries.

## Conclusion

rhosocial ActiveRecord provides flexible tools for integrating heterogeneous data sources, allowing you to leverage the strengths of different database systems while maintaining a consistent programming model. By following the patterns and practices outlined in this document, you can build robust applications that seamlessly work with data across multiple database technologies.