import os
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Try importing tree-sitter bindings
HAS_TREE_SITTER = False
try:
    from tree_sitter import Language, Parser
    import tree_sitter_python
    import tree_sitter_javascript
    import tree_sitter_typescript
    import tree_sitter_rust
    import tree_sitter_go
    import tree_sitter_java
    import tree_sitter_c
    import tree_sitter_cpp

    def get_lang(mod):
        try:
            lang = mod.language()
            if not isinstance(lang, Language):
                return Language(lang)
            return lang
        except Exception:
            return None

    LANGUAGE_MAP = {
        ".py": get_lang(tree_sitter_python),
        ".js": get_lang(tree_sitter_javascript),
        ".ts": get_lang(tree_sitter_typescript),
        ".tsx": get_lang(tree_sitter_typescript),
        ".rs": get_lang(tree_sitter_rust),
        ".go": get_lang(tree_sitter_go),
        ".java": get_lang(tree_sitter_java),
        ".c": get_lang(tree_sitter_c),
        ".cpp": get_lang(tree_sitter_cpp),
        ".hpp": get_lang(tree_sitter_cpp),
        ".cc": get_lang(tree_sitter_cpp),
        ".h": get_lang(tree_sitter_cpp),
        ".rb": None
    }
    HAS_TREE_SITTER = any(v is not None for v in LANGUAGE_MAP.values())
except Exception as e:
    logger.warning(f"Failed to load tree-sitter bindings: {e}. Fallback to regex parser.")
    LANGUAGE_MAP = {ext: None for ext in [".py", ".js", ".ts", ".tsx", ".rs", ".go", ".java", ".c", ".cpp", ".hpp", ".cc", ".h", ".rb"]}

