import typer
import yaml
from pathlib import Path
import ast
import os
import subprocess
import shutil

app = typer.Typer()

CONFIG_FILE_NAME = "docu-gen-config.yaml"

DEFAULT_CONFIG = {
    "projects": [
        {
            "name": "User-Service",
            "path": "/home/varun/repos/project-user-service",
        },
        {
            "name": "Product-API",
            "path": "/home/varun/repos/project-product-api",
        },
        {
            "name": "Billing-Engine",
            "path": "/home/varun/repos/project-billing-engine",
        },
    ],
    "output_dir": "./generated_docs",
}

def get_config():
    """Reads the config file."""
    config_path = Path(CONFIG_FILE_NAME)
    if not config_path.exists():
        typer.echo(f"Error: '{CONFIG_FILE_NAME}' not found. Please run 'docu-gen init'.")
        raise typer.Exit(code=1)

    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def get_project_path(project_name: str) -> Path:
    """Gets the path of a project from the config file."""
    config = get_config()
    for project in config.get("projects", []):
        if project["name"] == project_name:
            return Path(project["path"])

    typer.echo(f"Error: Project '{project_name}' not found in '{CONFIG_FILE_NAME}'.")
    raise typer.Exit(code=1)


@app.command()
def init():
    """
    Initializes a new docu-gen-config.yaml file in the current directory.
    """
    config_path = Path(CONFIG_FILE_NAME)
    if config_path.exists():
        typer.echo(f"'{CONFIG_FILE_NAME}' already exists.")
        raise typer.Exit(code=1)

    with open(config_path, "w") as f:
        yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)

    typer.echo(f"Successfully created '{CONFIG_FILE_NAME}'.")


@app.command()
def find_undocumented(project_name: str):
    """
    Finds APIViews without @extend_schema in a project.
    """
    project_path = get_project_path(project_name)

    if not project_path.exists() or not project_path.is_dir():
        typer.echo(f"Error: Project directory not found at '{project_path}'.")
        raise typer.Exit(code=1)

    typer.echo(f"Scanning '{project_name}' for undocumented APIViews...")
    undocumented_views = []

    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        source = f.read()
                        tree = ast.parse(source)

                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                is_api_view = False
                                for base in node.bases:
                                    if isinstance(base, ast.Name) and base.id == "APIView":
                                        is_api_view = True
                                        break

                                if is_api_view:
                                    has_extend_schema = False
                                    for decorator in node.decorator_list:
                                        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id == "extend_schema":
                                            has_extend_schema = True
                                            break
                                        elif isinstance(decorator, ast.Name) and decorator.id == "extend_schema":
                                            has_extend_schema = True
                                            break

                                    if not has_extend_schema:
                                        undocumented_views.append((str(file_path), node.name))

                except Exception as e:
                    typer.echo(f"Warning: Could not parse {file_path}. Error: {e}")

    if undocumented_views:
        typer.echo("\nUndocumented APIViews found:")
        for file_path, view_name in undocumented_views:
            typer.echo(f"- {file_path}: {view_name}")
    else:
        typer.echo("\nNo undocumented APIViews found. Great job!")


@app.command()
def generate():
    """
    Generates OpenAPI schema and Postman collections for all projects.
    """
    config = get_config()
    output_dir = Path(config.get("output_dir", "./generated_docs"))
    output_dir.mkdir(exist_ok=True)

    projects = config.get("projects", [])
    if not projects:
        typer.echo("No projects found in the configuration file.")
        raise typer.Exit()

    typer.echo(f"Generating documentation for {len(projects)} project(s)...")

    for project in projects:
        project_name = project["name"]
        project_path = Path(project["path"])
        project_output_dir = output_dir / project_name
        project_output_dir.mkdir(exist_ok=True)

        typer.echo(f"\nProcessing project: {project_name}")

        if not project_path.is_dir():
            typer.echo(f"  - Skipping: Directory not found at '{project_path}'")
            continue

        # Generate OpenAPI schema
        schema_file = "schema.yml"
        schema_command = ["python", "manage.py", "spectacular", "--file", schema_file]

        try:
            subprocess.run(
                schema_command,
                cwd=project_path,
                check=True,
                capture_output=True,
                text=True,
            )
            shutil.move(project_path / schema_file, project_output_dir / schema_file)
            typer.echo(f"  - Generated OpenAPI schema: {project_output_dir / schema_file}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            typer.echo(f"  - Failed to generate OpenAPI schema.")
            if isinstance(e, subprocess.CalledProcessError):
                typer.echo(f"    Error: {e.stderr}")

        # Generate Postman collection
        postman_file = "postman.json"
        postman_command = ["python", "manage.py", "spectacular", "--postman", "--file", postman_file]

        try:
            subprocess.run(
                postman_command,
                cwd=project_path,
                check=True,
                capture_output=True,
                text=True,
            )
            shutil.move(project_path / postman_file, project_output_dir / postman_file)
            typer.echo(f"  - Generated Postman collection: {project_output_dir / postman_file}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            typer.echo(f"  - Failed to generate Postman collection.")
            if isinstance(e, subprocess.CalledProcessError):
                typer.echo(f"    Error: {e.stderr}")

    typer.echo("\nDocumentation generation complete.")


if __name__ == "__main__":
    app()