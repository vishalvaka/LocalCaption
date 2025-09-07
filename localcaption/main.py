import sys
from PyQt5 import QtWidgets

from .ui.main_window import MainWindow


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("LocalCaption")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
