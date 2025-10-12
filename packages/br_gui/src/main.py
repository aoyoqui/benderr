import sys

from br_sdk.br_logging import setup_logger
from br_sdk.config import AppConfig
from PySide6.QtWidgets import QApplication
from views.main_window import MainWindow


def main(): 
    AppConfig.load(profile="gui", config_dirs=["./config"])
    setup_logger()
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.showMaximized()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
