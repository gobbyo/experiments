import _thread
from time import sleep

lock = _thread.allocate_lock()
counter = 0

def thread_task():
    global counter
    for i in range(5):
        lock.acquire()
        counter += 1
        print(f"Thread: counter = {counter}")
        lock.release()
        sleep(0.1)

_thread.start_new_thread(thread_task, ())

for i in range(5):
    lock.acquire()
    counter += 1
    print(f"Main: counter = {counter}")
    lock.release()
    sleep(0.1)

sleep(1)