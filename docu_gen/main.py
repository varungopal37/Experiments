import typer
import yaml
from pathlib import Path
import ast
import os
import subprocess
import shutil

app = typer.Typer()

CONFIG_FILE_NAME = "docu-gen-config.yaml"

# Simplified config for per-project workflow
DEFAULT_CONFIG = {
    "output_dir": "./docs/api",
}

def get_config():
    """Reads the config file from the current directory."""
    config_path = Path(CONFIG_FILE_NAME)
    if not config_path.exists():
        typer.echo(f"Error: '{CONFIG_FILE_NAME}' not found in the current directory.")
        typer.echo("Please run 'docu-gen init' to create a configuration file.")
        raise typer.Exit(code=1)

    with open(config_path, "r") as f:
        return yaml.safe_load(f)

@app.command()
def init():
    """
    Initializes a new docu-gen-config.yaml file in the current project directory.
    """
    config_path = Path(CONFIG_FILE_NAME)
    if config_path.exists():
        typer.echo(f"'{CONFIG_FILE_NAME}' already exists.")
        raise typer.Exit(code=1)

    with open(config_path, "w") as f:
        yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)

    typer.echo(f"Successfully created '{CONFIG_FILE_NAME}' in the current directory.")
    typer.echo("You can now run 'docu-gen find-undocumented' or 'docu-gen generate'.")


@app.command()
def find_undocumented():
    """
    Finds APIViews without @extend_schema in the current project.
    """
    project_path = Path(".")
    project_name = project_path.resolve().name

    typer.echo(f"Scanning '{project_name}' for undocumented APIViews...")
    undocumented_views = []

    for root, _, files in os.walk(project_path):
        # Exclude common virtual environment and git directories
        if ".venv" in root or "venv" in root or ".git" in root:
            continue

        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        source = f.read()
                        tree = ast.parse(source)

                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                is_api_view = any(
                                    isinstance(base, ast.Name) and base.id == "APIView"
                                    for base in node.bases
                                )

                                if is_api_view:
                                    has_extend_schema = any(
                                        (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "extend_schema")
                                        or (isinstance(d, ast.Name) and d.id == "extend_schema")
                                        for d in node.decorator_list
                                    )

                                    if not has_extend_schema:
                                        undocumented_views.append((str(file_path), node.name))

                except Exception as e:
                    typer.echo(f"Warning: Could not parse {file_path}. Error: {e}", err=True)

    if undocumented_views:
        typer.echo("\nUndocumented APIViews found:")
        for file_path, view_name in undocumented_views:
            typer.echo(f"- {file_path}: {view_name}")
    else:
        typer.echo("\nNo undocumented APIViews found. Great job!")


@app.command()
def generate():
    """
    Generates OpenAPI schema and Postman collections for the current project.
    """
    config = get_config()
    output_dir = Path(config.get("output_dir", "./generated_docs"))

    project_path = Path(".")
    project_name = project_path.resolve().name

    # The final output will be in a subfolder named after the project
    project_output_dir = output_dir / project_name
    project_output_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Processing project: {project_name}")

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
        # The schema file is created in the project root, so move it
        shutil.move(project_path / schema_file, project_output_dir / schema_file)
        typer.echo(f"  - Generated OpenAPI schema: {project_output_dir / schema_file}")
    except FileNotFoundError:
        typer.echo(f"  - Failed to generate OpenAPI schema. Is 'manage.py' in the current directory?", err=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"  - Failed to generate OpenAPI schema. Error from spectacular:", err=True)
        typer.echo(e.stderr, err=True)

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
    except FileNotFoundError:
        typer.echo(f"  - Failed to generate Postman collection. Is 'manage.py' in the current directory?", err=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"  - Failed to generate Postman collection. Error from spectacular:", err=True)
        typer.echo(e.stderr, err=True)

    typer.echo("\nDocumentation generation complete.")


if __name__ == "__main__":
    app()