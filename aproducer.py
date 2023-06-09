# aproducer.py
#
# Producer-consumer problem
# Challange: How to implement the same func., but no threads

import time

from collections import deque
import heapq

class Scheduler:
    def __init__(self):
        self.ready = deque()   # Functions ready to execute
        self.sleeping = []     # Sleeping functions
        self.sequence = 0
        
    def call_soon(self, func):
        self.ready.append(func)

    def call_later(self, delay, func):
        self.sequence += 1
        deadline = time.time() + delay     # Experiation time
        # Priority queue
        heapq.heappush(self.sleeping, (deadline, self.sequence, func))

    def run(self):
        while self.ready or self.sleeping:
            if not self.ready:
                # Find the nearest deadline
                deadline, _, func = heapq.heappop(self.sleeping)
                delta = deadline - time.time()
                if delta > 0:
                    time.sleep(delta)
                self.ready.append(func)
                
            while self.ready:
                func = self.ready.popleft()
                func()

sched = Scheduler()

# -------
class Result:
    def __init__(self, value=None, exc=None):
        self.value = value
        self.exc = exc

    def result(self):
        if self.exc:
            raise self.exc
        else:
            return self.value
        
class AsyncQueue:
    def __init__(self):
        self.items = deque()
        self.waiting = deque()     # All getters waiting for data
        self._closed = False       # Can queue be used anymore

    def close(self):
        self._closed = True

    def put(self, item):
        if self._closed:
            raise QueueClosed()
        
        self.items.append(item)
        if self.waiting:
            func = self.waiting.popleft()
            # Do we call it right away?
            sched.call_soon(func)
            # func() --> might get deep calls, recursion, etc

    def get(self, callback):
        # Wait until an item is available. Then return it
        # How does a closed queue interact with get()
        if self.items:
            callback(Result(value=self.items.popleft()))     # Good result
        else:
            # No items available (must wait)
            if self._closed:
                callback(Result(exc=QueueClosed()))  # Error result

            self.waiting.append(lambda: self.get(callback))  # Put yourself into the waiting queue

def producer(q, count):
    def _run(n):
        if n < count:
            print(f'Producing {n}')
            q.put(n)
            sched.call_later(1, lambda: _run(n+1))  # Not allowed to do for or while loops
        else:
            print('Producer done')
            q.close()                               # Means no more items will be used
    _run(0)                                         # kick start it

def consumer(q):
    def _consume(result):
        try:
            item = result.result()
            print(f'Consuming {item}')   # <<<<< Queue item (result) 
            sched.call_soon(lambda: consumer(q))
        except QueueClosed:
            print('Consumer done')
    q.get(callback=_consume)

q = AsyncQueue()
sched.call_soon(lambda: producer(q, 10))
sched.call_soon(lambda: consumer(q,))
sched.run()

