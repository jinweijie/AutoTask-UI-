from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class TaskItemWidget(QWidget):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.task_name = name
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        # 任务名称标签 - 设置为透明
        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("Arial", 10, QFont.Medium))
        self.name_label.setMinimumWidth(150)
        self.name_label.setStyleSheet("background: transparent;")  # 设置透明背景

        # 状态标签
        self.status_label = QLabel("已停止")
        self.status_label.setFont(QFont("Arial", 9))
        self.status_label.setStyleSheet("background: transparent;")  # 设置透明背景

        # 操作按钮 - 添加emoji
        self.start_btn = QPushButton("▶️")
        self.start_btn.setToolTip("开始任务")
        self.start_btn.setFixedSize(28, 28)

        self.stop_btn = QPushButton("⏹️")
        self.stop_btn.setToolTip("停止任务")
        self.stop_btn.setFixedSize(28, 28)
        # self.stop_btn.setEnabled(False)

        self.delete_btn = QPushButton("🗑️")
        self.delete_btn.setToolTip("删除任务")
        self.delete_btn.setFixedSize(28, 28)

        # 添加到布局
        layout.addWidget(self.name_label)
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.delete_btn)

        # 连接信号
        self.start_btn.clicked.connect(self.start_task)
        self.stop_btn.clicked.connect(self.stop_task)
        self.delete_btn.clicked.connect(lambda: self.parent.delete_task(name))

    def start_task(self):
        self.status_label.setText("运行中")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        # 更新主界面状态
        if self.parent:
            self.parent.task_status.setText("运行中")
            self.parent.start_current_task()

    def stop_task(self):
        self.status_label.setText("已停止")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        # 更新主界面状态
        if self.parent:
            # 检查是否是当前任务且正在定时
            if (
                self.parent.current_task == self.task_name
                and self.task_name in self.parent.scheduled_timers
            ):
                self.parent.stop_current_task()
            elif self.parent.current_task == self.task_name:
                self.parent.task_status.setText("已停止")
                self.parent.stop_current_task()
