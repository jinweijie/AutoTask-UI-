import sys

from PySide6.QtWidgets import QApplication

from app.ui.components.at_icon import ATIcon
from app.ui.main_window import AutomationUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutomationUI()
    window.setWindowIcon(ATIcon.icon())
    window.show()
    sys.exit(app.exec())
