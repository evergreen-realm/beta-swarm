import ast
import os
from typing import Dict, List, Any

class PythonASTParser:
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        imports = []
        classes = []
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.append(n.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for n in node.names:
                    imports.append(f"{module}.{n.name}")
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
                
        return {
            "file_path": file_path,
            "imports": imports,
            "classes": classes,
            "functions": functions
        }

parser = PythonASTParser()
