import threading

from pynput import keyboard
from PySide6.QtCore import QThread, Signal


class HotkeyListener(QThread):
    # 自定义信号：当按下 Esc 时触发
    hotkey_activated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.listener = None

    def run(self):
        """QThread 的主执行函数"""

        def on_press(key):
            try:
                if key == keyboard.Key.esc:
                    self.hotkey_activated.emit()  # 安全发射信号到主线程
            except Exception as e:
                print(f"热键监听错误: {e}")

        # 启动 pynput 键盘监听（阻塞）
        with keyboard.Listener(on_press=on_press) as self.listener:
            self.listener.join()

    def stop(self):
        """安全停止监听线程"""
        if self.listener:
            self.listener.stop()
        self.quit()  # 请求线程退出
        self.wait()  # 等待线程结束
