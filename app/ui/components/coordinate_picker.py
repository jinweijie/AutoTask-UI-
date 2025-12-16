from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QWidget


class CoordinatePickerOverlay(QDialog):
    """
    坐标拾取覆盖层，用于获取鼠标位置坐标
    """

    coordinate_selected = Signal(tuple)  # 发送选中的坐标 (x, y)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # 关键：不遮挡鼠标
        self.setModal(True)

        # 关键修复：设置窗口可接受焦点
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

        # 获取屏幕信息和缩放比例
        self.screen = QApplication.primaryScreen()
        self.screen_geometry = self.screen.geometry()
        self.device_pixel_ratio = self.screen.devicePixelRatio()

        # 覆盖全屏
        self.setGeometry(self.screen_geometry)

        # 坐标显示标签
        self.coord_label = QLabel(self)
        self.coord_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 180);
            color: #00FF00;
            padding: 8px 12px;
            border-radius: 4px;
            font-family: Consolas, monospace;
            font-size: 14px;
            border: 1px solid #00FF00;
        """)
        self.coord_label.hide()

        # 提示标签
        self.tip_label = QLabel(
            "【坐标拾取模式】\n移动鼠标查看坐标\n按 Enter / 点击左键 确认\n按 Esc 取消",
            self,
        )
        self.tip_label.setAlignment(Qt.AlignCenter)
        self.tip_label.setStyleSheet("""
            background-color: rgba(255, 255, 255, 220);
            color: #FFA500;
            padding: 10px 16px;
            border-radius: 6px;
            font-family: Microsoft YaHei, sans-serif;
            font-size: 12px;
            border: 2px solid rgba(255, 165, 0, 150);
            font-weight: bold;
        """)
        self.tip_label.hide()

        # 定时器用于更新坐标显示
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_position)
        self.timer.start(16)  # ~60fps

        # 跟踪鼠标位置
        self.current_pos = QPoint(0, 0)
        self.raw_pos = QPoint(0, 0)  # 原始坐标

        # 显示提示信息
        QTimer.singleShot(100, self.show_tip)

        # 放大镜部件
        self.magnifier = QWidget(self)
        self.magnifier.setFixedSize(120, 120)
        self.magnifier.hide()  # 默认隐藏，或者可以实现放大镜功能

    def show_tip(self):
        """显示操作提示"""
        self.tip_label.show()
        self.tip_label.adjustSize()

        # 将提示标签定位在屏幕中央底部
        tip_x = (self.screen_geometry.width() - self.tip_label.width()) // 2
        tip_y = self.screen_geometry.height() - 100
        self.tip_label.move(tip_x, tip_y)

    def showEvent(self, event):
        """窗口显示时自动获取焦点"""
        super().showEvent(event)
        self.setFocus()
        self.activateWindow()
        # 确保窗口在最前面
        self.raise_()
        self.timer.start(16)

    def hideEvent(self, event):
        """窗口隐藏时停止定时器"""
        super().hideEvent(event)
        self.timer.stop()

    def exec_(self):
        """重写exec_方法确保焦点正确设置"""
        self.setFocus()
        self.activateWindow()
        self.raise_()
        return super().exec_()

    def get_scaled_coordinates(self, pos):
        """
        获取缩放校正后的坐标
        返回调整后的坐标和原始坐标
        """
        raw_x, raw_y = pos.x(), pos.y()

        # 方法1: 使用设备像素比例校正
        scaled_x = int(raw_x * self.device_pixel_ratio)
        scaled_y = int(raw_y * self.device_pixel_ratio)

        # 方法2: 备用方法 - 使用屏幕虚拟大小
        virtual_geometry = self.screen.virtualGeometry()
        if virtual_geometry.width() != self.screen_geometry.width():
            scale_factor = virtual_geometry.width() / self.screen_geometry.width()
            scaled_x = int(raw_x * scale_factor)
            scaled_y = int(raw_y * scale_factor)

        return (scaled_x, scaled_y), (raw_x, raw_y)

    def update_position(self):
        """更新鼠标位置显示"""
        mouse_pos = QCursor.pos()
        self.raw_pos = mouse_pos

        # 获取校正后的坐标
        scaled_coords, raw_coords = self.get_scaled_coordinates(mouse_pos)
        self.current_pos = QPoint(scaled_coords[0], scaled_coords[1])

        # 更新坐标标签文本
        coord_text = f"坐标: {scaled_coords[0]}, {scaled_coords[1]}"
        coord_text += f"\n原始: {raw_coords[0]}, {raw_coords[1]}"
        coord_text += f"\n缩放: {self.device_pixel_ratio:.1f}x"

        self.coord_label.setText(coord_text)
        self.coord_label.adjustSize()

        # 标签定位（避免超出屏幕边界）
        label_x = mouse_pos.x() + 25
        label_y = mouse_pos.y() + 25

        if label_x + self.coord_label.width() > self.screen_geometry.width():
            label_x = mouse_pos.x() - self.coord_label.width() - 15
        if label_y + self.coord_label.height() > self.screen_geometry.height():
            label_y = mouse_pos.y() - self.coord_label.height() - 15

        self.coord_label.move(label_x, label_y)
        self.coord_label.show()

    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            print(
                f"[DEBUG] 确认坐标 - 原始: ({self.raw_pos.x()}, {self.raw_pos.y()}), "
                f"校正: ({self.current_pos.x()}, {self.current_pos.y()})"
            )
            self.coordinate_selected.emit((self.current_pos.x(), self.current_pos.y()))
            self.accept()
        elif event.key() == Qt.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key_Space:
            # 空格键切换放大镜显示
            self.magnifier.setVisible(not self.magnifier.isVisible())
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        """鼠标点击时也确认坐标"""
        if event.button() == Qt.LeftButton:
            print(
                f"[DEBUG] 鼠标确认坐标 - 原始: ({self.raw_pos.x()}, {self.raw_pos.y()}), "
                f"校正: ({self.current_pos.x()}, {self.current_pos.y()})"
            )
            self.coordinate_selected.emit((self.current_pos.x(), self.current_pos.y()))
            self.accept()
        else:
            super().mousePressEvent(event)
