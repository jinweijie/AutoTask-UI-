from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QScreen,
)
from PySide6.QtWidgets import QApplication, QWidget


class RegionCaptureOverlay(QWidget):
    """
    区域截图覆盖层，用于选择屏幕区域
    支持多屏幕、放大镜、网格显示等功能
    """

    finished = Signal(QRect)  # 自选区确认信号
    cancelled = Signal()  # 取消操作信号

    def __init__(self, background_pixmap=None):
        super().__init__(None)
        # ... existing code ...
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)

        # 多屏幕支持
        self.screens = QApplication.screens()
        self.setGeometry(self._get_combined_screen_geometry())

        # 背景截图 - 如果未传入，尝试自动补救截取（此时可能包含淡出动画，但也比递归好）
        if background_pixmap and not background_pixmap.isNull():
            print("✅ RegionCaptureOverlay received valid background_pixmap")
            self.background_pixmap = background_pixmap
        else:
            print(
                "⚠️ RegionCaptureOverlay received None/Null pixmap, attempting self-capture..."
            )
            self.background_pixmap = QApplication.primaryScreen().grabWindow(0)
            if self.background_pixmap.isNull():
                print("❌ Self-capture failed! background_pixmap is Null")
            else:
                print("✅ Self-capture successful")

        # 设置窗口属性
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.setFocus()

        # 选择状态
        self.start_pos = QPoint()
        self.end_pos = QPoint()
        self.is_selecting = False
        self.current_mouse_pos = QPoint()

        # 放大镜配置
        self.magnifier_size = 200
        self.magnification = 3
        self.show_magnifier = True

        # 网格和参考线
        self.show_grid = False
        self.show_crosshair = True

        # 性能优化
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update)
        self.last_mouse_pos = QPoint()

        # UI配置
        self.overlay_color = QColor(0, 0, 0, 120)
        self.selection_color = QColor(255, 0, 0, 180)
        self.info_bg_color = QColor(0, 0, 0, 200)
        self.grid_color = QColor(255, 255, 255, 80)
        self.crosshair_color = QColor(255, 255, 255, 120)

        # 背景截图
        self.background_pixmap = background_pixmap

    def _get_combined_screen_geometry(self):
        """获取所有屏幕的合并几何区域"""
        combined = QRect()
        for screen in self.screens:
            combined = combined.united(screen.geometry())
        return combined

    def _get_screen_at_point(self, point: QPoint) -> QScreen:
        """获取指定点所在的屏幕"""
        for screen in self.screens:
            if screen.geometry().contains(point):
                return screen
        return QApplication.primaryScreen()

    def keyPressEvent(self, event: QKeyEvent):
        """处理键盘事件"""
        if event.key() == Qt.Key_Escape:
            self.cancel_capture()
        elif event.key() == Qt.Key_Space:
            # 空格键切换放大镜显示
            self.show_magnifier = not self.show_magnifier
            self.update()
        elif event.key() == Qt.Key_G:
            # G键切换网格显示
            self.show_grid = not self.show_grid
            self.update()
        elif event.key() == Qt.Key_C:
            # C键切换十字线显示
            self.show_crosshair = not self.show_crosshair
            self.update()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # 回车键确认当前选区
            self.confirm_selection()
        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            # 增加放大倍数
            self.magnification = min(8, self.magnification + 1)
            self.update()
        elif event.key() == Qt.Key_Minus:
            # 减少放大倍数
            self.magnification = max(1, self.magnification - 1)
            self.update()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.is_selecting = True
            self.start_pos = event.globalPosition().toPoint()
            self.end_pos = self.start_pos
            self.update()
        elif event.button() == Qt.RightButton:
            self.cancel_capture()
        elif event.button() == Qt.MiddleButton:
            # 中键重置选择
            self.start_pos = QPoint()
            self.end_pos = QPoint()
            self.is_selecting = False
            self.update()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件 - 带性能优化"""
        self.current_mouse_pos = event.globalPosition().toPoint()

        # 性能优化：限制更新频率
        if (self.current_mouse_pos - self.last_mouse_pos).manhattanLength() > 2:
            self.last_mouse_pos = self.current_mouse_pos

            if self.is_selecting:
                self.end_pos = self.current_mouse_pos
                # 使用定时器延迟更新，避免过于频繁的重绘
                if not self.update_timer.isActive():
                    self.update_timer.start(16)  # ~60 FPS
            elif self.show_magnifier or self.show_crosshair:
                if not self.update_timer.isActive():
                    self.update_timer.start(16)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            self.confirm_selection()
        else:
            super().mouseReleaseEvent(event)

    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        self.setFocus(Qt.ActiveWindowFocusReason)
        self.grabMouse()
        self.grabKeyboard()

    def hideEvent(self, event):
        """窗口隐藏事件"""
        self.releaseMouse()
        self.releaseKeyboard()
        super().hideEvent(event)

    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制半透明遮罩
        painter.setBrush(self.overlay_color)
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.rect())

        # 绘制背景（如果有）
        if self.background_pixmap:
            painter.setOpacity(1.0)
            painter.drawPixmap(0, 0, self.background_pixmap)

            # 再次绘制半透明遮罩，使背景变暗
            painter.setBrush(self.overlay_color)
            painter.setPen(Qt.NoPen)
            painter.drawRect(self.rect())

        # 绘制选区
        if not self.start_pos.isNull() and not self.end_pos.isNull():
            selected_rect = QRect(self.start_pos, self.end_pos).normalized()
            self._draw_selection(painter, selected_rect)

        # 绘制十字线（非选择状态下）
        if self.show_crosshair and not self.is_selecting:
            self._draw_crosshair(painter, self.current_mouse_pos)

        # 绘制放大镜
        if self.show_magnifier and not self.current_mouse_pos.isNull():
            self._draw_magnifier(painter, self.current_mouse_pos)

    def _draw_selection(self, painter: QPainter, rect: QRect):
        """绘制选区"""
        # 清除选区内的遮罩 -> 改为绘制原图（确保与 magnifier 一致）
        if self.background_pixmap:
            # 计算在背景图中的源区域
            # 注意：rect 是相对于窗口的，background_pixmap 也是 0,0 对齐的
            source_rect = rect
            target_rect = rect
            painter.drawPixmap(target_rect, self.background_pixmap, source_rect)
        else:
            # 降级：如果没有背景图，只能用 Clear 模式
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.setBrush(Qt.transparent)
            painter.setPen(Qt.NoPen)
            painter.drawRect(rect)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        # 绘制红色边框
        pen = QPen(self.selection_color, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect)

        # 绘制尺寸信息
        self._draw_size_info(painter, rect)

        # 绘制网格
        if self.show_grid:
            self._draw_grid(painter, rect)

    def _draw_size_info(self, painter: QPainter, rect: QRect):
        """绘制尺寸信息"""
        info_text = f"{rect.width()} x {rect.height()}"
        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(info_text)
        text_height = font_metrics.height()

        # 信息框位置
        info_rect = QRect(
            rect.left(), rect.top() - text_height - 5, text_width + 10, text_height + 4
        )

        # 边界处理：防止超出屏幕
        if info_rect.top() < 0:
            info_rect.moveTop(rect.bottom() + 5)

        painter.setBrush(self.info_bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(info_rect, 3, 3)

        painter.setPen(Qt.white)
        painter.drawText(info_rect, Qt.AlignCenter, info_text)

    def _draw_grid(self, painter: QPainter, rect: QRect):
        """在选区内绘制网格"""
        if rect.width() < 50 or rect.height() < 50:
            return

        pen = QPen(self.grid_color, 1, Qt.DotLine)
        painter.setPen(pen)

        # 计算网格间距
        x_spacing = max(20, rect.width() // 10)
        y_spacing = max(20, rect.height() // 10)

        # 绘制垂直线
        for x in range(rect.left() + x_spacing, rect.right(), x_spacing):
            painter.drawLine(x, rect.top(), x, rect.bottom())

        # 绘制水平线
        for y in range(rect.top() + y_spacing, rect.bottom(), y_spacing):
            painter.drawLine(rect.left(), y, rect.right(), y)

    def _draw_crosshair(self, painter: QPainter, pos: QPoint):
        """绘制十字线"""
        pen = QPen(self.crosshair_color, 1, Qt.DashLine)
        painter.setPen(pen)

        # 水平线
        painter.drawLine(0, pos.y(), self.width(), pos.y())
        # 垂直线
        painter.drawLine(pos.x(), 0, pos.x(), self.height())

    def _draw_magnifier(self, painter: QPainter, pos: QPoint):
        """绘制放大镜 - 终极重构版"""
        size = self.magnifier_size

        # -------------------------------------------------------------
        # 1. 坐标映射与源图像提取 (核心修复)
        # -------------------------------------------------------------
        magnified_pixmap = None

        # 检查背景图是否存在且有效
        if self.background_pixmap and not self.background_pixmap.isNull():
            bg_w = self.background_pixmap.width()
            bg_h = self.background_pixmap.height()
            widget_w = self.width()
            widget_h = self.height()

            # 计算物理像素与逻辑像素的比例 (DPI Scale Factor)
            # 例如：屏幕逻辑宽度 1920，实际截图宽度 3840 -> scale_x = 2.0
            scale_x = bg_w / widget_w if widget_w > 0 else 1.0
            scale_y = bg_h / widget_h if widget_h > 0 else 1.0

            # 目标：以鼠标为中心，在"物理图"上截取多大区域？
            # 逻辑上我们需要截取 size / magnification 的大小
            # 物理上需要乘以 scale
            grab_size_logical = size / self.magnification
            grab_w_physical = int(grab_size_logical * scale_x)
            grab_h_physical = int(grab_size_logical * scale_y)

            # 鼠标在"物理图"上的位置
            mouse_x_physical = int(pos.x() * scale_x)
            mouse_y_physical = int(pos.y() * scale_y)

            # 计算物理源矩形 (Source Rect in Physical Coords)
            src_x = mouse_x_physical - grab_w_physical // 2
            src_y = mouse_y_physical - grab_h_physical // 2

            source_rect = QRect(src_x, src_y, grab_w_physical, grab_h_physical)

            # 安全裁剪：确保不超出背景图边界
            # 注意：如果鼠标在屏幕边缘，source_rect 可能会超出 bg_rect
            # 我们必须处理这个情况，否则 copy 会失败或返回空。
            # 方案：Clamp Source Rect into Image
            clamped_rect = QRect(source_rect)
            if clamped_rect.left() < 0:
                clamped_rect.moveLeft(0)
            if clamped_rect.top() < 0:
                clamped_rect.moveTop(0)
            if clamped_rect.right() > bg_w:
                clamped_rect.moveRight(bg_w)
            if clamped_rect.bottom() > bg_h:
                clamped_rect.moveBottom(bg_h)

            # 提取图像
            raw_img = self.background_pixmap.copy(clamped_rect).toImage()

            if not raw_img.isNull():
                # --- 修复变暗关键点 ---
                # 强制转换为 RGB32 (忽略 Alpha)，确保 100% 不透明
                raw_img = raw_img.convertToFormat(QImage.Format_RGB32)

                # 缩放到目标显示大小 (size x size)
                scaled_img = raw_img.scaled(
                    size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
                )
                magnified_pixmap = QPixmap.fromImage(scaled_img)

        # -------------------------------------------------------------
        # 2. 降级处理 (Fallback)
        # -------------------------------------------------------------
        if not magnified_pixmap:
            # 如果上述过程失败（例如没有背景图），尝试直接抓屏
            # 这是一个最后的保险，尽管可能会暗，但比黑屏好
            screen = self._get_screen_at_point(pos)
            grab_s = int(size / self.magnification)
            screen_pix = screen.grabWindow(
                0, pos.x() - grab_s // 2, pos.y() - grab_s // 2, grab_s, grab_s
            )
            if not screen_pix.isNull():
                magnified_pixmap = screen_pix.scaled(
                    size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
                )

        # -------------------------------------------------------------
        # 3. 绘制 UI
        # -------------------------------------------------------------
        offset = 20
        magnifier_rect = QRect(pos.x() + offset, pos.y() + offset, size, size)

        # 智能避让
        if (
            magnifier_rect.right() > self.width()
            or magnifier_rect.bottom() > self.height()
        ):
            magnifier_rect.moveBottomRight(QPoint(pos.x() - offset, pos.y() - offset))

        # 边界保护
        if magnifier_rect.right() > self.width():
            magnifier_rect.moveRight(self.width())
        if magnifier_rect.bottom() > self.height():
            magnifier_rect.moveBottom(self.height())
        if magnifier_rect.left() < 0:
            magnifier_rect.moveLeft(0)
        if magnifier_rect.top() < 0:
            magnifier_rect.moveTop(0)

        painter.save()

        # 剪裁为圆形
        path = QPainterPath()
        path.addEllipse(magnifier_rect)
        painter.setClipPath(path)

        # 绘制背景 (黑色) - 确保即便图也是透明的，底下也是黑的而不是混合色
        painter.setBrush(Qt.black)
        painter.setPen(Qt.NoPen)
        painter.drawRect(magnifier_rect)

        # 绘制图像
        if magnified_pixmap and not magnified_pixmap.isNull():
            painter.setOpacity(1.0)
            painter.drawPixmap(magnifier_rect, magnified_pixmap)

        # 绘制中心十字准星
        center = magnifier_rect.center()
        painter.setPen(QPen(Qt.red, 1))

        # 修正：画十字时 +/- 5 可能会画歪，确保中心感
        painter.drawLine(center.x() - 10, center.y(), center.x() + 10, center.y())
        painter.drawLine(center.x(), center.y() - 10, center.x(), center.y() + 10)

        # 绘制边框
        painter.setPen(QPen(Qt.white, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(magnifier_rect)

        # 绘制信息
        self._draw_pixel_info(painter, pos, magnifier_rect)

        painter.restore()

    def _draw_pixel_info(self, painter: QPainter, pos: QPoint, magnifier_rect: QRect):
        """绘制像素信息"""
        # 获取颜色需要重新截取1x1像素（或者从grab_pixmap中取）
        if self.background_pixmap:
            pixel_color = self.background_pixmap.toImage().pixelColor(pos)
        else:
            pixel_color = (
                QScreen.grabWindow(
                    QApplication.primaryScreen(), 0, pos.x(), pos.y(), 1, 1
                )
                .toImage()
                .pixelColor(0, 0)
            )

        info = f"({pos.x()}, {pos.y()})\n{pixel_color.name()}"

        painter.setPen(Qt.white)
        painter.setFont(painter.font())

        # 简单的文字阴影效果
        text_rect = magnifier_rect.adjusted(0, magnifier_rect.height() - 40, 0, 0)
        painter.drawText(text_rect, Qt.AlignCenter, info)

    def confirm_selection(self):
        """确认当前选区"""
        if self.start_pos.isNull() or self.end_pos.isNull():
            self.cancel_capture()
            return

        rect = QRect(self.start_pos, self.end_pos).normalized()

        # 验证选区有效性
        if rect.width() >= 5 and rect.height() >= 5:
            # 确保选区在屏幕范围内
            screen_geometry = self._get_combined_screen_geometry()
            rect = rect.intersected(screen_geometry)

            if rect.isValid() and not rect.isEmpty():
                self.finished.emit(rect)
                self.close()
                return

        # 无效选区
        self.cancel_capture()

    def cancel_capture(self):
        """取消截图操作"""
        self.cancelled.emit()
        self.close()
