# Cross-database Transaction Handling

> **⚠️ IMPORTANT NOTE:** Cross-database transactions described in this document are essentially nested transactions initiated by two separate ActiveRecord classes and **cannot achieve true cross-database atomicity**. The implementation strategies described here are workarounds for this fundamental limitation and may undergo significant changes in future releases.

This document explains how to handle transactions that span multiple databases in rhosocial ActiveRecord, including the challenges, available approaches, and best practices.

## Understanding Cross-database Transactions

A cross-database transaction is an operation that needs to update data in multiple database systems while maintaining ACID properties (Atomicity, Consistency, Isolation, Durability) across all of them. This is challenging because most database systems only support transactions within their own boundaries.

## Challenges of Cross-database Transactions

### 1. Lack of Native Support

Most database systems do not natively support distributed transactions across different database instances or different database types. Each database manages its own transaction state independently.

### 2. Two-Phase Commit Limitations

The traditional two-phase commit (2PC) protocol for distributed transactions is:
- Not supported by all database systems
- Often has performance implications
- May not work across different database types

### 3. Consistency Challenges

Ensuring data consistency across multiple databases requires careful planning and implementation, especially when databases have different transaction isolation levels or capabilities.

## Approaches to Cross-database Transactions in rhosocial ActiveRecord

### 1. Best-Effort Transactions

In this approach, you attempt to perform operations on multiple databases and handle failures by implementing compensating actions.

```python
from rhosocial.activerecord import ConnectionManager, ActiveRecord

def transfer_funds(from_account_id, to_account_id, amount):
    success = False
    
    # Start transaction on first database
    with ConnectionManager.using('bank_db_1').transaction():
        # Update sender account in first database
        from_account = Account.find(from_account_id)
        if from_account.balance < amount:
            raise ValueError("Insufficient funds")
        
        from_account.balance -= amount
        from_account.save()
        
        try:
            # Start transaction on second database
            with ConnectionManager.using('bank_db_2').transaction():
                # Update receiver account in second database
                to_account = Account.find(to_account_id)
                to_account.balance += amount
                to_account.save()
                
                # If we get here, both transactions succeeded
                success = True
        except Exception as e:
            # Second transaction failed, first will be rolled back automatically
            # when we re-raise the exception
            raise e
    
    return success
```

This approach works well for simple cases but doesn't guarantee atomicity across both databases if the second transaction succeeds but there's a failure before the method returns.

### 2. Saga Pattern

The Saga pattern manages a sequence of local transactions, with compensating transactions to undo changes if any step fails.

```python
class Saga:
    def __init__(self):
        self.actions = []
        self.compensations = []
        self.executed_actions = []
    
    def add_step(self, action, compensation):
        self.actions.append(action)
        self.compensations.append(compensation)
    
    def execute(self):
        try:
            for action in self.actions:
                action()
                self.executed_actions.append(action)
            return True
        except Exception as e:
            # Execute compensating transactions in reverse order
            for i in range(len(self.executed_actions) - 1, -1, -1):
                try:
                    self.compensations[i]()
                except Exception as comp_error:
                    # Log compensation error but continue with other compensations
                    import logging
                    logging.error(f"Compensation failed: {comp_error}")
            raise e

# Example usage for a cross-database operation
def transfer_funds_saga(from_account_id, to_account_id, amount):
    saga = Saga()
    
    # Define action and compensation for debiting the sender's account
    def debit_sender():
        with ConnectionManager.using('bank_db_1').transaction():
            from_account = Account.find(from_account_id)
            if from_account.balance < amount:
                raise ValueError("Insufficient funds")
            from_account.balance -= amount
            from_account.save()
    
    def credit_sender():
        with ConnectionManager.using('bank_db_1').transaction():
            from_account = Account.find(from_account_id)
            from_account.balance += amount
            from_account.save()
    
    # Define action and compensation for crediting the receiver's account
    def credit_receiver():
        with ConnectionManager.using('bank_db_2').transaction():
            to_account = Account.find(to_account_id)
            to_account.balance += amount
            to_account.save()
    
    def debit_receiver():
        with ConnectionManager.using('bank_db_2').transaction():
            to_account = Account.find(to_account_id)
            to_account.balance -= amount
            to_account.save()
    
    # Add steps to the saga
    saga.add_step(debit_sender, credit_sender)
    saga.add_step(credit_receiver, debit_receiver)
    
    # Execute the saga
    return saga.execute()
```

