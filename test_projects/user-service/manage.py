#!/usr/bin/env python
import sys

def main():
    if "spectacular" in sys.argv:
        try:
            file_index = sys.argv.index("--file") + 1
            file_path = sys.argv[file_index]

            if "--postman" in sys.argv:
                with open(file_path, "w") as f:
                    f.write('{"info": {"name": "Postman Collection"}, "item": []}')
                print(f"Generated Postman collection at {file_path}")
            else:
                with open(file_path, "w") as f:
                    f.write("openapi: 3.0.0\\ninfo:\\n  title: My API\\n  version: 1.0.0\\npaths: {}")
                print(f"Generated OpenAPI schema at {file_path}")
        except (ValueError, IndexError):
            print("Error: --file argument not found or invalid.", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()