# Header-------------------
__author__ = "Philip Tyler"
__copyright__ = "Copyright 2011, TiVo Corp."
__credits__ = ["Philip Tyler", "David Platt", "Mukesh Patel"]
__license__ = "TiVo Confidential"
__version__ = "1.08-11"
__maintainer__ = "Philip Tyler"
__email__ = "ptyler@calpoly.edu"
__status__ = "Developement"

# Imports------------------
from SimPy.Simulation import *
from Schedule import Scheduler, DLScheduler
from HDD import HDD
from Stream import *
from System import *

class Parameters():
    def __init__(self):
        self.maxSimTime=500000 # ms
        self.hddCacheSize=16000 # kBs
        self.hddTrackMove=1.63 # ms
        self.hddMaxTurn=10 # ms
        self.hddRWkBpms=110 # kBs per ms
        self.hddFullStroke=28.55 # ms
        self.baseChanceATR=0 # Percent
        self.iBSize=8000  # kBs
        self.oBSize=8000 # kBs
        self.numTuners=10 # mb per s
        self.numOutputs=2 # mb per s
        self.tunerBitrate = 20 # mb per s
        self.outputBitrate = 20 # mb per s
        self.iInterval=100 # ms
        self.oInterval=100 # ms
        self.iThreshhold=2048 # kBs
        self.oThreshhold=6144 # kBs
        self.waitInterval=100 # ms
        self.iReqTimeOut=1000 # ms
        self.oReqTimeOut=1000 # ms
        self.wMaxSize=2048 # kBs
        self.rMaxSize=2048 # kBs
        self.CPUnumMsPerOp = 0.01 # ms
        self.RAMtranSpeed = 0.00026 # ms per kB
        self.RAMoverhead = .00007 # ms

class Variables():
    def __init__(self, sim):
        self.sim = sim

    def initVarData(self):
        self.vals = []
        self.names = []
        self.units = []
        self.maxVals = []
        for stream in self.sim.streams:
            self.units.append("kBs")
            self.names.append(stream.name)
            self.vals.append(0.0)
            if stream.name.startswith("Tuner"):
                self.maxVals.append(self.sim.params.iBSize)
            else:
                self.maxVals.append(self.sim.params.oBSize)

    def updateVals(self):
        self.vals = []
        for stream in self.sim.streams:
            self.vals.append(stream.requester.buffer.amount)

# Main Simulation Function
class Sim():
    def __init__(self):
        self.params = Parameters()
        self.vars = Variables(self)
        self.errors = []

    def currTime(self):
        return now()

    def stop(self):
        stopSimulation()

    def prepare(self):

        params = self.params

        # Instantiate Scheduler(s), HDD(s), RAMBus and CPU(s) modules
        params.rambus = RAMBus(params.RAMtranSpeed, params.RAMoverhead)
        params.cpu = CPU(params.CPUnumMsPerOp)
        params.sched = Scheduler()
        params.hdd = HDD("HDD", params)

        # Instantiate Input/Ouput Streams
        self.streams = []
        for i in range(0, params.numTuners):
            self.streams.append(InputStream("Tuner #%i"%i, params.tunerBitrate, self))
        for i in range(0, params.numOutputs):
            self.streams.append(OutputStream("Output #%i"%i, params.outputBitrate, self))
        self.vars.initVarData()

    def activate(self):
        params = self.params
        # Activate all processes
        activate(params.sched, params.sched.sortRequests(params.waitInterval, params.cpu))
        activate(params.hdd, params.hdd.processRequests(params.waitInterval))
        for i in range(0, params.numTuners):
            activate(self.streams[i], self.streams[i].fillBuffer())
        for i in range(params.numTuners, len(self.streams)):
            activate(self.streams[i], self.streams[i].drainBuffer())

    def simulate(self):
        # Simulate system for params.maxTime simulation milliseconds
        print "Starting Simulation"
        simulate(until=self.params.maxSimTime)

        # Report Simulation findings
        print 'Done!'

