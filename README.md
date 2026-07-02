[README.md](https://github.com/user-attachments/files/29594871/README.md)
# BMW Corporate - 架构规格设计与历史回溯系统

基于 Python 3 与 PyQt6 构建的企业级软件架构蓝图 spec 生成器。支持通过可视化树状图调整工程骨架，并支持历史架构的双向正逆向解析。

## 🛠️ 项目结构
- `main.py`: 程序主启动入口
- `src/`: 核心业务逻辑层（Markdown 正逆向双向转换引擎）
- `ui/`: 表现层（高级拖拽树组件与 BMW 规范主界面）
- `history/`: 历史生成的 `DESIGN.md` 文件固化库

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
