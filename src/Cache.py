#coding=utf-8
try:
    from Queue import Queue
except Exception as e:
    from queue import Queue


# Cache class, first in, first out
class FIFOCache:
    def __init__(self, size=100):
        self.size = size
        self.cache = Queue(size)

    def put(self, obj):
        if self.cache.full():
            self.cache.get_nowait()
        self.cache.put_nowait(obj)

    def get(self):
        if self.cache.empty():
            return None
        else:
            return self.cache.get_nowait()

    def isFull(self):
        return self.cache.full()

    def isEmpty(self):
        return self.cache.empty()


if __name__ == '__main__':
    cache = FIFOCache(5)
    ii = 1
    while ii < 11:
        cache.put("item:"+str(ii))
        ii = ii+1
    while not cache.isEmpty():
        obj = cache.get()
        print(str(obj))

