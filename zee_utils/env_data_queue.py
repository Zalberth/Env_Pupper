import queue
# 自己建立的队列   
class EnvDataQueue:
    def __init__(self, maxsize):
        self.queue = queue.Queue(maxsize=maxsize)

    def push_data(self, data):
        if self.queue.full():
            self.queue.get()
        self.queue.put(data)

    def get_data_list(self):
        return list(self.queue.queue)