from time import sleep
import _thread

THREAD_DELAY = 1.5
 
def core0_thread():
    for counter in range(10):
        print(f"Thread 0: Count = {counter + 1}")
        sleep(1)
 
 
def core1_thread():
    for counter in range(10):
        print(f"Thread 1: Count = {counter + 1}")
        sleep(THREAD_DELAY) # Slightly different sleep to see interleaving
 
print("Starting multithreading example with two threads counting to 10.")
 
# Start the second thread
_thread.start_new_thread(core1_thread, ())
 
# Run the main thread
core0_thread()

# Keep the main thread alive to allow the second thread to complete
sleep(10 * THREAD_DELAY)  # Wait for the second thread to finish (10 iterations * 1.5 seconds)