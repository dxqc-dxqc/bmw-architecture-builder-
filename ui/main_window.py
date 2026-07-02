# ui/main_window.py
import json
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTreeWidgetItem, QFileDialog, QMessageBox, QFrame, QTextEdit
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from ui.custom_widgets import RobustTreeWidget
from src.core_logic import (
    generate_markdown_text, parse_markdown_to_tree_data,
    ensure_history_dir, scan_local_directory_to_tree_data,
    save_last_session_cache, load_last_session_cache
)

BMW_COLORS = {
    "primary": "#1c69d4",  # 宝马蓝
    "primary-active": "#0653b6",  # 激活蓝
    "success-green": "#10b981",  # 科技绿
    "success-green-active": "#059669",
    "ink": "#262626",
    "canvas": "#ffffff",
    "surface-soft": "#f7f7f7",
    "surface-card": "#fafafa",
    "hairline": "#e6e6e6",
    "on-primary": "#ffffff"
}

BMW_STYLE_SHEET = f"""
    QMainWindow {{ background-color: {BMW_COLORS["canvas"]}; }}
    QLabel {{ color: {BMW_COLORS["ink"]}; }}
    QFrame#HeaderBand {{ background-color: {BMW_COLORS["canvas"]}; border-bottom: 1px solid {BMW_COLORS["hairline"]}; }}
    QPushButton#SecondaryButton {{
        background-color: {BMW_COLORS["canvas"]}; color: {BMW_COLORS["ink"]};
        border: 1px solid {BMW_COLORS["hairline"]}; border-radius: 0px;
        padding: 10px 24px; font-size: 14px; font-weight: 700;
    }}
    QPushButton#SecondaryButton:pressed {{ background-color: {BMW_COLORS["surface-soft"]}; }}
    QLineEdit, QTextEdit {{
        background-color: {BMW_COLORS["canvas"]}; color: {BMW_COLORS["ink"]};
        border: 1px solid {BMW_COLORS["hairline"]}; border-radius: 0px;
        padding: 8px 12px; font-size: 14px;
    }}
    QLineEdit:focus, QTextEdit:focus {{ border: 1px solid {BMW_COLORS["ink"]}; }}
"""


