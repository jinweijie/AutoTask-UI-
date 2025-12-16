from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class StepTableHelper:
    """负责把步骤对象渲染成表格行的工具类，可放到主窗口里复用"""

    FIXED_ROW_HEIGHT = 32
    ICON_SIZE = 20
    IMG_HEIGHT = 32

    @staticmethod
    def thumb_widget(img_path: str, row_height: int) -> QWidget:
        """返回一个已设置好缩略图的 QLabel，高度=row_height，宽度自适应"""
        label = QLabel()
        label.setScaledContents(True)
        label.setAlignment(Qt.AlignCenter)

        # 读图并缩放到行高
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaledToHeight(row_height, Qt.SmoothTransformation)
        label.setPixmap(pixmap)

        # 用 QWidget 包一层，方便后续扩展
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.addWidget(label)
        return w

    @staticmethod
    def type_widget(step_type: str, use_color: bool = True) -> QWidget:
        """
        创建一个用于显示步骤类型的QWidget容器，可以直接添加到表格中

        Args:
            step_type: 步骤类型
            use_color: 是否使用彩色样式，False时使用黑灰色调样式

        Returns:
            QWidget: 包含图标和类型标签的容器
        """
        # 创建主容器
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setAlignment(Qt.AlignCenter)

        # 创建图标标签
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 14px; margin-right: 5px;")

        # 根据步骤类型设置对应图标
        icons = {
            "鼠标点击": "🖱️",
            "文本输入": "⌨️",
            "等待": "⏱️",
            "截图": "📸",
            "拖拽": "✋",
            "鼠标滚轮": "🖱️",  # 使用相同图标但可以区分
            "键盘热键": "⌨️",
            "AI 自动回复": "🤖",
        }

        icon_text = icons.get(step_type, "❓")  # 默认问号图标
        icon_label.setText(icon_text)

        # 创建类型标签
        type_label = QLabel(step_type)
        type_label.setAlignment(Qt.AlignCenter)

        # 设置样式
        if not use_color:
            # 统一使用黑灰色调
            type_label.setStyleSheet("""color:#ffffff;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #555555,stop:0.5 #777777,stop:1 #999999);
    border-radius:6px;
    padding:2px 6px;
    font-weight:bold;""")
        else:
            # 根据不同类型返回不同颜色样式
            styles = {
                "鼠标点击": """color:#ffffff;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #a8c0ff,stop:1 #a8c0ff);
    border-radius:6px;
    padding:2px 6px;
    font-weight:bold;""",
                "文本输入": """color:#ffffff;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #d4fc79,stop:1 #96e6a1);
    border-radius:6px;
    padding:2px 6px;
    font-weight:bold;""",
                "等待": """color:#ffffff;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #f6d365,stop:1 #fda085);
    border-radius:6px;
    padding:2px 6px;
    font-weight:bold;""",
                "截图": """color:#ffffff;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #84fab0,stop:1 #8fd3f4);
    border-radius:6px;
    padding:2px 6px;
    font-weight:bold;""",
                "拖拽": """color:#ffffff;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #fbc2eb,stop:1 #a6c1ee);
    border-radius:6px;
    padding:2px 6px;
    font-weight:bold;""",
                "鼠标滚轮": """color:#ffffff;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #a6c0fe,stop:1 #f68084);
    border-radius:6px;
    padding:2px 6px;
    font-weight:bold;""",
                "键盘热键": """color:#ffffff;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #d299c2,stop:1 #fef9d7);
    border-radius:6px;
    padding:2px 6px;
    font-weight:bold;""",
                "AI 自动回复": """color:#ffffff;
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #a6c0fe,stop:1 #f68084);
            border-radius:6px;
            padding:2px 6px;
            font-weight:bold;""",  # 添加这一行
            }

            # 设置对应样式或默认样式
            style = styles.get(
                step_type,
                """color:#ffffff;
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e5e5e5,stop:0.5 #bdbdbd,stop:1 #9e9e9e);
    border-radius:6px;
    padding:2px 6px;
    font-weight:bold;""",
            )
            type_label.setStyleSheet(style)

        # 添加到布局
        layout.addWidget(icon_label)
        layout.addWidget(type_label)

        return container
