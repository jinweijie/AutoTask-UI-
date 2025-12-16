from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.config_manager import ConfigManager
from app.services.chatbot import ChatBot


class AITestDialog(QDialog):
    """AI 测试对话框，支持 Kimi 和豆包"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🤖 AI 测试")
        self.setModal(True)
        self.resize(650, 550)

        # 初始化配置管理器
        self.config_manager = ConfigManager()

        # 初始化 ChatBot
        self.chat_bot = None
        self.current_provider = "kimi"
        self.init_chat_bot()

        self.setup_ui()

    def init_chat_bot(self):
        """初始化 ChatBot，尝试自动读取配置"""
        try:
            # 读取配置
            config = self.config_manager.load()
            kimi_key = config.get("moonshot_api_key")
            doubao_ak = config.get("volcano_access_key")
            doubao_sk = config.get("volcano_secret_key")
            doubao_endpoint = config.get("ark_endpoint_id")

            # 优先使用 Kimi（如果配置了的话）
            if kimi_key:
                self.chat_bot = ChatBot(
                    provider="kimi", token_json_path="./config/token.json"
                )
                self.current_provider = "kimi"
            # 否则使用豆包（如果配置了的话）
            elif all([doubao_ak, doubao_sk, doubao_endpoint]):
                self.chat_bot = ChatBot(
                    provider="doubao", token_json_path="./config/token.json"
                )
                self.current_provider = "doubao"
            else:
                # 如果都没有配置，尝试使用默认的 Kimi
                self.chat_bot = ChatBot(
                    provider="kimi", token_json_path="./config/token.json"
                )
                self.current_provider = "kimi"
        except Exception as e:
            QMessageBox.warning(self, "初始化失败", f"ChatBot 初始化失败: {str(e)}")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 说明文本
        intro_label = QLabel("AI 测试对话")
        intro_label.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            color: #2c3e50;
            padding: 5px 0;
            border-bottom: 2px solid #3498db;
            margin-bottom: 2px;
        """)
        layout.addWidget(intro_label)

        # AI 提供商选择
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("AI 提供商:"))

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Kimi", "豆包"])
        self.provider_combo.setCurrentText(
            "Kimi" if self.current_provider == "kimi" else "豆包"
        )
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        provider_layout.addStretch()

        layout.addLayout(provider_layout)

        # 对话历史区域
        history_group = QGroupBox("对话历史")
        history_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #000000;
                border-radius: 10px;
                margin-top: 1ex;
                padding-top: 2px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subline-position: top center;
                padding: 0 2px;
                background-color: #000000;
                color: white;
                border-radius: 5px;
            }
        """)
        history_layout = QVBoxLayout(history_group)
        history_layout.setContentsMargins(15, 25, 15, 15)

        self.history_display = QPlainTextEdit()
        self.history_display.setReadOnly(True)
        self.history_display.setPlaceholderText("对话历史将显示在这里...")
        self.history_display.setStyleSheet("""
            QPlainTextEdit {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                padding: 2px;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
        """)
        # 使用策略扩展，让它占据更多空间
        self.history_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 创建一个容器来更好地控制历史显示区域
        history_container = QWidget()
        history_container_layout = QVBoxLayout(history_container)
        history_container_layout.setContentsMargins(0, 0, 0, 0)
        history_container_layout.addWidget(self.history_display)

        history_layout.addWidget(history_container)
        layout.addWidget(history_group)

        # 用户输入区域
        input_group = QGroupBox("用户输入")
        input_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #000000;
                border-radius: 10px;
                margin-top: 1ex;
                padding-top: 2px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subline-position: top center;
                padding: 0 2px;
                background-color: #000000;
                color: white;
                border-radius: 5px;
            }
        """)
        input_layout = QVBoxLayout(input_group)
        input_layout.setContentsMargins(15, 25, 15, 15)

        self.user_input_edit = QTextEdit()
        self.user_input_edit.setMaximumHeight(180)
        self.user_input_edit.setPlaceholderText("请输入要发送给 AI 的消息...")
        self.user_input_edit.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                padding: 10px;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
        """)
        input_layout.addWidget(self.user_input_edit)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.setContentsMargins(0, 10, 0, 0)

        self.clear_history_btn = QPushButton("🗑️ 清空历史")
        self.clear_history_btn.clicked.connect(self.clear_history)
        self.clear_history_btn.setMinimumWidth(120)
        self.clear_history_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
            QPushButton:pressed {
                background-color: #6c7a7b;
            }
        """)
        button_layout.addWidget(self.clear_history_btn)

        button_layout.addStretch()

        self.send_btn = QPushButton("🚀 发送消息")
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setDefault(True)
        self.send_btn.setMinimumWidth(120)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        button_layout.addWidget(self.send_btn)

        input_layout.addLayout(button_layout)
        layout.addWidget(input_group)

        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("""
            color: #7f8c8d; 
            font-size: 12px;
            padding: 8px 0;
            border-top: 1px solid #ecf0f1;
            font-weight: bold;
        """)
        layout.addWidget(self.status_label)

    def on_provider_changed(self, text):
        """处理 AI 提供商更改"""
        provider = "kimi" if text == "Kimi" else "doubao"
        if provider != self.current_provider:
            self.current_provider = provider
            try:
                self.chat_bot = ChatBot(
                    provider=provider, token_json_path="./config/token.json"
                )
                self.status_label.setText(f"已切换到 {text} 提供商")
                self.clear_history()
            except Exception as e:
                QMessageBox.warning(self, "切换失败", f"切换 AI 提供商失败: {str(e)}")
                # 恢复到之前的提供商
                self.provider_combo.setCurrentText(
                    "Kimi" if self.current_provider == "kimi" else "豆包"
                )

    def send_message(self):
        """发送消息到 AI"""
        if not self.chat_bot:
            QMessageBox.warning(self, "错误", "ChatBot 未初始化")
            return

        user_message = self.user_input_edit.toPlainText().strip()
        if not user_message:
            QMessageBox.warning(self, "警告", "请输入消息内容")
            return

        system_prompt = "你是我的朋友，微信语音里很随和。用一句口语化的话回应我"

        # 更新状态
        self.status_label.setText("正在获取 AI 回复...")
        self.send_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            # 发送消息并获取回复
            reply = self.chat_bot.reply(
                message=user_message,
                system=system_prompt if system_prompt else None,
                use_history=True,
                stream=False,
            )

            # 更新对话历史
            self.update_history(f"👤 用户: {user_message}")
            self.update_history(f"🤖 AI: {reply}")

            # 清空输入框
            self.user_input_edit.clear()

            self.status_label.setText("回复成功")
        except Exception as e:
            error_msg = f"❌ 错误: {str(e)}"
            self.update_history(error_msg)
            self.status_label.setText("发送失败")
            QMessageBox.critical(self, "发送失败", f"发送消息时出错: {str(e)}")
        finally:
            self.send_btn.setEnabled(True)

    def update_history(self, message):
        """更新对话历史显示"""
        current_text = self.history_display.toPlainText()
        if current_text:
            current_text += "\n" + message
        else:
            current_text = message

        self.history_display.setPlainText(current_text)
        # 滚动到底部
        self.history_display.verticalScrollBar().setValue(
            self.history_display.verticalScrollBar().maximum()
        )

    def clear_history(self):
        """清空对话历史"""
        self.history_display.clear()
        if self.chat_bot:
            self.chat_bot.clear_history()
        self.status_label.setText("历史已清空")