class ArchitectureBuilder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BMW Corporate - 架构规格设计与历史回溯系统")
        self.resize(1200, 800)
        self.setStyleSheet(BMW_STYLE_SHEET)
        ensure_history_dir()

        # 历史回溯双栈
        self.undo_stack = []
        self.redo_stack = []
        self.block_snapshot = False

        self.init_ui()

        # 1. 初始状态先记录一次绝对空树快照，确保能“一直回溯到最开始的位置”
        self.save_snapshot(write_to_disk=False)  # 初始空状态不需要覆盖本地有效的缓存

        # 🚀 2. 【核心功能升级：启动时自动读取最新一次的本地快照】
        self.auto_load_last_session()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        outer_layout = QVBoxLayout(main_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 1. 顶端导航栏
        header_band = QFrame()
        header_band.setObjectName("HeaderBand")
        header_band.setFixedHeight(64)
        header_layout = QHBoxLayout(header_band)
        header_layout.setContentsMargins(32, 0, 32, 0)

        title_label = QLabel("ARCHITECT 架构蓝图生成器")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        outer_layout.addWidget(header_band)

        # 2. 核心工作区
        workspace = QWidget()
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(32, 24, 32, 32)
        workspace_layout.setSpacing(24)

        # 左侧控制面板
        left_panel = QFrame()
        left_panel.setStyleSheet(f"background-color: {BMW_COLORS['surface-soft']}; border: none; border-radius: 0px;")
        left_panel.setFixedWidth(360)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(24, 24, 24, 24)
        left_layout.setSpacing(12)

        panel_title = QLabel("项目控制与属性")
        panel_title.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        left_layout.addWidget(panel_title)

        # 双重读取入口排版布局
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_load_dir = QPushButton("📁 载入本地文件夹")
        self.btn_load_dir.setObjectName("SecondaryButton")
        self.btn_load_dir.setStyleSheet(
            f"color: {BMW_COLORS['primary']}; border-color: {BMW_COLORS['primary']}; background-color: #ffffff; padding: 10px 12px; font-size: 13px;")
        self.btn_load_dir.clicked.connect(self.load_from_local_directory)
        btn_box.addWidget(self.btn_load_dir)

        self.btn_load_history = QPushButton("📄 读取历史 MD")
        self.btn_load_history.setObjectName("SecondaryButton")
        self.btn_load_history.setStyleSheet(
            f"color: {BMW_COLORS['primary']}; border-color: {BMW_COLORS['primary']}; background-color: #ffffff; padding: 10px 12px; font-size: 13px;")
        self.btn_load_history.clicked.connect(self.load_from_history_md)
        btn_box.addWidget(self.btn_load_history)

        left_layout.addLayout(btn_box)

        # 时间回溯控制组
        history_title = QLabel("架构时间线回溯")
        history_title.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        left_layout.addWidget(history_title)

        timeline_box = QHBoxLayout()
        timeline_box.setSpacing(8)

        self.btn_undo = QPushButton("⏮ 撤销变更 (Undo)")
        self.btn_undo.setObjectName("SecondaryButton")
        self.btn_undo.setStyleSheet("padding: 8px; font-size: 12px;")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self.undo)
        timeline_box.addWidget(self.btn_undo)

        self.btn_redo = QPushButton("⏭ 重做变更 (Redo)")
        self.btn_redo.setObjectName("SecondaryButton")
        self.btn_redo.setStyleSheet("padding: 8px; font-size: 12px;")
        self.btn_redo.setEnabled(False)
        self.btn_redo.clicked.connect(self.redo)
        timeline_box.addWidget(self.btn_redo)

        left_layout.addLayout(timeline_box)

        left_layout.addWidget(QLabel("节点名称："))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如: src, main.py")
        self.name_input.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Light))
        left_layout.addWidget(self.name_input)

        left_layout.addWidget(QLabel("功能/角色说明 (向 Codex 表明用途)："))
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("例如: 负责核心算法 / 数据处理入口")
        self.desc_input.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Light))
        self.desc_input.setFixedHeight(100)
        left_layout.addWidget(self.desc_input)

        self.btn_update_node = QPushButton("修改当前选中节点")
        self.btn_update_node.setObjectName("SecondaryButton")
        self.btn_update_node.clicked.connect(self.update_selected_node)
        left_layout.addWidget(self.btn_update_node)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {BMW_COLORS['hairline']}; max-height: 1px;")
        left_layout.addWidget(line)

        self.btn_add_folder = QPushButton("+ 添加为子文件夹")
        self.btn_add_folder.setObjectName("SecondaryButton")
        self.btn_add_folder.clicked.connect(lambda: self.add_node(is_folder=True))
        left_layout.addWidget(self.btn_add_folder)

        self.btn_add_file = QPushButton("+ 添加为子文件")
        self.btn_add_file.setObjectName("SecondaryButton")
        self.btn_add_file.clicked.connect(lambda: self.add_node(is_folder=False))
        left_layout.addWidget(self.btn_add_file)

        self.btn_delete = QPushButton("删除选中节点")
        self.btn_delete.setObjectName("SecondaryButton")
        self.btn_delete.setStyleSheet("color: #dc2626;")
        self.btn_delete.clicked.connect(self.delete_node)
        left_layout.addWidget(self.btn_delete)

        left_layout.addStretch()

        # 生成并导出主动作 (内联渲染科技绿)
        self.btn_export = QPushButton("生成并导出 DESIGN.md")
        self.btn_export.setStyleSheet(f"""
            QPushButton {{
                background-color: {BMW_COLORS["success-green"]}; color: {BMW_COLORS["on-primary"]};
                border: none; border-radius: 0px; padding: 14px 24px; font-size: 14px; font-weight: 700;
            }}
            QPushButton:pressed {{ background-color: {BMW_COLORS["success-green-active"]}; }}
        """)
        self.btn_export.clicked.connect(self.export_to_markdown)
        left_layout.addWidget(self.btn_export)

        workspace_layout.addWidget(left_panel)

        # 右侧表现层：物理重排交互树
        self.tree = RobustTreeWidget()
        self.tree.setStyleSheet(
            f"background-color: {BMW_COLORS['surface-card']}; border: 1px solid {BMW_COLORS['hairline']}; border-radius: 0px; padding: 8px; color: {BMW_COLORS['ink']}; font-size: 14px;")
        self.tree.setHeaderLabels(["自定义项目架构树 (支持鼠标自由拖拽、排序与归类)"])
        self.tree.header().setStyleSheet(f"font-weight: 700; color: {BMW_COLORS['ink']};")
        self.tree.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Light))
        self.tree.itemClicked.connect(self.on_item_clicked)

        # 监听树状图内部由于拖拽物理落位引发的层级改变
        self.tree.model().rowsMoved.connect(lambda: self.save_snapshot())

        workspace_layout.addWidget(self.tree)
        outer_layout.addWidget(workspace)

    # --- 核心时间线回溯引擎 ---

    def _serialize_tree_to_data(self):
        """将当前的树形 UI 实体深度压缩提取为纯数据格式的扁平节点列表"""

        def recurse(item, indent_level=0):
            nodes = []
            node_type = item.data(0, Qt.ItemDataRole.UserRole)
            name = item.data(1, Qt.ItemDataRole.UserRole) or ""
            desc = item.data(2, Qt.ItemDataRole.UserRole) or ""

            nodes.append({
                'indent': indent_level * 2,
                'name': name,
                'desc': desc,
                'type': node_type
            })
            for i in range(item.childCount()):
                nodes.extend(recurse(item.child(i), indent_level + 1))
            return nodes

        serialized_data = []
        for i in range(self.tree.topLevelItemCount()):
            serialized_data.extend(recurse(self.tree.topLevelItem(i)))
        return serialized_data

    def save_snapshot(self, write_to_disk=True):
        """在任何写操作发生时，将当前右侧状态打包为不朽快照推入撤销栈，并静默写入本地缓存"""
        if self.block_snapshot:
            return

        current_state = self._serialize_tree_to_data()

        if self.undo_stack and self.undo_stack[-1] == current_state:
            return

        self.undo_stack.append(current_state)
        self.redo_stack.clear()
        self._update_timeline_buttons_status()

        # 🚀【功能升级：每次状态变更，实时同步持久化保存到本地隐藏文件中】
        if write_to_disk:
            save_last_session_cache(current_state)

    def auto_load_last_session(self):
        """🚀【新核心功能】启动时静默检查并加载最新一次的本地会话快照"""
        last_state = load_last_session_cache()
        if last_state:
            self.block_snapshot = True
            self._render_node_list_to_tree(last_state)
            self.block_snapshot = False

            # 将读取到的历史状态压入撤销栈，使得刚开机时也可以选择 Undo 撤销回最开始的空白状态
            self.undo_stack.append(last_state)
            self._update_timeline_buttons_status()

    def undo(self):
        """退回上一步"""
        if len(self.undo_stack) <= 1:
            return

        current_state = self.undo_stack.pop()
        self.redo_stack.append(current_state)
        previous_state = self.undo_stack[-1]

        self.block_snapshot = True
        self._render_node_list_to_tree(previous_state)
        self.block_snapshot = False

        self._update_timeline_buttons_status()
        # 撤销后，本地最新缓存也随之同步回滚
        save_last_session_cache(previous_state)

    def redo(self):
        """前进一步"""
        if not self.redo_stack:
            return

        next_state = self.redo_stack.pop()
        self.undo_stack.append(next_state)

        self.block_snapshot = True
        self._render_node_list_to_tree(next_state)
        self.block_snapshot = False

        self._update_timeline_buttons_status()
        # 重做后，本地最新缓存也随之同步前进
        save_last_session_cache(next_state)

    def _update_timeline_buttons_status(self):
        self.btn_undo.setEnabled(len(self.undo_stack) > 1)
        self.btn_redo.setEnabled(len(self.redo_stack) > 0)

    # --- UI 交互与渲染引擎 ---

    def _render_node_list_to_tree(self, node_list):
        self.tree.clear()
        self.name_input.clear()
        self.desc_input.clear()

        history_stack = []
        for node in node_list:
            new_item = QTreeWidgetItem()
            is_folder = node['type'] == 'folder'

            prefix = "📁 " if is_folder else "📄 "
            display_text = f"{prefix}{node['name']}"
            if node['desc']:
                display_text += f"  /* {node['desc']} */"

            new_item.setText(0, display_text)
            new_item.setData(0, Qt.ItemDataRole.UserRole, node['type'])
            new_item.setData(1, Qt.ItemDataRole.UserRole, node['name'])
            new_item.setData(2, Qt.ItemDataRole.UserRole, node['desc'])

            flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDragEnabled
            if is_folder:
                flags |= Qt.ItemFlag.ItemIsDropEnabled
            new_item.setFlags(flags)

            while history_stack and history_stack[-1][0] >= node['indent']:
                history_stack.pop()

            if not history_stack:
                self.tree.addTopLevelItem(new_item)
            else:
                history_stack[-1][1].addChild(new_item)
                self.tree.expandItem(history_stack[-1][1])

            history_stack.append((node['indent'], new_item))

    def load_from_local_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择你想要载入扫描的项目文件夹")
        if not dir_path:
            return

        try:
            node_list = scan_local_directory_to_tree_data(dir_path)
            if not node_list:
                QMessageBox.information(self, "提示", "所选文件夹为空。")
                return

            self._render_node_list_to_tree(node_list)
            self.save_snapshot()
            QMessageBox.information(self, "载入成功", f"成功抓取了本地项目物理架构！")
        except Exception as e:
            QMessageBox.critical(self, "系统故障", f"无法读取该本地文件夹: {str(e)}")

    def load_from_history_md(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "读取历史架构蓝图", "history", "Markdown 规范文件 (*.md)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                md_content = f.read()

            node_list = parse_markdown_to_tree_data(md_content)
            if not node_list:
                QMessageBox.warning(self, "恢复终止", "未能在此文件中找到匹配的标准 ```text 架构区块。")
                return

            self._render_node_list_to_tree(node_list)
            self.save_snapshot()
            QMessageBox.information(self, "架构恢复成功", f"成功从历史文件中逆向加载了架构节点！")
        except Exception as e:
            QMessageBox.critical(self, "系统故障", f"逆向解析历史架构文件失败: {str(e)}")

    def add_node(self, is_folder):
        name = self.name_input.text().strip()
        desc = self.desc_input.toPlainText().strip()
        if not name:
            QMessageBox.warning(self, "验证错误", "节点名称不能为空。")
            return

        selected_items = self.tree.selectedItems()
        if selected_items:
            parent = selected_items[0]
            if parent.data(0, Qt.ItemDataRole.UserRole) == "file":
                QMessageBox.warning(self, "结构错误", "无法在文件内创建子项。")
                return
            new_item = QTreeWidgetItem(parent)
            self.tree.expandItem(parent)
        else:
            new_item = QTreeWidgetItem(self.tree)

        flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsDragEnabled
        if is_folder:
            flags |= Qt.ItemFlag.ItemIsDropEnabled
        new_item.setFlags(flags)

        prefix = "📁 " if is_folder else "📄 "
        display_text = f"{prefix}{name}"
        if desc:
            display_text += f"  /* {desc} */"

        new_item.setText(0, display_text)
        new_item.setData(0, Qt.ItemDataRole.UserRole, "folder" if is_folder else "file")
        new_item.setData(1, Qt.ItemDataRole.UserRole, name)
        new_item.setData(2, Qt.ItemDataRole.UserRole, desc)

        self.name_input.clear()
        self.desc_input.clear()

        self.save_snapshot()

    def on_item_clicked(self, item, column):
        self.name_input.setText(item.data(1, Qt.ItemDataRole.UserRole) or "")
        self.desc_input.setText(item.data(2, Qt.ItemDataRole.UserRole) or "")

    def update_selected_node(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先在右侧点击选中一个项目。")
            return

        item = selected_items[0]
        new_name = self.name_input.text().strip()
        new_desc = self.desc_input.toPlainText().strip()

        if not new_name:
            QMessageBox.warning(self, "验证错误", "名称不能为空。")
            return

        node_type = item.data(0, Qt.ItemDataRole.UserRole)
        prefix = "📁 " if node_type == "folder" else "📄 "
        display_text = f"{prefix}{new_name}"
        if new_desc:
            display_text += f"  /* {new_desc} */"

        item.setText(0, display_text)
        item.setData(1, Qt.ItemDataRole.UserRole, new_name)
        item.setData(2, Qt.ItemDataRole.UserRole, new_desc)

        self.save_snapshot()

    def delete_node(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            (item.parent() or self.tree.invisibleRootItem()).removeChild(item)
        self.name_input.clear()
        self.desc_input.clear()

        self.save_snapshot()

    def export_to_markdown(self):
        if self.tree.topLevelItemCount() == 0:
            QMessageBox.warning(self, "导出终止", "当前项目架构为空。")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "生成架构蓝图", "history/DESIGN.md", "Markdown 规范文件 (*.md)"
        )

        if file_path:
            md_template = generate_markdown_text(self.tree)
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(md_template)
                QMessageBox.information(self, "导出成功", "工程架构规范已存入历史库！")
            except Exception as e:
                QMessageBox.critical(self, "系统错误", f"文件导出失败: {str(e)}")