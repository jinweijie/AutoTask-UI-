import os
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
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

    @staticmethod
    def widget_of(step: dict, use_color: bool = True) -> QWidget:
        """
        返回一个可直接塞进 QTableWidget 的 QWidget，
        内部 QLabel 负责显示图标/文字/图片 + 时间
        """
        t = step["type"]
        p = step["params"]
        time_str = p.get("step_time", datetime.now().strftime("%H:%M:%S"))

        # 主容器
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)

        # 左侧图标或图片
        icon_label = QLabel()
        icon_label.setFixedSize(StepTableHelper.ICON_SIZE, StepTableHelper.ICON_SIZE)
        icon_label.setScaledContents(True)

        # 中间文字/图片
        content_label = QLabel()
        content_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        content_label.setStyleSheet("""color:#ffffff;
background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e5e5e5,stop:0.5 #bdbdbd,stop:1 #9e9e9e);
border-radius:6px;
padding:2px 6px;
font-weight:bold;""")

        # 右侧时间
        time_label = QLabel(time_str)
        time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        font = QFont()
        font.setPointSize(8)
        time_label.setFont(font)
        # 在 time_label 设置样式之前添加以下代码
        # 将时间字符串转换为颜色值
        time_obj = datetime.strptime(time_str, "%H:%M:%S")
        hour = time_obj.hour
        # minute = time_obj.minute
        # second = time_obj.second
        # 根据小时数生成低饱和度渐变色
        # 早晨(6-12): 蓝绿色调
        if 6 <= hour < 12:
            # 从浅蓝到浅绿的渐变（饱和度×1.3）
            r1, g1, b1 = 152, 196, 211  # 原 173,216,230
            r2, g2, b2 = 114, 227, 114  # 原 144,238,144

        elif 12 <= hour < 18:
            # 从浅黄到浅橙的渐变（饱和度×1.3）
            r1, g1, b1 = 255, 255, 159  # 原 255,255,224
            r2, g2, b2 = 255, 198, 137  # 原 255,218,185

        elif 18 <= hour < 21:
            # 从浅粉到浅紫的渐变（饱和度×1.3）
            r1, g1, b1 = 255, 156, 169  # 原 255,182,193
            r2, g2, b2 = 214, 214, 238  # 原 230,230,250

        else:  # 21-6 夜晚
            # 从浅蓝到浅紫的渐变（饱和度×1.3）
            r1, g1, b1 = 230, 238, 245  # 原 240,248,255
            r2, g2, b2 = 214, 214, 238  # 原 230,230,250
        if use_color:
            time_label.setStyleSheet(f"""color:#ffffff;
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 rgb({r1},{g1},{b1}),stop:1 rgb({r2},{g2},{b2}));
            border-radius:10px;
            padding:2px 6px;
            font-weight:bold;""")
        else:
            time_label.setStyleSheet("""color:#ffffff;
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e5e5e5,stop:0.5 #bdbdbd,stop:1 #9e9e9e);
            border-radius:6px;
            padding:2px 6px;
            font-weight:bold;""")

        # 根据类型生成内容
        if t == "鼠标点击":
            use_image = p.get("use_image", True)
            use_coordinates = p.get("use_coordinates", False)

            if use_image:
                img_path = p.get("image_path", "")
                click_type = p.get("click_type", "左键单击")
                if os.path.isfile(img_path):
                    pm = QPixmap(img_path).scaledToHeight(
                        StepTableHelper.IMG_HEIGHT, Qt.SmoothTransformation
                    )
                    icon_label.setPixmap(pm)
                else:
                    icon_label.setText("🖼️")
                content_label.setText(f"{click_type}\n图片模式")

            elif use_coordinates:
                x_coord = p.get("x_coordinate", 0)
                y_coord = p.get("y_coordinate", 0)
                click_type = p.get("click_type", "左键单击")
                icon_label.setText("📍")
                content_label.setText(f"{click_type}\n坐标({x_coord},{y_coord})")

            else:
                icon_label.setText("❓")
                content_label.setText("未设置模式")
            click_type = p.get("click_type", "左键单击")
            # 为不同点击类型设置不同的低饱和度渐变背景
            if use_color:
                if click_type == "左键单击":
                    content_label.setStyleSheet("""color:#ffffff;
                        background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #a8c0ff,stop:1 #a8c0ff);
                        border-radius:6px;padding:2px 6px;font-weight:bold;""")
                elif click_type == "左键双击":
                    content_label.setStyleSheet("""color:#ffffff;
                        background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #d4fc79,stop:1 #96e6a1);
                        border-radius:6px;padding:2px 6px;font-weight:bold;""")
                elif click_type == "右键单击":
                    content_label.setStyleSheet("""color:#ffffff;
                        background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #f6d365,stop:1 #fda085);
                        border-radius:6px;padding:2px 6px;font-weight:bold;""")
                elif click_type == "中键单击":
                    content_label.setStyleSheet("""color:#ffffff;
                        background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #84fab0,stop:1 #8fd3f4);
                        border-radius:6px;padding:2px 6px;font-weight:bold;""")
            else:
                # 默认样式（如果出现其他点击类型）
                content_label.setStyleSheet("""color:#ffffff;
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e5e5e5,stop:0.5 #bdbdbd,stop:1 #9e9e9e);
                    border-radius:6px;padding:2px 6px;font-weight:bold;""")

        elif t == "文本输入":
            txt = p.get("text", "")
            if txt:
                txt = txt[:10] + "…" if len(txt) > 10 else txt
                content_label.setText(txt)
            else:
                mode = p.get("mode", "顺序")
                file = os.path.basename(p.get("excel_path", ""))
                content_label.setText(f"{mode}·{file}")
            icon_label.setText("⌨")
            # 设置低饱和度渐变背景
            if use_color:
                content_label.setStyleSheet("""color:#ffffff;
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #d4fc79,stop:1 #96e6a1);
                    border-radius:6px;padding:2px 6px;font-weight:bold;""")
            else:
                content_label.setStyleSheet("""color:#ffffff;
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e5e5e5,stop:0.5 #bdbdbd,stop:1 #9e9e9e);
                    border-radius:6px;padding:2px 6px;font-weight:bold;""")

        elif t == "等待":
            content_label.setText(f"{p.get('seconds', 0)}s")
            icon_label.setText("⏱")
            # 设置低饱和度渐变背景
            if use_color:
                content_label.setStyleSheet("""color:#ffffff;
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #f6d365,stop:1 #fda085);
                    border-radius:6px;padding:2px 6px;font-weight:bold;""")
            else:
                content_label.setStyleSheet("""color:#ffffff;
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e5e5e5,stop:0.5 #bdbdbd,stop:1 #9e9e9e);
                    border-radius:6px;padding:2px 6px;font-weight:bold;""")

        elif t == "截图":
            save_path = p.get("save_path", "")
            if os.path.isfile(save_path):
                pm = QPixmap(save_path).scaledToHeight(
                    StepTableHelper.IMG_HEIGHT, Qt.SmoothTransformation
                )
                content_label.setPixmap(pm)
            else:
                content_label.setText(os.path.basename(save_path))
            icon_label.setText("📸")

        elif t == "鼠标滚轮":
            dire = p.get("direction", "向下")
            clicks = p.get("clicks", 3)
            content_label.setText(f"{dire}{clicks}格")
            icon_label.setText("⚙")
            # 设置低饱和度渐变背景
            if use_color:
                content_label.setStyleSheet("""color:#ffffff;
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #a6c0fe,stop:1 #f68084);
                    border-radius:6px;padding:2px 6px;font-weight:bold;""")
            else:
                content_label.setStyleSheet("""color:#ffffff;
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e5e5e5,stop:0.5 #bdbdbd,stop:1 #9e9e9e);
                    border-radius:6px;padding:2px 6px;font-weight:bold;""")

        elif t == "键盘热键":
            hotkey = p.get("hotkey", "ctrl+c").upper()
            delay = p.get("delay_ms", 100)
            content_label.setText(f"{hotkey}")
            time_label.setText(f"{delay} ms")
            icon_label.setText("⌨")
            # 设置低饱和度渐变背景
            if use_color:
                content_label.setStyleSheet("""color:#ffffff;
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #d299c2,stop:1 #fef9d7);
                    border-radius:6px;padding:2px 6px;font-weight:bold;""")
            else:
                content_label.setStyleSheet("""color:#ffffff;
                    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e5e5e5,stop:0.5 #bdbdbd,stop:1 #9e9e9e);
                    border-radius:6px;padding:2px 6px;font-weight:bold;""")
        elif t == "拖拽":
            use_image = p.get("use_image", True)
            # 清除可能存在的旧图片
            icon_label.setText("")
            icon_label.setPixmap(QPixmap())

            if use_image:
                img_path = p.get("image_path", "")
                # 根据拖拽方向确定显示文本
                dx, dy = p.get("drag_x", 0), p.get("drag_y", 100)
                if dx == 0 and dy > 0:
                    content_label.setText("↓下拉")
                    content_label.setStyleSheet("""color:#ffffff;
                            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #a8c0ff,stop:1 #a8c0ff);
                            border-radius:6px;padding:2px 6px;font-weight:bold;""")
                elif dx == 0 and dy < 0:
                    content_label.setText("↑上拉")
                    content_label.setStyleSheet("""color:#ffffff;
                            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #d4fc79,stop:1 #96e6a1);
                            border-radius:6px;padding:2px 6px;font-weight:bold;""")
                elif dx > 0 and dy == 0:
                    content_label.setText("→右拉")
                    content_label.setStyleSheet("""color:#ffffff;
                            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #f6d365,stop:1 #fda085);
                            border-radius:6px;padding:2px 6px;font-weight:bold;""")
                elif dx < 0 and dy == 0:
                    content_label.setText("←左拉")
                    content_label.setStyleSheet("""color:#ffffff;
                            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #84fab0,stop:1 #8fd3f4);
                            border-radius:6px;padding:2px 6px;font-weight:bold;""")
                else:
                    content_label.setText(f"图像拖拽 ({dx},{dy})")
                    content_label.setStyleSheet("""color:#ffffff;
                            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #fbc2eb,stop:1 #a6c1ee);
                            border-radius:6px;padding:2px 6px;font-weight:bold;""")
                if not use_color:
                    content_label.setStyleSheet("""color:#ffffff;
                        background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e5e5e5,stop:0.5 #bdbdbd,stop:1 #9e9e9e);
                        border-radius:6px;padding:2px 6px;font-weight:bold;""")

                # 在icon_label中显示图片缩略图
                if os.path.isfile(img_path):
                    pm = QPixmap(img_path).scaledToHeight(
                        StepTableHelper.ICON_SIZE, Qt.SmoothTransformation
                    )
                    icon_label.setPixmap(pm)
                else:
                    icon_label.setText("✋")  # 图片不存在时显示手型图标
            else:
                sx, sy = p.get("start_x", 0), p.get("start_y", 0)
                ex, ey = p.get("end_x", 0), p.get("end_y", 0)
                # 根据坐标变化显示箭头
                dx, dy = ex - sx, ey - sy
                if dx == 0 and dy > 0:
                    content_label.setText("↓下拉")
                    content_label.setStyleSheet("""color:#ffffff;
                            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #a8c0ff,stop:1 #a8c0ff);
                            border-radius:6px;padding:2px 6px;font-weight:bold;""")
                elif dx == 0 and dy < 0:
                    content_label.setText("↑上拉")
                    content_label.setStyleSheet("""color:#ffffff;
                            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #d4fc79,stop:1 #96e6a1);
                            border-radius:6px;padding:2px 6px;font-weight:bold;""")
                elif dx > 0 and dy == 0:
                    content_label.setText("→右拉")
                    content_label.setStyleSheet("""color:#ffffff;
                            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #f6d365,stop:1 #fda085);
                            border-radius:6px;padding:2px 6px;font-weight:bold;""")
                elif dx < 0 and dy == 0:
                    content_label.setText("←左拉")
                    content_label.setStyleSheet("""color:#ffffff;
                            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #84fab0,stop:1 #8fd3f4);
                            border-radius:6px;padding:2px 6px;font-weight:bold;""")
                else:
                    content_label.setText(f"坐标拖拽 ({sx},{sy})→({ex},{ey})")
                    content_label.setStyleSheet("""color:#ffffff;
                            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #fbc2eb,stop:1 #a6c1ee);
                            border-radius:6px;padding:2px 6px;font-weight:bold;""")
                if not use_color:
                    content_label.setStyleSheet("""color:#ffffff;
                        background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e5e5e5,stop:0.5 #bdbdbd,stop:1 #9e9e9e);
                        border-radius:6px;padding:2px 6px;font-weight:bold;""")
                icon_label.setText("✋")
        elif t == "AI 自动回复":
            provider = p.get("provider", "kimi")
            content_label.setText(f"{provider}")
            icon_label.setText("🤖")

            # 设置样式
            if use_color:
                content_label.setStyleSheet("""color:#ffffff;
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #a6c0fe,stop:1 #f68084);
            border-radius:6px;
            padding:2px 6px;
            font-weight:bold;""")
            else:
                content_label.setStyleSheet("""color:#ffffff;
            background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #e5e5e5,stop:0.5 #bdbdbd,stop:1 #9e9e9e);
            border-radius:6px;
            padding:2px 6px;
            font-weight:bold;""")
        else:
            content_label.setText(t)
            icon_label.setText("?")

        # 加入布局
        layout.addWidget(icon_label)
        layout.addWidget(content_label, 1)  # 伸缩
        layout.addWidget(time_label)

        return container
