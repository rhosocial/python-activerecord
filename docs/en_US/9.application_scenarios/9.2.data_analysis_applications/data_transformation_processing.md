# Data Transformation Processing with rhosocial ActiveRecord

Data transformation is a critical component of data analysis workflows. rhosocial ActiveRecord provides powerful capabilities for transforming and processing data from databases. This document explores various approaches to data transformation using ActiveRecord.

## Basic Data Transformation

### Selecting and Transforming Columns

ActiveRecord allows you to transform data directly in your queries using SQL expressions:

```python
# Transform data during selection
transformed_data = Product.query()\
    .select('id', 'name')\
    .select('price * 1.1 as price_with_tax')\
    .select('UPPER(category) as category')\
    .select('CONCAT(name, " (", category, ")") as display_name')\
    .all()
```

### Filtering and Transforming Data

Combine filtering with transformation for targeted data processing:

```python
# Filter and transform data for analysis
high_value_orders = Order.query()\
    .filter('total_amount > ?', (1000,))\
    .select('id', 'customer_id', 'order_date')\
    .select('total_amount * 0.9 as discounted_amount')\
    .select('CASE WHEN total_amount > 5000 THEN "Premium" ELSE "Standard" END as order_tier')\
    .order_by('total_amount DESC')\
    .all()
```

## Advanced Data Transformation Techniques

### Using Window Functions for Ranking and Analysis

Window functions are powerful tools for advanced data transformation:

```python
# Rank products by price within each category
ranked_products = Product.query()\
    .select('id', 'name', 'category', 'price')\
    .window_function(
        'RANK() OVER (PARTITION BY category ORDER BY price DESC)',
        'price_rank'
    )\
    .window_function(
        'AVG(price) OVER (PARTITION BY category)',
        'category_avg_price'
    )\
    .window_function(
        'price - AVG(price) OVER (PARTITION BY category)',
        'price_diff_from_avg'
    )\
    .order_by('category', 'price_rank')\
    .aggregate()
```

### JSON Data Processing

ActiveRecord supports JSON operations for complex data transformation:

```python
# Extract and transform JSON data
user_preferences = UserProfile.query()\
    .select('user_id', 'username')\
    .json_extract('preferences', '$.theme', 'theme')\
    .json_extract('preferences', '$.notifications', 'notification_settings')\
    .json_extract('preferences', '$.language', 'language')\
    .filter('JSON_EXTRACT(preferences, "$.notifications.email") = ?', ('true',))\
    .all()
```

### Data Pivoting and Unpivoting

Implement pivot (cross-tabulation) operations using conditional aggregation:

```python
# Pivot sales data by region
pivoted_sales = Sales.query()\
    .select('product_id', 'product_name')\
    .select_expr(FunctionExpression('SUM', 
                                   CaseExpression('region', 
                                                 {'North': 'amount'}, 
                                                 '0'), 
                                   alias='north_sales'))\
    .select_expr(FunctionExpression('SUM', 
                                   CaseExpression('region', 
                                                 {'South': 'amount'}, 
                                                 '0'), 
                                   alias='south_sales'))\
    .select_expr(FunctionExpression('SUM', 
                                   CaseExpression('region', 
                                                 {'East': 'amount'}, 
                                                 '0'), 
                                   alias='east_sales'))\
    .select_expr(FunctionExpression('SUM', 
                                   CaseExpression('region', 
                                                 {'West': 'amount'}, 
                                                 '0'), 
                                   alias='west_sales'))\
    .group_by('product_id', 'product_name')\
    .aggregate()
```

## ETL (Extract, Transform, Load) Processes

### Batch Data Processing

Implement ETL processes using ActiveRecord for batch data transformation:

```python
def etl_customer_data(batch_size=1000):
    """ETL process to transform customer data and load into analytics table"""
    offset = 0
    processed_count = 0
    
    while True:
        # Extract: Get a batch of source data
        customers = Customer.query()\
            .select('id', 'first_name', 'last_name', 'email', 'created_at', 'last_login', 'purchase_count')\
            .order_by('id')\
            .limit(batch_size)\
            .offset(offset)\
            .all()
        
        if not customers:
            break
            
        # Transform: Process the data
        transformed_data = []
        for customer in customers:
            # Calculate customer lifetime in days
            if customer.last_login:
                lifetime_days = (customer.last_login - customer.created_at).days
            else:
                lifetime_days = 0
                
            # Determine customer segment
            if customer.purchase_count > 10:
                segment = 'High Value'
            elif customer.purchase_count > 5:
                segment = 'Regular'
            else:
                segment = 'New'
                
            # Create transformed record
            transformed_data.append({
                'customer_id': customer.id,
                'full_name': f"{customer.first_name} {customer.last_name}",
                'email_domain': customer.email.split('@')[1] if '@' in customer.email else '',
                'lifetime_days': lifetime_days,
                'segment': segment,
                'processed_at': datetime.now()
            })
        
        # Load: Insert transformed data into target table
        CustomerAnalytics.insert_many(transformed_data)
        
        processed_count += len(customers)
        print(f"Processed {processed_count} customer records")
        offset += batch_size
    
    return processed_count
```

