# src/rhosocial/__init__.py
# Extend the namespace path to support backend implementations from separate packages
# This is crucial for the distributed backend architecture where each database backend
# (mysql, postgresql, etc.) can be installed independently
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
