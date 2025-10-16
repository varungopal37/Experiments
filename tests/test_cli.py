import unittest
from unittest.mock import patch, mock_open
from typer.testing import CliRunner
import os
import shutil
from pathlib import Path

# Add the project root to the Python path to allow importing 'docu_gen'
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from docu_gen.main import app

runner = CliRunner()

class TestCli(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path("test_cli_run")
        self.test_dir.mkdir(exist_ok=True)
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir("..")
        shutil.rmtree(self.test_dir)

    def test_init_command(self):
        result = runner.invoke(app, ["init"])
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(Path("docu-gen-config.yaml").exists())
        self.assertIn("Successfully created 'docu-gen-config.yaml'", result.stdout)

    def test_init_command_already_exists(self):
        Path("docu-gen-config.yaml").touch()
        result = runner.invoke(app, ["init"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("'docu-gen-config.yaml' already exists.", result.stdout)

    @patch("docu_gen.main.get_project_path")
    def test_find_undocumented_command(self, mock_get_project_path):
        # Create a mock project structure
        mock_project_dir = Path("mock_project")
        mock_project_dir.mkdir()
        (mock_project_dir / "views").mkdir()

        # Mock project path to return our controlled test directory
        mock_get_project_path.return_value = mock_project_dir

        # Create a view file with one documented and one undocumented APIView
        view_content = """
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

@extend_schema(summary="A documented view")
class DocumentedView(APIView):
    pass

class UndocumentedView(APIView):
    pass
"""
        (mock_project_dir / "views" / "some_views.py").write_text(view_content)

        # Run the command
        result = runner.invoke(app, ["find-undocumented", "MyProject"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Undocumented APIViews found:", result.stdout)
        self.assertIn("UndocumentedView", result.stdout)
        self.assertNotIn("DocumentedView", result.stdout)

    @patch("subprocess.run")
    @patch("shutil.move")
    def test_generate_command(self, mock_move, mock_subprocess_run):
        # Create a config file
        config_content = """
projects:
  - name: "TestProject"
    path: "test_project_path"
output_dir: "output"
"""
        Path("docu-gen-config.yaml").write_text(config_content)
        Path("test_project_path").mkdir()

        # Mock subprocess to "create" the files
        def side_effect(*args, **kwargs):
            cwd = kwargs.get("cwd", Path("."))
            cmd = args[0]
            if "--file" in cmd:
                file_path = Path(cwd) / cmd[cmd.index("--file") + 1]
                file_path.touch()
            return unittest.mock.MagicMock(check_returncode=lambda: None, stderr="")

        mock_subprocess_run.side_effect = side_effect

        # Run the command
        result = runner.invoke(app, ["generate"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Generating documentation for 1 project(s)", result.stdout)
        self.assertIn("Generated OpenAPI schema", result.stdout)
        self.assertIn("Generated Postman collection", result.stdout)
        self.assertTrue(Path("output/TestProject").is_dir())
        self.assertEqual(mock_move.call_count, 2)


if __name__ == "__main__":
    unittest.main()