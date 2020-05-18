# coding: utf-8

import os
import json


class Log():

    def __init__(self, path):
        self.file_path = path + '/log.json'
        
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.entries = json.load(f)
        else:
            self.entries = []

    @property
    def last_log_index(self):
        return len(self.entries)-1

    @property
    def last_log_term(self): 
        return self.get_log_term(self.last_log_index)


    def get_log_term(self, log_index):
        if log_index >= len(self.entries) or log_index < 0 :
            return -1
        return self.entries[log_index]['term']

    def get_entries(self, next_index):
        return self.entries[max(0, next_index):]
    

    def delete_entries(self, prev_log_index):
        self.entries = self.entries[:max(0, prev_log_index)]
        self.save()
        

    def append_entries(self, prev_log_index, entries):
        self.entries = self.entries[:max(0, prev_log_index+1)] + entries
        self.save()


    def save(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.entries, f, indent=4)
