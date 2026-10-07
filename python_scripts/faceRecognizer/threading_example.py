from threading import Thread
import time

def BigBox(color, l):
    while True:
        print(color, 'big box open with length', l)
        time.sleep(5)
        print(color, 'big box closed with length', l)
        time.sleep(5)

def SmallBox(color, l):
    while True:
        print(color, 'small box open with length', l)
        time.sleep(1)
        print(color, 'small box closed with length', l)
        time.sleep(1)

color = 'red'
l = 5

BigBoxThread = Thread(target=BigBox, args=(color,l))
SmallBoxThread = Thread(target=SmallBox, args=(color,l))

# daemon=False (default)	Keeps Python running until the thread finishes.
# daemon=True	            Does not keep Python running. Stops when no non-daemon threads remain.
BigBoxThread.daemon = True
SmallBoxThread.daemon = True

# Start two threads that work independently from each other
BigBoxThread.start()
SmallBoxThread.start()

while True:
    pass

