import json
import sys
from pathlib import Path

from src.parser import load_ableton_xml, build_ast
from src.server import ASTServer


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.main <path-to-als-or-xml> [--mode=MODE]")
        print("\nModes:")
        print("  legacy    - Output raw dict AST (default)")
        print("  server    - Use AST server with node objects")
        print("  info      - Show project info summary")
        sys.exit(1)

    path = Path(sys.argv[1])
    mode = "legacy"

    # Parse optional mode argument
    if len(sys.argv) > 2:
        for arg in sys.argv[2:]:
            if arg.startswith("--mode="):
                mode = arg.split("=")[1]

    if mode == "server" or mode == "info":
        # Use new AST server
        server = ASTServer()
        server.load_project(path)

        if mode == "info":
            # Show project info
            info = server.get_project_info()
            print(json.dumps(info, indent=2))
        else:
            # Show full AST
            print(server.get_ast_json())
    else:
        # Legacy mode: output raw dict
        tree = load_ableton_xml(path)
        ast = build_ast(tree.getroot())
        print(json.dumps(ast, indent=2))


if __name__ == "__main__":
    main()
