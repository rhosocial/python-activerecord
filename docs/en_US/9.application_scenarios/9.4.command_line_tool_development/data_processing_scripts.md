# Data Processing Scripts

This document explores how to leverage rhosocial ActiveRecord for building efficient data processing scripts in command-line environments.

## Introduction

Data processing scripts are essential tools for automating routine data operations, transformations, and analyses. rhosocial ActiveRecord provides an elegant and powerful ORM framework that simplifies database interactions in these scripts, allowing developers to focus on business logic rather than database connectivity details.

## Common Use Cases

### Data Cleaning and Normalization

ActiveRecord models can be used to implement data cleaning and normalization processes:

```python
import sys
from rhosocial.activerecord import ActiveRecord, Field
from rhosocial.activerecord.backend import SQLiteBackend

# Define your model
class UserData(ActiveRecord):
    table_name = 'user_data'
    name = Field(str)
    email = Field(str)
    
    def normalize_email(self):
        if self.email:
            self.email = self.email.lower().strip()
        return self

# Setup connection
db = SQLiteBackend('data.sqlite')
UserData.connect(db)

# Process all records
def normalize_all_emails():
    count = 0
    for user in UserData.find_all():
        user.normalize_email()
        if user.save():
            count += 1
    print(f"Normalized {count} email addresses")

if __name__ == '__main__':
    normalize_all_emails()
```

### Data Import from External Sources

Importing data from CSV, JSON, or other formats into your database:

```python
import csv
import sys
from rhosocial.activerecord import ActiveRecord, Field
from rhosocial.activerecord.backend import SQLiteBackend

class Product(ActiveRecord):
    table_name = 'products'
    code = Field(str)
    name = Field(str)
    price = Field(float)
    category = Field(str)

# Setup connection
db = SQLiteBackend('inventory.sqlite')
Product.connect(db)

def import_products_from_csv(filename):
    success_count = 0
    error_count = 0
    
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Use transaction for better performance and data integrity
        with Product.transaction():
            for row in reader:
                try:
                    product = Product()
                    product.code = row['product_code']
                    product.name = row['product_name']
                    product.price = float(row['price'])
                    product.category = row['category']
                    
                    if product.save():
                        success_count += 1
                    else:
                        error_count += 1
                        print(f"Error saving product {row['product_code']}: {product.errors}")
                except Exception as e:
                    error_count += 1
                    print(f"Error processing row: {e}")
    
    print(f"Import completed: {success_count} products imported, {error_count} errors")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python import_products.py <csv_filename>")
        sys.exit(1)
    
    import_products_from_csv(sys.argv[1])
```

### Data Export and Reporting

Generating reports or exporting data to various formats:

```python
import csv
import json
import sys
from rhosocial.activerecord import ActiveRecord, Field
from rhosocial.activerecord.backend import SQLiteBackend

class SalesRecord(ActiveRecord):
    table_name = 'sales'
    date = Field(str)
    product_id = Field(int)
    quantity = Field(int)
    amount = Field(float)
    region = Field(str)

# Setup connection
db = SQLiteBackend('sales.sqlite')
SalesRecord.connect(db)

def generate_sales_report(start_date, end_date, output_format='csv'):
    # Query data with ActiveRecord
    sales = SalesRecord.find_all(
        conditions=["date >= ? AND date <= ?", start_date, end_date],
        order="region, date"
    )
    
    # Process and output based on format
    if output_format == 'csv':
        with open('sales_report.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Date', 'Product ID', 'Quantity', 'Amount', 'Region'])
            
            for sale in sales:
                writer.writerow([sale.date, sale.product_id, sale.quantity, sale.amount, sale.region])
                
        print(f"CSV report generated: sales_report.csv")
    
    elif output_format == 'json':
        data = [{
            'date': sale.date,
            'product_id': sale.product_id,
            'quantity': sale.quantity,
            'amount': sale.amount,
            'region': sale.region
        } for sale in sales]
        
        with open('sales_report.json', 'w') as jsonfile:
            json.dump(data, jsonfile, indent=2)
            
        print(f"JSON report generated: sales_report.json")
    
    else:
        print(f"Unsupported output format: {output_format}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python sales_report.py <start_date> <end_date> [format]")
        print("Format options: csv, json (default: csv)")
        sys.exit(1)
    
    start_date = sys.argv[1]
    end_date = sys.argv[2]
    output_format = sys.argv[3] if len(sys.argv) > 3 else 'csv'
    
    generate_sales_report(start_date, end_date, output_format)
```

## Best Practices

### Command-line Argument Handling

For robust command-line scripts, use proper argument parsing:

