import json
from enum import Enum
from ast import expr
from typing import Dict, Set
import sys
import ast

from pathlib import Path
from dataclasses import dataclass, field

ADDED_OPS: Set[str] = {"AddField"}
REMOVED_OPS: Set[str] = {"RemoveField"}

MODEL_OPS: Set[str] = {"CreateModel", "RemoveModel", "RenameModel"}

class Status(Enum):
    DELETED = -1
    MODIFIED = 0
    CREATED = 1

@dataclass
class ModelChanges:
    status: Status = field(default=Status.MODIFIED)

    renamed_from: str | None = field(default=None)
    added: Set[str] = field(default_factory=set)
    removed: Set[str] = field(default_factory=set)

    def to_json(self) -> str:
        data = {
            "status": self.status.value,
            "renamed_from": self.renamed_from,
            "added": list(self.added),
            "removed": list(self.removed)
        }
        return json.dumps(data, indent=2)

migration_changes: Dict[str, ModelChanges] = {}

def extract_app_label(file_path: str) -> str:
    path = Path(file_path)
    return path.parent.parent.name

def extract_str_from_node(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None

def get_model(model_name: str) -> ModelChanges:
    return migration_changes.setdefault(model_name, ModelChanges())

def parse_migration_file(file_path: str):
    with open(file_path, "r", encoding="utf-8") as file:
        tree = ast.parse(file.read())

    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Migration":
            continue

        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue

            if not any(isinstance(t, ast.Name) and t.id == "operations" for t in stmt.targets):
                continue

            if not isinstance(stmt.value, ast.List):
                continue

            for operation in stmt.value.elts:
                if not isinstance(operation, ast.Call):
                    continue

                if not isinstance(operation.func, ast.Attribute):
                    continue

                operation_name = operation.func.attr
                kwargs: Dict[str, ast.expr] = {
                    kw.arg: kw.value
                    for kw in operation.keywords
                    if kw.arg is not None
                }

                if operation_name in MODEL_OPS:
                    model_name = extract_str_from_node(kwargs.get("name"))

                    if operation_name == "CreateModel" and model_name:
                        model = get_model(model_name.lower())
                        model.status = Status.CREATED

                        fields_node = kwargs.get("fields")
                        if isinstance(fields_node, ast.List):
                            for field_tuple in fields_node.elts:
                                if isinstance(field_tuple, ast.Tuple) and len(field_tuple.elts) >= 1:
                                    field_name_node = field_tuple.elts[0]
                                    field_name = extract_str_from_node(field_name_node)
                                    if field_name:
                                        model.added.add(field_name)

                    elif operation_name == "DeleteModel" and model_name:
                        model = get_model(model_name.lower())
                        model.status = Status.DELETED

                    elif operation_name == "RenameModel":
                        old_name = extract_str_from_node(kwargs.get("old_name"))
                        new_name = extract_str_from_node(kwargs.get("new_name"))

                        if old_name and new_name:
                            old_name = old_name.lower()
                            new_name = new_name.lower()

                            model = get_model(old_name)
                            if model.renamed_from is None:
                                model.renamed_from = old_name
                            migration_changes[new_name] = model
                            migration_changes.pop(old_name, None)

                    continue

                field_name = extract_str_from_node(kwargs.get("name"))
                model_name = extract_str_from_node(kwargs.get("model_name"))

                if not field_name or not model_name:
                    continue

                model = get_model(model_name)

                if operation_name in ADDED_OPS:
                    model.added.add(field_name)

                elif operation_name in REMOVED_OPS:
                    model.removed.add(field_name)

                elif operation_name == "RenameField":
                    old_name = extract_str_from_node(kwargs.get("old_name"))
                    new_name = extract_str_from_node(kwargs.get("new_name"))

                    if old_name and new_name:
                        model.removed.add(old_name)
                        model.added.add(new_name)

if __name__ == "__main__":
    migration_files = sys.argv[1:]
    for file_path in migration_files:
        parse_migration_file(file_path)

    # print(migration_changes.to_json())
    for obj in migration_changes:
        # print(migration_changes[obj].to_json())
        print(f"{obj}: {migration_changes[obj].to_json()}")
