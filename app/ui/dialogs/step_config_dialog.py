import os
from datetime import date, datetime, time, timedelta

from pynput import keyboard
from pynput.keyboard import Key, KeyCode
from PySide6.QtCore import QDate, QDateTime, QRect, Qt, QThread, QTime
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStackedLayout,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui.components.at_icon import ATIcon
from app.ui.components.coordinate_picker import CoordinatePickerOverlay
from app.ui.components.region_capture import RegionCaptureOverlay


class StepConfigDialog(QDialog):
    def __init__(self, step_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("配置步骤")
        self.setMinimumWidth(500)
        self.setWindowIcon(ATIcon.icon())

        layout = QVBoxLayout(self)

        # 步骤类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("步骤类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(
            [
                "鼠标点击",
                "文本输入",
                "等待",
                "截图",
                "拖拽",
                "鼠标滚轮",
                "键盘热键",
                "AI 自动回复",
            ]
        )
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)

        # 参数配置区域
        self.params_stack = QWidget()
        self.params_layout = QStackedLayout(self.params_stack)
        self.params_layout.setContentsMargins(0, 10, 0, 0)

        # 创建不同步骤类型的参数面板
        self.mouse_click_panel = self.create_mouse_click_panel()
        self.keyboard_input_panel = self.create_keyboard_input_panel()
        self.wait_panel = self.create_wait_panel()
        self.screenshot_panel = self.create_screenshot_panel()
        self.drag_panel = self.create_drag_panel()
        self.scroll_panel = self.create_mouse_scroll_panel()
        self.hot_keyboard_panel = self.create_hot_keyboard_panel()
        self.ai_reply_panel = self.create_ai_reply_panel()

        # 添加到堆栈
        self.params_layout.addWidget(self.mouse_click_panel)
        self.params_layout.addWidget(self.keyboard_input_panel)
        self.params_layout.addWidget(self.wait_panel)
        self.params_layout.addWidget(self.screenshot_panel)
        self.params_layout.addWidget(self.drag_panel)
        self.params_layout.addWidget(self.scroll_panel)
        self.params_layout.addWidget(self.hot_keyboard_panel)
        self.params_layout.addWidget(self.ai_reply_panel)

        layout.addWidget(self.params_stack)

        # 延时设置
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("步骤执行后延时(秒):"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 3600)
        self.delay_spin.setValue(0)
        delay_layout.addWidget(self.delay_spin)
        layout.addLayout(delay_layout)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # 连接信号
        self.type_combo.currentIndexChanged.connect(self.update_params_panel)

        # 初始化UI
        self.update_params_panel()

        # 如果有传入步骤数据，填充表单
        if step_data:
            self.load_step_data(step_data)

    # 1. 新增极简滚轮面板
    def create_mouse_scroll_panel(self):
        panel = QWidget()
        layout = QFormLayout(panel)

        # 方向
        self.scroll_direction_combo = QComboBox()
        self.scroll_direction_combo.addItems(["向上滚动", "向下滚动"])
        layout.addRow("滚动方向:", self.scroll_direction_combo)

        # 格数
        self.scroll_clicks_spin = QSpinBox()
        self.scroll_clicks_spin.setRange(1, 100)
        self.scroll_clicks_spin.setValue(3)
        layout.addRow("滚动格数:", self.scroll_clicks_spin)

        return panel

    def create_hot_keyboard_panel(self):
        panel = QWidget()
        layout = QFormLayout(panel)

        # 热键输入框和按钮
        hotkey_layout = QHBoxLayout()
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setPlaceholderText("点击按钮录制热键")
        self.hotkey_input.setReadOnly(True)

        self.record_hotkey_btn = QPushButton("录制热键")
        self.record_hotkey_btn.clicked.connect(self.start_hotkey_recording)

        hotkey_layout.addWidget(self.hotkey_input)
        hotkey_layout.addWidget(self.record_hotkey_btn)

        layout.addRow("热键:", hotkey_layout)

        # 预设热键下拉框（可选）
        self.preset_hotkey_combo = QComboBox()
        self.preset_hotkey_combo.addItems(
            [
                "Ctrl+C",
                "Ctrl+V",
                "Ctrl+X",
                "Ctrl+Z",
                "Ctrl+A",
                "Ctrl+S",
                "Ctrl+F",
                "Alt+Tab",
                "Ctrl+Alt+Del",
                "F1",
                "F2",
                "F3",
                "F4",
                "F5",
                "F6",
                "F7",
                "F8",
                "F9",
                "F10",
                "F11",
                "F12",
                "Ctrl+F1",
                "Ctrl+F2",
                "Ctrl+F3",
                "Ctrl+F4",
                "Ctrl+F5",
                "Alt+F4",
                "Ctrl+Shift+Esc",
                "Ctrl+Alt+W",
                "Ctrl+Alt+S",
                "Enter",
                "Backspace",
                "Tab",
            ]
        )
        self.hotkey_input.setText("Ctrl+C")
        self._hotkey_value = "Ctrl+C"
        self.preset_hotkey_combo.currentTextChanged.connect(
            self.on_preset_hotkey_selected
        )
        layout.addRow("预设热键:", self.preset_hotkey_combo)

        # 额外延迟（ms）
        self.hotkey_delay_spin = QSpinBox()
        self.hotkey_delay_spin.setRange(0, 5000)
        self.hotkey_delay_spin.setValue(100)
        self.hotkey_delay_spin.setSuffix(" ms")
        layout.addRow("执行后延时:", self.hotkey_delay_spin)

        # 存储热键值的隐藏属性
        return panel

    def on_preset_hotkey_selected(self, text):
        """处理预设热键选择事件"""
        if text:
            self.hotkey_input.setText(text)
            self._hotkey_value = text  # 同时更新 _hotkey_value

    def start_hotkey_recording(self):
        """开始录制热键"""
        self.record_hotkey_btn.setText("按下热键...")
        self.record_hotkey_btn.setEnabled(False)
        self.hotkey_input.clear()

        # 启动热键监听
        self.hotkey_listener = keyboard.Listener(
            on_press=self.on_hotkey_press, on_release=self.on_hotkey_release
        )
        self.hotkey_listener.start()
        self.current_keys = set()

    def on_hotkey_press(self, key):
        """热键按下事件"""
        # ========== 新增开始 ==========
        # Windows 把 Ctrl+字母 变成控制字符，这里还原成字母
        if (
            isinstance(key, KeyCode)
            and key.char
            and "\x00" <= key.char <= "\x1f"
            and Key.ctrl_l in self.current_keys
            or Key.ctrl_r in self.current_keys
        ):
            # 还原成 Ctrl+字母
            letter = chr(ord(key.char) + 64)  # 0x01 -> 'A'
            self.current_keys.add(KeyCode.from_char(letter.lower()))
            # 不再把原始 \x01 放进集合
            return
        # ========== 新增结束 ==========
        self.current_keys.add(key)
        # 实时显示当前按键组合
        hotkey_str = self.format_hotkey(self.current_keys)
        self.hotkey_input.setText(hotkey_str)

    def on_hotkey_release(self, key):
        """热键释放事件"""
        # 当所有键都释放时，完成录制
        if key in self.current_keys:
            self.current_keys.remove(key)
            print(self.current_keys)
        if not self.current_keys:  # 所有键都已释放
            hotkey_str = self.hotkey_input.text()
            if hotkey_str:
                self._hotkey_value = hotkey_str
                self.record_hotkey_btn.setText("录制热键")
                self.record_hotkey_btn.setEnabled(True)
                if self.hotkey_listener:
                    self.hotkey_listener.stop()
            return False  # 停止监听

    def format_hotkey(self, keys):
        """
        把 pynput 得到的按键列表转成统一字符串，例如：
        [Key.ctrl, Key.alt, KeyCode.from_char('w')]  ->  'CTRL+ALT+W'
        """
        names = []

        for k in keys:
            if isinstance(k, Key):
                # 特殊键：统一大小写并去掉 _l / _r
                name = {
                    Key.ctrl_l: "CTRL",
                    Key.ctrl_r: "CTRL",
                    Key.alt_l: "ALT",
                    Key.alt_r: "ALT",
                    Key.shift_l: "SHIFT",
                    Key.shift_r: "SHIFT",
                    Key.cmd: "WIN",  # ← 新增这一行
                    Key.cmd_r: "WIN",  # 右Win 保险起见也写上
                    Key.cmd_l: "WIN",  # 左Win 保险起见也写上
                }.get(k, k.name.upper())
                names.append(name)

            elif isinstance(k, KeyCode):
                # 普通字符：优先用 char 字段
                char = k.char.upper() if k.char else ""
                if char:
                    names.append(char)
                else:
                    # 功能键、空格、回车等用 vk → 名字映射
                    try:
                        names.append(Key.from_vk(k.vk).name.upper())
                    except ValueError as e:
                        print(f"无法将按键 {k} 转换为名称：{e}")

        # 去重并保持顺序：CTRL/ALT/SHIFT 在前，其余在后
        modifiers = [n for n in names if n in {"CTRL", "ALT", "SHIFT", "WIN"}]
        others = [n for n in names if n not in {"CTRL", "ALT", "SHIFT", "WIN"}]

        # 利用 dict.fromkeys 去重并保持首次出现顺序
        ordered = list(dict.fromkeys(modifiers + others))
        return "+".join(ordered)

    def capture_region(self):
        # 1. 严格清理旧的 overlay 实例
        if hasattr(self, "overlay") and self.overlay is not None:
            try:
                self.overlay.close()
                self.overlay.deleteLater()
            except Exception as e:
                print(f"Error cleaning up overlay: {e}")
            self.overlay = None

        parent = self.parent()
        if parent:
            parent.hide()
        self.hide()

        # 使用 QTimer 异步延时，不阻塞事件循环，确保窗口彻底隐藏
        # 增加到 500ms 以确保万无一失
        from PySide6.QtCore import QTimer

        QTimer.singleShot(500, self._perform_capture)

    def _perform_capture(self):
        # 截取全屏
        screen = QApplication.primaryScreen()
        bg_pixmap = None
        if screen:
            bg_pixmap = screen.grabWindow(0)
            self._temp_screenshot = bg_pixmap  # 保持引用
        else:
            self._temp_screenshot = None

        self.overlay = RegionCaptureOverlay(background_pixmap=bg_pixmap)
        self.overlay.finished.connect(self.on_region_done)
        self.overlay.cancelled.connect(self.on_region_cancelled)
        self.overlay.show()

    def on_region_cancelled(self):
        """处理取消截图的情况"""
        # 清理
        if hasattr(self, "overlay") and self.overlay is not None:
            self.overlay.close()
            self.overlay.deleteLater()
            self.overlay = None

        if hasattr(self, "_temp_screenshot"):
            del self._temp_screenshot

        parent = self.parent()
        if parent:
            parent.show()
        self.show()

    def on_region_done(self, geo: QRect):
        # 先关闭覆盖层窗口（关键修复！）
        if hasattr(self, "overlay") and self.overlay is not None:
            self.overlay.close()  # 或者 self.overlay.hide()
            self.overlay.deleteLater()  # 可选，帮助 Qt 彻底清理
            self.overlay = None  # 可选，避免野指针

        # 清理临时截图
        if hasattr(self, "_temp_screenshot"):
            del self._temp_screenshot

        parent = self.parent()
        if geo.isNull():
            print("❌ 用户未选择有效区域")
            if parent:
                parent.show()
            self.show()
            return

        pixmap = QApplication.primaryScreen().grabWindow(
            0, geo.x(), geo.y(), geo.width(), geo.height()
        )
        img_dir = os.path.join(os.getcwd(), "img")
        # img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")
        os.makedirs(img_dir, exist_ok=True)
        file_name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        file_path = os.path.join(img_dir, file_name)

        if pixmap.save(file_path, "PNG"):
            if hasattr(self, "image_path_edit") and self.image_path_edit:
                self.image_path_edit.setText(file_path)
            if hasattr(self, "drag_image_path_edit") and self.drag_image_path_edit:
                self.drag_image_path_edit.setText(file_path)
            QMessageBox.information(self, "框选截图成功", f"已保存：{file_name}")

            # 直接调用 add_step_to_table 如果父窗口是 AutomationUI
            if parent and hasattr(parent, "add_step_to_table"):
                step_data = self.get_step_data()
                parent.add_step_to_table(step_data)
                # 添加到当前任务配置
                if parent.current_task and parent.current_task in parent.tasks:
                    parent.tasks[parent.current_task]["steps"].append(step_data)
        else:
            QMessageBox.warning(self, "失败", "截图保存失败！")

        if parent:
            parent.show()
        self.show()

    def create_mouse_click_panel(self):
        panel = QWidget()
        layout = QGridLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.dianji_use_image_checkbox = QCheckBox("启用图片")
        self.dianji_use_image_checkbox.setChecked(True)  # 默认
        layout.addWidget(self.dianji_use_image_checkbox, 0, 0)
        layout.addWidget(QLabel("图片路径:"), 0, 1)
        self.image_path_edit = QLineEdit()
        layout.addWidget(self.image_path_edit, 0, 2)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_image)
        layout.addWidget(browse_btn, 0, 3)

        # >>> 新增：一键录制按钮
        record_btn = QPushButton("框选截图")
        record_btn.clicked.connect(self.capture_region)
        record_btn.setToolTip(
            "请先设置鼠标点击的其他设置\n 如偏移 识别精度 最后再进行框选截图 \n这样才会使得其他设置有效\n（ps:这是个使用bug 待修复）"
        )
        layout.addWidget(record_btn, 0, 4)
        layout.addWidget(record_btn, 0, 4)

        # 坐标输入行
        self.use_coordinate_checkbox = QCheckBox("启用坐标")
        self.use_coordinate_checkbox.setChecked(False)  # 默认

        layout.addWidget(self.use_coordinate_checkbox, 1, 0)
        layout.addWidget(QLabel("X坐标:"), 1, 1)
        self.x_coordinate_spinbox = QSpinBox()
        self.x_coordinate_spinbox.setRange(0, 100000)
        self.x_coordinate_spinbox.setValue(0)
        layout.addWidget(self.x_coordinate_spinbox, 1, 2)

        layout.addWidget(QLabel("Y坐标:"), 1, 3)
        self.y_coordinate_spinbox = QSpinBox()
        self.y_coordinate_spinbox.setRange(0, 100000)
        self.y_coordinate_spinbox.setValue(0)
        layout.addWidget(self.y_coordinate_spinbox, 1, 4)

        # 创建互斥的按钮组
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)  # 设置为互斥模式
        self.mode_group.addButton(self.dianji_use_image_checkbox)
        self.mode_group.addButton(self.use_coordinate_checkbox)
        self.mode_group.buttonToggled.connect(self.on_mode_changed)

        # 坐标拾取按钮
        self.pick_coordinate_btn = QPushButton("拾取坐标")
        self.pick_coordinate_btn.clicked.connect(self.start_coordinate_picking)
        layout.addWidget(self.pick_coordinate_btn, 1, 5)

        # 点击类型和读取方向
        layout.addWidget(QLabel("点击类型:"), 2, 0)
        self.click_type_combo = QComboBox()
        self.click_type_combo.addItems(["左键单击", "左键双击", "右键单击", "中键单击"])
        layout.addWidget(self.click_type_combo, 2, 1)

        # 图片读取方向
        layout.addWidget(QLabel("读取方向:"), 2, 2)
        self.scan_direction_combo = QComboBox()
        self.scan_direction_combo.addItems(
            ["默认", "从左到右", "从右到左", "从上到下", "从下到上"]
        )
        layout.addWidget(self.scan_direction_combo, 2, 3)

        # 偏移量
        layout.addWidget(QLabel("X偏移:"), 3, 0)
        self.offset_x_spin = QSpinBox()
        self.offset_x_spin.setRange(-1000, 1000)
        layout.addWidget(self.offset_x_spin, 3, 1)

        layout.addWidget(QLabel("Y偏移:"), 3, 2)
        self.offset_y_spin = QSpinBox()
        self.offset_y_spin.setRange(-1000, 1000)
        layout.addWidget(self.offset_y_spin, 3, 3)

        # 识别设置
        layout.addWidget(QLabel("识别精度(0-1):"), 4, 0)
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.5, 1.0)
        self.confidence_spin.setValue(0.8)
        self.confidence_spin.setSingleStep(0.05)
        layout.addWidget(self.confidence_spin, 4, 1)

        layout.addWidget(QLabel("超时时间(秒):"), 4, 2)
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.1, 60)
        self.timeout_spin.setSingleStep(0.1)
        self.timeout_spin.setValue(1.0)
        self.timeout_spin.setDecimals(1)
        layout.addWidget(self.timeout_spin, 4, 3)

        return panel

    def on_mode_changed(self, button, checked):
        """模式切换处理"""
        if checked:
            self.update_controls_state()

    def update_controls_state(self):
        """更新控件启用状态"""
        image_enabled = self.dianji_use_image_checkbox.isChecked()
        coordinate_enabled = self.use_coordinate_checkbox.isChecked()

        # 更新图片相关控件状态
        self.image_path_edit.setEnabled(image_enabled)

        # 更新坐标相关控件状态
        self.x_coordinate_spinbox.setEnabled(coordinate_enabled)
        self.y_coordinate_spinbox.setEnabled(coordinate_enabled)

    def start_coordinate_picking(self):
        """
        开始坐标拾取
        """

        self.coord_picker = CoordinatePickerOverlay(self)
        self.coord_picker.coordinate_selected.connect(self.on_coordinate_selected)
        self.coord_picker.finished.connect(self.on_coordinate_picking_finished)
        # 创建并显示坐标拾取覆盖层
        parent = self.parent()
        if parent:
            parent.showMinimized()
        self.coord_picker.show()
        self.coord_picker.raise_()
        self.coord_picker.activateWindow()

    def on_coordinate_selected(self, coordinate):
        """
        坐标选择完成的回调
        """
        x, y = coordinate
        self.x_coordinate_spinbox.setValue(x)
        self.y_coordinate_spinbox.setValue(y)

        # 如果当前是使用坐标模式，更新预览
        if not self.dianji_use_image_checkbox.isChecked():
            self.update_mouse_click_preview()
        parent = self.parent()
        if parent:
            parent.showMinimized()

    def on_coordinate_picking_finished(self):
        """
        坐标拾取完成后的处理
        """
        # 清理引用
        self.coord_picker.deleteLater()
        self.coord_picker = None

        # 显示主窗口
        parent = self.parent()
        if parent:
            parent.showNormal()
        self.raise_()
        self.activateWindow()

    def update_mouse_click_preview(self):
        """
        更新鼠标点击预览
        """
        # 这里可以添加预览逻辑，如果需要的话
        pass

    def create_ai_reply_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # AI 提供商选择
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("AI 提供商:"))
        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItems(["kimi", "doubao"])
        provider_layout.addWidget(self.ai_provider_combo)
        layout.addLayout(provider_layout)

        # 预设角色选择
        role_layout = QHBoxLayout()
        role_layout.addWidget(QLabel("预设角色:"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(
            [
                "自定义",
                "贴心朋友 ❤️",
                "幽默损友 😂",
                "专业助手 🧠",
                "温柔恋人 💕",
                "严厉老师 🎓",
            ]
        )
        role_layout.addWidget(self.role_combo)
        layout.addLayout(role_layout)

        # 系统提示词
        system_prompt_layout = QVBoxLayout()
        system_prompt_layout.addWidget(QLabel("系统提示词:"))
        self.ai_system_prompt_edit = QTextEdit()  # 改名以避免冲突
        self.ai_system_prompt_edit.setMaximumHeight(150)
        self.ai_system_prompt_edit.setPlaceholderText(
            "请输入系统提示词，例如：\n你是我的朋友，微信语音里很随和。用一句口语化的话回应我..."
        )
        system_prompt_layout.addWidget(self.ai_system_prompt_edit)
        layout.addLayout(system_prompt_layout)

        # 预设角色提示词
        self.role_prompts = {
            "自定义": "",
            "贴心朋友 ❤️": (
                "你是关系不错的朋友，语气温暖但不过度热情。先简短共情，再给一个贴心小建议或小问题，"
                "全程口语化、一句话为主，不提自己是AI，不使用列表。"
            ),
            "幽默损友 😂": (
                "你是损友风格的朋友，聊天轻松搞笑但不冒犯。用一句俏皮话回应，"
                "可以小小自嘲或反转，像真人发语音那样自然，不暴露身份。"
            ),
            "专业助手 🧠": (
                "你是一位专业的助手，回答问题时要准确、清晰、有条理。"
                "使用正式但友好的语气，提供有用的信息和建议，避免冗长。"
            ),
            "温柔恋人 💕": (
                "你是我温柔的恋人，说话充满关爱和体贴。"
                "用甜蜜温馨的话语回应，适当使用表情符号表达情感，让对话充满爱意。"
            ),
            "严厉老师 🎓": (
                "你是一位严格的老师，语气认真且专业。"
                "回答问题时要指出关键要点，适当纠正错误，给出建设性的建议和指导。"
            ),
        }

        # 连接角色选择信号
        self.role_combo.currentTextChanged.connect(self.on_ai_role_changed)

        # 初始化为贴心朋友角色
        # self.role_combo.setCurrentText("贴心朋友 ❤️")
        # self.on_ai_role_changed("贴心朋友 ❤️")

        # 历史记录选项
        history_layout = QHBoxLayout()
        self.use_history_checkbox = QCheckBox("使用对话历史")
        self.use_history_checkbox.setChecked(True)
        history_layout.addWidget(self.use_history_checkbox)
        layout.addLayout(history_layout)

        # 流式输出选项
        stream_layout = QHBoxLayout()
        self.stream_checkbox = QCheckBox("流式输出")
        self.stream_checkbox.setChecked(False)
        stream_layout.addWidget(self.stream_checkbox)
        layout.addLayout(stream_layout)

        return panel

    def on_ai_role_changed(self, role_text):
        """处理AI角色选择变化"""
        # 检查控件是否仍然存在
        if not hasattr(self, "ai_system_prompt_edit"):
            return
        try:
            if role_text in self.role_prompts:
                prompt = self.role_prompts[role_text]
                self.ai_system_prompt_edit.setPlainText(prompt)
                # 如果是自定义角色，允许用户编辑
                self.ai_system_prompt_edit.setReadOnly(role_text != "自定义")
        except RuntimeError as e:
            # 控件已被删除，忽略错误
            print(e)
            pass

    def generate_love_text(self):
        love_dt = self.love_datetime_edit.dateTime().toPython()  # 用户选的时刻
        today = date.today()
        today_1314 = datetime.combine(today, time(13, 14))  # 今天 13:14

        # 相恋时长（精确到秒）
        delta = today_1314 - love_dt
        days = delta.days
        sec = delta.seconds
        hours, rem = divmod(sec, 3600)
        minutes, secs = divmod(rem, 60)
        duration = f"{days}天{hours}时{minutes}分{secs}秒"

        # 今年第几个 13:14
        year_start_1314 = datetime(today.year, 1, 1, 13, 14)
        count = (today_1314 - year_start_1314).days + 1

        # 特殊节日
        year = today.year
        is_xmas = (love_dt.month, love_dt.day) == (12, 25)
        special = None
        if is_xmas:
            special = "我们的爱情从圣诞夜点亮，愿它像圣诞树一样永远闪耀！"
        elif today == date(year, 2, 14):
            special = "情人节快乐！"
        elif today == self.chinese_qixi(year):
            special = "七夕快乐，鹊桥相会！"
        elif today == date(year, 12, 25):
            special = "圣诞快乐，Merry Christmas！"

        today_str = f"{today.year}年{today.month}月{today.day}日"
        if is_xmas:
            text = (
                f"宝宝，今天是{today_str}第{count}个1314，"
                f"我们已相恋{duration}，"
                f"从圣诞夜一直走到今天，未来也要一起闪耀！🎄❤"
            )
        else:
            text = (
                f"宝宝，今天是{today_str}第{count}个1314，"
                f"我们已经相恋了{duration}，爱你❤ "
            )
            if special:
                text += f"\n{special}"

        self.text_edit.setPlainText(text)

    def chinese_qixi(self, year: int) -> date:
        """
        计算指定年份的七夕节（农历七月初七）的公历日期
        使用近似算法，误差在±1天内

        Args:
            year: 要计算的年份

        Returns:
            该年份七夕节的公历日期
        """
        # 扩展的年份对照表（2000-2030年）
        table = {
            2000: date(2000, 8, 6),
            2001: date(2001, 8, 25),
            2002: date(2002, 8, 15),
            2003: date(2003, 8, 4),
            2004: date(2004, 8, 22),
            2005: date(2005, 8, 11),
            2006: date(2006, 7, 31),
            2007: date(2007, 8, 19),
            2008: date(2008, 8, 7),
            2009: date(2009, 8, 26),
            2010: date(2010, 8, 16),
            2011: date(2011, 8, 6),
            2012: date(2012, 8, 23),
            2013: date(2013, 8, 13),
            2014: date(2014, 8, 2),
            2015: date(2015, 8, 20),
            2016: date(2016, 8, 9),
            2017: date(2017, 8, 28),
            2018: date(2018, 8, 17),
            2019: date(2019, 8, 7),
            2020: date(2020, 8, 25),
            2021: date(2021, 8, 14),
            2022: date(2022, 8, 4),
            2023: date(2023, 8, 22),
            2024: date(2024, 8, 10),
            2025: date(2025, 8, 1),
            2026: date(2026, 8, 19),
            2027: date(2027, 8, 8),
            2028: date(2028, 7, 28),
            2029: date(2029, 8, 16),
            2030: date(2030, 8, 5),
        }

        # 如果在已知年份范围内，直接返回表中日期
        if year in table:
            return table[year]

        # 对于表外的年份，使用近似算法计算
        # 基础年份选择2023年，七夕日期为8月22日
        base_year = 2023
        base_date = date(base_year, 8, 22)

        # 计算与基础年份的差异（考虑农历年的平均长度）
        year_diff = year - base_year
        # 农历年平均长度约为29.53天×12个月 = 354.36天
        days_diff = round(year_diff * 354.36 - year_diff * 365.25)

        # 计算预估日期
        estimated_date = base_date + timedelta(days=days_diff)

        # 调整到8月附近（七夕通常在7月底到8月底之间）
        if estimated_date.month < 7:
            estimated_date += timedelta(days=30)
        elif estimated_date.month > 9:
            estimated_date -= timedelta(days=30)

        return estimated_date

    def create_keyboard_input_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 1. 原始文本输入（多行）
        layout.addWidget(QLabel("输入文本（留空则用 Excel 或纪念日）:"))

        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText(
            "在此输入固定文本...\n留空则自动从 Excel 或纪念日生成内容"
        )
        self.text_edit.setMaximumHeight(80)
        self.text_edit.setLineWrapMode(QPlainTextEdit.WidgetWidth)

        layout.addWidget(self.text_edit)

        # -------- 新增纪念日区域 --------
        love_group = QWidget()
        h_layout = QHBoxLayout(love_group)  # 横向布局

        # 1. 启用复选框
        self.use_love_checkbox = QCheckBox("启用纪念日")
        self.use_love_checkbox.setChecked(False)  # 默认不启用
        h_layout.addWidget(self.use_love_checkbox)

        # 2. 标签
        h_layout.addWidget(QLabel("时间:"))

        # 3. 时间选择器
        self.love_datetime_edit = QDateTimeEdit()
        self.love_datetime_edit.setCalendarPopup(True)
        self.love_datetime_edit.setDisplayFormat("yyyy-MM-dd hh:mm:ss")
        self.love_datetime_edit.setDateTime(
            QDateTime(QDate(2022, 12, 25), QTime(7, 0, 0))
        )
        # 可选：默认禁用，直到 checkbox 勾选
        self.love_datetime_edit.setEnabled(False)
        self.use_love_checkbox.toggled.connect(self.love_datetime_edit.setEnabled)

        h_layout.addWidget(self.love_datetime_edit)
        # 4. 生成按钮
        gen_btn = QPushButton("生成文案")
        gen_btn.setEnabled(False)
        self.use_love_checkbox.toggled.connect(
            gen_btn.setEnabled
        )  # 勾选/取消自动启用/禁用
        gen_btn.clicked.connect(self.generate_love_text)
        h_layout.addWidget(gen_btn)

        # 可选：设置拉伸，防止挤压
        h_layout.addStretch()

        # 将 group 添加到主 layout
        layout.addWidget(love_group)

        # 3. Excel 区域
        excel_group = QWidget()
        g = QVBoxLayout(excel_group)

        # 文件选择
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Excel 文件:"))
        self.excel_path_edit = QLineEdit()
        btn = QPushButton("浏览")
        btn.clicked.connect(
            lambda: self.excel_path_edit.setText(
                QFileDialog.getOpenFileName(filter="*.xlsx")[0]
            )
        )
        h1.addWidget(self.excel_path_edit)
        h1.addWidget(btn)
        g.addLayout(h1)

        # 工作表
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("工作表(名称或序号):"))
        self.sheet_edit = QLineEdit("0")
        h2.addWidget(self.sheet_edit)
        g.addLayout(h2)

        # 列
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("列(首列=0):"))
        self.col_spin = QSpinBox()
        self.col_spin.setValue(0)
        h3.addWidget(self.col_spin)
        g.addLayout(h3)

        # 读取模式
        h4 = QHBoxLayout()
        h4.addWidget(QLabel("读取模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["顺序", "随机"])
        h4.addWidget(self.mode_combo)
        g.addLayout(h4)

        layout.addWidget(excel_group)
        return panel

    def create_wait_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("等待时间(秒):"))
        self.wait_spin = QSpinBox()
        self.wait_spin.setRange(1, 3600)
        self.wait_spin.setValue(5)
        layout.addWidget(self.wait_spin)

        return panel

    def create_screenshot_panel(self):
        panel = QWidget()
        layout = QGridLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # 保存路径
        layout.addWidget(QLabel("保存路径:"), 0, 0)
        self.screenshot_path_edit = QLineEdit()
        layout.addWidget(self.screenshot_path_edit, 0, 1)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_save_path)
        layout.addWidget(browse_btn, 0, 2)

        # 截图区域
        layout.addWidget(QLabel("截图区域(可选):"), 1, 0)

        layout.addWidget(QLabel("X:"), 2, 0)
        self.screenshot_x_spin = QSpinBox()
        self.screenshot_x_spin.setRange(0, 10000)
        layout.addWidget(self.screenshot_x_spin, 2, 1)

        layout.addWidget(QLabel("Y:"), 2, 2)
        self.screenshot_y_spin = QSpinBox()
        self.screenshot_y_spin.setRange(0, 10000)
        layout.addWidget(self.screenshot_y_spin, 2, 3)

        layout.addWidget(QLabel("宽度:"), 3, 0)
        self.screenshot_width_spin = QSpinBox()
        self.screenshot_width_spin.setRange(1, 10000)
        self.screenshot_width_spin.setValue(800)
        layout.addWidget(self.screenshot_width_spin, 3, 1)

        layout.addWidget(QLabel("高度:"), 3, 2)
        self.screenshot_height_spin = QSpinBox()
        self.screenshot_height_spin.setRange(1, 10000)
        self.screenshot_height_spin.setValue(600)
        layout.addWidget(self.screenshot_height_spin, 3, 3)

        return panel

    # 在 StepConfigDialog 类中添加新的拖拽面板
    def create_drag_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # 添加图像识别选项
        self.use_image_checkbox = QCheckBox("使用图像识别定位起始点")
        self.use_image_checkbox.setChecked(True)
        layout.addWidget(self.use_image_checkbox)

        # 图像路径设置
        image_layout = QHBoxLayout()
        image_layout.addWidget(QLabel("起始点图像:"))
        self.drag_image_path_edit = QLineEdit()
        image_browse_btn = QPushButton("浏览...")
        image_browse_btn.clicked.connect(self.browse_drag_image)

        # >>> 新增：一键录制按钮
        record_btn = QPushButton("框选截图")
        record_btn.clicked.connect(self.capture_region)

        image_layout.addWidget(self.drag_image_path_edit)
        image_layout.addWidget(image_browse_btn)
        image_layout.addWidget(record_btn)
        layout.addLayout(image_layout)

        # 偏移量设置
        offset_layout = QHBoxLayout()
        offset_layout.addWidget(QLabel("图像识别偏移:"))
        offset_layout.addWidget(QLabel("X:"))
        self.drag_offset_x_spin = QSpinBox()
        self.drag_offset_x_spin.setRange(-1000, 1000)
        offset_layout.addWidget(self.drag_offset_x_spin)

        offset_layout.addWidget(QLabel("Y:"))
        self.drag_offset_y_spin = QSpinBox()
        self.drag_offset_y_spin.setRange(-1000, 1000)
        offset_layout.addWidget(self.drag_offset_y_spin)

        offset_layout.addWidget(QLabel("读取方向:"))
        self.drag_scan_direction_combo = QComboBox()
        self.drag_scan_direction_combo.addItems(
            ["默认", "从左到右", "从右到左", "从上到下", "从下到上"]
        )
        offset_layout.addWidget(self.drag_scan_direction_combo)
        offset_layout.addStretch()
        layout.addLayout(offset_layout)

        # 拖拽距离（相对拖拽）
        distance_layout = QHBoxLayout()
        distance_layout.addWidget(QLabel("横向距离:"))
        self.drag_distance_x_spin = QSpinBox()
        self.drag_distance_x_spin.setRange(-1000, 1000)
        self.drag_distance_x_spin.setValue(0)
        distance_layout.addWidget(self.drag_distance_x_spin)

        distance_layout.addWidget(QLabel("纵向距离:"))
        self.drag_distance_y_spin = QSpinBox()
        self.drag_distance_y_spin.setRange(-1000, 1000)
        self.drag_distance_y_spin.setValue(100)  # 默认向下拖拽100像素
        distance_layout.addWidget(self.drag_distance_y_spin)

        # 添加快捷按钮
        up_btn = QPushButton("↑上拉")
        up_btn.setFixedSize(60, 25)
        up_btn.clicked.connect(lambda: self.set_drag_distance(0, -100))
        distance_layout.addWidget(up_btn)

        down_btn = QPushButton("↓下拉")
        down_btn.setFixedSize(60, 25)
        down_btn.clicked.connect(lambda: self.set_drag_distance(0, 100))
        distance_layout.addWidget(down_btn)

        left_btn = QPushButton("←左拉")
        left_btn.setFixedSize(60, 25)
        left_btn.clicked.connect(lambda: self.set_drag_distance(-100, 0))
        distance_layout.addWidget(left_btn)

        right_btn = QPushButton("→右拉")
        right_btn.setFixedSize(60, 25)
        right_btn.clicked.connect(lambda: self.set_drag_distance(100, 0))
        distance_layout.addWidget(right_btn)

        layout.addLayout(distance_layout)

        return panel

    def set_drag_distance(self, x, y):
        """设置拖拽距离"""
        self.drag_distance_x_spin.setValue(x)
        self.drag_distance_y_spin.setValue(y)

    def browse_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.bmp)"
        )
        if filename:
            self.image_path_edit.setText(filename)

    def browse_save_path(self):
        directory = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if directory:
            self.screenshot_path_edit.setText(directory)

    def browse_drag_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择起始点图片", "", "图片文件 (*.png *.jpg *.bmp)"
        )
        if filename:
            self.drag_image_path_edit.setText(filename)

    def update_params_panel(self):
        step_type = self.type_combo.currentText()
        if step_type == "鼠标点击":
            self.params_stack.layout().setCurrentWidget(self.mouse_click_panel)
        elif step_type == "文本输入":
            self.params_stack.layout().setCurrentWidget(self.keyboard_input_panel)
        elif step_type == "等待":
            self.params_stack.layout().setCurrentWidget(self.wait_panel)
        elif step_type == "截图":
            self.params_stack.layout().setCurrentWidget(self.screenshot_panel)
        elif step_type == "拖拽":
            self.params_stack.layout().setCurrentWidget(self.drag_panel)
        elif step_type == "鼠标滚轮":
            self.params_stack.layout().setCurrentWidget(self.scroll_panel)
        elif step_type == "键盘热键":
            self.params_stack.layout().setCurrentWidget(self.hot_keyboard_panel)
        elif step_type == "AI 自动回复":
            self.params_stack.layout().setCurrentWidget(self.ai_reply_panel)

    def get_step_data(self):
        step_type = self.type_combo.currentText()
        params = {}

        if step_type == "鼠标点击":
            params["use_image"] = self.dianji_use_image_checkbox.isChecked()
            params["image_path"] = self.image_path_edit.text()
            params["confidence"] = self.confidence_spin.value()
            params["click_type"] = self.click_type_combo.currentText()
            params["offset_x"] = self.offset_x_spin.value()
            params["offset_y"] = self.offset_y_spin.value()
            params["timeout"] = self.timeout_spin.value()
            params["x"] = self.x_coordinate_spinbox.value()
            params["y"] = self.y_coordinate_spinbox.value()
            params["scan_direction"] = self.scan_direction_combo.currentText()

        elif step_type == "文本输入":
            params["text"] = self.text_edit.toPlainText()
            # Excel
            params["excel_path"] = self.excel_path_edit.text()
            params["excel_sheet"] = self.sheet_edit.text()
            params["excel_col"] = self.col_spin.value()
            params["excel_mode"] = self.mode_combo.currentText()
            # 纪念日
            params["use_love"] = self.use_love_checkbox.isChecked()
            if params["use_love"]:
                params["love_date"] = self.love_datetime_edit.dateTime().toString(
                    Qt.ISODate
                )

        elif step_type == "等待":
            pass

        elif step_type == "截图":
            params["save_path"] = self.screenshot_path_edit.text()
            params["x"] = self.screenshot_x_spin.value()
            params["y"] = self.screenshot_y_spin.value()
            params["width"] = self.screenshot_width_spin.value()
            params["height"] = self.screenshot_height_spin.value()

        elif step_type == "拖拽":
            params["use_image"] = self.use_image_checkbox.isChecked()
            params["image_path"] = self.drag_image_path_edit.text()
            params["offset_x"] = self.drag_offset_x_spin.value()
            params["offset_y"] = self.drag_offset_y_spin.value()
            params["distance_x"] = self.drag_distance_x_spin.value()
            params["distance_y"] = self.drag_distance_y_spin.value()
            params["scan_direction"] = self.drag_scan_direction_combo.currentText()

        elif step_type == "鼠标滚轮":
            params["direction"] = self.scroll_direction_combo.currentText()
            params["clicks"] = self.scroll_clicks_spin.value()
        elif step_type == "键盘热键":
            # 使用隐藏属性 _hotkey_value
            params["hotkey"] = getattr(self, "_hotkey_value", "Ctrl+C")
            params["hotkey_delay"] = self.hotkey_delay_spin.value()
        elif step_type == "AI 自动回复":
            params["ai_provider"] = self.ai_provider_combo.currentText()
            # 保存角色、Prompt、历史、流式
            params["ai_role"] = self.role_combo.currentText()
            params["ai_system_prompt"] = self.ai_system_prompt_edit.toPlainText()
            params["use_history"] = self.use_history_checkbox.isChecked()
            params["stream"] = self.stream_checkbox.isChecked()

        return {"type": step_type, "params": params, "delay": self.delay_spin.value()}

    def load_step_data(self, step_data):
        self.type_combo.setCurrentText(step_data["type"])
        self.delay_spin.setValue(step_data.get("delay", 0))
        params = step_data.get("params", {})

        if step_data["type"] == "鼠标点击":
            self.dianji_use_image_checkbox.setChecked(params.get("use_image", True))
            self.use_coordinate_checkbox.setChecked(not params.get("use_image", True))
            self.image_path_edit.setText(params.get("image_path", ""))
            self.confidence_spin.setValue(params.get("confidence", 0.9))
            self.click_type_combo.setCurrentText(params.get("click_type", "左键单击"))
            self.offset_x_spin.setValue(params.get("offset_x", 0))
            self.offset_y_spin.setValue(params.get("offset_y", 0))
            self.scan_direction_combo.setCurrentText(
                params.get("scan_direction", "默认")
            )
            self.timeout_spin.setValue(params.get("timeout", 10.0))
            self.x_coordinate_spinbox.setValue(params.get("x", 0))
            self.y_coordinate_spinbox.setValue(params.get("y", 0))
            self.update_controls_state()

        elif step_data["type"] == "文本输入":
            self.text_edit.setPlainText(params.get("text", ""))
            self.excel_path_edit.setText(params.get("excel_path", ""))
            self.sheet_edit.setText(params.get("excel_sheet", "0"))
            self.col_spin.setValue(params.get("excel_col", 0))
            self.mode_combo.setCurrentText(params.get("excel_mode", "顺序"))
            self.use_love_checkbox.setChecked(params.get("use_love", False))
            if params.get("love_date"):
                self.love_datetime_edit.setDateTime(
                    QDateTime.fromString(params.get("love_date"), Qt.ISODate)
                )

        elif step_data["type"] == "等待":
            self.wait_spin.setValue(params.get("seconds", 1))

        elif step_data["type"] == "截图":
            self.screenshot_path_edit.setText(params.get("save_path", ""))
            self.screenshot_x_spin.setValue(params.get("x", 0))
            self.screenshot_y_spin.setValue(params.get("y", 0))
            self.screenshot_width_spin.setValue(params.get("width", 0))
            self.screenshot_height_spin.setValue(params.get("height", 0))

        elif step_data["type"] == "拖拽":
            self.use_image_checkbox.setChecked(params.get("use_image", True))
            self.drag_image_path_edit.setText(params.get("image_path", ""))
            self.drag_offset_x_spin.setValue(params.get("offset_x", 0))
            self.drag_offset_y_spin.setValue(params.get("offset_y", 0))
            self.drag_distance_x_spin.setValue(params.get("distance_x", 0))
            self.drag_distance_y_spin.setValue(params.get("distance_y", 0))
            self.drag_scan_direction_combo.setCurrentText(
                params.get("scan_direction", "默认")
            )

        elif step_data["type"] == "鼠标滚轮":
            self.scroll_direction_combo.setCurrentText(
                params.get("direction", "向下滚动")
            )
            self.scroll_clicks_spin.setValue(params.get("clicks", 3))

        elif step_data["type"] == "键盘热键":
            # 还原热键
            hotkey = params.get("hotkey", "Ctrl+C")
            self._hotkey_value = hotkey
            self.hotkey_input.setText(hotkey)
            self.hotkey_delay_spin.setValue(params.get("hotkey_delay", 100))

        elif step_data["type"] == "AI 自动回复":
            self.ai_provider_combo.setCurrentText(params.get("ai_provider", "kimi"))
            self.role_combo.setCurrentText(params.get("ai_role", "自定义"))
            self.ai_system_prompt_edit.setPlainText(params.get("ai_system_prompt", ""))
            self.use_history_checkbox.setChecked(params.get("use_history", True))
            self.stream_checkbox.setChecked(params.get("stream", False))
