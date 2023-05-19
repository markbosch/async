# Build Your Own Async
# Tutorial: David Beazley https://www.youtube.com/watch?v=Y4Gt3Xjd7G8&t=82s
# Checkout as well: Raymond Hettinger https://www.youtube.com/watch?v=9zinZmE3Ogk

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
        deadline = time.time() + delay     # Expiration time
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
        
def countdown(n):
    if n > 0:
        print(f'Down {n}')
        #time.sleep(4)       # Blocking call (nothing else can happen)
        sched.call_later(4, lambda: countdown(n-1))  # call with lambda so that no argument function

def countup(stop):
    def _run(x):
        if x < stop:
            print(f'Up {x}')
            #time.sleep(1)
            sched.call_later(1, lambda: _run(x+1))
    _run(0)

sched.call_soon(lambda: countdown(5))
sched.call_soon(lambda: countup(20))
sched.run()

# Problem: How to achieve concurrency without threads?
# Issue: Figure out how to switch between tasks.

