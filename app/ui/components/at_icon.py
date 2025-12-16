from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)


class ATIcon:
    """
    为「Auto Tool」桌面自动办公软件生成一枚
    64×64 带毛玻璃效果、渐变背景的「AT」图标。
    """

    SIZE = 64
    _cache = {}  # 缓存，避免重复渲染

    @classmethod
    def pixmap(cls, size=SIZE) -> QPixmap:
        """返回渲染好的 QPixmap，可自由缩放"""
        if size in cls._cache:
            return cls._cache[size]

        px = QPixmap(size, size)
        px.fill(Qt.transparent)

        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)

        # 1. 圆角矩形背景 -------------------------------------------------
        rect = QRectF(0, 0, size, size)
        radius = size * 0.18
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        # 2. 渐变填充 ------------------------------------------------------
        g = QLinearGradient(QPointF(0, 0), QPointF(size, size))
        g.setColorAt(0.0, QColor("#6A11CB"))  # 紫
        g.setColorAt(1.0, QColor("#2575FC"))  # 蓝
        p.fillPath(path, QBrush(g))

        # 3. 毛玻璃：一层极低不透明度白色蒙版 -------------------------------
        blur_layer = QPainterPath()
        blur_layer.addRoundedRect(rect, radius, radius)
        p.fillPath(blur_layer, QColor(255, 255, 255, 35))

        # 4. 字母 “AT” ----------------------------------------------------
        font = QFont("Segoe UI", size * 0.32, QFont.Bold)
        p.setFont(font)
        p.setPen(QPen(Qt.white))
        p.drawText(rect, Qt.AlignCenter, "AT")

        p.end()
        cls._cache[size] = px
        return px

    @classmethod
    def icon(cls, size=SIZE) -> QIcon:
        """直接拿到 QIcon，可设给窗口、托盘、按钮等"""
        return QIcon(cls.pixmap(size))
