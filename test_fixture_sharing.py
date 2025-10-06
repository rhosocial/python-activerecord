#!/usr/bin/env python3
"""
Test script to verify that our fixture group implementation correctly shares
backend connections among models in the same fixture group.
"""

import os
os.environ.setdefault('TESTSUITE_PROVIDER_REGISTRY', 'tests.providers.registry:provider_registry')

from tests.providers.query import QueryProvider
from tests.providers.scenarios import get_enabled_scenarios

def test_fixture_group_sharing():
    """Test that fixture groups correctly share backend connections"""
    print("Testing fixture group backend sharing...")
    
    provider = QueryProvider()
    scenarios = get_enabled_scenarios()
    
    if not scenarios:
        print("No scenarios found!")
        return False
    
    scenario_name = list(scenarios.keys())[0]
    print(f"Using scenario: {scenario_name}")
    
    # Test order fixtures group
    print("\n1. Testing order fixtures...")
    User, Order, OrderItem = provider.setup_order_fixtures(scenario_name)
    
    # Verify all models have the same backend instance
    user_backend = User.__backend__
    order_backend = Order.__backend__
    order_item_backend = OrderItem.__backend__
    
    print(f"   User backend: {user_backend}")
    print(f"   Order backend: {order_backend}")
    print(f"   OrderItem backend: {order_item_backend}")
    
    # Check if all backends are the same instance
    if user_backend is order_backend is order_item_backend:
        print("   [PASS] All models share the same backend instance")
    else:
        print("   [FAIL] Models have different backend instances!")
        return False
    
    # Test that we can create records in one model and query from another
    print("\n2. Testing cross-model operations...")
    
    # Create a user
    user = User(username='testuser', email='test@example.com', age=30)
    user.save()
    print(f"   Created user with ID: {user.id}")
    
    # Create an order for that user
    order = Order(user_id=user.id, order_number='TEST-001', total_amount=100.00)
    order.save()
    print(f"   Created order with ID: {order.id}")
    
    # Query the order from database
    found_order = Order.find_one({'id': order.id})
    if found_order:
        print(f"   Found order: {found_order.order_number}")
        print("\n[PASS] All tests passed!")
        return True
    else:
        print("   [FAIL] Could not find order!")
        return False

if __name__ == "__main__":
    try:
        success = test_fixture_group_sharing()
        if success:
            print("\n*** SUCCESS: Fixture group implementation is working correctly! ***")
        else:
            print("\n*** FAILURE: There were issues with the implementation. ***")
    except Exception as e:
        print(f"\n*** ERROR: {e} ***")
        import traceback
        traceback.print_exc()