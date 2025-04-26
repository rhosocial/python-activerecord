# 数据处理脚本

本文档探讨如何在命令行环境中利用rhosocial ActiveRecord构建高效的数据处理脚本。

## 引言

数据处理脚本是自动化常规数据操作、转换和分析的重要工具。rhosocial ActiveRecord提供了一个优雅而强大的ORM框架，简化了这些脚本中的数据库交互，使开发人员能够专注于业务逻辑而非数据库连接细节。

## 常见用例

### 数据清洗和规范化

ActiveRecord模型可用于实现数据清洗和规范化流程：

```python
import sys
from rhosocial.activerecord import ActiveRecord, Field
from rhosocial.activerecord.backend import SQLiteBackend

# 定义模型
class UserData(ActiveRecord):
    table_name = 'user_data'
    name = Field(str)
    email = Field(str)
    
    def normalize_email(self):
        if self.email:
            self.email = self.email.lower().strip()
        return self

# 设置连接
db = SQLiteBackend('data.sqlite')
UserData.connect(db)

# 处理所有记录
def normalize_all_emails():
    count = 0
    for user in UserData.find_all():
        user.normalize_email()
        if user.save():
            count += 1
    print(f"已规范化 {count} 个电子邮件地址")

if __name__ == '__main__':
    normalize_all_emails()
```

### 从外部源导入数据

从CSV、JSON或其他格式导入数据到数据库：

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

# 设置连接
db = SQLiteBackend('inventory.sqlite')
Product.connect(db)

def import_products_from_csv(filename):
    success_count = 0
    error_count = 0
    
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # 使用事务以提高性能和确保数据完整性
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
                        print(f"保存产品 {row['product_code']} 时出错: {product.errors}")
                except Exception as e:
                    error_count += 1
                    print(f"处理行时出错: {e}")
    
    print(f"导入完成: 已导入 {success_count} 个产品, {error_count} 个错误")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("用法: python import_products.py <csv文件名>")
        sys.exit(1)
    
    import_products_from_csv(sys.argv[1])
```

### 数据导出和报表生成

生成报表或将数据导出为各种格式：

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

# 设置连接
db = SQLiteBackend('sales.sqlite')
SalesRecord.connect(db)

def generate_sales_report(start_date, end_date, output_format='csv'):
    # 使用ActiveRecord查询数据
    sales = SalesRecord.find_all(
        conditions=["date >= ? AND date <= ?", start_date, end_date],
        order="region, date"
    )
    
    # 根据格式处理和输出
    if output_format == 'csv':
        with open('sales_report.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['日期', '产品ID', '数量', '金额', '地区'])
            
            for sale in sales:
                writer.writerow([sale.date, sale.product_id, sale.quantity, sale.amount, sale.region])
                
        print(f"CSV报表已生成: sales_report.csv")
    
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
            
        print(f"JSON报表已生成: sales_report.json")
    
    else:
        print(f"不支持的输出格式: {output_format}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python sales_report.py <开始日期> <结束日期> [格式]")
        print("格式选项: csv, json (默认: csv)")
        sys.exit(1)
    
    start_date = sys.argv[1]
    end_date = sys.argv[2]
    output_format = sys.argv[3] if len(sys.argv) > 3 else 'csv'
    
    generate_sales_report(start_date, end_date, output_format)
```

## 最佳实践

### 命令行参数处理

对于健壮的命令行脚本，使用适当的参数解析：

```python
import argparse
from rhosocial.activerecord import ActiveRecord, Field

def setup_argument_parser():
    parser = argparse.ArgumentParser(description='使用ActiveRecord处理数据')
    parser.add_argument('--action', choices=['import', 'export', 'update'], required=True,
                        help='要执行的操作')
    parser.add_argument('--file', help='输入/输出文件路径')
    parser.add_argument('--format', choices=['csv', 'json', 'xml'], default='csv',
                        help='文件格式 (默认: csv)')
    parser.add_argument('--verbose', action='store_true', help='启用详细输出')
    return parser

def main():
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # 根据参数处理
    if args.action == 'import':
        if not args.file:
            print("错误: 导入操作需要 --file 参数")
            return 1
        # 导入逻辑
    elif args.action == 'export':
        # 导出逻辑
        pass
    # ...

if __name__ == '__main__':
    main()
```

