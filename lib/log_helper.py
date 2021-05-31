import os
import re
import time

import gevent

from lib.colorer import color_stdout


class StartError(OSError):
    def __init__(self, name=None, timeout=None):
        self.name = name
        self.timeout = timeout

    def __str__(self):
        if self.timeout:
            return "\n[Instance '{}'] Start timeout {} was reached.\n".format(
                self.name, self.timeout)
        return "Failed {}".format(self.name)


class Log(object):
    def __init__(self, path):
        self.path = path
        self.log_begin = 0
        self.last_position = 0

    def positioning(self):
        if os.path.exists(self.path):
            with open(self.path, 'r') as f:
                f.seek(0, os.SEEK_END)
                self.log_begin = f.tell()
        return self

    def seek_once(self, msg):
        if not os.path.exists(self.path):
            return -1
        with open(self.path, 'r') as f:
            f.seek(self.log_begin, os.SEEK_SET)
            while True:
                log_str = f.readline()

                if not log_str:
                    return -1
                pos = log_str.find(msg)
                if pos != -1:
                    return pos

    def seek_wait(self, msg, proc=None, name=None, deadline=None, timeout=10,
                  start_from_beginning=True):
        while True:
            if os.path.exists(self.path):
                break
            gevent.sleep(0.001)

        with open(self.path, 'r') as f:
            if start_from_beginning:
                f.seek(self.log_begin, os.SEEK_SET)
            else:
                f.seek(self.last_position, os.SEEK_SET)
            cur_pos = self.log_begin
            if deadline is None:
                deadline = time.time() + timeout
            while time.time() < deadline:
                if not (proc is None):
                    if not (proc.poll() is None):
                        raise StartError(name)
                log_str = f.readline()
                if not log_str:
                    gevent.sleep(0.001)
                    f.seek(cur_pos, os.SEEK_SET)
                    continue
                if re.search(msg, log_str):
                    self.last_position = re.search(msg, log_str).end() + \
                                         cur_pos
                    return True
                cur_pos = f.tell()
        return False
