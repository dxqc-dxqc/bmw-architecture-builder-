# src/core_logic.py
import os
import re


def ensure_history_dir():
    """确保 history 文件夹存在"""
    if not os.path.exists("history"):
        os.makedirs("history")


def generate_markdown_text(tree_widget):
    """【正向转换】将当前 RobustTreeWidget 的结构递归转化为标准的 Markdown 规格文本"""

    def recurse(item, indent=""):
        md_text = ""
        pure_name = item.data(1, 0x0100) or ""  # Qt.ItemDataRole.UserRole 为 0x0100
        desc = item.data(2, 0x0100) or ""
        is_folder = item.data(0, 0x0100) == "folder"

        formatted_name = f"{pure_name}/" if is_folder else pure_name
        comment = f" # 👉 {desc}" if desc else ""

        md_text += f"{indent}- {formatted_name}{comment}\n"

        for i in range(item.childCount()):
            md_text += recurse(item.child(i), indent + "  ")
        return md_text

    tree_content = ""
    for i in range(tree_widget.topLevelItemCount()):
        tree_content += recurse(tree_widget.topLevelItem(i))

    md_template = f"""# Project Architecture Blueprint

> 本文件规定了软件项目的目录、文件结构标准与设计职责。请 Codex 严格以此骨架为准绳进行代码编写、重构或逻辑重排。

## Directory Tree & Responsibilities

```text
{tree_content}```

---
*Generated via BMW Corporate Architecture Builder Component.*
"""
    return md_template


def parse_markdown_to_tree_data(md_content):
    """【反向读取】解析历史 MD 文件，精确提取其中的目录层级、节点类型与长注释说明"""
    match = re.search(r'```text\s*(.*?)\s*```', md_content, re.DOTALL)
    if not match:
        return []

    raw_lines = match.group(1).split('\n')
    tree_nodes = []

    for line in raw_lines:
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip())
        content = line.strip().lstrip('- ').strip()

        desc = ""
        if " # 👉 " in content:
            content, desc = content.split(" # 👉 ", 1)

        is_folder = content.endswith('/')
        pure_name = content.rstrip('/')

        tree_nodes.append({
            'indent': indent,
            'name': pure_name,
            'desc': desc,
            'type': 'folder' if is_folder else 'file'
        })

    return tree_nodes


def scan_local_directory_to_tree_data(root_path):
    """【新核心功能】递归扫描本地物理文件夹，转换为带有层级缩进的数据字典"""
    tree_nodes = []

    # 定义需要忽略的常见无关文件夹和系统隐藏文件（防污染）
    ignored_dirs = {'.git', '.vscode', '.idea', '__pycache__', 'my_env', 'venv', 'dist', 'build'}
    ignored_files = {'.DS_Store', 'Thumbs.db', '.gitignore'}

    def traverse(current_path, indent_level=0):
        try:
            # 获取当前目录下的所有文件和文件夹，并进行排序让结构更美观
            items = sorted(os.listdir(current_path))
        except Exception:
            return

        # 分离文件夹和文件，确保渲染时文件夹排在前面
        dirs = [d for d in items if os.path.isdir(os.path.join(current_path, d)) and d not in ignored_dirs]
        files = [f for f in items if os.path.isfile(os.path.join(current_path, f)) and f not in ignored_files]

        # 先处理文件夹
        for d in dirs:
            full_dir_path = os.path.join(current_path, d)
            tree_nodes.append({
                'indent': indent_level * 2,  # 转化为与MD解析兼容的空格缩进数量
                'name': d,
                'desc': "",  # 本地初始读取没有描述，留空供用户后续在UI中填写
                'type': 'folder'
            })
            # 递归深入下一层级
            traverse(full_dir_path, indent_level + 1)

        # 后处理文件
        for f in files:
            tree_nodes.append({
                'indent': indent_level * 2,
                'name': f,
                'desc': "",
                'type': 'file'
            })

    traverse(root_path)
    return tree_nodes