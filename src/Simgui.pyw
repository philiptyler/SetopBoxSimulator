# Import Python Standard Modules
import os
import platform
import sys

# Import third-party modules
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from SimPy.Simulation import *

# Import local modules
from Simulation import Sim

class MainWindow(QMainWindow, Process):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        Process.__init__(self, name="Main Window")
        self.simDataMenuActs = []
        self.simData = Sim()

        # Initialize Simulation
        self.createMainDialog()
        self.simData.paramDialog = ParamDialog(self.simData, self)
        self.connect(self.simData.paramDialog, SIGNAL('accepted()'), self.createMainDialog)

        logDockWidget = QDockWidget("Log", self)
        logDockWidget.setObjectName("LogDockWidget")
        logDockWidget.setAllowedAreas(Qt.LeftDockWidgetArea|
                                      Qt.RightDockWidgetArea)
        
        self.textBrowser = QTextBrowser()
        logDockWidget.setWidget(self.textBrowser)
        self.addDockWidget(Qt.RightDockWidgetArea, logDockWidget)

        self.simDataMenu = self.menuBar().addMenu("&Simulation")
        simAct = self.createAction("Simulate...", self.simulate,
                    tip="Perform IO Simulation with given parameters")
        self.simDataMenu.addAction(simAct)
        simAct = self.createAction("Reset Sim", self.createMainDialog,
                    tip="Reset all Simulation modules")
        self.simDataMenu.addAction(simAct)
        simAct = self.createAction("Stop Sim", self.simData.stop,
                    tip="Cancel Current Simulation")
        self.simDataMenu.addAction(simAct)
        
        self.simDataMenu = self.menuBar().addMenu("&Parameters")
        simAct = self.createAction("Edit...", self.simData.paramDialog.show,
                    tip="Edit internal simulation parameters")
        self.simDataMenu.addAction(simAct)

        self.setWindowTitle("TiVo IO Simulator")
    
    def createMainDialog(self):
        self.simData.prepare()
        initialize()
        self.simData.dialog = SimDialog(self.simData.vars, self)
        self.setCentralWidget(self.simData.dialog)
        self.simData.statusBar = SimStatusBar(self.simData, self)
        self.setStatusBar(self.simData.statusBar)

    def createAction(self, text, slot=None, shortcut=None, icon=None,
                     tip=None, checkable=False, signal="triggered()"):
        act = QAction(text,self)
        if icon is not None:
            act.setIcon(QIcon("/%s.png"%icon))
        if shortcut is not None:
            act.setShortcut(shortcut)
        if tip is not None:
            act.setToolTip(tip)
            act.setStatusTip(tip)
        if slot is not None:
            self.connect(act,SIGNAL(signal),slot)
        if checkable:
            act.setCheckable(True)
        return act

    def postErrors(self):
        while True:
            while len(self.simData.errors):
                self.textBrowser.append(self.simData.errors.pop(0))
            self.repaint()
            yield hold, self, 100

    def simulate(self):
        self.createMainDialog()
        self.textBrowser.append("<b>Beginning Simulation...</b>")
        self.simData.activate()
        activate(self.simData.dialog, self.simData.dialog.updateLabels(), at=10)
        activate(self.simData.statusBar, self.simData.statusBar.updateStatusBar(), at=10)
        activate(self, self.postErrors())
        self.simData.simulate()
        self.simData.statusBar.progressBar.setValue(self.simData.params.maxSimTime)
        self.textBrowser.append("Done!")
        self.statusBar().statusLabel.setText("Finished Simulation")

class SimDialog(QLabel, Process):
    def __init__(self, vars, parent=None):
        QLabel.__init__(self, parent)
        Process.__init__(self, name="Monitoring Dialog Box")
        self.setMinimumSize(300,300)
        self.vars = vars
        self.labels = []
        self.numVars = len(vars.vals)
        self.grid = QGridLayout()

        self.createLabels()
        self.setLayout(self.grid)
        self.repaint()

    def createLabels(self):
        for i in xrange(self.numVars):
            self.grid.addWidget(QLabel("<b>%s<b> [%s]: "%(self.vars.names[i], self.vars.units[i])), i, 0)
            if self.vars.maxVals[i] is not None:
                varBar = QProgressBar(self)
                varBar.setMaximum(self.vars.maxVals[i])
                varBar.setValue(self.vars.vals[i])
            else:
                varBar = QLabel(str(self.vars.vals[i]))
            self.labels.append(varBar)
            self.grid.addWidget(varBar, i, 1)
            
    def resetLabels(self):
        for i in xrange(self.numVars):
            self.labels[i].setValue(0)

    def updateLabels(self):
        while True:
            self.vars.updateVals()
            for i in xrange(self.numVars):
                if self.vars.maxVals[i] is not None:
                    self.labels[i].setValue(self.vars.vals[i])
                else:
                    self.labels[i].setText(str(self.vars.vals[i]))
            app.processEvents()
            yield hold, self, 100

