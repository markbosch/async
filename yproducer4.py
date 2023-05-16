# producer.py
#
# Producer-consumer problem. With async-await

import time
from collections import deque
import heapq
from select import select

# Layer async/await on top of a callback based
# scheduler so it will support both models
#  - async / await
#  - callback based
#
# Now with support of IO

# Callback based scheduler (from earlier)
class Scheduler:
    def __init__(self):
        self.ready = deque()   # Functions ready to execute
        self.sleeping = []     # Sleeping functions
        self.sequence = 0
        self._read_waiting = { }
        self._write_waiting = { }
        
    def call_soon(self, func):
        self.ready.append(func)

    def call_later(self, delay, func):
        self.sequence += 1
        deadline = time.time() + delay     # Experiation time
        # Priority queue
        heapq.heappush(self.sleeping, (deadline, self.sequence, func))

    def read_wait(self, fileno, func):
        # Trigger func() when fileno is readable
        self._read_waiting[fileno] = func

    def write_wait(self, fileno, func):
        # Trigger func() when fileno is writeable
        self._write_waiting[fileno] = func
        
    def run(self):
        # Check all 'Queue's'
        while (self.ready or self.sleeping or self._read_waiting or self._write_waiting):
            if not self.ready:
                # Two things happen here
                # - Wait for I/O
                # - Wait for sleeping (Doing nothing)
                # Find the nearest deadline
                if self.sleeping:
                    deadline, _, func = self.sleeping[0] # get the top most sleeping
                    timeout = deadline - time.time()
                    if timeout < 0:
                        timeout = 0
                else:
                    timeout = None     # Wait forever

                # Wait for I/O (and sleep)
                can_read, can_write, _ = select(self._read_waiting,
                                                self._write_waiting, [], timeout)
                # Add to the 'ready' queue
                for fd in can_read:
                    self.ready.append(self._read_waiting.pop(fd))
                for fd in can_write:
                    self.ready.append(self._write_waiting.pop(fd))

                # Check for sleeping task
                now = time.time()
                while self.sleeping:
                    if now > self.sleeping[0][0]:   # This is the deadline
                        self.ready.append(heapq.heappop(self.sleeping)[2])
                    else:
                        break     # deadline not past
                
            while self.ready:
                func = self.ready.popleft()
                func()

    def new_task(self, coro):  # fake the interface
        self.ready.append(Task(coro))  # Wrapped coroutine

    async def sleep(self, delay):
        # self.current = Task
        self.call_later(delay, self.current)  # callback based
        self.current = None
        await switch()     # Switch to a new Task

    async def recv(self, sock, maxbytes):
        self.read_wait(sock, self.current)
        self.current = None
        await switch()
        return sock.recv(maxbytes)

    async def send(self, sock,  data):
        self.write_wait(sock, self.current)
        self.current = None
        await switch()
        return sock.send(data)

    async def accept(self, sock):
        self.read_wait(sock, self.current)
        self.current = None
        await switch()
        return sock.accept()
    
# Task is a 'extra' layer which adapts coroutine
# and supports the api interface
class Task:
    def __init__(self, coro):
        self.coro = coro         # "Wrapped coroutine"

    # Make it look a callback... fake the API
    def __call__(self):
        try:
            # Driving the coroutine as before
            sched.current = self
            self.coro.send(None)  # Drive the coroutine
            if sched.current:
                sched.ready.append(self)
        except StopIteration:
            pass
        
sched = Scheduler()

class Awaitable:
    def __await__(self):
        yield

def switch():
    return Awaitable()

# ----------------

class QueueClosed(Exception):
    pass

class AsyncQueue:
    def __init__(self):
        self.items = deque()
        self.waiting = deque()
        self._closed = False

    def close(self):
        self._closed = True
        if self.waiting and not self.items:
            sched.ready.append(self.waiting.popleft())   # Reschedule waiting task

    async def put(self, item):     # make put also async because of 'api' design
        if self._closed:
            raise QueueClosed()

        self.items.append(item)
        if self.waiting:
            sched.ready.append(self.waiting.popleft())
        
    async def get(self):
        while not self.items:
            if self._closed:
                raise QueueClosed()
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
    q.close()

async def consumer(q):
    try:
        while True:
            item = await q.get()
            if item is None:
                break
            print(f'Consuming {item}')
    except QueueClosed:
        print('Consuming done')

q = AsyncQueue()
sched.new_task(producer(q, 10))  # async / await functions
sched.new_task(consumer(q,))     # async / await functions

# callback functions
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

sched.call_soon(lambda: countdown(5))  # callback functions
sched.call_soon(lambda: countup(20))   # callback functions

from socket import *
async def tcp_server(addr):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.bind(addr)
    sock.listen(1)
    while True:
        client, add = await sched.accept(sock)
        sched.new_task(echo_handler(client))

async def echo_handler(sock):
    while True:
        data = await sched.recv(sock, 10000)
        if not data:
            break
        await sched.send(sock, b'Got:' + data)
    print('Connection closed')
    sock.close()

sched.new_task(tcp_server(('', 30000)))
# nc localhost 3000
# start typing :-) will echo back
sched.run()

