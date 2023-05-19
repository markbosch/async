# Build Your Own Async

This is a summary / note on the tutorial [Build Your Own Async](https://www.youtube.com/watch?v=Y4Gt3Xjd7G8).

The summary is more of understanding for myself.

## How to do concurrency without threads

The goal of this tutorial is to do concurrency **without** any threads involved and have an understanding of the core concept of the standard async libraries in Python. 

Threads are in this case real Operation System threads used by Python. By not utilizing threads you'll get a way more scalable solution.

Concurrency can be done by:

- Processes
- Threads
- see below ;-)

Simple concurrency example with threads:

```python
import time
import threading

def countdown(n):
    while n > 0:
      	print(f'Down {n}')
	  	time.sleep(1)
	  	n -= 1

def countup(stop):
    x = 0
    while x < stop:
	  	print(f'Up {x}')
	  	time.sleep(1)
	  	x += 1

threading.Thread(target=countdown, args=(5,)).start()
threading.Thread(target=countup, args=(5,)).start()

# Down 5
# Up 0
# Down 4
# ...
```

There are multiple solutions to on how to solve this problem. 

### Callbacks

One of them is introducing callbacks to switch between tasks. You then schedule callbacks on a scheduler which will run the tasks.

The downside of this approach is that you can't use program elements that are blocking the execution of a function like `for`-, `while`-loops or `time.sleep()` and you'll have to deal with them in a other way.

The `Scheduler` contains functions where you can schedule the callbacks - `call_soon(func)` - on or postpone (sleep) - `call_later(delay, func)` - the callbacks the be scheduled later. 

The `Scheduler` also contains a `main`-loop to execute the work by getting the callbacks from a `ready` and `sleeping` queue. 

Scheduler:

```python
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
```
A re-write of the `countdown` and `countup` functions is needed, because the `while` and the `sleep` can't be used. They need to interact with the `Scheduler` to recursively call them self.

``` python        
sched = Scheduler()

def countdown(n):
    if n > 0:
        print(f'Down {n}')
        #time.sleep(4)       # Blocking call (nothing else can happen)
        sched.call_later(4, lambda: countdown(n-1))  # call with lambda as a no argument function

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
```

### Async/Await

A alternative approach instead of callbacks is to leverage the `async` and `await` features of Python where `generators` and `coroutines` will drive the `Scheduler`. 

In Python a `generator` object is returned if you're using a `yield` statement in your function. The `yield` is mostly used for iteration. A `generator` will not get executed until you call `next` on it and waits for the next `next`.

A `coroutine` object is returned if a `await` statement is in the function together with the `async` keyword. In order to execute a `coroutine` you must `send` it something via `coro.send(None)`.

``` python
# generator
def countdown(n):
	while n > 0:
		print(f'Down {n}')
		yield
		n -= 1

# will not execute the method, but gives a generator object back
# which can be invoke by calling next on it
countdown(10)
next(_)
# prints Down 10
next(_)
# prints Down 9
#...

# coroutine
def switch():
    yield

async def foo():
    await switch()

foo()
# <coroutine object foo at 0x0x7fa307f43ec0>

```

In order to execute `Tasks` and let `Tasks` sleep, the `Scheduler` must be modified. Instead of adding `functions` to the 'ready; queue, it will add `coroutines` to the queue. The `Task` will be executed by sending `None` to it. In order to support waiting the `Scheduler` contains a async `sleep` method  where it will push the `current` task onto the sleeping queue and `switch` tasks by awaiting. This `switch` task needs to be done by a trick where the `yield` is called in a `__await__` method of a class.

async / await `Scheduler`:

``` python
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

class Awaitable:
    def __await__(self):
        yield

def switch():
    return Awaitable()

```

The whole async / await approach will give a much better and easier programming model then the callback based. For- and while-loops are now possible. It's more like the `Thread` based.

While the program is waiting for something it can `switch` tasks between these executions.

To illustrate that:

``` python
sched = Scheduler()

async def countdown(n):
    while n > 0:
        print(f'Down {n}')
        await sched.sleep(4)
        n -= 1

async def countup(stop):
    x = 0
    while x < stop:
        print(f'Up {x}')
        await sched.sleep(1)
        x += 1

sched.new_task(countdown(5))
sched.new_task(countup(20))
sched.run()
```

## Extra notes

It's even possible to take a step further and do real `I/O` with it by expanding the `Scheduler` to have some wrapper functions for e.g. Sockets (see yproducer4.py).

Most of the existing async libraries in Python are using a callback based `Scheduler` with a compatible `async/await` interface to support both programming models. See also yproducer4.py.

