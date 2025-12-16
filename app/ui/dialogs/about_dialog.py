import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.utils import resource_path


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AboutDialog")
        self.setWindowTitle("关于")
        self.setModal(True)
        self.resize(480, 520)

        # 根布局
        root = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        lay = QVBoxLayout(content)
        lay.setAlignment(Qt.AlignTop)

        # 1. 标题
        title = QLabel("自动化任务管理器")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)
        # 2. 版本 + 作者 + 头像
        author_layout = QHBoxLayout()
        author_layout.setSpacing(12)

        # 头像
        self.avatar = QLabel()
        self.avatar.setFixedSize(64, 64)
        self.avatar.setObjectName("avatarLabel")
        self.load_avatar()

        # 作者信息
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.addRow("版　本：", QLabel("1.0.0"))
        form.addRow("作　者：", QLabel("B_arbarian from UESTC"))
        author_layout.addWidget(self.avatar)
        author_layout.addLayout(form)
        author_layout.addStretch()
        lay.addLayout(author_layout)
        # 3. 联系方式（带超链接）
        link_lbl = QLabel(
            'B站主页：<a href="https://space.bilibili.com/521967044">'
            '<span style="color:#409EFF;">点击访问</span></a><br>'
            '邮　　箱：<a href="mailto:264214429@qq.com">'
            '<span style="color:#409EFF;">264214429@qq.com</span></a>'
        )
        link_lbl.setObjectName("linkLabel")
        link_lbl.setOpenExternalLinks(True)
        link_lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
        lay.addWidget(link_lbl, alignment=Qt.AlignCenter)

        # 4. 简介
        intro = QTextEdit()
        intro.setObjectName("introText")
        intro.setMaximumHeight(180)
        intro.setPlainText(
            "自动化任务管理器是一款强大的桌面自动化工具，可以帮助您自动化执行重复的计算机操作，提高工作效率。\n\n"
            "主要功能：\n"
            "• 基于图像识别的鼠标操作\n"
            "• 文本输入自动化\n"
            "• 定时任务执行\n"
            "• 详细执行日志记录\n\n"
            "感谢使用本软件！如有任何问题或建议，请通过上述联系方式与我们联系。"
        )
        lay.addWidget(intro)
        # 5. 打赏二维码
        qr_lay = QHBoxLayout()
        qr_lay.setSpacing(16)
        qr_lay.addStretch()

        self.wx_qr = QLabel()
        self.wx_qr.setObjectName("qrLabel")
        self.wx_qr.setFixedSize(160, 160)
        self.load_qr(self.wx_qr, "img/donate.png", "微信赞赏")

        self.zfb_qr = QLabel()
        self.zfb_qr.setObjectName("qrLabel")
        self.zfb_qr.setFixedSize(160, 160)
        self.load_qr(self.zfb_qr, "img/zhifubao.jpg", "支付宝打赏")

        qr_lay.addWidget(self.wx_qr)
        qr_lay.addWidget(self.zfb_qr)
        qr_lay.addStretch()
        lay.addLayout(qr_lay)

        # 6. 按钮
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(self.accept)
        root.addWidget(btn_box)

        # 7. 加载样式
        self.load_qss()

    # ---------- 私有方法 ----------
    def load_avatar(self):
        avatar_path = "img/avatar.jpg"
        pixmap = QPixmap(avatar_path)
        if pixmap.isNull():
            self.avatar.setText("头像")
            return

        size = self.avatar.width()
        rounded = QPixmap(size, size)
        rounded.fill(Qt.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, size, size, size // 2, size // 2)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, size, size, pixmap)
        painter.end()

        self.avatar.setPixmap(rounded)

    def load_qr(self, label: QLabel, path: str, alt: str):
        path = resource_path(path)
        pixmap = QPixmap(path)
        if pixmap.isNull():
            label.setText(f"{alt}\n加载失败")
            label.setAlignment(Qt.AlignCenter)
            return
        label.setPixmap(
            pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def load_qss(self):
        try:
            # app/ui/dialogs/about_dialog.py -> ... -> root
            root_dir = Path(__file__).resolve().parent.parent.parent.parent
            qss_path = root_dir / "css" / "about_style.qss"

            if qss_path.exists():
                with open(qss_path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
            else:
                # Try resource path if frozen
                if hasattr(sys, "frozen"):
                    qss_path = Path(resource_path("css/about_style.qss"))
                    if qss_path.exists():
                        with open(qss_path, "r", encoding="utf-8") as f:
                            self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Error loading QSS: {e}")