### Incremental Data Processing

Implement incremental ETL to process only new or changed data:

```python
def incremental_etl_orders(last_processed_id=None, batch_size=1000):
    """Incremental ETL process for order data"""
    query = Order.query()\
        .select('id', 'customer_id', 'order_date', 'total_amount', 'status')\
        .order_by('id')\
        .limit(batch_size)
    
    if last_processed_id:
        query = query.filter('id > ?', (last_processed_id,))
    
    orders = query.all()
    last_id = None
    
    if not orders:
        return last_id
    
    # Transform and load data
    transformed_data = []
    for order in orders:
        # Apply transformations
        transformed_data.append({
            'order_id': order.id,
            'customer_id': order.customer_id,
            'year_month': order.order_date.strftime('%Y-%m'),
            'amount_category': 'High' if order.total_amount > 1000 else 'Medium' if order.total_amount > 500 else 'Low',
            'is_completed': order.status == 'completed',
            'processed_at': datetime.now()
        })
        last_id = order.id
    
    # Batch insert transformed data
    OrderAnalytics.insert_many(transformed_data)
    
    return last_id
```

## Data Cleansing and Enrichment

### Data Cleansing

Use ActiveRecord to identify and clean problematic data:

```python
def clean_customer_data():
    """Clean customer data by fixing common issues"""
    # Find and fix invalid email addresses
    invalid_emails = Customer.query()\
        .filter('email NOT LIKE "%@%.%"')\
        .all()
    
    for customer in invalid_emails:
        print(f"Fixing invalid email for customer {customer.id}: {customer.email}")
        # Apply a fix or mark for review
        if '@' not in customer.email:
            customer.email = f"{customer.email}@unknown.com"
        customer.needs_verification = True
        customer.save()
    
    # Standardize phone numbers
    customers_with_phones = Customer.query()\
        .filter('phone IS NOT NULL')\
        .all()
    
    for customer in customers_with_phones:
        # Remove non-numeric characters
        cleaned_phone = ''.join(c for c in customer.phone if c.isdigit())
        if cleaned_phone != customer.phone:
            print(f"Standardizing phone for customer {customer.id}: {customer.phone} -> {cleaned_phone}")
            customer.phone = cleaned_phone
            customer.save()
```

### Data Enrichment

Enrich data by combining information from multiple sources:

```python
def enrich_product_data():
    """Enrich product data with additional information"""
    products = Product.query().all()
    
    for product in products:
        # Get sales statistics
        sales_stats = OrderItem.query()\
            .filter('product_id = ?', (product.id,))\
            .select_expr(FunctionExpression('COUNT', 'id', alias='sales_count'))\
            .select_expr(FunctionExpression('SUM', 'quantity', alias='units_sold'))\
            .select_expr(FunctionExpression('AVG', 'price', alias='avg_sale_price'))\
            .aggregate()[0]
        
        # Get customer reviews
        avg_rating = Review.query()\
            .filter('product_id = ?', (product.id,))\
            .select_expr(FunctionExpression('AVG', 'rating', alias='avg_rating'))\
            .select_expr(FunctionExpression('COUNT', 'id', alias='review_count'))\
            .aggregate()[0]
        
        # Update product with enriched data
        product.sales_count = sales_stats['sales_count']
        product.units_sold = sales_stats['units_sold']
        product.avg_sale_price = sales_stats['avg_sale_price']
        product.avg_rating = avg_rating['avg_rating'] or 0
        product.review_count = avg_rating['review_count']
        product.save()
```

## Integration with Data Science Tools

### Pandas Integration

Seamlessly integrate ActiveRecord with pandas for advanced data manipulation:

