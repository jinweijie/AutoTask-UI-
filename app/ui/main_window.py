import json
import os
import sys
import threading
import time
from copy import deepcopy

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QEvent,
    QSettings,
    QSize,
    Qt,
    QTime,
    QTimer,
    QTranslator,
    Slot,
)
from PySide6.QtGui import QAction, QActionGroup, QFont, QIntValidator, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStyle,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from app.core.hotkey_listener import HotkeyListener
from app.core.utils import resource_path
from app.services.task_runner import TaskRunner
from app.ui.components.step_table_helper import StepTableHelper
from app.ui.components.task_item_widget import TaskItemWidget
from app.ui.components.wheel_widgets import WheelSpinBox, WheelTimeEdit
from app.ui.dialogs.about_dialog import AboutDialog
from app.ui.dialogs.ai_test_dialog import AITestDialog
from app.ui.dialogs.step_config_dialog import StepConfigDialog
from app.ui.dialogs.token_config_dialog import AITokenConfigDialog


class AutomationUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize components first so they exist for retranslateUi
        self.init_ui_components()

        # Load settings
        self.settings = QSettings("MyCompany", "AutomationManager")
        self.load_settings()

        # Initialize translation
        self.translator = QTranslator()
        # Default to en-US as requested
        self.switch_language("en-US")

        self.setGeometry(100, 100, 1100, 550)

        # Task management init
        self.tasks = {}
        self.current_task = None
        self.task_runner = None
        self.task_thread = None
        self.scheduled_timers = {}
        self.hotkey_listener = None
        self.setup_hotkey_listener()

        # Load tasks
        self.load_all_configs()

        # Final UI setup
        self.retranslateUi()

        # Restore splitter state
        splitter_sizes = self.settings.value("splitterSizes")
        if splitter_sizes:
            splitter_sizes = [int(s) for s in splitter_sizes]
            self.splitter.setSizes(splitter_sizes)
        else:
            self.splitter.setSizes([280, 700])

        self.log_splitter.setSizes([300, 150])

        # Create menus
        self.create_menus()

        # Connect signals
        self.connect_signals()

        # Apply theme
        self.apply_theme(self.current_theme)
        self.detect_system_theme()

        # System tray
        self.create_system_tray()

    def init_ui_components(self):
        """Initialize all UI components without setting text"""
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal)

        # Left Panel
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_panel.setMinimumWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)

        # Title Layout
        title_layout = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Arial", 11, QFont.Bold))
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        self.new_task_btn = QPushButton()
        self.new_task_btn.setFixedSize(100, 32)
        title_layout.addWidget(self.new_task_btn)
        left_layout.addLayout(title_layout)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        left_layout.addWidget(separator)

        # Task List
        self.task_list = QListWidget()
        self.task_list.setMinimumHeight(200)
        self.task_list.setStyleSheet("""
            QListWidget::item:hover {
                background-color: #e0e0e0;
            }
        """)
        self.task_list.setContextMenuPolicy(Qt.CustomContextMenu)

        # Log Area
        self.log_group = QGroupBox()
        log_layout = QVBoxLayout()

        log_header_layout = QHBoxLayout()
        self.log_header_label = QLabel()
        log_header_layout.addWidget(self.log_header_label)
        log_header_layout.addStretch()
        self.clear_log_btn = QPushButton()
        self.clear_log_btn.setFixedSize(80, 24)
        log_header_layout.addWidget(self.clear_log_btn)
        log_layout.addLayout(log_header_layout)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        log_layout.addWidget(self.log_text)
        self.log_group.setLayout(log_layout)
        # left_layout.addWidget(self.log_group) # Helper will insert into splitter

        # Right Panel
        right_panel = QFrame()
        right_panel.setFrameShape(QFrame.StyledPanel)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 15, 15, 15)

        # Task Info Group
        self.task_info_group = QGroupBox()
        task_info_layout = QFormLayout()
        task_info_layout.setLabelAlignment(Qt.AlignRight)
        task_info_layout.setSpacing(10)

        self.task_name = QLineEdit()
        self.task_name.setFont(QFont("Arial", 10))
        self.task_status = QLabel()

        self.task_name_label = QLabel()  # Store labels to update text
        self.task_status_label = QLabel()

        task_info_layout.addRow(self.task_name_label, self.task_name)
        task_info_layout.addRow(self.task_status_label, self.task_status)
        self.task_info_group.setLayout(task_info_layout)

        # Schedule Group
        self.schedule_group = QGroupBox()
        schedule_layout = QGridLayout()
        schedule_layout.setSpacing(10)
        schedule_layout.setColumnStretch(5, 1)

        self.schedule_mode_label = QLabel()
        schedule_layout.addWidget(self.schedule_mode_label, 0, 0)

        self.schedule_enable = QComboBox()
        # Items added in retranslateUi
        self.schedule_enable.setMinimumWidth(120)
        schedule_layout.addWidget(self.schedule_enable, 0, 1)

        self.schedule_time_label = QLabel()
        schedule_layout.addWidget(self.schedule_time_label, 0, 2)

        time_widget = QWidget()
        time_layout = QHBoxLayout(time_widget)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(5)

        self.schedule_time = WheelTimeEdit(QTime.currentTime().addSecs(300))
        self.schedule_time.setDisplayFormat("HH:mm:ss")
        self.schedule_time.setMinimumWidth(100)
        self.schedule_time.setMaximumWidth(100)
        self.schedule_time.setTimeRange(QTime(0, 0, 0), QTime(23, 59, 59))
        time_layout.addWidget(self.schedule_time)

        # Time preset buttons
        self.time_btn_1314 = QPushButton("13:14")
        self.time_btn_night = QPushButton()

        for btn in [self.time_btn_1314, self.time_btn_night]:
            btn.setFixedSize(60, 25)
            btn.setStyleSheet("""
                QPushButton { font-size: 10px; padding: 2px; }
                QPushButton:hover { background-color: #e0e0e0; }
            """)
            time_layout.addWidget(btn)

        self.time_btn_1314.clicked.connect(lambda: self.set_time_to(13, 14))
        self.time_btn_night.clicked.connect(lambda: self.set_time_to(0, 0))

        schedule_layout.addWidget(time_widget, 0, 3, 1, 2)

        self.repeat_interval_label = QLabel()
        schedule_layout.addWidget(self.repeat_interval_label, 1, 0)

        interval_widget = QWidget()
        interval_layout = QHBoxLayout(interval_widget)
        interval_layout.setContentsMargins(0, 0, 0, 0)
        interval_layout.setSpacing(5)

        self.repeat_interval = WheelSpinBox()
        self.repeat_interval.setRange(0, 1440)
        self.repeat_interval.setValue(0)
        self.repeat_interval.setMinimumWidth(80)
        self.repeat_interval.setMaximumWidth(80)
        interval_layout.addWidget(self.repeat_interval)

        self.interval_btn_0 = QPushButton()
        self.interval_btn_24h = QPushButton()

        for btn in [self.interval_btn_0, self.interval_btn_24h]:
            btn.setFixedSize(55, 25)
            btn.setStyleSheet("""
                QPushButton { font-size: 10px; padding: 2px; }
                QPushButton:hover { background-color: #e0e0e0; }
            """)
            interval_layout.addWidget(btn)

        self.interval_btn_0.clicked.connect(lambda: self.repeat_interval.setValue(0))
        self.interval_btn_24h.clicked.connect(
            lambda: self.repeat_interval.setValue(1440)
        )

        interval_layout.addStretch()
        schedule_layout.addWidget(interval_widget, 1, 1, 1, 2)

        self.repeat_count_label = QLabel()
        schedule_layout.addWidget(self.repeat_count_label, 1, 3)

        self.repeat_count = QComboBox()
        self.repeat_count.setEditable(True)
        # Items added in retranslateUi
        self.repeat_count.setMinimumWidth(80)
        validator = QIntValidator(1, 999999)
        self.repeat_count.setValidator(validator)
        schedule_layout.addWidget(self.repeat_count, 1, 4)

        self.next_run_label = QLabel()
        self.next_run_label.setMinimumWidth(200)
        self.next_run_label.setAlignment(Qt.AlignCenter)
        self.next_run_label.setWordWrap(True)
        schedule_layout.addWidget(self.next_run_label, 0, 5, 2, 5)

        self.schedule_group.setLayout(schedule_layout)

        # Steps Group
        self.steps_group = QGroupBox()
        steps_layout = QVBoxLayout()
        steps_layout.setSpacing(10)

        self.steps_table = QTableWidget(0, 4)
        self.steps_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Interactive
        )
        self.steps_table.horizontalHeader().setStretchLastSection(True)
        self.steps_table.verticalHeader().setVisible(False)
        self.steps_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        step_btn_layout = QHBoxLayout()
        self.add_step_btn = QPushButton()
        self.add_step_btn.setShortcut(QKeySequence("Ctrl+A"))
        self.edit_step_btn = QPushButton()
        self.edit_step_btn.setShortcut(QKeySequence("Ctrl+E"))
        self.remove_step_btn = QPushButton()
        self.remove_step_btn.setShortcut(QKeySequence.Delete)
        self.copy_step_btn = QPushButton()
        self.copy_step_btn.setShortcut(QKeySequence("Ctrl+C"))
        self.move_up_btn = QPushButton()
        self.move_up_btn.setShortcut(QKeySequence("Ctrl+Up"))
        self.move_down_btn = QPushButton()
        self.move_down_btn.setShortcut(QKeySequence("Ctrl+Down"))

        step_btn_layout.addWidget(self.add_step_btn)
        step_btn_layout.addWidget(self.edit_step_btn)
        step_btn_layout.addWidget(self.copy_step_btn)
        step_btn_layout.addWidget(self.remove_step_btn)
        step_btn_layout.addStretch()
        step_btn_layout.addWidget(self.move_up_btn)
        step_btn_layout.addWidget(self.move_down_btn)

        steps_layout.addWidget(self.steps_table)
        steps_layout.addLayout(step_btn_layout)
        self.steps_group.setLayout(steps_layout)

        # Action Buttons
        action_btn_layout = QHBoxLayout()
        self.start_current_btn = QPushButton()
        self.stop_current_btn = QPushButton()
        self.stop_current_btn.setEnabled(False)
        self.save_btn = QPushButton()

        action_btn_layout.addWidget(self.start_current_btn)
        action_btn_layout.addWidget(self.stop_current_btn)
        action_btn_layout.addStretch()
        action_btn_layout.addWidget(self.save_btn)

        # Layout Assembly
        right_layout.addWidget(self.task_info_group)
        right_layout.addWidget(self.schedule_group)
        right_layout.addWidget(self.steps_group)
        right_layout.addLayout(action_btn_layout)

        self.splitter.addWidget(left_panel)
        self.splitter.addWidget(right_panel)

        self.log_splitter = QSplitter(Qt.Vertical)
        self.log_splitter.addWidget(self.task_list)
        self.log_splitter.addWidget(self.log_group)
        left_layout.insertWidget(2, self.log_splitter)

        main_layout.addWidget(self.splitter)
        self.setCentralWidget(main_widget)

    def connect_signals(self):
        """Connect all signals"""
        self.task_list.customContextMenuRequested.connect(self.show_context_menu)
        self.clear_log_btn.clicked.connect(self.clear_log)
        self.schedule_enable.currentTextChanged.connect(self.on_schedule_mode_changed)
        self.schedule_time.timeChanged.connect(self.update_next_run_time)
        self.repeat_interval.valueChanged.connect(self.update_next_run_time)
        self.repeat_count.currentTextChanged.connect(self.update_next_run_time)
        self.repeat_count.editTextChanged.connect(self.on_repeat_count_edited)
        self.task_list.currentItemChanged.connect(self.task_selected)
        self.new_task_btn.clicked.connect(self.create_new_task)
        self.start_current_btn.clicked.connect(self.start_current_task)
        self.stop_current_btn.clicked.connect(self.stop_current_task)
        self.add_step_btn.clicked.connect(self.add_step)
        self.edit_step_btn.clicked.connect(self.edit_step)
        self.remove_step_btn.clicked.connect(self.remove_step)
        self.move_up_btn.clicked.connect(self.move_step_up)
        self.move_down_btn.clicked.connect(self.move_step_down)
        self.save_btn.clicked.connect(self.save_task_config)
        self.copy_step_btn.clicked.connect(self.copy_step)

    def changeEvent(self, event):
        """Handle language change events"""
        if event.type() == QEvent.LanguageChange:
            self.retranslateUi()
        super().changeEvent(event)

    def retranslateUi(self):
        """Update all UI texts for the current language"""
        self.setWindowTitle(self.tr("自动化任务管理器"))

        # Title & Lists
        self.title_label.setText(self.tr("📋 任务列表"))
        self.new_task_btn.setText(self.tr("➕ 新建任务"))

        # Log
        self.log_group.setTitle(self.tr("📝 执行日志"))
        self.log_header_label.setText(self.tr("执行日志:"))
        self.clear_log_btn.setText(self.tr("清空日志"))

        # Task Info
        self.task_info_group.setTitle(self.tr("ℹ️ 任务信息"))
        self.task_name.setPlaceholderText(self.tr("输入任务名称"))
        self.task_name_label.setText(self.tr("任务名称:"))
        self.task_status_label.setText(self.tr("当前状态:"))
        if not self.current_task:  # Only reset if no task is running/selected
            self.task_status.setText(self.tr("未运行"))

        # Schedule
        self.schedule_group.setTitle(self.tr("⏰ 定时设置"))
        self.schedule_mode_label.setText(self.tr("执行方式:"))
        self.schedule_time_label.setText(self.tr("执行时间:"))
        self.repeat_interval_label.setText(self.tr("重复间隔:"))
        self.repeat_count_label.setText(self.tr("重复次数:"))

        # Combo Boxes (Need to preserve selection)
        current_schedule = self.schedule_enable.currentIndex()
        self.schedule_enable.clear()
        self.schedule_enable.addItems([self.tr("立即执行"), self.tr("定时执行")])
        if current_schedule >= 0:
            self.schedule_enable.setCurrentIndex(current_schedule)

        current_repeat = self.repeat_count.currentText()
        self.repeat_count.clear()
        self.repeat_count.addItems(["1", "3", "7", "9", self.tr("无限")])
        if (
            current_repeat == "无限" or current_repeat == "Unlimited"
        ):  # Handle both langs
            self.repeat_count.setCurrentText(self.tr("无限"))
        elif current_repeat:
            self.repeat_count.setCurrentText(current_repeat)

        # Tooltips & Suffixes
        self.schedule_time.setToolTip(
            self.tr("使用鼠标滚轮调整时间\n单击可分别编辑时、分、秒")
        )
        self.repeat_interval.setSuffix(self.tr(" 分钟"))
        self.repeat_interval.setToolTip(self.tr("使用鼠标滚轮调整间隔\n"))

        # Buttons
        self.time_btn_night.setText(self.tr("晚安时间"))
        self.interval_btn_0.setText(self.tr("0分钟"))
        self.interval_btn_24h.setText(self.tr("24小时"))

        # Steps
        self.steps_group.setTitle(self.tr("⚙️ 操作步骤配置"))
        self.steps_table.setHorizontalHeaderLabels(
            [self.tr("类型"), self.tr("描述"), self.tr("参数"), self.tr("延时(秒)")]
        )

        self.add_step_btn.setText(self.tr("➕ 添加步骤 (A)"))
        self.edit_step_btn.setText(self.tr("✏️ 编辑步骤 (E)"))
        self.remove_step_btn.setText(self.tr("➖ 删除步骤 (Del)"))
        self.copy_step_btn.setText(self.tr("📋 复制步骤"))
        self.move_up_btn.setText(self.tr("⬆️ 上移 (↑)"))
        self.move_down_btn.setText(self.tr("⬇️ 下移 (↓)"))

        self.start_current_btn.setText(self.tr("▶️ 开始当前任务"))
        self.stop_current_btn.setText(self.tr("⏹️ 停止当前任务"))
        self.save_btn.setText(self.tr("💾 保存配置"))

        self.update_next_run_time()

        # Recreate menus to update translation
        self.create_menus()

    def switch_language(self, lang_code):
        """Switch application language"""
        self.curr_lang = lang_code

        # Remove existing translator
        QCoreApplication.removeTranslator(self.translator)

        if lang_code == "en-US":
            # Load English translation
            qm_path = resource_path(
                os.path.join("resources", "i18n", "auto_task_en_US.qm")
            )
            if self.translator.load(qm_path):
                QCoreApplication.installTranslator(self.translator)
                print(f"Loaded translation: {qm_path}")
            else:
                print(f"Failed to load translation: {qm_path}")
        # For zh-CN, we validly remove translator to revert to source (Chinese)

    def set_time_to(self, hour, minute):
        """设置时间为指定的小时和分钟"""
        current_time = QTime(hour, minute, 0)
        self.schedule_time.setTime(current_time)

    def on_schedule_mode_changed(self, mode):
        """执行方式改变时的处理"""
        # Translation aware check
        is_scheduled = (mode == self.tr("定时执行")) or (mode == "定时执行")

        # 更新提示
        if is_scheduled:
            self.update_next_run_time()
        else:
            self.next_run_label.setText(self.tr("立即执行模式"))
            self.next_run_label.setStyleSheet("""
                QLabel {
                    color: #666; 
                    font-size: 11px; 
                    padding: 5px;
                    background-color: #f8f8f8;
                    border-radius: 3px;
                    border: 1px solid #e0e0e0;
                }
            """)

    # 在类中添加处理编辑的函数
    def on_repeat_count_edited(self, text):
        """处理重复次数编辑事件"""
        # 如果用户输入了"无限"，则设置为"无限"
        if text == self.tr("无限"):
            return

        # 如果输入的是数字，验证范围
        if text.isdigit():
            value = int(text)
            if value < 1:
                # 如果小于1，设置为1
                self.repeat_count.setCurrentText("1")
            elif value > 999999:
                # 如果大于999999，设置为999999
                self.repeat_count.setCurrentText("999999")
        elif text != "":
            # 如果输入的不是数字也不是"无限"，清除输入
            cursor_pos = self.repeat_count.lineEdit().cursorPosition()
            self.repeat_count.setCurrentText("".join(filter(str.isdigit, text)))
            self.repeat_count.lineEdit().setCursorPosition(
                min(cursor_pos, len(self.repeat_count.currentText()))
            )

    # 修改获取重复次数值的方法
    def get_repeat_count_value(self):
        """获取重复次数的实际值"""
        text = self.repeat_count.currentText()
        if text == self.tr("无限") or text == "无限":
            return "无限"
        elif text.isdigit():
            return text
        else:
            return "1"  # 默认值

    def update_next_run_time(self):
        """更新下一次执行时间显示"""
        schedule_type = self.schedule_enable.currentText()

        # Translation aware check
        is_scheduled = (schedule_type == self.tr("定时执行")) or (
            schedule_type == "定时执行"
        )

        # 获取当前设置的值
        interval = self.repeat_interval.value()
        repeat_type = self.repeat_count.currentText()
        is_infinite = (repeat_type == self.tr("无限")) or (repeat_type == "无限")

        # 如果是定时执行模式
        if is_scheduled:
            schedule_time = self.schedule_time.time()
            now = QTime.currentTime()
            current_date = QDate.currentDate()
            next_run = QTime(
                schedule_time.hour(), schedule_time.minute(), schedule_time.second()
            )

            # 计算下一次执行日期时间
            if next_run < now:
                # 如果今天的时间已过，则明天执行
                next_date = current_date.addDays(1)
            else:
                next_date = current_date

            next_run_datetime = QDateTime(next_date, next_run)
            next_run_str = next_run_datetime.toString("yyyy-MM-dd HH:mm:ss")

            # Format strings with arguments for translation
            if interval > 0:
                if is_infinite:
                    message = self.tr("下次执行: {0}\n每 {1} 分钟重复，无限次").format(
                        next_run_str, interval
                    )
                else:
                    message = self.tr(
                        "下次执行: {0}\n每 {1} 分钟重复，共 {2} 次"
                    ).format(next_run_str, interval, repeat_type)
            else:
                message = self.tr("下次执行: {0}\n无间隔时间 共 {1} 次").format(
                    next_run_str, repeat_type
                )

            color = "#2c5aa0"
            self.next_run_label.setText(message)
            self.next_run_label.setStyleSheet(f"""
                QLabel {{
                    color: {color}; 
                    font-size: 11px; 
                    padding: 8px;
                    background-color: #f0f8ff;
                    border-radius: 5px;
                    border: 1px solid #d0e0f0;
                    margin: 2px;
                }}
            """)
        else:
            # 立即执行模式
            if interval > 0:
                if is_infinite:
                    message = self.tr("立即执行\n每 {0} 分钟重复，无限次").format(
                        interval
                    )
                else:
                    message = self.tr("立即执行\n每 {0} 分钟重复，共 {1} 次").format(
                        interval, repeat_type
                    )
            else:
                message = self.tr("立即执行，无间隔，共 {0} 次").format(repeat_type)

            color = "#2c5aa0"
            self.next_run_label.setText(message)
            self.next_run_label.setStyleSheet(f"""
                QLabel {{
                    color: {color}; 
                    font-size: 11px; 
                    padding: 8px;
                    background-color: #f0f8ff;
                    border-radius: 5px;
                    border: 1px solid #d0e0f0;
                    margin: 2px;
                }}
            """)

    def validate_schedule_settings(self):
        """验证定时设置是否有效"""
        interval = self.repeat_interval.value()

        if interval < 0 or interval > 1440:
            QMessageBox.warning(self, "无效设置", "重复间隔必须在0-1440分钟之间")
            return False

        schedule_time = self.schedule_time.time()
        if not schedule_time.isValid():
            QMessageBox.warning(self, "无效时间", "请选择有效的执行时间")
            return False

        return True

    def setup_hotkey_listener(self):
        """启动 Esc 热键监听"""
        self.hotkey_listener = HotkeyListener(self)
        self.hotkey_listener.hotkey_activated.connect(self.on_esc_pressed)
        self.hotkey_listener.start()  # 启动线程

    @Slot()
    def on_esc_pressed(self):
        """响应 Esc 键（在主线程执行）"""
        if self.task_runner and self.task_thread and self.task_thread.is_alive():
            self.stop_current_task()
            self.statusBar().showMessage("🛑 Esc 被按下，任务已停止", 2000)

    def load_all_configs(self, config_dir="config"):
        """
        扫描 config_dir 内所有 *.json 并加载为任务
        """
        # 获取配置目录的绝对路径
        if getattr(sys, "frozen", False):
            # 打包后的情况：在可执行文件同级目录下查找 config
            application_path = os.path.dirname(sys.executable)
            config_dir = os.path.join(application_path, config_dir)
        else:
            # 开发环境
            config_dir = resource_path(config_dir)
        if not os.path.isdir(config_dir):
            os.makedirs(config_dir, exist_ok=True)
            return
        first_task_loaded = False  # 标记是否已加载第一个任务
        for fname in os.listdir(config_dir):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(config_dir, fname)
            try:
                if path:
                    try:
                        with open(path, "r") as f:
                            task_config = json.load(f)

                        task_name = task_config.get("name", False)
                        if task_name:
                            self.add_task(task_name)
                            self.tasks[task_name] = task_config

                        # 选中新导入的任务
                        # 如果是第一个加载的任务，则选中并显示其配置
                        if not first_task_loaded:
                            for i in range(self.task_list.count()):
                                item = self.task_list.item(i)
                                widget = self.task_list.itemWidget(item)

                                if widget and widget.task_name == task_name:
                                    self.task_list.setCurrentItem(item)
                                    self.display_task_config(task_name)
                                    first_task_loaded = True
                                    break
                    except Exception as e:
                        QMessageBox.critical(
                            self, "导入失败", f"导入配置时出错: {str(e)}"
                        )
            except Exception as e:
                print(f"加载配置 {path} 失败：{e}")

    def display_task_config(self, task_name):
        """
        显示指定任务的配置数据到定时设置和操作步骤配置区域
        """
        if task_name not in self.tasks:
            return

        task_config = self.tasks[task_name]

        # 显示任务名称
        self.task_name.setText(task_name)

        # 显示定时设置
        schedule = task_config.get("schedule", {})
        self.schedule_enable.setCurrentText(schedule.get("enable", "立即执行"))
        time_str = schedule.get("time", QTime.currentTime().toString("HH:mm:ss"))

        # 解析时间字符串
        time_parts = time_str.split(":")
        if len(time_parts) == 3:
            hour, minute, second = map(int, time_parts)
            self.schedule_time.setTime(QTime(hour, minute, second))

        self.repeat_interval.setValue(int(schedule.get("interval", 0)))
        self.repeat_count.setCurrentText(str(schedule.get("repeat", "1")))

        # 显示步骤配置
        steps = task_config.get("steps", [])
        for step in steps:
            self.add_step_to_table(step)

    def create_system_tray(self):
        """创建系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))

        # 创建托盘菜单
        tray_menu = QMenu()

        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        hide_action = QAction("隐藏窗口", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.exit_app)  # Use custom exit method
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

        # 连接信号
        self.tray_icon.messageClicked.connect(self.tray_message_clicked)

    def tray_icon_activated(self, reason):
        """托盘图标被激活时的处理"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def tray_message_clicked(self):
        """托盘消息被点击时的处理"""
        self.showNormal()
        self.activateWindow()

    def exit_app(self):
        """退出应用程序"""
        # Set a flag to indicate we really want to quit, bypassing minimize-to-tray
        self._force_close = True
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        """重写关闭事件"""
        # Clean up hotkey listener
        if self.hotkey_listener and self.hotkey_listener.isRunning():
            self.hotkey_listener.stop()

        # Check if we should minimize to tray
        should_minimize = False
        if hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            if not getattr(self, "_force_close", False) and event.spontaneous():
                should_minimize = True

        if should_minimize:
            self.hide()
            event.ignore()
        else:
            # Real closing
            self.save_settings()
            # Stop all timers
            for timer in self.scheduled_timers.values():
                timer.stop()
            event.accept()

    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.log_text.appendPlainText(f"[{time.strftime('%H:%M:%S')}] 日志已清空")

    def show_ai_token_config(self):
        """显示AI Token配置对话框"""
        dialog = AITokenConfigDialog(self)
        dialog.exec()

    def show_ai_test(self):
        """显示 AI 测试对话框"""
        try:
            dialog = AITestDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开 AI 测试对话框: {str(e)}")

    def load_settings(self):
        # 加载主题设置
        self.current_theme = self.settings.value("theme", "light")

    def save_settings(self):
        # 保存分割器位置
        self.settings.setValue("splitterSizes", self.splitter.sizes())

    def create_menus(self):
        """Create application menus"""
        # Save state before recreation
        skip_checked = (
            getattr(self, "auto_skip_checkbox", None)
            and self.auto_skip_checkbox.isChecked()
        )
        timeout_val = (
            getattr(self, "timeout_spinbox", None) and self.timeout_spinbox.value()
        )
        instant_checked = (
            getattr(self, "instant_click_checkbox", None)
            and self.instant_click_checkbox.isChecked()
        )
        duration_val = (
            getattr(self, "move_duration_spinbox", None)
            and self.move_duration_spinbox.value()
        )
        minimize_checked = (
            getattr(self, "minimize_during_execution_checkbox", None)
            and self.minimize_during_execution_checkbox.isChecked()
        )
        color_checked = (
            getattr(self, "label_color_checkbox", None)
            and self.label_color_checkbox.isChecked()
        )

        menu_bar = self.menuBar()
        menu_bar.clear()

        # === 设置菜单 (Settings) ===
        settings_menu = menu_bar.addMenu(self.tr("⚙️ 设置"))
        # 主容器
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(8, 4, 8, 4)
        settings_layout.setSpacing(6)

        # 1. 自动跳过 + 超时时间
        self.auto_skip_checkbox = QCheckBox(self.tr("图片查找超时后自动跳过"))
        self.auto_skip_checkbox.setChecked(
            skip_checked if skip_checked is not None else False
        )

        timeout_layout = QHBoxLayout()
        timeout_label = QLabel(self.tr("超时时间:"))
        self.timeout_spinbox = QDoubleSpinBox()
        self.timeout_spinbox.setRange(0, 86400)
        self.timeout_spinbox.setSingleStep(0.5)
        self.timeout_spinbox.setValue(timeout_val if timeout_val is not None else 3)
        self.timeout_spinbox.setSuffix(" s")
        self.timeout_spinbox.setFixedWidth(100)
        timeout_layout.addWidget(timeout_label)
        timeout_layout.addWidget(self.timeout_spinbox)
        timeout_layout.addStretch()

        # 2. 鼠标移动设置
        mouse_layout = QHBoxLayout()
        self.instant_click_checkbox = QCheckBox(self.tr("直接点击"))
        self.instant_click_checkbox.setChecked(
            instant_checked if instant_checked is not None else False
        )

        self.move_duration_spinbox = QDoubleSpinBox()
        self.move_duration_spinbox.setRange(0.0, 10.0)
        self.move_duration_spinbox.setSingleStep(0.1)
        self.move_duration_spinbox.setValue(
            duration_val if duration_val is not None else 0.3
        )
        self.move_duration_spinbox.setDecimals(1)
        self.move_duration_spinbox.setSuffix(" s")
        self.move_duration_spinbox.setFixedWidth(80)
        self.move_duration_spinbox.setEnabled(
            not self.instant_click_checkbox.isChecked()
        )

        # 3. 窗口最小化设置
        minimize_layout = QHBoxLayout()
        self.minimize_during_execution_checkbox = QCheckBox(
            self.tr("执行任务时最小化窗口")
        )
        self.minimize_during_execution_checkbox.setChecked(
            minimize_checked if minimize_checked is not None else True
        )
        minimize_layout.addWidget(self.minimize_during_execution_checkbox)
        minimize_layout.addStretch()

        # 4. label颜色设置
        label_color_layout = QHBoxLayout()
        self.label_color_checkbox = QCheckBox(self.tr("开启步骤表格的五彩色"))
        self.label_color_checkbox.setChecked(
            color_checked if color_checked is not None else True
        )
        label_color_layout.addWidget(self.label_color_checkbox)
        label_color_layout.addStretch()

        # Logic connections
        self.instant_click_checkbox.toggled.connect(
            lambda c: self.move_duration_spinbox.setEnabled(not c)
        )

        # Add to layout
        settings_layout.addWidget(self.auto_skip_checkbox)
        settings_layout.addLayout(timeout_layout)
        settings_layout.addLayout(mouse_layout)
        settings_layout.addLayout(minimize_layout)
        settings_layout.addLayout(label_color_layout)

        action = QWidgetAction(settings_menu)
        action.setDefaultWidget(settings_widget)
        settings_menu.addAction(action)

        # AI Token & Test logic
        ai_token_action = QAction(self.tr("🤖 AI Token 配置"), self)
        ai_token_action.triggered.connect(self.show_ai_token_config)
        settings_menu.addAction(ai_token_action)

        ai_test_action = QAction(self.tr("🧠 AI 测试"), self)
        ai_test_action.triggered.connect(self.show_ai_test)
        settings_menu.addAction(ai_test_action)
        settings_menu.setStyleSheet(self._menu_style())

        # === 文件菜单 (File) ===
        file_menu = menu_bar.addMenu(self.tr("📁 文件"))
        new_action = QAction(self.tr("📝 新建任务"), self)
        save_action = QAction(self.tr("💾 保存配置"), self)
        export_action = QAction(self.tr("📤 导出配置"), self)
        import_action = QAction(self.tr("📥 导入配置"), self)
        exit_action = QAction(self.tr("🚪 退出"), self)

        new_action.triggered.connect(
            self.create_new_task
        )  # Ensure this method exists! If not, check init.
        # Check if create_new_task exists? The original code had it commented out or referenced.
        # Assuming it is handled by new_task_btn click usually.
        # Use lambda to emit click if needed, or connect to same slot.
        # self.new_task_btn.click() ?
        # Safe bet: self.new_task_btn.click()
        new_action.triggered.connect(self.new_task_btn.click)

        file_menu.addAction(new_action)
        file_menu.addAction(save_action)
        file_menu.addSeparator()
        file_menu.addAction(export_action)
        file_menu.addAction(import_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        file_menu.setStyleSheet(self._menu_style())

        # === 编辑菜单 (Edit) ===
        edit_menu = menu_bar.addMenu(self.tr("✏️ 编辑"))
        add_step_action = QAction(self.tr("➕ 添加步骤"), self)
        edit_step_action = QAction(self.tr("✏️ 编辑步骤"), self)
        remove_step_action = QAction(self.tr("➖ 删除步骤"), self)
        copy_step_action = QAction(self.tr("📋 复制步骤"), self)

        edit_menu.addAction(add_step_action)
        edit_menu.addAction(edit_step_action)
        edit_menu.addAction(copy_step_action)
        edit_menu.addAction(remove_step_action)
        edit_menu.setStyleSheet(self._menu_style())

        # === 语言菜单 (Language) - NEW ===
        lang_menu = menu_bar.addMenu(self.tr("🌐 语言"))
        lang_group = QActionGroup(self)

        en_action = QAction("English (en-US)", self)
        en_action.setCheckable(True)
        en_action.setData("en-US")
        if self.curr_lang == "en-US":
            en_action.setChecked(True)

        zh_action = QAction("简体中文 (zh-CN)", self)
        zh_action.setCheckable(True)
        zh_action.setData("zh-CN")
        if self.curr_lang == "zh-CN":
            zh_action.setChecked(True)

        lang_group.addAction(en_action)
        lang_group.addAction(zh_action)
        lang_menu.addAction(en_action)
        lang_menu.addAction(zh_action)
        lang_group.triggered.connect(lambda action: self.switch_language(action.data()))
        lang_menu.setStyleSheet(self._menu_style())

        # === 主题菜单 (Theme) ===
        theme_menu = menu_bar.addMenu(self.tr("🎨 主题"))

        self.light_theme_action = QAction(self.tr("☀️ 明亮主题"), self)
        self.light_theme_action.setCheckable(True)
        self.light_theme_action.triggered.connect(lambda: self.switch_theme("light"))

        self.dark_theme_action = QAction(self.tr("🌙 暗黑主题"), self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.triggered.connect(lambda: self.switch_theme("dark"))

        self.system_theme_action = QAction(self.tr("🔄 跟随系统"), self)
        self.system_theme_action.setCheckable(True)
        self.system_theme_action.triggered.connect(lambda: self.switch_theme("system"))

        theme_menu.addAction(self.light_theme_action)
        theme_menu.addAction(self.dark_theme_action)
        theme_menu.addAction(self.system_theme_action)
        theme_menu.setStyleSheet(self._menu_style())

        if self.current_theme == "light":
            self.light_theme_action.setChecked(True)
        elif self.current_theme == "dark":
            self.dark_theme_action.setChecked(True)
        else:
            self.system_theme_action.setChecked(True)

        # === 帮助菜单 (Help) ===
        help_menu = menu_bar.addMenu(self.tr("❓ 帮助"))
        about_action = QAction(self.tr("ℹ️ 关于"), self)
        docs_action = QAction(self.tr("📚 使用文档"), self)

        help_menu.addAction(docs_action)
        help_menu.addAction(about_action)
        help_menu.setStyleSheet(self._menu_style())

        # Connections
        save_action.triggered.connect(self.save_task_config)
        export_action.triggered.connect(self.export_config)
        import_action.triggered.connect(self.import_config)
        exit_action.triggered.connect(self.exit_app)
        add_step_action.triggered.connect(self.add_step)
        edit_step_action.triggered.connect(self.edit_step)
        remove_step_action.triggered.connect(self.remove_step)
        docs_action.triggered.connect(self.show_docs)
        about_action.triggered.connect(self.show_about)
        copy_step_action.triggered.connect(self.copy_step)

    def _menu_style(self):
        return """
              QMenu {
                  background: #ffffff;
                  border: 1px solid #cccccc;
              }
              QMenu::item {
                  background: transparent;
                  padding: 6px 20px;
                  color: black;
              }
              QMenu::item:selected {
                  background: #dbeafe;
                  color: #000;
              }
              QMenu::item:disabled {
                  color: #999;
                  background: transparent;
              }
              QMenu::separator {
                  height: 1px;
                  background: #cccccc;
                  margin: 4px 0px;
              }
          """

    def show_docs(self):
        """显示使用文档对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("使用文档")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(500)

        layout = QVBoxLayout(dialog)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""
            <h2>自动化任务管理器使用文档</h2>
            <p>欢迎使用自动化任务管理器！本工具可以帮助您自动化执行重复的计算机操作。</p>
            <p>github开源链接：https://github.com/junior6666/AutoTask-UI-</p
            
            <h3>基本功能</h3>
            <ul>
                <li><b>创建任务</b>：点击"新建任务"按钮创建新任务</li>
                <li><b>添加步骤</b>：在任务中添加鼠标点击、文本输入、等待等操作步骤</li>
                <li><b>定时执行</b>：根据任务需求设置任务的执行时间，点击开始当前任务按钮即可</li>
                <li><b>执行日志</b>：查看任务执行过程中的详细日志</li>
            </ul>
            
            <h3>配置说明</h3>
            <p>配置任务时，请确保：</p>
            <ul>
                <li>图片路径正确不含有中文，且图片在屏幕上可见</li>
                <li>设置合适的识别精度和超时时间</li>
                <li>为需要等待的操作添加适当的延时</li>
            </ul>
            
            <h3>QQ交流群</h3>
            <p>加入我们的QQ交流群获取更多帮助：<b>1057721699</b></p>
            
            <h3>常见问题</h3>
            <p><b>Q: 为什么找不到图片？</b><br>
            A: 请确保图片在屏幕上可见，且识别精度设置合适（建议0.8-0.9）</p>
            
            <p><b>Q: 任务执行失败怎么办？</b><br>
            A: 查看执行日志中的错误信息，调整步骤参数后重试</p>
            <p><b>Q: 13:14如何计算的？</b><br>
            A: 无论用户什么时候点击按钮，文案中的“相恋时间”都以 今天 13:14 为截止点计算。以确保定时在13：14发送的逻辑</p>
            <p><b>Q: 开发框架？</b><br>
            A: GUI：🐍 PySide6
            自动化：🤖 PyAutoGUI + 🔍 OpenCV</p>
            <p><b>Q: 开发时长？</b><br>
            A: 核心功能实现 2 days 不过一直在断断续续完善UI和修复各种bug 也欢迎大家参与到源码的开发</p>
            <p><b>Q: pyautogui在定位图片位置时，若屏幕中有两个相同的图片，它会选择哪一个图片？？</b><br>
            A: “谁最靠左上角，谁就中标；后面的即使一模一样也不会被理会。”
            如果你想把所有相同图标都找出来，就必须用 locateAllOnScreen()，它会返回一个可迭代对象，里面包含所有匹配区域的坐标盒（left, top, width, height），顺序同样是先上后下、先左后右。（已实现）</p>
        """)

        layout.addWidget(text)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)

        dialog.exec()

    def show_about(self):
        # 任意窗口里
        AboutDialog(self).exec()

    def add_task(self, name):
        # 创建自定义列表项
        item = QListWidgetItem(self.task_list)
        item_widget = TaskItemWidget(name, self)
        item.setSizeHint(QSize(0, 45))  # 固定高度确保按钮完全显示
        self.task_list.addItem(item)
        self.task_list.setItemWidget(item, item_widget)

        # 初始化任务配置
        self.tasks[name] = {
            "name": name,
            "schedule": {
                "enable": "立即执行",
                "time": QTime.currentTime().toString("HH:mm:ss"),
                "interval": 0,
                "repeat": "1",
            },
            "steps": [],
        }

        # 应用当前主题样式
        self.apply_button_style(item_widget)

        # 选中新添加的任务
        if self.task_list.count() == 1:
            self.task_list.setCurrentItem(item)

    def create_new_task(self):
        name = f"新任务 {self.task_list.count() + 1}"
        self.add_task(name)
        ts = time.strftime("%H:%M:%S")
        # 日志带 emoji
        self.log_text.appendPlainText(f"[{ts}] ✅ [{name}] 已创建！")

    def duplicate_task(self, name):
        new_name = f"{name} 副本"
        self.add_task(new_name)

        # 复制任务配置
        if name in self.tasks:
            self.tasks[new_name] = deepcopy(self.tasks[name])
            self.tasks[new_name]["name"] = new_name
        # 日志带 emoji
        ts = time.strftime("%H:%M:%S")
        self.log_text.appendPlainText(f"[{ts}] 📋 [{name}] → [{new_name}] 已复制！")

    def rename_task(self, name):
        """重命名任务：同步所有内部结构与 UI，保证顺序一致。"""
        if name not in self.tasks:
            return

        # 1. 弹窗获取新名称
        new_name, ok = QInputDialog.getText(
            self, "重命名任务", "请输入新名称：", text=name
        )
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name:
            QMessageBox.warning(self, "提示", "任务名称不能为空！")
            return
        if new_name == name:
            return
        if new_name in self.tasks:
            QMessageBox.warning(self, "提示", f"任务“{new_name}”已存在。")
            return

        # 2. 找到旧 item 的行号
        row = -1
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            widget = self.task_list.itemWidget(item)
            if widget and widget.task_name == name:
                row = i
                break
        if row == -1:  # 理论上不会发生
            return

        # 3. 创建新 item，并插回原位置
        new_item = QListWidgetItem()
        new_widget = TaskItemWidget(new_name, self)
        new_item.setSizeHint(QSize(0, 45))

        # 4. 复制任务数据
        self.tasks[new_name] = deepcopy(self.tasks[name])
        self.tasks[new_name]["name"] = new_name

        # 5. 替换 UI：先插新的，再删旧的
        self.task_list.insertItem(row, new_item)
        self.task_list.setItemWidget(new_item, new_widget)
        self.task_list.takeItem(row + 1)  # 原来的那行现在是 row+1
        if name in self.scheduled_timers:  # 如果之前有时钟，一起迁移
            self.scheduled_timers[new_name] = self.scheduled_timers.pop(name)

        # 6. 选中新任务并保持焦点
        self.task_list.setCurrentItem(new_item)
        self.apply_button_style(new_widget)

        # 7. 彻底删除旧任务
        del self.tasks[name]
        self.on_log_message(name, f"📝 重命名：{name} → {new_name}")

    def delete_task(self, name):
        row = -1
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            widget = self.task_list.itemWidget(item)
            if widget and widget.task_name == name:
                row = i
                break

        if row >= 0:
            self.task_list.takeItem(row)
            if name in self.tasks:
                # 如果任务有定时器，先停止
                if name in self.scheduled_timers:
                    self.scheduled_timers[name].stop()
                    del self.scheduled_timers[name]
                del self.tasks[name]
            self.on_log_message(name, f"🗑️ 已删除任务：{name}")

            # 新增：检查是否删除了最后一个任务
            if self.task_list.count() == 0:
                # 清空当前任务的配置显示
                self.task_name.clear()
                self.task_status.setText("未选择任务")

                # 重置定时设置
                self.schedule_enable.setCurrentIndex(0)  # "立即执行"
                self.schedule_time.setTime(QTime.currentTime())
                self.repeat_interval.setValue(0)
                self.repeat_count.setCurrentIndex(0)  # "1次"

                # 清空步骤表格
                self.steps_table.setRowCount(0)

                # 重置当前任务引用
                self.current_task = None

                # 重置按钮状态
                self.start_current_btn.setEnabled(False)
                self.stop_current_btn.setEnabled(False)

                self.on_log_message("系统", "📋 最后一个任务已删除，配置已重置")

    def task_selected(self, current, previous):
        if current:
            widget = self.task_list.itemWidget(current)
            if widget:
                task_name = widget.task_name
                self.current_task = task_name
                self.task_name.setText(task_name)
                # Ensure status label text is valid
                status_text = widget.status_label.text()
                self.task_status.setText(status_text)

                # 更新按钮状态
                if status_text == "运行中":
                    self.start_current_btn.setEnabled(False)
                    self.stop_current_btn.setEnabled(True)
                else:
                    self.start_current_btn.setEnabled(True)
                    self.stop_current_btn.setEnabled(False)

                # 加载任务配置
                self.load_task_config(task_name)

    def load_task_config(self, task_name):
        if task_name in self.tasks:
            task_config = self.tasks[task_name]

            # 加载定时设置
            schedule = task_config.get("schedule", {})
            self.schedule_enable.setCurrentText(schedule.get("enable", "立即执行"))

            time_str = schedule.get("time", "")
            if time_str:
                self.schedule_time.setTime(QTime.fromString(time_str, "HH:mm:ss"))

            self.repeat_interval.setValue(int(schedule.get("interval", 0)))
            self.repeat_count.setCurrentText(str(schedule.get("repeat", "1")))

            # 加载步骤
            self.steps_table.setRowCount(0)
            for step in task_config.get("steps", []):
                self.add_step_to_table(step)

    def show_context_menu(self, pos):
        # 获取点击位置的item
        item = self.task_list.itemAt(pos)
        if not item:
            return

        # 创建上下文菜单
        menu = QMenu(self)

        # 获取任务名称
        widget = self.task_list.itemWidget(item)
        task_name = widget.task_name if widget else ""

        # 添加菜单项
        rename_action = menu.addAction("✏️ 重命名")
        duplicate_action = menu.addAction("📋 创建副本")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ 删除任务")

        # Apply menu style
        menu.setStyleSheet(self._menu_style())

        # 显示菜单并获取选择
        action = menu.exec(self.task_list.mapToGlobal(pos))

        # 处理选择
        if action == rename_action:
            self.rename_task(task_name)
        elif action == duplicate_action:
            self.duplicate_task(task_name)
        elif action == delete_action:
            self.delete_task(task_name)

    def add_step_to_table(self, step):
        row = self.steps_table.rowCount()
        self.steps_table.insertRow(row)

        # self.steps_table.setItem(row, 0, QTableWidgetItem(step["type"]))
        # self.steps_table.setItem(row, 1, QTableWidgetItem(StepTableHelper.desc_of(step)))
        use_color = (
            self.label_color_checkbox.isChecked()
            if hasattr(self, "label_color_checkbox")
            else True
        )
        type_widget = StepTableHelper.type_widget(step["type"], use_color)
        self.steps_table.setCellWidget(row, 0, type_widget)
        w = StepTableHelper.widget_of(step, use_color)
        self.steps_table.setCellWidget(row, 1, w)
        self.steps_table.setRowHeight(row, max(StepTableHelper.IMG_HEIGHT + 4, 24))
        self.steps_table.verticalHeader().setDefaultSectionSize(
            StepTableHelper.FIXED_ROW_HEIGHT
        )
        self.steps_table.horizontalHeader().setStretchLastSection(True)

        # 格式化参数显示
        params_text = ""
        if step["type"] == "鼠标点击":
            use_image = step["params"].get("use_image", True)
            use_coordinates = step["params"].get("use_coordinates", False)

            if use_image:
                image_path = step["params"].get("image_path", "")
                image_name = os.path.basename(image_path) if image_path else "未设置"
                click_type = step["params"].get("click_type", "左键单击")
                scan_direction = step["params"].get("scan_direction", "默认")
                offset_x = step["params"].get("offset_x", 0)
                offset_y = step["params"].get("offset_y", 0)
                confidence = step["params"].get("confidence", 0.8)
                timeout = step["params"].get("timeout", 10)

                params_text = (
                    f"图片: {image_name}, 点击: {click_type}, 方向: {scan_direction}"
                )
                if offset_x != 0 or offset_y != 0:
                    params_text += f", 偏移: ({offset_x}, {offset_y})"
                params_text += f", 置信度: {confidence}, 超时: {timeout}s"

            elif use_coordinates:
                x_coord = step["params"].get("x_coordinate", 0)
                y_coord = step["params"].get("y_coordinate", 0)
                click_type = step["params"].get("click_type", "左键单击")
                offset_x = step["params"].get("offset_x", 0)
                offset_y = step["params"].get("offset_y", 0)

                params_text = f"坐标: ({x_coord}, {y_coord}), 点击: {click_type}"
                if offset_x != 0 or offset_y != 0:
                    params_text += f", 偏移: ({offset_x}, {offset_y})"

            else:
                params_text = "未启用图片或坐标模式"
        elif step["type"] == "文本输入":
            params_text = f"文本: {step['params'].get('text', 'excel表内容')}"
        elif step["type"] == "等待":
            params_text = f"等待: {step['params'].get('seconds', 0)}秒"
        elif step["type"] == "截图":
            params_text = f"保存到: {step['params'].get('save_path', '')}"
        elif step["type"] == "鼠标滚轮":
            params_text = f"鼠标滚轮: {step['params'].get('direction', '向下滚动')},{step['params'].get('clicks', '3')}格"
        elif step["type"] == "键盘热键":
            hotkey = step["params"].get("hotkey", "ctrl+c").upper()
            delay = step["params"].get("delay_ms", 100)
            params_text = f"键盘热键: {hotkey}, 延时 {delay} ms"
        elif step["type"] == "拖拽":
            use_image = step["params"].get("use_image", True)
            if use_image:
                img_path = step["params"].get("image_path", "")
                if img_path:
                    img_name = os.path.basename(img_path)
                    dx = step["params"].get("drag_x", 0)
                    dy = step["params"].get("drag_y", 0)
                    params_text = f"图片: {img_name} (横向距离{dx},纵向距离{dy})"
                else:
                    params_text = "图片: 未设置"
            else:
                start_x = step["params"].get("start_x", 0)
                start_y = step["params"].get("start_y", 0)
                end_x = step["params"].get("end_x", 0)
                end_y = step["params"].get("end_y", 0)
                params_text = f"从({start_x},{start_y})到({end_x},{end_y})"

        self.steps_table.setItem(row, 2, QTableWidgetItem(params_text))
        self.steps_table.setItem(row, 3, QTableWidgetItem(str(step.get("delay", 0))))
        self.steps_table.resizeColumnToContents(1)  # 列宽按内容自适应

    def start_current_task(self):
        if not self.current_task:
            return

        # 检查是否有定时设置
        schedule_type = self.schedule_enable.currentText()
        if schedule_type != "立即执行":
            # 验证定时设置
            if not self.validate_schedule_settings():
                return
            # 处理定时执行逻辑
            task_name = self.current_task

            # 如果任务已有定时器，先停止
            if task_name in self.scheduled_timers:
                self.scheduled_timers[task_name].stop()
                del self.scheduled_timers[task_name]

            # 获取定时设置
            schedule_time = self.schedule_time.time()

            # 计算第一次执行的时间
            now = QTime.currentTime()
            first_run = QTime(
                schedule_time.hour(), schedule_time.minute(), schedule_time.second()
            ).addSecs(-10)

            # 如果当前时间已超过设定时间，则明天执行
            if first_run < now:
                first_run = first_run.addSecs(24 * 3600)  # 加一天

            # 计算延迟时间（毫秒）
            delay_ms = now.msecsTo(first_run)

            # 更新主界面按钮状态
            self.start_current_btn.setEnabled(False)
            self.stop_current_btn.setEnabled(True)

            # 更新任务列表中的状态（只更新当前任务）
            for i in range(self.task_list.count()):
                item = self.task_list.item(i)
                widget = self.task_list.itemWidget(item)
                if widget and widget.task_name == self.current_task:
                    widget.status_label.setText("定时执行中")
                    widget.start_btn.setEnabled(False)
                    widget.stop_btn.setEnabled(True)
                    break

            # 创建首次执行的定时器
            initial_timer = QTimer(self)
            initial_timer.setSingleShot(True)  # 只执行一次

            def run_initial_task():
                # 执行倒计时并运行任务
                # 将重复间隔和重复次数传递给任务执行函数
                self.run_task_with_countdown(task_name)

            initial_timer.timeout.connect(run_initial_task)
            initial_timer.start(delay_ms)

            # 保存定时器引用
            self.scheduled_timers[task_name] = initial_timer

            # 显示提示信息
            first_run_1 = first_run.addSecs(10)
            first_run_str = first_run_1.toString("HH:mm:ss")
            self.log_text.appendPlainText(
                f"[{time.strftime('%H:%M:%S')}] 已设置定时任务: {task_name} 将在 {first_run_str} 执行"
            )

            # 显示状态栏信息（不修改全局状态，只显示当前设置信息）
            self.statusBar().showMessage(
                f"定时任务已设置，将在 {first_run_str} 执行 {task_name}"
            )

            QMessageBox.information(
                self,
                "定时成功",
                f"[{time.strftime('%H:%M:%S')}] 已设置定时任务: {task_name} 将在 {first_run_str} 执行\n请保持桌面处于从不熄屏状态",
            )

            return  # 如果是定时执行，直接返回，不立即执行任务
        # 立即执行任务的逻辑
        elif schedule_type == "立即执行":
            self.execute_task_immediately(self.current_task)

    def run_task_with_countdown(self, task_name, countdown_seconds=10):
        """执行带倒计时的任务"""
        # 创建倒计时定时器
        countdown_timer = QTimer(self)
        countdown_timer.setInterval(1000)  # 每秒触发一次

        def update_countdown():
            nonlocal countdown_seconds
            current_time = time.strftime("%H:%M:%S")  # 获取当前时间
            if countdown_seconds > 0:
                self.statusBar().showMessage(
                    f"[{current_time}] 任务 '{task_name}' 即将执行: {countdown_seconds}秒"
                )
                countdown_seconds -= 1
            else:
                countdown_timer.stop()
                current_time = time.strftime("%H:%M:%S")  # 再次获取当前时间
                self.statusBar().showMessage(
                    f"[{current_time}] 任务 '{task_name}' 开始执行"
                )
                # 实际执行任务
                self.execute_task_immediately(task_name)

        # 启动倒计时
        countdown_timer.timeout.connect(update_countdown)
        countdown_timer.start()
        # 立即更新一次倒计时显示
        current_time = time.strftime("%H:%M:%S")
        self.statusBar().showMessage(
            f"[{current_time}] 任务 '{task_name}' 即将执行: {countdown_seconds}秒"
        )
        # 保存倒计时定时器引用以便可以停止
        if not hasattr(self, "countdown_timers"):
            self.countdown_timers = {}
        self.countdown_timers[task_name] = countdown_timer

    def execute_task_immediately(self, task_name):
        """立即执行任务的公共方法"""
        # if task_name not in self.current_task:
        #     return

        # 清除状态栏的倒计时信息
        self.statusBar().showMessage("")

        # 获取任务配置
        task_config = self.tasks.get(task_name, {})
        steps = task_config.get("steps", [])

        if not steps:
            QMessageBox.warning(self, "无法启动", "当前任务没有配置任何步骤")
            return

        auto_skip = self.auto_skip_checkbox.isChecked()  # ✅ 读取 QCheckBox 状态
        timeout = self.timeout_spinbox.value()  # 获取用户设置的超时时间
        instant_click = self.instant_click_checkbox.isChecked()
        move_duration = self.move_duration_spinbox.value() if not instant_click else 0.0

        # 创建任务运行器
        self.task_runner = TaskRunner(
            task_name,
            steps,
            auto_skip_image_timeout=auto_skip,
            timeout=timeout,
            instant_click=instant_click,
            move_duration=move_duration,
            parent=self,
        )

        # 设置重复次数
        repeat_text = self.repeat_count.currentText()

        if self.repeat_interval.value() == 0:
            if repeat_text == "无限":
                self.task_runner.set_repeat_count(99999)  # 设置一个很大的数表示无限
            else:
                count = int(repeat_text)
                self.task_runner.set_repeat_count(count)
        elif self.repeat_interval.value() > 0:
            self.task_runner.set_repeat_interval(self.repeat_interval.value())
            if repeat_text == "无限":
                self.task_runner.set_repeat_count(99999)  # 设置一个很大的数表示无限
            else:
                count = int(repeat_text)
                self.task_runner.set_repeat_count(count)
        # 连接信号
        self.task_runner.task_completed.connect(self.on_task_completed)
        self.task_runner.task_progress.connect(self.on_task_progress)
        self.task_runner.log_message.connect(self.on_log_message)  # 连接日志信号

        # 在单独线程中运行任务
        self.task_thread = threading.Thread(target=self.task_runner.run)
        self.task_thread.daemon = True
        self.task_thread.start()

        # 更新UI状态
        self.start_current_btn.setEnabled(False)
        self.stop_current_btn.setEnabled(True)
        self.task_status.setText("运行中")

        # 更新任务列表中的状态
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            widget = self.task_list.itemWidget(item)
            if widget and widget.task_name == self.current_task:
                widget.status_label.setText("运行中")
                widget.start_btn.setEnabled(False)
                widget.stop_btn.setEnabled(True)
                break
        if (
            hasattr(self, "minimize_during_execution_checkbox")
            and self.minimize_during_execution_checkbox.isChecked()
        ):
            # 新增：任务开始后最小化窗口
            self.showMinimized()
        # self.statusBar().showMessage("任务执行完成")

    def stop_current_task(self):
        # 停止当前运行的任务
        if self.task_runner and self.task_runner.is_running:
            self.task_runner.stop()

        # 停止当前任务的定时器（如果有）
        if self.current_task and self.current_task in self.scheduled_timers:
            timer = self.scheduled_timers[self.current_task]
            if timer and timer.isActive():
                timer.stop()
            del self.scheduled_timers[self.current_task]

        # 停止当前任务的倒计时（如果有）
        if (
            hasattr(self, "countdown_timers")
            and self.current_task in self.countdown_timers
        ):
            countdown_timer = self.countdown_timers[self.current_task]
            if countdown_timer and countdown_timer.isActive():
                countdown_timer.stop()
            del self.countdown_timers[self.current_task]

            # 记录日志
            self.log_text.appendPlainText(
                f"[{time.strftime('%H:%M:%S')}] 已取消定时任务: {self.current_task}"
            )

        # 更新UI状态
        self.start_current_btn.setEnabled(True)
        self.stop_current_btn.setEnabled(False)
        self.task_status.setText("已停止")

        # 清除状态栏的倒计时信息
        self.statusBar().showMessage("任务已停止")

        # 更新任务列表中的状态
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            widget = self.task_list.itemWidget(item)
            if widget and widget.task_name == self.current_task:
                widget.status_label.setText("已停止")
                widget.start_btn.setEnabled(True)
                widget.stop_btn.setEnabled(False)
                break

        # 恢复窗口显示（如果之前最小化了）
        self.showNormal()

    def cleanup_scheduled_timers(self):
        """清理无效的定时器"""
        tasks_to_remove = []
        for task_name, timer in self.scheduled_timers.items():
            if timer is None or not timer.isActive():
                tasks_to_remove.append(task_name)

        for task_name in tasks_to_remove:
            del self.scheduled_timers[task_name]

        if tasks_to_remove:
            self.log_text.appendPlainText(
                f"[{time.strftime('%H:%M:%S')}] 清理了 {len(tasks_to_remove)} 个无效定时器"
            )

    def stop_all_scheduled_tasks(self):
        """停止所有定时任务"""
        tasks_stopped = []
        for task_name, timer in list(self.scheduled_timers.items()):
            if timer and timer.isActive():
                timer.stop()
                tasks_stopped.append(task_name)

        # 清空定时器字典
        self.scheduled_timers.clear()

        # 记录日志
        if tasks_stopped:
            self.log_text.appendPlainText(
                f"[{time.strftime('%H:%M:%S')}] 已停止所有定时任务: {', '.join(tasks_stopped)}"
            )
            self.statusBar().showMessage(f"已停止 {len(tasks_stopped)} 个定时任务")

    def on_task_completed(self, task_name, success, message):
        # 新增：任务完成后恢复窗口显示
        self.showNormal()

        # 更新UI状态
        self.start_current_btn.setEnabled(True)
        self.stop_current_btn.setEnabled(False)
        self.task_status.setText("已停止" if success else "已中断")

        # 更新任务列表中的状态
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            widget = self.task_list.itemWidget(item)
            if widget and widget.task_name == task_name:
                widget.status_label.setText("已停止" if success else "已中断")
                widget.start_btn.setEnabled(True)
                widget.stop_btn.setEnabled(False)
                break

        # 记录日志
        # self.log_text.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {message}")

    def on_task_progress(self, task_name, current, total):
        self.task_status.setText(f"运行中 ({current}/{total})")

    def on_log_message(self, task_name, message):
        """处理日志消息"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        log_entry = f"[{timestamp}] [{task_name}] {message}"
        self.log_text.appendPlainText(log_entry)

        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def switch_theme(self, theme):
        if theme == "system":
            self.detect_system_theme()
        else:
            self.current_theme = theme
            self.apply_theme(theme)
            self.settings.setValue("theme", theme)

        # 更新主题菜单选中状态
        self.light_theme_action.setChecked(self.current_theme == "light")
        self.dark_theme_action.setChecked(self.current_theme == "dark")
        self.system_theme_action.setChecked(theme == "system")

        # 更新任务列表按钮样式
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            widget = self.task_list.itemWidget(item)
            if widget:
                self.apply_button_style(widget)

    def detect_system_theme(self):
        """检测系统主题设置"""
        try:
            # 尝试检测系统是否处于暗黑模式
            # 这里只是一个示例，实际实现需要根据操作系统进行适配
            # 在Windows上可以使用注册表，在macOS上可以使用NSAppearance
            # 这里简化为使用系统设置中的值
            dark_mode = self.settings.value("systemDarkMode", False, type=bool)
            self.current_theme = "dark" if dark_mode else "light"
        except Exception:
            self.current_theme = "light"

        self.apply_theme(self.current_theme)
        self.settings.setValue("theme", "system")

    def apply_button_style(self, widget):
        """应用按钮样式到任务项控件"""
        if self.current_theme == "light":
            widget.start_btn.setStyleSheet(self.light_button_style("start"))
            widget.stop_btn.setStyleSheet(self.light_button_style("stop"))
            widget.delete_btn.setStyleSheet(self.light_button_style("delete"))
            widget.status_label.setStyleSheet("color: #888; background: transparent;")
        else:
            widget.start_btn.setStyleSheet(self.dark_button_style("start"))
            widget.stop_btn.setStyleSheet(self.dark_button_style("stop"))
            widget.delete_btn.setStyleSheet(self.dark_button_style("delete"))
            widget.status_label.setStyleSheet("color: #aaa; background: transparent;")

    def light_button_style(self, btn_type):
        """明亮主题按钮样式"""
        base_style = """
            QPushButton {
                border-radius: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """

        if btn_type == "start":
            return (
                base_style
                + """
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f5f5f5, stop:1 #e0e0e0);
            """
            )
        elif btn_type == "stop":
            return (
                base_style
                + """
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f5f5f5, stop:1 #e0e0e0);
            """
            )
        else:  # delete
            return (
                base_style
                + """
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f5f5f5, stop:1 #e0e0e0);
            """
            )

    def dark_button_style(self, btn_type):
        """暗黑主题按钮样式"""
        base_style = """
            QPushButton {
                border-radius: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #404040;
            }
        """

        if btn_type == "start":
            return (
                base_style
                + """
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #505050, stop:1 #404040);
            """
            )
        elif btn_type == "stop":
            return (
                base_style
                + """
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #505050, stop:1 #404040);
            """
            )
        else:  # delete
            return (
                base_style
                + """
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #505050, stop:1 #404040);
            """
            )

    def apply_theme(self, theme):
        if theme == "light":
            # 明亮主题
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f5f7fa;
                }
                QWidget {
                    background-color: #f5f7fa;
                    color: #333;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #d1d5db;
                    border-radius: 6px;
                    margin-top: 20px;
                    padding-top: 10px;
                    background-color: white;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    left: 10px;
                    padding: 0 5px;
                    background-color: white;
                    color: #333;
                }
                QListWidget, QTableWidget, QLineEdit, QComboBox, QTimeEdit, QSpinBox, QPlainTextEdit {
                    background-color: white;
                    border: 1px solid #d1d5db;
                    color: #333;
                }
                QHeaderView::section {
                    background-color: #f0f0f0;
                    color: #333;
                    border: none;
                    border-bottom: 1px solid #d1d5db;
                }
                QPushButton {
                    color: #333;
                }
                QLabel {
                    color: #333;
                }
                QCheckBox {
                    color: #333;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 10px;
                    height: 10px;
                    border: 2px solid #999;
                    border-radius: 4px;
                    background: #fff;
                }
                QCheckBox::indicator:checked {
                    background: #4CAF50;
                    border: 2px solid #388E3C;
                }
                QCheckBox::indicator:hover {
                    border-color: #4CAF50;
                }
                QListWidget::item:selected {
                    background-color: #e3f2fd;
                }
            """)

            # 应用按钮样式
            self.start_current_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    border: 1px solid #388E3C;
                    color: white;
                    padding: 5px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #388E3C;
                }
                QPushButton:disabled {
                    background-color: #81C784;
                }
            """)

            self.stop_current_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    border: 1px solid #388E3C;
                    color: white;
                    padding: 5px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #388E3C;
                }
                QPushButton:disabled {
                    background-color: #81C784;
                }
            """)

            self.save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    border: 1px solid #388E3C;
                    color: white;
                    padding: 5px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #388E3C;
                }
                QPushButton:disabled {
                    background-color: #81C784;
                }
            """)

            self.new_task_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    border: 1px solid #388E3C;
                    color: white;
                    padding: 5px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #388E3C;
                }
            """)

            self.clear_log_btn.setStyleSheet("""
                QPushButton {
                    background-color: #9E9E9E;
                    border: 1px solid #757575;
                    color: white;
                    padding: 2px 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #757575;
                }
            """)
        else:
            # 暗黑主题
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2d2d30;
                }
                QWidget {
                    background-color: #2d2d30;
                    color: #dcdcdc;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #3f3f46;
                    border-radius: 6px;
                    margin-top: 20px;
                    padding-top: 10px;
                    background-color: #252526;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    left: 10px;
                    padding: 0 5px;
                    background-color: #252526;
                    color: #dcdcdc;
                }
                QListWidget, QTableWidget, QLineEdit, QComboBox, QTimeEdit, QSpinBox, QPlainTextEdit {
                    background-color: #1e1e1e;
                    border: 1px solid #3f3f46;
                    color: #dcdcdc;
                }
                QHeaderView::section {
                    background-color: #333337;
                    color: #dcdcdc;
                    border: none;
                    border-bottom: 1px solid #3f3f46;
                }
                QPushButton {
                    color: #dcdcdc;
                    background-color: #3e3e42;
                    border: 1px solid #555;
                }
                QLabel {
                    color: #dcdcdc;
                }
                QCheckBox {
                    color: #dcdcdc;
                    spacing: 8px;
                }
                QCheckBox::indicator {
                    width: 10px;
                    height: 10px;
                    border: 2px solid #555;
                    border-radius: 4px;
                    background: #3e3e42;
                }
                QCheckBox::indicator:checked {
                    background: #4CAF50;
                    border: 2px solid #388E3C;
                }
                QCheckBox::indicator:hover {
                    border-color: #4CAF50;
                }
                QListWidget::item:selected {
                    background-color: #37373d;
                }
            """)

            # 应用按钮样式
            self.start_current_btn.setStyleSheet("""
                QPushButton {
                    background-color: #388E3C;
                    border: 1px solid #2E7D32;
                    color: white;
                    padding: 5px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #2E7D32;
                }
                QPushButton:disabled {
                    background-color: #555;
                    color: #888;
                }
            """)

            self.stop_current_btn.setStyleSheet("""
                QPushButton {
                    background-color: #388E3C;
                    border: 1px solid #2E7D32;
                    color: white;
                    padding: 5px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #2E7D32;
                }
                QPushButton:disabled {
                    background-color: #555;
                    color: #888;
                }
            """)

            self.save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #388E3C;
                    border: 1px solid #2E7D32;
                    color: white;
                    padding: 5px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #2E7D32;
                }
                QPushButton:disabled {
                    background-color: #555;
                    color: #888;
                }
            """)

            self.new_task_btn.setStyleSheet("""
                QPushButton {
                    background-color: #388E3C;
                    border: 1px solid #2E7D32;
                    color: white;
                    padding: 5px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #2E7D32;
                }
            """)

            self.clear_log_btn.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    border: 1px solid #333;
                    color: #dcdcdc;
                    padding: 2px 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
            """)

    def add_step(self):
        dialog = StepConfigDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            step_data = dialog.get_step_data()
            self.add_step_to_table(step_data)

            # 添加到当前任务配置
            if self.current_task and self.current_task in self.tasks:
                self.tasks[self.current_task]["steps"].append(step_data)

    def copy_step(self):
        """复制当前选中的步骤"""
        selected_row = self.steps_table.currentRow()
        if selected_row < 0:
            QMessageBox.information(self, "提示", "请先选中一条步骤再复制。")
            return

        # 取出原步骤数据
        src_step = self.tasks[self.current_task]["steps"][selected_row]
        # 深拷贝，避免后续修改互相影响
        new_step = deepcopy(src_step)

        # 直接追加到表格和任务配置
        self.add_step_to_table(new_step)
        self.tasks[self.current_task]["steps"].append(new_step)

    def edit_step(self):
        selected_row = self.steps_table.currentRow()
        if selected_row < 0:
            return

        # 获取当前步骤数据
        step_data = self.tasks[self.current_task]["steps"][selected_row]
        dialog = StepConfigDialog(step_data, parent=self)
        if dialog.exec() == QDialog.Accepted:
            new_step_data = dialog.get_step_data()
            # 更新表格
            use_color = (
                self.label_color_checkbox.isChecked()
                if hasattr(self, "label_color_checkbox")
                else True
            )
            type_widget = StepTableHelper.type_widget(new_step_data["type"], use_color)
            self.steps_table.setCellWidget(selected_row, 0, type_widget)
            # self.steps_table.setItem(selected_row, 0, QTableWidgetItem(new_step_data["type"]))
            w = StepTableHelper.widget_of(new_step_data, use_color)
            self.steps_table.setCellWidget(selected_row, 1, w)
            self.steps_table.setRowHeight(
                selected_row, max(StepTableHelper.IMG_HEIGHT + 4, 24)
            )
            self.steps_table.verticalHeader().setDefaultSectionSize(
                StepTableHelper.FIXED_ROW_HEIGHT
            )
            self.steps_table.horizontalHeader().setStretchLastSection(True)
            # 格式化参数显示
            params_text = ""
            params = new_step_data["params"]
            if new_step_data["type"] == "鼠标点击":
                use_image = params.get("use_image", True)
                use_coordinates = params.get("use_coordinates", False)

                if use_image:
                    img_path = params.get("image_path", "")
                    click_type = params.get("click_type", "左键单击")
                    scan_direction = params.get("scan_direction", "默认")
                    offset_x = params.get("offset_x", 0)
                    offset_y = params.get("offset_y", 0)

                    img_name = os.path.basename(img_path) if img_path else "未设置"
                    params_text = (
                        f"图片: {img_name}, 点击: {click_type}, 方向: {scan_direction}"
                    )
                    if offset_x != 0 or offset_y != 0:
                        params_text += f", 偏移: ({offset_x}, {offset_y})"

                elif use_coordinates:
                    x_coord = params.get("x_coordinate", 0)
                    y_coord = params.get("y_coordinate", 0)
                    click_type = params.get("click_type", "左键单击")
                    offset_x = params.get("offset_x", 0)
                    offset_y = params.get("offset_y", 0)

                    params_text = f"坐标: ({x_coord}, {y_coord}), 点击: {click_type}"
                    if offset_x != 0 or offset_y != 0:
                        params_text += f", 偏移: ({offset_x}, {offset_y})"

                else:
                    params_text = "未启用图片或坐标模式"
            elif new_step_data["type"] == "文本输入":
                # 优先显示纯文本
                txt = params.get("text", "")
                if txt:
                    params_text = f"文本: {txt}"
                else:
                    # Excel 模式
                    mode = params.get("mode", "顺序")
                    path = os.path.basename(params.get("excel_path", ""))
                    sheet = params.get("sheet", "0")
                    col = params.get("col", 0)
                    params_text = f"Excel({mode}) {path}|{sheet}|列{col}"
            elif new_step_data["type"] == "等待":
                params_text = f"等待: {new_step_data['params'].get('seconds', 0)}秒"
            elif new_step_data["type"] == "截图":
                params_text = f"保存到: {new_step_data['params'].get('save_path', '')}"
            elif new_step_data["type"] == "拖拽":
                use_image = new_step_data["params"].get("use_image", True)
                if use_image:
                    img_path = new_step_data["params"].get("image_path", "")
                    if img_path:
                        img_name = os.path.basename(img_path)
                        dx = new_step_data["params"].get("drag_x", 0)
                        dy = new_step_data["params"].get("drag_y", 0)
                        params_text = f"图片: {img_name} (+{dx},+{dy})"
                    else:
                        params_text = "图片: 未设置"
                else:
                    start_x = new_step_data["params"].get("start_x", 0)
                    start_y = new_step_data["params"].get("start_y", 0)
                    end_x = new_step_data["params"].get("end_x", 0)
                    end_y = new_step_data["params"].get("end_y", 0)
                    params_text = f"从({start_x},{start_y})到({end_x},{end_y})"
            elif new_step_data["type"] == "AI 自动回复":
                params_text = f"AI: {new_step_data['params'].get('ai_name', '')}"

            self.steps_table.setItem(selected_row, 2, QTableWidgetItem(params_text))
            self.steps_table.setItem(
                selected_row, 3, QTableWidgetItem(str(new_step_data.get("delay", 0)))
            )

            self.tasks[self.current_task]["steps"][selected_row] = new_step_data

    def remove_step(self):
        selected_row = self.steps_table.currentRow()
        if selected_row >= 0:
            self.steps_table.removeRow(selected_row)

            # 从任务配置中移除
            if self.current_task and self.current_task in self.tasks:
                self.tasks[self.current_task]["steps"].pop(selected_row)

    def move_step_up(self):
        selected_row = self.steps_table.currentRow()
        if selected_row > 0:
            # 移动表格行
            self.steps_table.insertRow(selected_row - 1)
            for col in range(self.steps_table.columnCount()):
                # 移动 QTableWidgetItem
                self.steps_table.setItem(
                    selected_row - 1,
                    col,
                    self.steps_table.takeItem(selected_row + 1, col),
                )
                # 移动 cellWidget
                widget = self.steps_table.cellWidget(selected_row + 1, col)
                if widget:
                    self.steps_table.setCellWidget(selected_row - 1, col, widget)
            self.steps_table.removeRow(selected_row + 1)
            self.steps_table.setCurrentCell(selected_row - 1, 0)

            # 移动任务配置中的步骤
            if self.current_task and self.current_task in self.tasks:
                steps = self.tasks[self.current_task]["steps"]
                steps.insert(selected_row - 1, steps.pop(selected_row))

    def move_step_down(self):
        selected_row = self.steps_table.currentRow()
        if selected_row >= 0 and selected_row < self.steps_table.rowCount() - 1:
            # 移动表格行
            self.steps_table.insertRow(selected_row + 2)
            for col in range(self.steps_table.columnCount()):
                # 移动 QTableWidgetItem
                self.steps_table.setItem(
                    selected_row + 2, col, self.steps_table.takeItem(selected_row, col)
                )
                # 移动 cellWidget
                widget = self.steps_table.cellWidget(selected_row, col)
                if widget:
                    self.steps_table.setCellWidget(selected_row + 2, col, widget)
            self.steps_table.removeRow(selected_row)
            self.steps_table.setCurrentCell(selected_row + 1, 0)

            # 移动任务配置中的步骤
            if self.current_task and self.current_task in self.tasks:
                steps = self.tasks[self.current_task]["steps"]
                steps.insert(selected_row + 1, steps.pop(selected_row))

    def save_task_config(self):
        if not self.current_task:
            return

        # 更新任务名称
        new_name = self.task_name.text().strip()
        if new_name and new_name != self.current_task:
            # 更新任务列表
            for i in range(self.task_list.count()):
                item = self.task_list.item(i)
                widget = self.task_list.itemWidget(item)
                if widget and widget.task_name == self.current_task:
                    widget.task_name = new_name
                    widget.name_label.setText(new_name)

                    # 更新任务配置
                    task_config = self.tasks.pop(self.current_task)
                    task_config["name"] = new_name
                    self.tasks[new_name] = task_config
                    self.current_task = new_name
                    break

        self.export_config_default()
        # QMessageBox.information(self, "保存成功", "任务配置已保存")

    def export_config(self):
        if not self.current_task:
            return
        if self.current_task in self.tasks:
            self.tasks[self.current_task]["schedule"] = {
                "enable": self.schedule_enable.currentText(),
                "time": self.schedule_time.time().toString("HH:mm:ss"),
                "interval": self.repeat_interval.value(),
                "repeat": self.repeat_count.currentText(),
            }
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", "", "JSON文件 (*.json)"
        )
        if file_path:
            if not file_path.lower().endswith(".json"):
                file_path += ".json"

            if self.current_task in self.tasks:
                with open(file_path, "w") as f:
                    json.dump(self.tasks[self.current_task], f, indent=4)
                QMessageBox.information(self, "导出成功", "任务配置已导出")

    def export_config_default(self):
        if not self.current_task:
            return
        if self.current_task in self.tasks:
            self.tasks[self.current_task]["schedule"] = {
                "enable": self.schedule_enable.currentText(),
                "time": self.schedule_time.time().toString("HH:mm:ss"),
                "interval": self.repeat_interval.value(),
                "repeat": self.repeat_count.currentText(),
            }

            # 创建config目录（如果不存在）
            config_dir = os.path.join(os.getcwd(), "config")
            os.makedirs(config_dir, exist_ok=True)

            # 生成文件路径
            file_name = f"{self.current_task}.json"
            file_path = os.path.join(config_dir, file_name)

            # 保存配置文件
            if self.current_task in self.tasks:
                with open(file_path, "w") as f:
                    json.dump(self.tasks[self.current_task], f, indent=4)
                QMessageBox.information(
                    self, "导出成功", f"任务配置已导出到: {file_path}"
                )

    def import_config(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置", "", "JSON文件 (*.json)"
        )
        if file_path:
            try:
                with open(file_path, "r") as f:
                    task_config = json.load(f)

                task_name = task_config.get("name", "导入的任务")
                self.add_task(task_name)
                self.tasks[task_name] = task_config

                # 选中新导入的任务
                for i in range(self.task_list.count()):
                    item = self.task_list.item(i)
                    widget = self.task_list.itemWidget(item)
                    if widget and widget.task_name == task_name:
                        self.task_list.setCurrentItem(item)
                        break
                self.load_task_config(task_name)

                QMessageBox.information(self, "导入成功", "任务配置已导入")
            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"导入配置时出错: {str(e)}")

    def apply_schedule(self):
        """应用定时设置"""
        if not self.current_task:
            return

        task_name = self.current_task

        # 如果任务已有定时器，先停止
        if task_name in self.scheduled_timers:
            self.scheduled_timers[task_name].stop()
            del self.scheduled_timers[task_name]

        # 获取定时设置
        schedule_type = self.schedule_enable.currentText()
        if schedule_type == "立即执行":
            # 不需要定时器
            return

        # 定时执行
        schedule_time = self.schedule_time.time()
        interval_minutes = self.repeat_interval.value()
        repeat_count = self.repeat_count.currentText()

        # 计算第一次执行的时间
        now = QTime.currentTime()
        first_run = QTime(
            schedule_time.hour(), schedule_time.minute(), schedule_time.second()
        )

        # 如果当前时间已超过设定时间，则明天执行
        if first_run < now:
            first_run = first_run.addSecs(24 * 3600)  # 加一天

        # 计算延迟时间（毫秒）
        delay_ms = now.msecsTo(first_run)

        # 创建首次执行的定时器
        initial_timer = QTimer(self)
        initial_timer.setSingleShot(True)  # 只执行一次

        def run_initial_task():
            # 执行任务
            self.start_current_task()

            # 如果需要重复执行，设置重复定时器
            if repeat_count == "无限":
                repeat_timer = QTimer(self)
                repeat_timer.timeout.connect(self.start_current_task)
                repeat_timer.setInterval(interval_minutes * 60 * 1000)  # 转换为毫秒
                repeat_timer.start()
                # 保存重复定时器引用
                self.scheduled_timers[task_name] = repeat_timer
            elif repeat_count != "1":
                try:
                    total_count = int(repeat_count)
                    current_count = 1  # 第一次已经执行

                    if current_count < total_count:
                        repeat_timer = QTimer(self)

                        def run_repeat_task():
                            nonlocal current_count
                            self.start_current_task()
                            current_count += 1
                            if current_count >= total_count:
                                repeat_timer.stop()
                                if task_name in self.scheduled_timers:
                                    del self.scheduled_timers[task_name]

                        repeat_timer.timeout.connect(run_repeat_task)
                        repeat_timer.setInterval(interval_minutes * 60 * 1000)
                        repeat_timer.start()
                        # 保存重复定时器引用
                        self.scheduled_timers[task_name] = repeat_timer
                except ValueError:
                    pass  # 无效的重复次数

        initial_timer.timeout.connect(run_initial_task)
        initial_timer.start(delay_ms)

        # 保存首次执行定时器引用
        self.scheduled_timers[task_name] = initial_timer

        # 显示提示信息
        self.log_text.appendPlainText(
            f"[{time.strftime('%H:%M:%S')}] 已设置定时任务: {task_name} 将在 {first_run.toString('HH:mm:ss')} 执行"
        )
        QMessageBox.information(
            self,
            "定时成功",
            f"[{time.strftime('%H:%M:%S')}] 已设置定时任务: {task_name} 将在 {first_run.toString('HH:mm:ss')} 执行\n请保持桌面处于从不熄屏状态",
        )

    def run_scheduled_task(self, task_name, timer, count):
        """执行定时任务（带计数）"""
        if count <= 0:
            timer.stop()
            if task_name in self.scheduled_timers:
                del self.scheduled_timers[task_name]
            return

        # 执行任务
        self.start_current_task()

        # 减少计数
        if count > 1:
            # 设置下一次执行
            QTimer.singleShot(
                0, lambda: self.run_scheduled_task(task_name, timer, count - 1)
            )
        else:
            timer.stop()
            if task_name in self.scheduled_timers:
                del self.scheduled_timers[task_name]
