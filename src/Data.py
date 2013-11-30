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
from random import randint, expovariate

# This module acts as a data container for the simulation.  Data is either
# streamed into or out of the buffer via packets of random sizes.
class Buffer(Level):
    def __init__(self, bName, capacity, initAmount):
        Level.__init__(self, name=bName, monitored=True, monitorType=Monitor, initialBuffered=initAmount)
        self.capacity = capacity

    # Named subtraction for more readable code
    def freeSpace(self):
        return self.capacity - self.amount

# This is a parent module for the request creation modules that utilize the same
# watchBuffer process but do not create the same type of requests.
class BufferControl(Process):
    def __init__(self, bcName, cpu, capacity, initAmount, watchInterval):
        Process.__init__(self, name=bcName)
        self.buffer = Buffer(bcName, capacity, initAmount)
        self.watchInterval = watchInterval
        self.cpu = cpu

        # Buffer Control will only create an I/O request if the previous
        # request has completed processing.
        self.requestComplete = SimEvent(name="%s: HDD Request Complete"%self.name)

    # A continuous process that decides when a buffer needs more/less data
    # and makes the corresponding HDD request.
    def watchBuffer(self):
        # if maxNoReqTime in simulator ms passes without a request being sent
        # a new request will be made, even if the buffer's level has not
        # reached the required threshhold.
        timeNoReq = 0

        while True:
            # The process must "have" the cpu to do anything because in the
            # actual system, it is the CPU code that creates IO requests.
            yield request, self, self.cpu

            # In the child modules noReqCond is defined to return true if the
            # system does NOT meet requirements to create a request.  In that
            # case, the process will release the CPU and wait a psuedo-
            # random amount of milliseconds and check again.
            if (self.noReqCond(timeNoReq)):
                yield release, self, self.cpu
                yield hold, self, self.watchInterval
                timeNoReq += self.watchInterval

            # if the system does meet requirements for a new IO request, the
            # BufferControl child will call its own createRequest function,
            # hold the process for the time it would take the CPU to make the
            # request in real time, passes the new request to the scheduler
            # then releases the CPU.
            else:
                timeNoReq = 0
                req = self.createRequest()
                yield hold, self, self.cpu.processTime(10+req.size/128)
                yield release, self, self.cpu

                print self.name, "created a request", req
                yield waitevent, self, self.requestComplete
                if req.write:
                    yield get, self, self.buffer, req.size
                else:
                    yield put, self, self.buffer, req.size


    # Abstract Method to be overwritten by subclasses
    def createRequest(self):
        pass

    # Abstract Method to be overwritten by subclasses
    def noReqCond(self, timeNoReq):
        return timeNoReq

# A container class for an IORequest.  These are instantiated in subclasses of
# the BufferControl Monitor, which then waits until the requests completion.
# These are passed to a scheduler object, and completed by the HDD module.
class IORequest():
    def __init__(self, bufferCon, size, diskAddress, write=0):
        self.bufferCon = bufferCon
        self.size = size
        self.diskAddress = diskAddress
        self.deadline = bufferCon.computeDeadline()
        self.write = write

    def __str__(self):
        if self.write:
            return "WRITE Request|Size:%ikBs|LBA:%i|DL:%s"%(self.size,
             self.diskAddress, self.deadline)
        else:
            return "READ Request|Size:%ikBs|LBA:%i|DL:%s"%(self.size,
             self.diskAddress, self.deadline)

    def __repr__(self):
        return self.__str__()

    # When the data for a  write request is moved to the HDD cache, or the
    # data for a read request is moved from the HDD cache to the correct
    # buffer, the IO request is complete and the requester modules are
    # signaled to resume operation
    def completeRequest(self):
        print "Request completed:", self
        self.bufferCon.requestComplete.signal()

    # Grabber function for sort()
    def deadline(self):
        return self.deadline

    # Grabber function for sort()
    def diskAddress(self):
        return self.diskAddress

# This module watches a buffer that is being continously emptied.  To fill it,
# this process creates read requests to pull more data from the hdd, filling
# the buffer.
class RRequester(BufferControl):
    def __init__(self, name, params):
        BufferControl.__init__(self, name, params.cpu, params.oBSize, params.oBSize/2, params.oInterval)
        self.cap = params.oBSize
        self.maxData = params.oThreshhold
        self.largestRead = params.rMaxSize
        self.reqTimeOut = params.oReqTimeOut
        self.sched = params.sched

    # Used in parent's watchBuffer function to create a new read request
    # based on the buffer amount.
    def createRequest(self):
        sectorSize = 128 # kBs

        n = int(self.buffer.freeSpace() / sectorSize)
        reqSize = min(self.largestRead, n*sectorSize)
        req = IORequest(self, reqSize, randint(0,100))

        self.sched.add(req)
        return req

    # Used in parent's watchBuffer function.  Returns true if the system is
    # NOT ready to make a new IO request.
    def noReqCond(self, timeNoReq):
        return (self.buffer.amount >= self.maxData and timeNoReq < self.reqTimeOut)

    def computeDeadline(self):
        return 1000.0*self.buffer.amount/self.cap + now()

# This module watches a buffer that is being continously filled.  To empty it,
# this process creates write requests to add its data to the hdd, emptying
# the buffer.
class WRequester(BufferControl):
    def __init__(self, name, params):
        BufferControl.__init__(self, name, params.cpu, params.iBSize, 0, params.iInterval)
        self.cap = params.iBSize
        self.minData = params.iThreshhold
        self.largestWrite = params.wMaxSize
        self.reqTimeOut = params.iReqTimeOut
        self.sched = params.sched

    # Used in parent's watchBuffer function to create a new write request
    # based on the buffer amount.
    def createRequest(self):
        sectorSize = 128 # kBs
        timeToFinishReq = 1000 # ms

        n = int(self.buffer.amount / sectorSize)
        reqSize = min(self.largestWrite, n*sectorSize)
        req = IORequest(self, reqSize, randint(0,100), write=1)

        self.sched.add(req)
        return req

    # Used in parent's watchBuffer function.  Returns true if the system is
    # NOT ready to make a new IO request.
    def noReqCond(self, timeNoReq):
        return (self.buffer.amount < self.minData and timeNoReq < self.reqTimeOut)

    def computeDeadline(self):
        return 1000.0*self.buffer.freeSpace()/self.cap + now()