### 3. Two-Phase Commit (When Available)

If your databases support distributed transactions through XA or similar protocols, you can use a two-phase commit approach:

```python
# Note: This is a simplified example and requires database support for XA transactions
from rhosocial.activerecord import ConnectionManager, ActiveRecord
import uuid

def two_phase_commit_transfer(from_account_id, to_account_id, amount):
    # Generate a unique transaction ID
    xid = uuid.uuid4().hex
    
    # Get connections
    conn1 = ConnectionManager.get('bank_db_1').raw_connection()
    conn2 = ConnectionManager.get('bank_db_2').raw_connection()
    
    try:
        # Phase 1: Prepare
        conn1.tpc_begin(xid)
        cursor1 = conn1.cursor()
        cursor1.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", (amount, from_account_id))
        conn1.tpc_prepare()
        
        conn2.tpc_begin(xid)
        cursor2 = conn2.cursor()
        cursor2.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (amount, to_account_id))
        conn2.tpc_prepare()
        
        # Phase 2: Commit
        conn1.tpc_commit()
        conn2.tpc_commit()
        
        return True
    except Exception as e:
        # Rollback if anything fails
        try:
            conn1.tpc_rollback()
        except:
            pass
        
        try:
            conn2.tpc_rollback()
        except:
            pass
        
        raise e
```

### 4. Event-Driven Approach

This approach uses events and eventual consistency to manage cross-database operations:

```python
from rhosocial.activerecord import ConnectionManager, ActiveRecord
import json
import redis

# Configure Redis for message queue
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def transfer_funds_event_driven(from_account_id, to_account_id, amount):
    # Generate a unique transfer ID
    transfer_id = uuid.uuid4().hex
    
    # Step 1: Record the transfer request
    with ConnectionManager.using('bank_db_1').transaction():
        # Create a transfer record
        transfer = Transfer(
            id=transfer_id,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            status='pending'
        )
        transfer.save()
        
        # Deduct from sender's account
        from_account = Account.find(from_account_id)
        if from_account.balance < amount:
            raise ValueError("Insufficient funds")
        
        from_account.balance -= amount
        from_account.save()
    
    # Step 2: Publish event to complete the transfer
    event_data = {
        'transfer_id': transfer_id,
        'from_account_id': from_account_id,
        'to_account_id': to_account_id,
        'amount': amount
    }
    redis_client.publish('fund_transfers', json.dumps(event_data))
    
    return transfer_id

# Consumer process to handle the second part of the transaction
def process_fund_transfers():
    pubsub = redis_client.pubsub()
    pubsub.subscribe('fund_transfers')
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                event = json.loads(message['data'])
                complete_transfer(event)
            except Exception as e:
                import logging
                logging.error(f"Failed to process transfer: {e}")

def complete_transfer(event):
    transfer_id = event['transfer_id']
    to_account_id = event['to_account_id']
    amount = event['amount']
    
    try:
        # Update receiver's account in the second database
        with ConnectionManager.using('bank_db_2').transaction():
            to_account = Account.find(to_account_id)
            to_account.balance += amount
            to_account.save()
        
        # Mark transfer as completed in the first database
        with ConnectionManager.using('bank_db_1').transaction():
            transfer = Transfer.find(transfer_id)
            transfer.status = 'completed'
            transfer.save()
    except Exception as e:
        # Mark transfer as failed and schedule compensation
        with ConnectionManager.using('bank_db_1').transaction():
            transfer = Transfer.find(transfer_id)
            transfer.status = 'failed'
            transfer.error_message = str(e)
            transfer.save()
            
            # Schedule compensation to refund the sender
            redis_client.publish('transfer_compensations', json.dumps({
                'transfer_id': transfer_id,
                'from_account_id': event['from_account_id'],
                'amount': amount
            }))

# Compensation handler
def process_transfer_compensations():
    pubsub = redis_client.pubsub()
    pubsub.subscribe('transfer_compensations')
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                event = json.loads(message['data'])
                compensate_transfer(event)
            except Exception as e:
                import logging
                logging.error(f"Failed to process compensation: {e}")

def compensate_transfer(event):
    transfer_id = event['transfer_id']
    from_account_id = event['from_account_id']
    amount = event['amount']
    
    with ConnectionManager.using('bank_db_1').transaction():
        # Refund the sender's account
        from_account = Account.find(from_account_id)
        from_account.balance += amount
        from_account.save()
        
        # Update transfer status
        transfer = Transfer.find(transfer_id)
        transfer.status = 'compensated'
        transfer.save()
```

