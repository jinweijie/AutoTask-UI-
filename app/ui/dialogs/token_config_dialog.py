from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.core.config_manager import ConfigManager


class AITokenConfigDialog(QDialog):
    """AI Token 配置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Token 配置")
        self.setModal(True)
        self.resize(500, 400)

        # 初始化配置管理器
        self.config_manager = ConfigManager()

        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 说明文本 - 改为可点击链接
        intro_text = QLabel("""
            <p>配置AI服务所需的访问密钥：</p>
            <ul>
                <li><b>Kimi API Key</b>: 用于访问月之暗面的Kimi AI服务 (<a href="https://platform.moonshot.cn/console/api-keys">获取API Key</a>)</li>
                <li><b>豆包 AccessKey/SecretKey</b>: 用于访问字节跳动的豆包AI服务 (<a href="https://www.volcengine.com/product/ark">获取豆包API</a>)</li>
                <li><b>豆包 Endpoint ID</b>: 豆包模型的端点标识</li>
            </ul>
            <p>配置将保存在 <code>./config/token.json</code> 文件中</p>
        """)
        intro_text.setMaximumHeight(120)
        intro_text.setStyleSheet("""
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 10px;
            font-size: 11px;
        """)
        intro_text.setOpenExternalLinks(True)  # 允许打开外部链接
        intro_text.setTextFormat(Qt.RichText)  # 设置为富文本格式
        intro_text.setTextInteractionFlags(Qt.TextBrowserInteraction)  # 允许文本交互
        layout.addWidget(intro_text)

        # Kimi 配置组
        kimi_group = QGroupBox("Kimi 配置")
        kimi_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dcdcdc;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
            }
            QGroupBox::title {
                subline-position: top center;
                padding: 0 10px;
            }
        """)
        kimi_layout = QFormLayout(kimi_group)
        kimi_layout.setLabelAlignment(Qt.AlignRight)
        kimi_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        kimi_layout.setHorizontalSpacing(20)
        kimi_layout.setVerticalSpacing(10)

        self.kimi_api_key_edit = QLineEdit()
        self.kimi_api_key_edit.setEchoMode(QLineEdit.Password)
        self.kimi_api_key_edit.setPlaceholderText("请输入 Kimi API Key")
        self.kimi_api_key_edit.setMinimumWidth(200)
        kimi_layout.addRow("API Key:", self.kimi_api_key_edit)

        layout.addWidget(kimi_group)

        # 豆包配置组
        doubao_group = QGroupBox("豆包配置")
        doubao_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dcdcdc;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
            }
            QGroupBox::title {
                subline-position: top center;
                padding: 0 10px;
            }
        """)
        doubao_layout = QFormLayout(doubao_group)
        doubao_layout.setLabelAlignment(Qt.AlignRight)
        doubao_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        doubao_layout.setHorizontalSpacing(20)
        doubao_layout.setVerticalSpacing(10)

        self.doubao_ak_edit = QLineEdit()
        self.doubao_ak_edit.setEchoMode(QLineEdit.Password)
        self.doubao_ak_edit.setPlaceholderText("请输入豆包 Access Key")
        self.doubao_ak_edit.setMinimumWidth(200)
        doubao_layout.addRow("Access Key:", self.doubao_ak_edit)

        self.doubao_sk_edit = QLineEdit()
        self.doubao_sk_edit.setEchoMode(QLineEdit.Password)
        self.doubao_sk_edit.setPlaceholderText("请输入豆包 Secret Key")
        self.doubao_sk_edit.setMinimumWidth(200)
        doubao_layout.addRow("Secret Key:", self.doubao_sk_edit)

        self.doubao_endpoint_edit = QLineEdit()
        self.doubao_endpoint_edit.setPlaceholderText("请输入豆包 Endpoint ID")
        self.doubao_endpoint_edit.setMinimumWidth(200)
        doubao_layout.addRow("Endpoint ID:", self.doubao_endpoint_edit)

        layout.addWidget(doubao_group)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(0, 10, 0, 0)

        self.load_btn = QPushButton("🔄 重新加载")
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        self.load_btn.clicked.connect(self.load_config)
        button_layout.addWidget(self.load_btn)

        button_layout.addStretch()

        self.save_btn = QPushButton("💾 保存配置")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_btn)

        self.close_btn = QPushButton("❌ 关闭")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def load_config(self):
        """从配置文件加载配置"""
        try:
            # 加载现有配置
            config = self.config_manager.load()

            # 填充到界面
            self.kimi_api_key_edit.setText(config.get("moonshot_api_key", ""))
            self.doubao_ak_edit.setText(config.get("volcano_access_key", ""))
            self.doubao_sk_edit.setText(config.get("volcano_secret_key", ""))
            self.doubao_endpoint_edit.setText(config.get("ark_endpoint_id", ""))

        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"加载配置时出错: {str(e)}")

    def save_config(self):
        """保存配置到文件"""
        try:
            # 获取界面中的值
            kimi_key = self.kimi_api_key_edit.text().strip()
            doubao_ak = self.doubao_ak_edit.text().strip()
            doubao_sk = self.doubao_sk_edit.text().strip()
            doubao_endpoint = self.doubao_endpoint_edit.text().strip()

            # 检查是否有任何值需要保存
            if not any([kimi_key, doubao_ak, doubao_sk, doubao_endpoint]):
                QMessageBox.information(self, "提示", "没有配置需要保存")
                return

            # 保存配置
            self.config_manager.save(
                moonshot_api_key=kimi_key if kimi_key else None,
                volcano_access_key=doubao_ak if doubao_ak else None,
                volcano_secret_key=doubao_sk if doubao_sk else None,
                ark_endpoint_id=doubao_endpoint if doubao_endpoint else None,
            )

            QMessageBox.information(self, "成功", "配置已保存")

        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存配置时出错: {str(e)}")
