import sys # For sys.argv (Command Line args)
import time # For sleep() function
from PyQt4.QtCore import *
from PyQt4.QtGui import *

app = QApplication(sys.argv)
# Every PyQt app must have a QApplication object
#   -provides access to global-like info (app directory, screen size, etc.)
#   -provides event loop
# Pass it command line args because PyQt recognizes some args
#   -Ex: -geometry, -style
#   -acts on any arguments it recognizes and removes them from sys.argv

try:
    due = QTime.currentTime()
    message = "Alert!"
    if len(sys.argv) < 2:
        raise ValueError
    hours, mins = sys.argv[1].split(":")
    due = QTime(int(hours), int(mins))
    if not due.isValid():
        raise ValueError
    if len(sys.argv) > 2:
        message = " ".join(sys.argv[2:])
except ValueError:
    message = "Usage: alert.pyw HH:MM [optional message]"

while QTime.currentTime() < due:
    time.sleep(20) # wait for 20 seconds before checking time again

label = QLabel("<font color=red size=72><b>" + message + "</b></font>")
# QLabel is a widget that can take HTML text

label.setWindowFlags(Qt.SplashScreen)
# Splash screens have no title bar

label.show()
# Adds a paint event to app's event queue

QTimer.singleShot(60000, app.quit)
# Shows message for 60000 milliseconds, then terminates the app

app.exec_()
# Begins app's event queue