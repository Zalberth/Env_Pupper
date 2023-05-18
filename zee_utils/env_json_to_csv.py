import csv
import json
from queue import Queue
import os
class JSONtoCSV:
    def __init__(self, csv_filename):
        self.csv_filename = csv_filename
        self.queue = Queue(maxsize=10)

    def add_data(self, json_data):
        self.queue.put(json_data)
        if self.queue.full():
            self.write_to_csv()

    def write_to_csv(self):
        # 创建父目录（如果不存在）
        parent_directory = os.path.dirname(self.csv_filename)
        if not os.path.exists(parent_directory):
            os.makedirs(parent_directory)
        with open(self.csv_filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if csvfile.tell() == 0:  # Check if file is empty
                # Write the header row
                header = list(self.queue.queue[0].keys())
                writer.writerow(header)

            while not self.queue.empty():
                json_data = self.queue.get()
                values = [float(value) if isinstance(value, str) and value.replace('.', '', 1).isdigit() else value
                          for value in json_data.values()]
                writer.writerow(values)

