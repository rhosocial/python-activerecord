# hatch_build.py
"""Custom build hooks for different packaging modes.

This module provides build hooks to support different packaging modes:
- default: Only source code and essential files
- test: Include test package for dependent packages
- docs: Include documentation files
- dev: Include everything for development

IMPORTANT: Wheel files always contain default mode content regardless of build mode.
Only source distributions (sdist) vary based on the build mode.
"""

import os
from typing import Any, Dict

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl


class CustomBuildHook(BuildHookInterface):
    """Custom build hook to handle different packaging modes."""

    PLUGIN_NAME = "custom"

    def __init__(self, root: str, config: Dict[str, Any], build_config=None, metadata=None, directory: str = "",
                 target_name: str = "", app=None) -> None:
        super().__init__(root, config, build_config, metadata, directory, target_name, app)

    def initialize(self, version: str, build_data: Dict[str, Any]) -> None:
        """Initialize the build hook."""
        # Check if we're building with test mode
        build_mode = os.environ.get('HATCH_BUILD_MODE', 'default')

        # IMPORTANT: Wheel files should always use default mode
        # Only sdist should vary based on build mode
        if self.target_name == 'wheel':
            # Force default mode for wheel builds
            build_mode = 'default'

        # Always exclude database backend implementations
        build_data.setdefault('exclude', [])
        backend_excludes = [
            'src/rhosocial/activerecord/backend/impl/mysql',
            'src/rhosocial/activerecord/backend/impl/pgsql',
            'src/rhosocial/activerecord/backend/impl/mariadb',
            'src/rhosocial/activerecord/backend/impl/mssql',
            'src/rhosocial/activerecord/backend/impl/oracle',
        ]
        build_data['exclude'].extend(backend_excludes)

        # Always exclude test database files
        build_data['exclude'].extend([
            '**/*test_db.sqlite',
            '**/*test_*.sqlite',
            '**/*test_*.db',
        ])

        # Handle different modes
        if self.target_name == 'sdist':
            # Use only-include for strict control
            if build_mode == 'default':
                # Default mode: ONLY src/, README.md, LICENSE, pyproject.toml
                build_data['only-include'] = [
                    'src',
                    'LICENSE',
                    'README.md',
                    'pyproject.toml',
                ]
                # Also exclude test package
                build_data['exclude'].append('src/rhosocial/activerecord_test')

            elif build_mode == 'test':
                # Test mode: src/, tests/, and specific files
                build_data['only-include'] = [
                    'src',
                    'tests',
                    'LICENSE',
                    'README.md',
                    'pyproject.toml',
                    'PACKAGING.md',
                    'TESTING.md',
                ]

                # Add dev requirements if exists
                if os.path.exists(os.path.join(self.root, 'requirements-dev.txt')):
                    build_data['only-include'].append('requirements-dev.txt')

                # Map test package
                build_data.setdefault('force_include', {})
                test_src_path = os.path.join(self.root, 'tests', 'rhosocial', 'activerecord_test')
                if os.path.exists(test_src_path):
                    build_data['force_include']['tests/rhosocial/activerecord_test'] = 'src/rhosocial/activerecord_test'

            elif build_mode == 'docs':
                # Docs mode: src/, docs/, and documentation files
                build_data['only-include'] = [
                    'src',
                    'docs',
                    'LICENSE',
                    'README.md',
                    'pyproject.toml',
                    'CONTRIBUTING.md',
                    'SECURITY.md',
                ]
                # Exclude test package
                build_data['exclude'].append('src/rhosocial/activerecord_test')

            elif build_mode == 'dev':
                # Dev mode: don't use only-include, include almost everything
                # The default behavior will include everything, we just exclude unwanted files
                build_data['exclude'].extend([
                    '.git',
                    '.github',
                    '__pycache__',
                    '*.pyc',
                    '*.pyo',
                    '.pytest_cache',
                    'build',
                    'dist',
                    '*.egg-info',
                    '.mypy_cache',
                    '.ruff_cache',
                    '.coverage',
                    'htmlcov',
                    '.DS_Store',
                    '.idea',
                    '.vscode',
                ])

                # Map test package
                build_data.setdefault('force_include', {})
                test_src_path = os.path.join(self.root, 'tests', 'rhosocial', 'activerecord_test')
                if os.path.exists(test_src_path):
                    build_data['force_include']['tests/rhosocial/activerecord_test'] = 'src/rhosocial/activerecord_test'

        else:
            # For wheel, only include the package
            build_data['only-include'] = ['src/rhosocial']
            # Exclude test package
            build_data['exclude'].append('src/rhosocial/activerecord_test')


@hookimpl
def hatch_register_build_hook():
    """Register the custom build hook."""
    return CustomBuildHook