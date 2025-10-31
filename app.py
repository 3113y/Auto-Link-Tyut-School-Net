import os
os.environ['APP_DIR'] = os.path.abspath(os.path.dirname(__file__))
import sys
from autolink_modules.main_window import AutoLoginWindow
from PyQt5.QtWidgets import QApplication
if __name__ == "__main__":
    # Disable SSL key logging by setting the environment variable to a null device
    # This prevents the "Failed opening SSL key log file" error.
    app = QApplication(sys.argv)
    win = AutoLoginWindow()
    win.show()
    sys.exit(app.exec_())
