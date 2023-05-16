# producer.py
#
# Producer-consumer problem. With async-await

import time
from collections import deque
import heapq

class Scheduler:
    def __init__(self):
        self.ready = deque()
        self.sleeping = [ ]
        self.current = None       # Currently executing generator
        self.sequence = 0
        
    async def sleep(self, delay):
        # The current "coroutine" wants to sleep. How???
        deadline = time.time() + delay
        self.sequence += 1
        heapq.heappush(self.sleeping, (deadline, self.sequence, self.current))
        self.current = None # "Disappear"
        await switch()      # Switch tasks
        
    def new_task(self, coro):
        self.ready.append(coro)

    def run(self):
        while self.ready or self.sleeping:
            if not self.ready:
                deadline, _, coro = heapq.heappop(self.sleeping)
                delta = deadline - time.time()
                if delta > 0:
                    time.sleep(delta)
                self.ready.append(coro)

            self.current = self.ready.popleft()
            # Drive as a generator
            try:
                self.current.send(None)  # Send to a coroutine
                if self.current:
                    self.ready.append(self.current)
            except StopIteration:
                pass

sched = Scheduler()    # Background scheduler object

class Awaitable:
    def __await__(self):
        yield

def switch():
    return Awaitable()

# ----------------

class AsyncQueue:
    def __init__(self):
        self.items = deque()
        self.waiting = deque()

    async def put(self, item):     # make put also async because of 'api' design
        self.items.append(item)
        if self.waiting:
            sched.ready.append(self.waiting.popleft())
        
    async def get(self):
        if not self.items:
            # Wait... how??
            self.waiting.append(sched.current)   # Put myself to sleep
            sched.current = None    # "Disappear"
            await switch()          # Switch to another task
        return self.items.popleft()

async def producer(q, count):
    for n in range(count):
        print(f'Producing {n}')
        await q.put(n)
        await sched.sleep(1)
    print('Producer done')    
    await q.put(None)    # "Sentinel" to shut down

async def consumer(q):
    while True:
        item = await q.get()
        if item is None:
            break
        print(f'Consuming {item}')
    print('Consuming done')

q = AsyncQueue()
sched.new_task(producer(q, 10))
sched.new_task(consumer(q,))
sched.run()
