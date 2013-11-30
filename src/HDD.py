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
from random import randint
from Data import Buffer
from Schedule import Scheduler

# Contains variables needed to Simulate different HDDs.
# Different HDDs are simulated using different numbers.
class Disk(Resource):
    def __init__(self, hddname, fullStroke, oneTrackMove, maxRotateTime, RWkBpms):
        Resource.__init__(self, "Disk of %s"%hddname) #, qType=PriorityQ, preemptable=True)
        self.currHeadPos = 0
        self.oneHeadMove=oneTrackMove
        self.maxRotateTime=maxRotateTime
        self.RWkBpms=RWkBpms
        self.fullStroke=fullStroke

    # Returns the total time needed to process a request on the disk:
    # Rotation time, write/read track time, moving the head to the correct
    # track etc.
    def processReq(self, IOReq):
        IOTime = randint(0, self.maxRotateTime)+IOReq.size/self.RWkBpms
        self.currHeadPos = IOReq.diskAddress
        return IOTime+min(self.fullStroke,
            abs(IOReq.diskAddress-self.currHeadPos)*self.oneHeadMove)

# This module represents the cache of the HDD.  A buffer for unwritten write
# requests and processed read requests.  The process of the cache constantly
# pulls new IO requests from the scheduler, thus filling the cache and keeping
# the HDD busy.
class Cache(Process):
    def __init__(self, hddname, sizekBs, sched, rambus):
        Process.__init__(self, "Cache of %s"%(hddname))
        self.sched = sched
        self.rambus = rambus
        self.openReqs = []
        self.closedReqs = []
        self.buffer = Buffer(self.name, sizekBs, 0)
        self.size = sizekBs
        self.flushNow = SimEvent(name="Flush Now")
        self.flush = Flush(self)

    def fillCache(self, waitInterval):
        activate(self.flush, self.flush.flushCache())
        while True:
            # Attempts to get a new request from the scheduler's sorted list
            # if it fails, the cache will wait waitInterval ms and try again.
            try:
                nextIO = self.sched.nextRequest()
            except IndexError:
                yield hold, self, waitInterval
                continue

            # Once the cache has found a request to be processed by the HDD,
            # it waits for the cache to have enough space for the data.
            print "IO being added to HDD Cache", nextIO
            while nextIO.size > self.buffer.freeSpace():
                print "not enough rooom for nextIO, %i items to flush"%len(self.closedReqs)
                if len(self.closedReqs) > 2:
                    self.flushNow.signal()
                    yield waitevent, self, self.flush.flushComplete
                else:
                    yield hold, self, waitInterval

            # Once enough bytes free up, the cache marks that the new request's
            # data size is being used in the cache and adds the request to
            # the cache's FIFO list of pending requests.  If the request is a
            # write request, it is marked as complete.
            yield put, self, self.buffer, nextIO.size
            self.openReqs.append(nextIO)
            if nextIO.write:
                self.closedReqs.append(nextIO)

class Flush(Process):
    def __init__(self, cache):
        Process.__init__(self, name="Cache Flusher")
        self.flushNow = cache.flushNow
        self.buffer = cache.buffer
        self.closedReqs = cache.closedReqs
        self.rambus = cache.rambus
        self.flushComplete = SimEvent(name="Flush Complete")

    def flushCache(self):
        # This loop simulates the cache actually transfering data to/from
        # the RAM buffers.  When write requests are recieved or read
        # requests have finished processing, they are put into closedReqs
        # list.  This loop iterates the list, and holds the cache process
        # while the data is transfered.
        while True:
            yield waitevent, self, self.flushNow
            print "FLUSHING COMENCING"
            print self.closedReqs
            while len(self.closedReqs):
                processedIO = self.closedReqs.pop(0)
                rtime = now()
                yield request, self, self.rambus
                rtime = now() - rtime
                htime = now()
                yield hold, self, self.rambus.processTime(processedIO.size)
                htime = now() - htime
                print "IO processed, RAM request time: %f, RAM processTime: %f"%(rtime,htime)
                yield release, self, self.rambus
                if not processedIO.write:
                    yield get, self, self.buffer, processedIO.size
                processedIO.completeRequest()
            self.flushComplete.signal()

# This module simulates the actual disk portion of the HDD.  Using a FIFO list
# created in the cache, this module uses parameter numbers to simulate the time
# needed to complete all the requests in the list.
class HDD(Process):
    def __init__(self, name, params):
        Process.__init__(self, name)
        self.cache = Cache(name, params.hddCacheSize, params.sched, params.cpu)
        self.disk = Disk(name, params.hddFullStroke, params.hddTrackMove, params.hddMaxTurn, params.hddRWkBpms)
        self.baseChance = params.baseChanceATR

    # A continuous process that simulates writes/reads on a HDD platter.  When
    # a request from the cache found, this process calculates an amount of time
    # to hold itself for bases on disk variables, then marks the request done.
    def processRequests(self, waitInterval):
        activate(self.cache, self.cache.fillCache(waitInterval))
        ATRchance = self.baseChance

        while True:
            # The HDD gets the next pending request from the cache, if none
            # are available, the HDD waits waitInterval ms.
            try:
                nextIO = self.cache.openReqs.pop(0)
            except IndexError:
                yield hold, self, waitInterval
                continue

            # The HDD calculates the time needed to process the request, and
            # simulates writing/reading the data by delaying the process.
            temp = self.disk.processReq(nextIO)
            print "Disk hold time:", temp
            yield hold, self, temp

            # if the processed request is a write request, its data is removed
            # from the cache.  If a read request, it is added to the cache's
            # list of IO requests to finish.
            if nextIO.write:
                yield get, self, self.cache.buffer, nextIO.size
            else:
                self.cache.closedReqs.append(nextIO)

            # After processing a request, the HDD has a chance to enter
            # Adjacent Track Repair mode, simulating that of a WD HDD.  A
            # random integer is generated, if below ATRchance, the HDD will
            # stall itself for a calculated amount of time, then resume
            # processing requests.
            if randint(0,100) < ATRchance:
                print "Adjacent Track Repair: %i ms"%(70+3*ATRchance)
                yield hold, self, 70+3*ATRchance
                ATRchance = self.baseChance
            else:
                ATRchance += 1
