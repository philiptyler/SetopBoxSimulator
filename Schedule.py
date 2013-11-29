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
from Data import IORequest

# This module represents the IO scheduler in the linux kernel.  It keeps two
# lists: a FIFO list that IO requesters add their newly-created requests to
# and a sorted list the HDD pulls requests from.
class Scheduler(Process):
    def __init__(self):
        Process.__init__(self, name="Scheduler");
        self.newReqsQ = []
        self.sortedReqsQ = []
        self.minReqs2Schedule = 5

    # Called by IO request creators
    def add(self, IOReq):
        self.newReqsQ.append(IOReq)

    # Called by the HDD's cache for the next request to be written to
    # the HDD
    def nextRequest(self):
        return self.sortedReqsQ.pop(0)

    # Sorts requests (This one is bases on diskAddress)
    def schedule(self):
        print "NOW SORTING %i items at %i"%(len(self.newReqsQ),now())
        self.sortedReqsQ = sorted(self.newReqsQ,key=IORequest.diskAddress)
        return len(self.sortedReqsQ)

    # A continuous process that waits for the schedulers sorted list to empty
    # then refills it after sorting the FIFO list.
    def sortRequests(self, interval, cpu):
        while True:
            if len(self.sortedReqsQ):
                #print "%s still has %i sorted requests, waiting %ims, now:%i"%(self.name, len(self.sortedReqsQ), interval, now())
                yield hold, self, interval
            else:
                if len(self.newReqsQ) >= self.minReqs2Schedule:
                    yield request, self, cpu
                    yield hold, self, cpu.processTime(self.schedule())
                    yield release, self, cpu
                else:
                    print "%s's newReqQ: %i requests, sorted: %i, waiting %ims"%(self.name, len(self.newReqsQ), len(self.sortedReqsQ), interval)
                    yield hold, self, interval

class DLScheduler(Scheduler):
    def __init__(self):
        Scheduler.__init__(self)
        self.minReqs2Schedule = 1

    def avgProcessingTime(self,IOReq):
        return 50

    def schedule(self):
        self.newReqsQ = sorted(self.newReqsQ,key=IORequest.deadline)
        IO = self.newReqsQ.pop(0)
        time = IO.deadline - now()
        print "Trying to schedule %i reqs with %f ms at %i"%(len(self.newReqsQ),time,now())

        while True:
            self.sortedReqsQ.append(IO)
            time -= self.avgProcessingTime(IO)
            if time < 0:
                break
            try:
                IO = self.newReqsQ.pop(0)
            except IndexError:
                break

        self.sortedReqsQ = sorted(self.sortedReqsQ,key=IORequest.diskAddress)
        print self.sortedReqsQ
        return pow(len(self.sortedReqsQ),2)