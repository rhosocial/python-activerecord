# CRUD Operations

This section covers the fundamental Create, Read, Update, and Delete (CRUD) operations in rhosocial ActiveRecord, as well as batch operations and transaction basics.

## Contents

- [Create, Read, Update, Delete](create_read_update_delete.md) - Basic operations for individual records
  - Creating records
  - Reading records
  - Updating records
  - Deleting records
  - Refreshing records
  - Checking record status

- [Batch Operations](batch_operations.md) - Efficiently working with multiple records
  - Batch creation
  - Batch updates
  - Batch deletes
  - Performance optimization for batch operations

- [Transaction Basics](transaction_basics.md) - Ensuring data integrity
  - Understanding transactions
  - Basic transaction usage
  - Error handling in transactions
  - Nested transactions
  - Transaction isolation levels
  - Best practices

## Overview

CRUD operations form the foundation of database interactions in your applications. rhosocial ActiveRecord provides an intuitive and powerful API for performing these operations, allowing you to focus on your application logic rather than writing complex SQL queries.

The batch operations section covers techniques for efficiently working with multiple records at once, which can significantly improve performance when dealing with large datasets.

The transaction basics section explains how to use transactions to ensure data integrity, even in the face of errors or concurrent access.