class TreeSitterParser:
    def __init__(self):
        try:
            self.language_map = LANGUAGE_MAP
            logger.info("TreeSitterParser initialized.")
        except Exception as e:
            logger.error(f"Error in init: {e}")

    def can_parse(self, filepath: str) -> bool:
        try:
            ext = os.path.splitext(filepath)[1].lower()
            return ext in self.language_map and self.language_map[ext] is not None
        except Exception:
            return False

    def _regex_parse(self, content: str, filepath: str, ext: str) -> Dict[str, Any]:
        try:
            functions = []
            classes = []
            imports = []
            calls = []
            
            lines = content.splitlines()
            for idx, line in enumerate(lines, 1):
                cls_match = re.search(r'\b(class|struct|interface)\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
                if cls_match:
                    classes.append({"name": cls_match.group(2), "start_line": idx, "end_line": idx})
                    continue

                fn_match = re.search(r'\b(def|fn|func|function)\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
                if fn_match:
                    functions.append({"name": fn_match.group(2), "start_line": idx, "end_line": idx, "type": "function"})
                    continue

                # Generic function declarations (e.g. C/C++, Java methods)
                gen_fn_match = re.search(r'\b(?:public|private|protected|static|\w+)\s+(\w+)\s*\([^)]*\)\s*\{', line)
                if gen_fn_match:
                    name = gen_fn_match.group(1)
                    if name not in {"if", "for", "while", "switch", "catch", "def", "fn", "func", "function", "class", "struct"}:
                        functions.append({"name": name, "start_line": idx, "end_line": idx, "type": "function"})
                        continue

                imp_match = re.search(r'\b(?:import|use)\s+([a-zA-Z_][a-zA-Z0-9_./]*)', line)
                if imp_match:
                    imports.append({"module": imp_match.group(1), "names": []})
                    continue

                inc_match = re.search(r'#include\s+([<"\w./>]+)', line)
                if inc_match:
                    imports.append({"module": inc_match.group(1), "names": []})
                    continue

                call_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', line)
                for name in call_matches:
                    if name not in {"if", "for", "while", "switch", "catch", "def", "fn", "func", "function", "class", "return"}:
                        calls.append({"function_name": name, "line": idx})

            return {
                "file": filepath,
                "language": "regex-fallback",
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "calls": calls,
                "error": "Using regex fallback"
            }
        except Exception as e:
            return {"file": filepath, "language": "error", "functions": [], "classes": [], "imports": [], "calls": [], "error": str(e)}

    def parse_file(self, filepath: str) -> Dict[str, Any]:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            ext = os.path.splitext(filepath)[1].lower()
            return self.extract_entities(content, ext, filepath)
        except Exception as e:
            logger.error(f"Failed to parse file {filepath}: {e}")
            return {"file": filepath, "language": "error", "functions": [], "classes": [], "imports": [], "calls": [], "error": str(e)}

    def extract_entities(self, content: str, language_name: str, filepath: str = "memory_artifact") -> Dict[str, Any]:
        try:
            # Map language name or extension to canonical extension
            lang_lower = language_name.lower()
            ext = lang_lower if lang_lower.startswith(".") else "." + lang_lower
            if lang_lower == "python" or lang_lower == "py":
                ext = ".py"
            elif lang_lower == "javascript" or lang_lower == "js":
                ext = ".js"
            elif lang_lower == "typescript" or lang_lower == "ts":
                ext = ".ts"
            elif lang_lower == "rust" or lang_lower == "rs":
                ext = ".rs"
            elif lang_lower == "go":
                ext = ".go"
            elif lang_lower == "java":
                ext = ".java"
            elif lang_lower == "cpp" or lang_lower == "c":
                ext = ".cpp" if lang_lower == "cpp" else ".c"

            if ext in self.language_map and self.language_map[ext] is not None:
                try:
                    lang = self.language_map[ext]
                    parser = Parser()
                    parser.set_language(lang)
                    source_bytes = content.encode("utf-8")
                    tree = parser.parse(source_bytes)
                    
                    functions = []
                    classes = []
                    imports = []
                    calls = []

                    def traverse(n):
                        node_type = n.type
                        if node_type in ("function_definition", "method_definition", "function_declarator"):
                            name_node = n.child_by_field_name("name")
                            name = ""
                            if name_node:
                                name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="ignore")
                            if not name:
                                for child in n.children:
                                    if child.type == "identifier":
                                        name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="ignore")
                                        break
                            if name:
                                functions.append({
                                    "name": name,
                                    "start_line": n.start_point[0] + 1,
                                    "end_line": n.end_point[0] + 1,
                                    "type": "method" if node_type == "method_definition" else "function"
                                })
                        elif node_type in ("class_definition", "struct_specifier", "class_specifier"):
                            name_node = n.child_by_field_name("name")
                            name = ""
                            if name_node:
                                name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="ignore")
                            if not name:
                                for child in n.children:
                                    if child.type in ("identifier", "type_identifier"):
                                        name = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="ignore")
                                        break
                            if name:
                                classes.append({
                                    "name": name,
                                    "start_line": n.start_point[0] + 1,
                                    "end_line": n.end_point[0] + 1
                                })
                        elif node_type in ("import_statement", "import_from_statement", "use_declaration", "include_directive"):
                            module_name = source_bytes[n.start_byte:n.end_byte].decode("utf-8", errors="ignore").strip()
                            imports.append({"module": module_name, "names": []})
                        elif node_type == "call_expression":
                            function_node = n.child_by_field_name("function")
                            if function_node:
                                fn_name = source_bytes[function_node.start_byte:function_node.end_byte].decode("utf-8", errors="ignore")
                                if fn_name:
                                    calls.append({"function_name": fn_name, "line": n.start_point[0] + 1})
                        
                        for child in n.children:
                            traverse(child)

                    traverse(tree.root_node)
                    return {
                        "file": filepath,
                        "language": ext.lstrip("."),
                        "functions": functions,
                        "classes": classes,
                        "imports": imports,
                        "calls": calls,
                        "error": None
                    }
                except Exception as parse_err:
                    logger.warning(f"Tree-sitter parse failed for {filepath}: {parse_err}. Trying regex.")
            
            return self._regex_parse(content, filepath, ext)
        except Exception as e:
            logger.error(f"Error in extract_entities: {e}")
            return {"file": filepath, "language": "error", "functions": [], "classes": [], "imports": [], "calls": [], "error": str(e)}

# Backward compatibility
ASTParser = TreeSitterParser