```python
import argparse
from rhosocial.activerecord import ActiveRecord, Field

def setup_argument_parser():
    parser = argparse.ArgumentParser(description='Process data with ActiveRecord')
    parser.add_argument('--action', choices=['import', 'export', 'update'], required=True,
                        help='Action to perform')
    parser.add_argument('--file', help='Input/output file path')
    parser.add_argument('--format', choices=['csv', 'json', 'xml'], default='csv',
                        help='File format (default: csv)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    return parser

def main():
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Process based on arguments
    if args.action == 'import':
        if not args.file:
            print("Error: --file is required for import action")
            return 1
        # Import logic here
    elif args.action == 'export':
        # Export logic here
        pass
    # ...

if __name__ == '__main__':
    main()
```

### Error Handling and Logging

Implement proper error handling and logging for production scripts:

```python
import logging
import sys
from rhosocial.activerecord import ActiveRecord, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data_processor.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("data_processor")

def process_data():
    try:
        # Database operations with ActiveRecord
        logger.info("Starting data processing")
        # ...
        logger.info("Data processing completed successfully")
    except Exception as e:
        logger.error(f"Error during data processing: {e}", exc_info=True)
        return False
    return True

if __name__ == '__main__':
    success = process_data()
    sys.exit(0 if success else 1)
```

### Progress Reporting for Long-running Tasks

For scripts that process large datasets, implement progress reporting:

```python
import sys
import time
from rhosocial.activerecord import ActiveRecord, Field

class LargeDataset(ActiveRecord):
    # Model definition
    pass

def process_large_dataset():
    total_records = LargeDataset.count()
    processed = 0
    
    print(f"Processing {total_records} records...")
    
    for record in LargeDataset.find_each(batch_size=100):
        # Process record
        # ...
        
        processed += 1
        if processed % 100 == 0:
            progress = (processed / total_records) * 100
            print(f"Progress: {progress:.1f}% ({processed}/{total_records})")
    
    print("Processing completed!")

if __name__ == '__main__':
    process_large_dataset()
```

## Advanced Techniques

### Parallel Processing

For CPU-bound tasks, leverage parallel processing:

```python
import multiprocessing
from rhosocial.activerecord import ActiveRecord, Field

class DataItem(ActiveRecord):
    # Model definition
    pass

def process_chunk(chunk_ids):
    results = []
    for id in chunk_ids:
        item = DataItem.find_by_id(id)
        if item:
            # Process item
            result = {'id': item.id, 'processed_value': item.value * 2}
            results.append(result)
    return results

def parallel_processing():
    # Get all IDs to process
    all_ids = [item.id for item in DataItem.find_all(select='id')]
    
    # Split into chunks for parallel processing
    cpu_count = multiprocessing.cpu_count()
    chunk_size = max(1, len(all_ids) // cpu_count)
    chunks = [all_ids[i:i + chunk_size] for i in range(0, len(all_ids), chunk_size)]
    
    # Process in parallel
    with multiprocessing.Pool(processes=cpu_count) as pool:
        all_results = pool.map(process_chunk, chunks)
    
    # Flatten results
    results = [item for sublist in all_results for item in sublist]
    print(f"Processed {len(results)} items using {cpu_count} processes")
    return results

if __name__ == '__main__':
    parallel_processing()
```

### Scheduled Execution

For scripts that need to run on a schedule, consider using tools like `cron` (Linux/macOS) or Task Scheduler (Windows), or implement scheduling within your script:

```python
import schedule
import time
from rhosocial.activerecord import ActiveRecord, Field

def daily_data_cleanup():
    # ActiveRecord operations for daily cleanup
    print(f"Running daily cleanup at {time.strftime('%Y-%m-%d %H:%M:%S')}")

def weekly_report_generation():
    # ActiveRecord operations for weekly reporting
    print(f"Generating weekly report at {time.strftime('%Y-%m-%d %H:%M:%S')}")

def setup_schedule():
    # Schedule daily cleanup at 1:00 AM
    schedule.every().day.at("01:00").do(daily_data_cleanup)
    
    # Schedule weekly report on Monday at 7:00 AM
    schedule.every().monday.at("07:00").do(weekly_report_generation)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == '__main__':
    setup_schedule()
```

## Conclusion

rhosocial ActiveRecord provides a powerful foundation for building data processing scripts that are maintainable, efficient, and robust. By leveraging ActiveRecord's ORM capabilities, developers can focus on implementing business logic rather than dealing with low-level database operations.

The examples in this document demonstrate common patterns and best practices for command-line data processing tools, but ActiveRecord's flexibility allows for many more specialized applications. As you develop your own scripts, remember to take advantage of ActiveRecord's transaction support, batch processing capabilities, and query optimization features to ensure your tools perform well even with large datasets.