class SimStatusBar(QStatusBar, Process):
    def __init__(self, sim, parent=None):
        QStatusBar.__init__(self, parent)
        Process.__init__(self, name="Simulation Status Bar")
        self.simData = sim

    def updateStatusBar(self):
        print "hello"
        self.progressBar = QProgressBar(self)
        self.progressBar.setMaximum(self.simData.params.maxSimTime)
        self.addWidget(self.progressBar)
        self.statusLabel = QLabel("Simulating...")
        self.addPermanentWidget(self.statusLabel)
        self.repaint()
        while True:
            self.progressBar.setValue(self.simData.currTime())
            yield hold, self, 100

class ParamDialog(QDialog):
    def __init__(self, sim, parent=None):
        QDialog.__init__(self, parent)
        self.simData = sim
        self.numParams = 0
        self.boxes = []
        self.grid = QGridLayout()
        self.fillDialog()
        self.addButtons()
        self.setLayout(self.grid)
        self.repaint()

    def fillDialog(self):
        self.addParam("Max Simulation Time", "Number of ms the program will simulate",
            self.simData.params.maxSimTime, 1000, 1000000000, " ms")
        self.addParam("HDD: Cache Size", "Number of KBs in HDD Cache",
            self.simData.params.hddCacheSize, 100, 128000, " kBs")
        self.addParam("HDD: One Track Move", "Time for head to move one track on platter",
            self.simData.params.hddTrackMove, .1, 5, " ms")
        self.addParam("HDD: Full Platter Rotation", "Time for platter to spin 360 degrees",
            self.simData.params.hddMaxTurn, 1, 20, " ms")
        self.addParam("HDD: Write Speed", "Write/Read Transfer rate from cache to platter",
            self.simData.params.hddRWkBpms, 10, 1000, " kB/ms")
        self.addParam("HDD: Full Stroke", "Time to move head across all tracks, reset head",
            self.simData.params.hddFullStroke, 10, 100, " ms")
        self.addParam("HDD: ATR Chance", "Percent chance ATR will occur on HDD in Simulation",
            self.simData.params.baseChanceATR, 0, 100, " %")
        self.addParam("Input Buffer Size", "Total Size, in KB, of input buffers",
            self.simData.params.iBSize, 1000, 32000, " KB")
        self.addParam("Output Buffer Size", "Total Size, in KB, of output buffers",
            self.simData.params.oBSize, 1000, 32000, " KB")
        self.addParam("Number of Tuners", "Total number of tuners used in system simulation",
            self.simData.params.numTuners, 1, 16, " ")
        self.addParam("Number of Outputs", "Total number of outputs used in system simulation",
            self.simData.params.numOutputs, 1, 16, " ")
        self.addParam("Input Data Bitrate", "Average bitrate input buffers will fill with data",
            self.simData.params.tunerBitrate, 1, 40, " Mb/s")
        self.addParam("Output Data Bitrate", "Average bitrate output buffers will remove data",
            self.simData.params.outputBitrate, 1, 40, " Mb/s")
        self.addParam("Input Buffer Interval", "Time between checking the tuner's data for HDD request",
            self.simData.params.iInterval, 50, 1000, " ms")
        self.addParam("Output Buffer Interval", "Time between checking the output's data for HDD request",
            self.simData.params.oInterval, 50, 1000, " ms")
        self.addParam("Tuner Data Threshhold", "Minimum amount of tuner data to make HDD request",
            self.simData.params.iThreshhold, 128, 4096, " kBs")
        self.addParam("Output Data Threshhold", "Minimum amount of output data to NOT make HDD request",
            self.simData.params.oThreshhold, 128, 4096, " kBs")
        self.addParam("Scheduler Interval", "Time between schedular process running",
            self.simData.params.waitInterval, 50, 1000, " ms")
        self.addParam("Input Data Deadline", "Time between HDD write request creation and expiration",
            self.simData.params.iReqTimeOut, 200, 3000, " ms")
        self.addParam("Output Data Deadline", "Time between HDD read request creation and expiration",
            self.simData.params.oReqTimeOut, 200, 3000, " ms")
        self.addParam("Max Write Size", "Max amount of data to write in one HDD request",
            self.simData.params.wMaxSize, 128, 4096, " kBs")
        self.addParam("Max Read Size", "Max amount of data to read in one HDD request",
            self.simData.params.rMaxSize, 128, 4096, " kBs")
        self.addParam("CPU Delay Multiplier", "Time cost of one CPU operation",
            self.simData.params.CPUnumMsPerOp, 0.0001, 1, " ms")
        self.addParam("RAM Transport Speed", "Transfer bitrate of system's RAM",
            self.simData.params.RAMtranSpeed, 0.00001, 0.01, " ms/kB")
        self.addParam("RAM Time Overhead", "Amount of delay time before every RAM Transfer delay",
            self.simData.params.RAMoverhead, 0.00001, 0.0001, " ms")

    def addParam(self, labelText, toolTip, val, minVal, maxVal, units=""):
        label = QLabel(labelText)
        label.setToolTip(toolTip)
        spinBox = QDoubleSpinBox()
        spinBox.setRange(minVal, maxVal)
        spinBox.setSuffix(units)
        spinBox.setValue(val)
        self.boxes.append(spinBox)
        if (self.numParams % 2):
            self.grid.addWidget(label, self.numParams/2, 0)
            self.grid.addWidget(spinBox, self.numParams/2, 1)
        else:
            self.grid.addWidget(label, self.numParams/2, 2)
            self.grid.addWidget(spinBox, self.numParams/2, 3)
        self.numParams += 1
        
    def addButtons(self):
        self.cancelButton = QPushButton("Cancel")
        self.connect(self.cancelButton, SIGNAL('clicked()'), self.close)
        self.acceptButton = QPushButton("Apply")
        self.connect(self.acceptButton, SIGNAL('clicked()'), self.updateParams)
        self.grid.addWidget(self.acceptButton, self.numParams/2, 2)
        self.grid.addWidget(self.cancelButton, self.numParams/2, 3)

    def updateParams(self):
        self.simData.params.maxSimTime=self.boxes[0].value()
        self.simData.params.hddCacheSize=self.boxes[1].value()
        self.simData.params.hddTrackMove=self.boxes[2].value()
        self.simData.params.hddMaxTurn=self.boxes[3].value()
        self.simData.params.hddRWkBpms=self.boxes[4].value()
        self.simData.params.hddFullStroke=self.boxes[5].value()
        self.simData.params.baseChanceATR=self.boxes[6].value()
        self.simData.params.iBSize=self.boxes[7].value()
        self.simData.params.oBSize=self.boxes[8].value()
        self.simData.params.numTuners=int(self.boxes[9].value())
        self.simData.params.numOutputs=int(self.boxes[10].value())
        self.simData.params.tunerBitrate =self.boxes[11].value()
        self.simData.params.outputBitrate =self.boxes[12].value()
        self.simData.params.iInterval=self.boxes[13].value()
        self.simData.params.oInterval=self.boxes[14].value()
        self.simData.params.iThreshhold=self.boxes[15].value()
        self.simData.params.oThreshhold=self.boxes[16].value()
        self.simData.params.waitInterval=self.boxes[17].value()
        self.simData.params.iReqTimeOut=self.boxes[18].value()
        self.simData.params.oReqTimeOut=self.boxes[19].value()
        self.simData.params.wMaxSize=self.boxes[20].value()
        self.simData.params.rMaxSize=self.boxes[21].value()
        self.simData.params.CPUnumMsPerOp=self.boxes[22].value()
        self.simData.params.RAMtranSpeed=self.boxes[23].value()
        self.simData.params.RAMoverhead=self.boxes[24].value()
        self.accept()
        self.close()

app = QApplication(sys.argv)
simu = MainWindow()
simu.show()
app.exec_()