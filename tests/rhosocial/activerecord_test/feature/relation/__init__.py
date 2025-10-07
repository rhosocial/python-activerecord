"""
Bridge tests for relation functionality.

This file imports and runs the tests from the testsuite for the relation feature.
"""
import pytest


# Import all tests from the testsuite relation feature
from rhosocial.activerecord.testsuite.feature.relation.test_base import TestRelationDescriptor
from rhosocial.activerecord.testsuite.feature.relation.test_cache import TestRelationCache
from rhosocial.activerecord.testsuite.feature.relation.test_descriptors import TestRelationDescriptors
from rhosocial.activerecord.testsuite.feature.relation.test_interfaces import TestRelationInterfaces
from rhosocial.activerecord.testsuite.feature.relation.test_nested_relationship_access import TestNestedRelationshipAccess


# The imports above bring in all the tests from the testsuite.
# These tests will run using the provider implementations defined in the local tests/ directory.