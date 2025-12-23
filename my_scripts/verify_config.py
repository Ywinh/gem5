import ast
import configparser
import os
import sys

# ==========================================
# 1. 静态代码分析器 (适配 Python 3.14+)
# ==========================================


class PyConfigExtractor(ast.NodeVisitor):
    def __init__(self, target_class_name):
        self.target_class_name = target_class_name
        self.config = {}
        self.in_target_class = False

    def get_value(self, node):
        """尝试从 AST 节点中提取静态值"""
        # Python 3.14+ 使用 ast.Constant
        if isinstance(node, ast.Constant):
            return node.value

        elif isinstance(node, ast.Name):
            if node.id == "NULL":
                return "null"
            return node.id

        elif isinstance(node, ast.Call):
            nested_conf = {}
            for keyword in node.keywords:
                if keyword.arg:
                    nested_conf[keyword.arg] = self.get_value(keyword.value)
            return nested_conf

        elif isinstance(node, ast.List):
            return [self.get_value(elt) for elt in node.elts]

        else:
            try:
                return ast.literal_eval(node)
            except:
                return "COMPLEX_EXPRESSION"

    def visit_ClassDef(self, node):
        if node.name == self.target_class_name:
            self.in_target_class = True
            for item in node.body:
                self.visit(item)
            self.in_target_class = False

    def visit_Assign(self, node):
        if not self.in_target_class:
            return
        target_names = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                target_names.append(target.id)
            elif isinstance(target, ast.Attribute):
                if (
                    isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    target_names.append(target.attr)
        val = self.get_value(node.value)
        for name in target_names:
            self.config[name] = val

    def visit_FunctionDef(self, node):
        if self.in_target_class and node.name == "__init__":
            for item in node.body:
                self.visit(item)


def parse_python_config(filepath, class_name):
    if not os.path.exists(filepath):
        return {}
    with open(filepath, encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    extractor = PyConfigExtractor(class_name)
    extractor.visit(tree)
    return extractor.config


# ==========================================
# 2. 详细比对逻辑 (Verbose Check)
# ==========================================


def normalize(val):
    if val is None:
        return "null"
    s = str(val).lower().strip()
    if s == "true":
        return "true"
    if s == "false":
        return "false"
    if s == "null":
        return "null"
    try:
        f = float(s)
        if f.is_integer():
            return int(f)
        return f
    except:
        pass
    return s


def verify_recursive(py_dict, ini_parser, section_name, path=""):
    if not ini_parser.has_section(section_name):
        print(
            f"❌ [SECTION MISSING] INI section [{section_name}] not found (Path: {path})"
        )
        return False

    ini_data = dict(ini_parser[section_name])
    all_match = True

    # 打印当前正在检查的 Section
    print(
        f"\n📂 Checking Section: [{section_name}] (Path: {path if path else 'Root'})"
    )
    print("-" * 60)
    print(
        f"{'Property':<30} | {'My.py (Source)':<15} | {'Config.ini (Target)':<15}"
    )
    print("-" * 60)

    for key, py_val in py_dict.items():
        # 1. 跳过复杂表达式
        if py_val == "COMPLEX_EXPRESSION":
            print(f"⚠️  {key:<28} | {'[Complex Expr]':<15} | {'[Skipped]':<15}")
            continue

        # 2. 查找 Key
        ini_key = None
        for k in ini_data.keys():
            if k.lower() == key.lower():
                ini_key = k
                break

        if not ini_key:
            print(f"❌ {key:<28} | {str(py_val):<15} | [MISSING IN INI]")
            all_match = False
            continue

        ini_val_raw = ini_data[ini_key]

        # 3. 递归处理对象
        if isinstance(py_val, dict):
            next_section = ini_val_raw
            if normalize(next_section) == "null":
                print(f"❌ {key:<28} | [Object]        | Null")
                all_match = False
            else:
                print(f"🔄 {key:<28} | [Object]        | -> [{next_section}]")
                # 递归调用
                if not verify_recursive(
                    py_val, ini_parser, next_section, path=f"{path}{key}."
                ):
                    all_match = False
        else:
            # 4. 普通值比对
            n_py = normalize(py_val)
            n_ini = normalize(ini_val_raw)

            if n_py != n_ini:
                print(
                    f"❌ {key:<28} | {str(py_val):<15} | {str(ini_val_raw):<15}"
                )
                all_match = False
            else:
                print(
                    f"✅ {key:<28} | {str(py_val):<15} | {str(ini_val_raw):<15}"
                )

    return all_match


# ==========================================
# 3. Main
# ==========================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("py_file")
    parser.add_argument("ini_file")
    parser.add_argument(
        "--map", action="append", required=True, help="ClassName:IniPath"
    )
    args = parser.parse_args()

    ini = configparser.ConfigParser()
    ini.optionxform = str
    if not os.path.exists(args.ini_file):
        print("INI file not found.")
        sys.exit(1)
    ini.read(args.ini_file)

    for mapping in args.map:
        try:
            cls_name, ini_path = mapping.split(":")
        except:
            continue

        print(
            f"\n============================================================"
        )
        print(f"🔍 Mapping: {cls_name}  -->  {ini_path}")
        print(f"============================================================")

        py_config = parse_python_config(args.py_file, cls_name)

        if not py_config:
            print(f"⚠️  No config found for class {cls_name}")
            continue

        if verify_recursive(py_config, ini, ini_path):
            print(f"\n✨ FINAL RESULT: {cls_name} MATCHES PERFECTLY! ✨")
        else:
            print(f"\n🚫 FINAL RESULT: {cls_name} HAS ERRORS.")