### 错误处理和日志记录

为生产脚本实现适当的错误处理和日志记录：

```python
import logging
import sys
from rhosocial.activerecord import ActiveRecord, Field

# 配置日志
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
        # 使用ActiveRecord进行数据库操作
        logger.info("开始数据处理")
        # ...
        logger.info("数据处理成功完成")
    except Exception as e:
        logger.error(f"数据处理过程中出错: {e}", exc_info=True)
        return False
    return True

if __name__ == '__main__':
    success = process_data()
    sys.exit(0 if success else 1)
```

### 长时间运行任务的进度报告

对于处理大型数据集的脚本，实现进度报告：

```python
import sys
import time
from rhosocial.activerecord import ActiveRecord, Field

class LargeDataset(ActiveRecord):
    # 模型定义
    pass

def process_large_dataset():
    total_records = LargeDataset.count()
    processed = 0
    
    print(f"正在处理 {total_records} 条记录...")
    
    for record in LargeDataset.find_each(batch_size=100):
        # 处理记录
        # ...
        
        processed += 1
        if processed % 100 == 0:
            progress = (processed / total_records) * 100
            print(f"进度: {progress:.1f}% ({processed}/{total_records})")
    
    print("处理完成!")

if __name__ == '__main__':
    process_large_dataset()
```

## 高级技术

### 并行处理

对于CPU密集型任务，利用并行处理：

```python
import multiprocessing
from rhosocial.activerecord import ActiveRecord, Field

class DataItem(ActiveRecord):
    # 模型定义
    pass

def process_chunk(chunk_ids):
    results = []
    for id in chunk_ids:
        item = DataItem.find_by_id(id)
        if item:
            # 处理项目
            result = {'id': item.id, 'processed_value': item.value * 2}
            results.append(result)
    return results

def parallel_processing():
    # 获取所有要处理的ID
    all_ids = [item.id for item in DataItem.find_all(select='id')]
    
    # 分割成块以进行并行处理
    cpu_count = multiprocessing.cpu_count()
    chunk_size = max(1, len(all_ids) // cpu_count)
    chunks = [all_ids[i:i + chunk_size] for i in range(0, len(all_ids), chunk_size)]
    
    # 并行处理
    with multiprocessing.Pool(processes=cpu_count) as pool:
        all_results = pool.map(process_chunk, chunks)
    
    # 扁平化结果
    results = [item for sublist in all_results for item in sublist]
    print(f"使用 {cpu_count} 个进程处理了 {len(results)} 个项目")
    return results

if __name__ == '__main__':
    parallel_processing()
```

### 计划执行

对于需要按计划运行的脚本，考虑使用`cron`（Linux/macOS）或任务计划程序（Windows）等工具，或在脚本中实现调度：

```python
import schedule
import time
from rhosocial.activerecord import ActiveRecord, Field

def daily_data_cleanup():
    # 每日清理的ActiveRecord操作
    print(f"在 {time.strftime('%Y-%m-%d %H:%M:%S')} 运行每日清理")

def weekly_report_generation():
    # 每周报告的ActiveRecord操作
    print(f"在 {time.strftime('%Y-%m-%d %H:%M:%S')} 生成每周报告")

def setup_schedule():
    # 安排每天凌晨1:00进行清理
    schedule.every().day.at("01:00").do(daily_data_cleanup)
    
    # 安排每周一上午7:00生成报告
    schedule.every().monday.at("07:00").do(weekly_report_generation)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

if __name__ == '__main__':
    setup_schedule()
```

## 结论

rhosocial ActiveRecord为构建可维护、高效和健壮的数据处理脚本提供了强大的基础。通过利用ActiveRecord的ORM功能，开发人员可以专注于实现业务逻辑，而不必处理低级数据库操作。

本文档中的示例演示了命令行数据处理工具的常见模式和最佳实践，但ActiveRecord的灵活性允许更多专业应用。在开发自己的脚本时，请记住利用ActiveRecord的事务支持、批处理功能和查询优化功能，以确保您的工具即使在处理大型数据集时也能良好运行。