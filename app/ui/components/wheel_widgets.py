from PySide6.QtCore import QTime
from PySide6.QtWidgets import QSpinBox, QTimeEdit


class WheelTimeEdit(QTimeEdit):
    """支持鼠标滚轮调整的TimeEdit"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWrapping(True)  # 允许循环滚动
        self.installEventFilter(self)

    def wheelEvent(self, event):
        """鼠标滚轮事件"""
        if not self.hasFocus():
            return

        delta = event.angleDelta().y()
        current_section = self.currentSection()

        if current_section == QTimeEdit.HourSection:
            # 调整小时
            hours = self.time().hour()
            if delta > 0:
                hours = (hours + 1) % 24
            else:
                hours = (hours - 1) % 24
            new_time = QTime(hours, self.time().minute(), self.time().second())

        elif current_section == QTimeEdit.MinuteSection:
            # 调整分钟
            minutes = self.time().minute()
            if delta > 0:
                minutes = (minutes + 1) % 60
            else:
                minutes = (minutes - 1) % 60
            new_time = QTime(self.time().hour(), minutes, self.time().second())

        elif current_section == QTimeEdit.SecondSection:
            # 调整秒
            seconds = self.time().second()
            if delta > 0:
                seconds = (seconds + 1) % 60
            else:
                seconds = (seconds - 1) % 60
            new_time = QTime(self.time().hour(), self.time().minute(), seconds)

        else:
            return

        self.setTime(new_time)
        event.accept()


class WheelSpinBox(QSpinBox):
    """支持鼠标滚轮调整的SpinBox"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.installEventFilter(self)

    def wheelEvent(self, event):
        """鼠标滚轮事件"""
        if not self.hasFocus():
            return

        delta = event.angleDelta().y()
        current_value = self.value()

        if delta > 0:
            # 向上滚动，增加值
            if current_value < 60:
                step = 1  # 小数值时步长为1
            elif current_value < 180:
                step = 5  # 中等值时步长为5
            else:
                step = 30  # 大值时步长为30
            new_value = min(self.maximum(), current_value + step)
        else:
            # 向下滚动，减少值
            if current_value <= 60:
                step = 1
            elif current_value <= 180:
                step = 5
            else:
                step = 30
            new_value = max(self.minimum(), current_value - step)

        self.setValue(new_value)
        event.accept()
