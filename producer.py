# producer.py
#
# Producer-consumer problem

import queue
import time
import threading

def producer(q, count):
    for n in range(count):
        print(f'Producing {n}')
        q.put(n)
        time.sleep(1)
    print('Producer done')    
    q.put(None)    # "Sentinel" to shut down

def consumer(q):
    while True:
        item = q.get()
        if item is None:
            break
        print(f'Consuming {item}')
    print('Consuming done')

q = queue.Queue()   # Thread-safe queue
threading.Thread(target=producer, args=(q, 10)).start()
threading.Thread(target=consumer, args=(q,)).start()
