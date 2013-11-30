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

# This module is used to simulate the system's CPU.  Since a core in a
# processor can only compute one task at any given point in time, this
# module acts as a "flag" that other modules must "hold" in order to
# use a CPU core.
class CPU(Resource):
    def __init__(self, msPerOp):
        Resource.__init__(self, name='CPU')
        self.msPerOp = msPerOp

    # Returns time for CPU to process numOps operations
    def processTime(self, numOps):
        return self.msPerOp * numOps

# This module is used to simulate the RAM data bus in the System.  Since only
# one part of the system can write/read from the RAM at any one point in time,
# this module acts as a "flag" that other modules must "hold" in order to
# transfer RAM data.
class RAMBus(Resource):
    def __init__(self, tranSpeedkBpms, tranOverhead):
        Resource.__init__(self, name='RAM data bus')
        self.tranSpeedkBpms = tranSpeedkBpms
        self.tranOverhead = tranOverhead

    # Returns time to read/write numDatakBs to RAM
    def processTime(self, numDatakBs):
        return self.tranOverhead + numDatakBs * self.tranSpeedkBpms
