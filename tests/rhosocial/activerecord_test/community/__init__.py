"""Community Example Test Module

Provides test cases for community-style applications including
users, articles, comments, friendships, and complex queries.
"""

# Import test modules
try:
    from . import test_users
except ImportError:
    pass

try:
    from . import test_articles
except ImportError:
    pass

try:
    from . import test_comments
except ImportError:
    pass

try:
    from . import test_friendships
except ImportError:
    pass

try:
    from . import test_queries
except ImportError:
    pass

__all__ = [
    'test_users',
    'test_articles',
    'test_comments',
    'test_friendships',
    'test_queries',
]