#
# Copyright (c) 2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

"""Integration tests: project structure, config files, YAML validity."""
# pylint: disable=protected-access
import os
import sys
import unittest

from tests.base import BaseHaTestCase

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))


class TestProjectStructure(BaseHaTestCase):
    """Validate project file structure."""

    def test_tox_ini_exists(self):
        """tox.ini exists at project root."""
        self.assertTrue(os.path.isfile(
            os.path.join(PROJECT_ROOT, 'tox.ini')))

    def test_zuul_yaml_exists(self):
        """.zuul.yaml exists at project root."""
        self.assertTrue(os.path.isfile(
            os.path.join(PROJECT_ROOT, '.zuul.yaml')))

    def test_test_requirements_exists(self):
        """test-requirements.txt exists."""
        self.assertTrue(os.path.isfile(
            os.path.join(PROJECT_ROOT, 'test-requirements.txt')))

    def test_license_exists(self):
        """LICENSE file exists."""
        self.assertTrue(os.path.isfile(
            os.path.join(PROJECT_ROOT, 'LICENSE')))

    def test_readme_exists(self):
        """README.rst exists."""
        self.assertTrue(os.path.isfile(
            os.path.join(PROJECT_ROOT, 'README.rst')))

    def test_sm_api_package(self):
        """sm_api package directory exists."""
        self.assertTrue(os.path.isdir(
            os.path.join(PROJECT_ROOT,
                         'service-mgmt-api', 'sm-api', 'sm_api')))

    def test_sm_client_package(self):
        """sm_client package directory exists."""
        self.assertTrue(
            os.path.isdir(
                os.path.join(
                    PROJECT_ROOT, 'service-mgmt-client', 'sm-client',
                    'sm_client')))

    def test_sm_tools_package(self):
        """sm_tools package directory exists."""
        self.assertTrue(os.path.isdir(
            os.path.join(PROJECT_ROOT,
                         'service-mgmt-tools', 'sm-tools', 'sm_tools')))

    def test_service_mgmt_c_sources(self):
        """C source directory exists under service-mgmt."""
        src_dir = os.path.join(
            PROJECT_ROOT, 'service-mgmt', 'sm', 'src')
        self.assertTrue(os.path.isdir(src_dir))


class TestConfigFileValidity(BaseHaTestCase):
    """Validate configuration files."""

    def test_tox_ini_parseable(self):
        """tox.ini is parseable by configparser."""
        import configparser
        config = configparser.ConfigParser()
        config.read(os.path.join(PROJECT_ROOT, 'tox.ini'))
        self.assertIn('tox', config.sections())

    def test_tox_has_envlist(self):
        """tox.ini has envlist defined."""
        import configparser
        config = configparser.ConfigParser()
        config.read(os.path.join(PROJECT_ROOT, 'tox.ini'))
        envlist = config.get('tox', 'envlist')
        self.assertIn('linters', envlist)

    def test_gitreview_exists(self):
        """.gitreview file exists and has content."""
        path = os.path.join(PROJECT_ROOT, '.gitreview')
        self.assertTrue(os.path.isfile(path))
        with open(path, 'r') as f:
            content = f.read()
        self.assertIn('gerrit', content.lower())

    def test_yaml_files_parseable(self):
        """YAML files in project root are parseable."""
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not available")

        # Add constructor for encrypted tags used in Zuul secrets
        class _SafeLoaderWithEncrypted(yaml.SafeLoader):
            """SafeLoader that handles !encrypted tags."""

        _SafeLoaderWithEncrypted.add_multi_constructor(
            '!encrypted/', lambda loader, suffix,
            node: loader.construct_sequence(node))

        zuul_path = os.path.join(PROJECT_ROOT, '.zuul.yaml')
        with open(zuul_path, 'r') as f:
            data = yaml.load(f, Loader=_SafeLoaderWithEncrypted)
        self.assertIsInstance(data, list)

    def test_setup_py_files_exist(self):
        """setup.py exists for each Python sub-package."""
        for sub in ('service-mgmt-api/sm-api',
                    'service-mgmt-client/sm-client',
                    'service-mgmt-tools/sm-tools'):
            path = os.path.join(PROJECT_ROOT, sub, 'setup.py')
            self.assertTrue(os.path.isfile(path),
                            msg=f"Missing setup.py in {sub}")


class TestPythonImports(BaseHaTestCase):
    """Validate Python packages are importable."""

    def setUp(self):
        """Add sub-packages to sys.path."""
        for sub in ('service-mgmt-tools/sm-tools',
                    'service-mgmt-client/sm-client',
                    'service-mgmt-api/sm-api'):
            p = os.path.join(PROJECT_ROOT, sub)
            if p not in sys.path:
                sys.path.insert(0, p)

    def test_import_sm_tools(self):
        """sm_tools package is importable."""
        import sm_tools  # noqa: F401
        self.assertTrue(True)

    def test_import_sm_api_msg_utils(self):
        """sm_tools.sm_api_msg_utils is importable."""
        from sm_tools import sm_api_msg_utils  # noqa: F401
        self.assertTrue(True)

    def test_import_sm_client_exc(self):
        """sm_client.exc is importable."""
        from sm_client import exc  # noqa: F401
        self.assertTrue(True)

    def test_import_sm_client_common_base(self):
        """sm_client.common.base is importable."""
        from sm_client.common import base  # noqa: F401
        self.assertTrue(True)

    def test_import_sm_dump(self):
        """sm_tools.sm_dump is importable."""
        from sm_tools import sm_dump  # noqa: F401
        self.assertTrue(True)

    def test_import_sm_query(self):
        """sm_tools.sm_query is importable."""
        from sm_tools import sm_query  # noqa: F401
        self.assertTrue(True)

    def test_import_sm_configure(self):
        """sm_tools.sm_configure is importable."""
        from sm_tools import sm_configure  # noqa: F401
        self.assertTrue(True)

    def test_import_sm_provision(self):
        """sm_tools.sm_provision is importable."""
        from sm_tools import sm_provision  # noqa: F401
        self.assertTrue(True)

    def test_import_sm_action(self):
        """sm_tools.sm_action is importable."""
        from sm_tools import sm_action  # noqa: F401
        self.assertTrue(True)


class TestSourceFilePresence(BaseHaTestCase):
    """Validate source files are present for all components."""

    def _count_files(self, ext):
        """Count files with given extension.

        :param ext: file extension to count
        :returns: int count of matching files
        """
        count = 0
        for root, _, files in os.walk(PROJECT_ROOT):
            if '.tox' in root:
                continue
            for f in files:
                if f.endswith(ext):
                    count += 1
        return count

    def test_python_files_present(self):
        """Project has Python source files."""
        self.assertGreater(self._count_files('.py'), 50)

    def test_c_files_present(self):
        """Project has C source files."""
        self.assertGreater(self._count_files('.c'), 50)

    def test_header_files_present(self):
        """Project has C header files."""
        self.assertGreater(self._count_files('.h'), 50)

    def test_cpp_files_present(self):
        """Project has C++ source files."""
        self.assertGreater(self._count_files('.cpp'), 5)

    def test_shell_scripts_present(self):
        """Project has shell scripts."""
        self.assertGreater(self._count_files('.sh'), 0)


if __name__ == '__main__':
    unittest.main()