## Implementing a Transaction Coordinator

For more complex scenarios, you might implement a transaction coordinator that manages the state of distributed transactions:

```python
class TransactionCoordinator:
    def __init__(self):
        self.transaction_store = {}  # In production, use a persistent store
    
    def start_transaction(self, transaction_id=None):
        transaction_id = transaction_id or uuid.uuid4().hex
        self.transaction_store[transaction_id] = {
            'status': 'started',
            'participants': [],
            'start_time': datetime.datetime.now()
        }
        return transaction_id
    
    def register_participant(self, transaction_id, participant_id, prepare_action, commit_action, rollback_action):
        if transaction_id not in self.transaction_store:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        self.transaction_store[transaction_id]['participants'].append({
            'id': participant_id,
            'prepare_action': prepare_action,
            'commit_action': commit_action,
            'rollback_action': rollback_action,
            'status': 'registered'
        })
    
    def prepare(self, transaction_id):
        if transaction_id not in self.transaction_store:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        transaction = self.transaction_store[transaction_id]
        all_prepared = True
        
        for participant in transaction['participants']:
            try:
                participant['prepare_action']()
                participant['status'] = 'prepared'
            except Exception as e:
                participant['status'] = 'prepare_failed'
                participant['error'] = str(e)
                all_prepared = False
                break
        
        if all_prepared:
            transaction['status'] = 'prepared'
        else:
            transaction['status'] = 'prepare_failed'
            self.rollback(transaction_id)
        
        return all_prepared
    
    def commit(self, transaction_id):
        if transaction_id not in self.transaction_store:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        transaction = self.transaction_store[transaction_id]
        
        if transaction['status'] != 'prepared':
            raise ValueError(f"Transaction {transaction_id} is not prepared")
        
        all_committed = True
        
        for participant in transaction['participants']:
            if participant['status'] == 'prepared':
                try:
                    participant['commit_action']()
                    participant['status'] = 'committed'
                except Exception as e:
                    participant['status'] = 'commit_failed'
                    participant['error'] = str(e)
                    all_committed = False
        
        if all_committed:
            transaction['status'] = 'committed'
        else:
            transaction['status'] = 'partially_committed'
        
        return all_committed
    
    def rollback(self, transaction_id):
        if transaction_id not in self.transaction_store:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        transaction = self.transaction_store[transaction_id]
        
        for participant in transaction['participants']:
            if participant['status'] in ['prepared', 'committed']:
                try:
                    participant['rollback_action']()
                    participant['status'] = 'rolled_back'
                except Exception as e:
                    participant['status'] = 'rollback_failed'
                    participant['error'] = str(e)
        
        transaction['status'] = 'rolled_back'

# Example usage
def transfer_with_coordinator(from_account_id, to_account_id, amount):
    coordinator = TransactionCoordinator()
    transaction_id = coordinator.start_transaction()
    
    # Register first database operations
    def prepare_db1():
        with ConnectionManager.using('bank_db_1'):
            from_account = Account.find(from_account_id)
            if from_account.balance < amount:
                raise ValueError("Insufficient funds")
            # Just validate, don't update yet
    
    def commit_db1():
        with ConnectionManager.using('bank_db_1').transaction():
            from_account = Account.find(from_account_id)
            from_account.balance -= amount
            from_account.save()
    
    def rollback_db1():
        # No action needed for rollback before commit
        pass
    
    coordinator.register_participant(
        transaction_id, 'bank_db_1', prepare_db1, commit_db1, rollback_db1
    )
    
    # Register second database operations
    def prepare_db2():
        with ConnectionManager.using('bank_db_2'):
            to_account = Account.find(to_account_id)
            if not to_account:
                raise ValueError("Destination account not found")
            # Just validate, don't update yet
    
    def commit_db2():
        with ConnectionManager.using('bank_db_2').transaction():
            to_account = Account.find(to_account_id)
            to_account.balance += amount
            to_account.save()
    
    def rollback_db2():
        # No action needed for rollback before commit
        pass
    
    coordinator.register_participant(
        transaction_id, 'bank_db_2', prepare_db2, commit_db2, rollback_db2
    )
    
    # Execute the two-phase commit
    if coordinator.prepare(transaction_id):
        return coordinator.commit(transaction_id)
    else:
        return False
```

