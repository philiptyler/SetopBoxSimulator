# Header-------------------
__author__ = "Philip Tyler"
__copyright__ = "Copyright 2012, TiVo Corp."
__credits__ = ["Philip Tyler", "David Platt", "Mukesh Patel"]
__license__ = "TiVo Confidential"
__version__ = "1.08-11"
__maintainer__ = "Philip Tyler"
__email__ = "ptyler@calpoly.edu"
__status__ = "Developement"

# Imports------------------
from SimPy.Simulation import *
from random import expovariate
from Data import RRequester, WRequester

# Simulates continous data being added to a buffer, specifically a TV tuner
# chip constantly filtering a given channel and sending the raw filtered
# video data to the RAM.  This module also activates a module that packages
# data in the buffer and schedules it to be written to the HDD
class InputStream(Process):
    def __init__(self, name, bitrate, sim):
        Process.__init__(self, name)
        self.requester = WRequester("Write Requester of %s"%name, sim.params)
        self.bitrate = bitrate
        self.rambus = sim.params.rambus
        self.errors = sim.errors

    def fillBuffer(self, avgPktSize=0):
        # Activate BufferControl's process in 100 ms
        activate(self.requester, self.requester.watchBuffer(), now()+100)

        # If the average packet size is not redefined, define as bitrate
        if avgPktSize <= 0:
            avgPktSize = self.bitrate/10.0

        # Continuously fill corresponding buffer with kBs based on the
        # given average bitrate.
        while True:
            sizemb = expovariate(1.0/avgPktSize)
            sizekB = sizemb*128   #Mb -> KB
            if self.requester.buffer.freeSpace() < sizekB:
                self.errors.append("<font color=red>%s Buffer Overflow at %.3f</font>"%(self.name, now()))
            else:
                yield put, self, self.requester.buffer, sizekB
                yield request, self, self.rambus
                yield hold, self, self.rambus.processTime(sizekB)
                yield release, self, self.rambus

            #print "Just added %f kBs to %s at %i"%(sizekB,self.name,now())
            yield hold, self, (1000*sizemb/self.bitrate)

# Simulates continous data being removed from a buffer, specifically a real-
# time MPEG decoder chip constantly pulling the raw MPEG video data from RAM
# to output to a disply.  This module also activates a module that schedules
# read requests to fill the buffers with data from the HDD
class OutputStream(Process):
    def __init__(self, name, bitrate, sim):
        Process.__init__(self, name)
        self.requester = RRequester("Read Requester of %s"%name, sim.params)
        self.bitrate = bitrate
        self.rambus = sim.params.rambus
        self.errors = sim.errors

    def drainBuffer(self, avgPktSize=0):
        # Activate BufferControl's process in 100 ms
        activate(self.requester, self.requester.watchBuffer(), now()+100)

        # If the average packet size is not redefined, define as bitrate
        if avgPktSize <= 0:
            avgPktSize = self.bitrate/10.0

        # Continuously drain corresponding buffer with kBs based on the
        # given average bitrate.
        while True:
            sizemb = expovariate(1.0/avgPktSize)
            sizekB = sizemb*128   #Mb -> KB
            if self.requester.buffer.amount < sizekB:
                self.errors.append("<font color=red>%s Buffer Underflow at %.3f</font>"%(self.name, now()))
                continue

            yield get, self, self.requester.buffer, sizekB
            yield request, self, self.rambus
            yield hold, self, self.rambus.processTime(sizekB)
            yield release, self, self.rambus

            #print "Just removed %f kBs from %s at %i"%(sizekB,self.name,now())
            yield hold, self, (1000*sizemb/self.bitrate) # 1000 ms in one s