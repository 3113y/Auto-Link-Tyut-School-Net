import os
import sys
from web_auto_login import AutoLoginWindow
from PyQt5.QtWidgets import QApplication

if __name__ == "__main__":
    # Disable SSL key logging by setting the environment variable to a null device
    # This prevents the "Failed opening SSL key log file" error.
    if sys.platform == "win32":
        os.environ["SSLKEYLOGFILE"] = "NUL"
    else:
        os.environ["SSLKEYLOGFILE"] = "/dev/null"
        
    app = QApplication(sys.argv)
    win = AutoLoginWindow()
    win.show()
    sys.exit(app.exec_())