## Best Practices for Cross-database Transactions

### 1. Minimize Cross-database Operations

Whenever possible, design your data model to minimize the need for operations that span multiple databases.

### 2. Use Idempotent Operations

Design operations to be idempotent (can be safely retried) to handle partial failures and recovery scenarios.

### 3. Implement Proper Logging and Monitoring

Log all steps of cross-database transactions to help with debugging and recovery:

```python
import logging

class TransactionLogger:
    def __init__(self, transaction_id):
        self.transaction_id = transaction_id
        self.logger = logging.getLogger('transactions')
    
    def log_start(self, details=None):
        self.logger.info(f"Transaction {self.transaction_id} started. Details: {details}")
    
    def log_prepare(self, participant_id, success):
        status = "succeeded" if success else "failed"
        self.logger.info(f"Prepare for participant {participant_id} in transaction {self.transaction_id} {status}")
    
    def log_commit(self, participant_id, success):
        status = "succeeded" if success else "failed"
        self.logger.info(f"Commit for participant {participant_id} in transaction {self.transaction_id} {status}")
    
    def log_rollback(self, participant_id, success):
        status = "succeeded" if success else "failed"
        self.logger.info(f"Rollback for participant {participant_id} in transaction {self.transaction_id} {status}")
    
    def log_complete(self, status):
        self.logger.info(f"Transaction {self.transaction_id} completed with status: {status}")
```

### 4. Implement Recovery Mechanisms

Design systems to recover from failures, including processes to identify and resolve incomplete transactions:

```python
def recover_incomplete_transactions():
    # Find transactions that were started but not completed
    incomplete_transactions = Transaction.where("status IN ('started', 'prepared', 'partially_committed')")
    
    for transaction in incomplete_transactions:
        # Check how old the transaction is
        age = datetime.datetime.now() - transaction.created_at
        
        if age.total_seconds() > 3600:  # Older than 1 hour
            try:
                # Attempt to complete or roll back the transaction
                if transaction.status == 'prepared':
                    # Try to commit if all participants were prepared
                    complete_transaction(transaction.id)
                else:
                    # Otherwise roll back
                    rollback_transaction(transaction.id)
            except Exception as e:
                logging.error(f"Failed to recover transaction {transaction.id}: {e}")
```

### 5. Consider Using a Message Queue

For many scenarios, using a message queue for asynchronous processing can be more reliable than trying to implement true distributed transactions:

```python
def transfer_funds_with_queue(from_account_id, to_account_id, amount):
    # Generate a unique transfer ID
    transfer_id = uuid.uuid4().hex
    
    # Step 1: Deduct from sender's account and record the pending transfer
    with ConnectionManager.using('bank_db_1').transaction():
        from_account = Account.find(from_account_id)
        if from_account.balance < amount:
            raise ValueError("Insufficient funds")
        
        from_account.balance -= amount
        from_account.save()
        
        # Record the pending transfer
        transfer = Transfer(
            id=transfer_id,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            status='pending'
        )
        transfer.save()
    
    # Step 2: Queue the credit operation for the receiver's account
    redis_client.lpush('pending_credits', json.dumps({
        'transfer_id': transfer_id,
        'to_account_id': to_account_id,
        'amount': amount
    }))
    
    return transfer_id
```

## Conclusion

Handling transactions across multiple databases is challenging but can be managed with careful design and implementation. rhosocial ActiveRecord provides the tools needed to work with multiple databases, but the responsibility for ensuring data consistency across them falls to the application code.

By understanding the limitations of cross-database transactions and implementing appropriate patterns like sagas, event-driven approaches, or transaction coordinators, you can build reliable systems that maintain data integrity across multiple database systems.