```python
import pandas as pd

# Query data with ActiveRecord and convert to pandas DataFrame
order_data = Order.query()\
    .select('id', 'customer_id', 'order_date', 'total_amount', 'status')\
    .filter('order_date >= ?', (datetime(2023, 1, 1),))\
    .all()

# Convert to DataFrame
df = pd.DataFrame([order.__dict__ for order in order_data])

# Perform pandas transformations
df['month'] = df['order_date'].dt.month
df['day_of_week'] = df['order_date'].dt.dayofweek
df['is_weekend'] = df['day_of_week'].isin([5, 6])
df['amount_category'] = pd.cut(df['total_amount'], 
                              bins=[0, 100, 500, 1000, float('inf')],
                              labels=['Low', 'Medium', 'High', 'Premium'])

# Analyze with pandas
monthly_stats = df.groupby('month').agg({
    'total_amount': ['sum', 'mean', 'count'],
    'is_weekend': 'mean'  # Proportion of weekend orders
})

# Write transformed data back to database
transformed_records = df.to_dict('records')
OrderAnalytics.insert_many(transformed_records)
```

### Machine Learning Preparation

Prepare data for machine learning models:

```python
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# Extract data for predictive modeling
customer_data = Customer.query()\
    .select('id', 'age', 'gender', 'location', 'signup_source', 'lifetime_value')\
    .join('LEFT JOIN orders ON customers.id = orders.customer_id')\
    .select('COUNT(orders.id) as order_count')\
    .select('AVG(orders.total_amount) as avg_order_value')\
    .select('MAX(orders.order_date) as last_order_date')\
    .select('DATEDIFF(NOW(), MAX(orders.order_date)) as days_since_last_order')\
    .group_by('customers.id', 'customers.age', 'customers.gender', 
              'customers.location', 'customers.signup_source', 'customers.lifetime_value')\
    .having('COUNT(orders.id) > 0')\
    .aggregate()

# Convert to DataFrame
df = pd.DataFrame(customer_data)

# Define target variable (e.g., high-value customer prediction)
df['is_high_value'] = df['lifetime_value'] > 1000

# Define feature preprocessing
numeric_features = ['age', 'order_count', 'avg_order_value', 'days_since_last_order']
categorical_features = ['gender', 'location', 'signup_source']

preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
    ])

# Create and train model
X = df.drop(['is_high_value', 'id', 'lifetime_value', 'last_order_date'], axis=1)
y = df['is_high_value']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier())
])

model.fit(X_train, y_train)
```

## Best Practices for Data Transformation

### Performance Optimization

1. **Push Transformations to the Database**: When possible, perform transformations in the database using SQL expressions rather than in Python code.

2. **Use Batch Processing**: For large datasets, process data in batches to avoid memory issues.

3. **Consider Materialized Views**: For complex, frequently-used transformations, consider using database materialized views.

4. **Index Appropriately**: Ensure that columns used in filtering and joining are properly indexed.

### Data Quality and Validation

1. **Validate Transformed Data**: Implement validation checks to ensure transformed data meets expected criteria:

```python
def validate_transformed_data(data):
    """Validate transformed data before loading"""
    validation_errors = []
    
    for i, record in enumerate(data):
        # Check for required fields
        if 'customer_id' not in record or not record['customer_id']:
            validation_errors.append(f"Record {i}: Missing customer_id")
        
        # Validate numeric fields
        if 'lifetime_days' in record and (not isinstance(record['lifetime_days'], (int, float)) or record['lifetime_days'] < 0):
            validation_errors.append(f"Record {i}: Invalid lifetime_days value: {record['lifetime_days']}")
        
        # Validate categorical fields
        if 'segment' in record and record['segment'] not in ['High Value', 'Regular', 'New']:
            validation_errors.append(f"Record {i}: Invalid segment value: {record['segment']}")
    
    return validation_errors
```

2. **Log Transformation Issues**: Maintain detailed logs of transformation processes:

```python
import logging

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   filename='data_transformation.log')

def transform_with_logging(source_data):
    transformed_data = []
    for i, record in enumerate(source_data):
        try:
            # Apply transformations
            transformed_record = apply_transformations(record)
            transformed_data.append(transformed_record)
        except Exception as e:
            logging.error(f"Error transforming record {i}: {str(e)}")
            logging.debug(f"Problematic record: {record}")
    
    return transformed_data
```

## Conclusion

rhosocial ActiveRecord provides powerful capabilities for data transformation processing in data analysis applications. By leveraging its query building features, expression support, and integration with Python's data science ecosystem, you can implement sophisticated data transformation workflows without writing complex SQL.

Whether you're performing simple column transformations, complex ETL processes, or preparing data for machine learning models, ActiveRecord's intuitive API and performance optimization features make it an excellent choice for data transformation tasks. The ability to push transformations to the database level while maintaining a clean, Pythonic interface provides both performance and developer productivity benefits.