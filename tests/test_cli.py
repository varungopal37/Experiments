import unittest
from unittest.mock import patch
from typer.testing import CliRunner
import os
import shutil
from pathlib import Path

# Add the project root to the Python path to allow importing 'docu_gen'
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from docu_gen.main import app

runner = CliRunner()

class TestCliPerProject(unittest.TestCase):

    def setUp(self):
        # Create a parent directory for test runs
        self.test_run_dir = Path("test_cli_runs")
        self.test_run_dir.mkdir(exist_ok=True)

        # Create a mock project directory where commands will be run
        self.mock_project_path = self.test_run_dir / "my-test-project"
        self.mock_project_path.mkdir()

        # Change the current working directory to the mock project
        self.original_cwd = Path.cwd()
        os.chdir(self.mock_project_path)

    def tearDown(self):
        # Change back to the original directory and clean up
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_run_dir)

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

    def test_find_undocumented_command(self):
        # Create a view file inside the mock project
        (Path("views")).mkdir()
        view_content = """
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

@extend_schema(summary="A documented view")
class DocumentedView(APIView):
    pass

class UndocumentedView(APIView):
    pass
"""
        (Path("views") / "some_views.py").write_text(view_content)

        # Run the command from within the project
        result = runner.invoke(app, ["find-undocumented"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Scanning 'my-test-project' for undocumented APIViews...", result.stdout)
        self.assertIn("Undocumented APIViews found:", result.stdout)
        self.assertIn("UndocumentedView", result.stdout)
        self.assertNotIn("DocumentedView", result.stdout)

    @patch("subprocess.run")
    @patch("shutil.move")
    def test_generate_command(self, mock_move, mock_subprocess_run):
        # Create a config file in the mock project
        runner.invoke(app, ["init"])

        # Create a mock manage.py
        (Path.cwd() / "manage.py").touch()

        # Mock subprocess to simulate file creation
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if "--file" in cmd:
                file_path = Path.cwd() / cmd[cmd.index("--file") + 1]
                file_path.touch()
            return unittest.mock.MagicMock(check_returncode=lambda: None, stderr="")

        mock_subprocess_run.side_effect = side_effect

        result = runner.invoke(app, ["generate"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Processing project: my-test-project", result.stdout)

        # The output path is now relative to the project dir
        expected_output_dir = Path("docs/api/my-test-project")
        self.assertTrue(expected_output_dir.is_dir())
        self.assertIn(f"Generated OpenAPI schema: {expected_output_dir / 'schema.yml'}", result.stdout)
        self.assertIn(f"Generated Postman collection: {expected_output_dir / 'postman.json'}", result.stdout)
        self.assertEqual(mock_move.call_count, 2)


if __name__ == "__main__":
    unittest.main()