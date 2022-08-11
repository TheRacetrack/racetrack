import logging
import threading
import sys
from queue import Queue


class DeadlyThread(threading.Thread):
    """threading.Thread that might be killed"""
    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self.killed = False

    def start(self):
        self.__run_backup = self.run
        self.run = self.__run     
        threading.Thread.start(self)

    def __run(self):
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, event, arg):
        if event == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, event, arg):
        if self.killed:
            if event == 'line':
                raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True


def timeout(max_time: int):
    """Timeout decorator builder, killing the function thread after max_time seconds"""
    def timeout_decorator(fn):

        def wrapper(*args, **kwargs):
            q = Queue()

            def enqueue_fn():
                try:  # Try adding the results of the function call
                    q.put(fn(*args, **kwargs))
                except BaseException:
                    # If it fails, enqueue the exception instead
                    q.put(sys.exc_info())

            thread = DeadlyThread(target=enqueue_fn)
            thread.start()
            thread.join(max_time)

            if not thread.isAlive():
                # thread finished normally
                output = q.get_nowait()
                # Reraise if an exception occured
                if isinstance(output, tuple) \
                    and type(output[0]) is type \
                    and isinstance(output[0](), BaseException):
                    raise output[0]
                else:  # return the results otherwise
                    return output

            thread.kill()
            thread.join()
            if thread.isAlive():
                logging.warning('timed-out thread is still running')

            raise TimeoutError(f"Processing took longer than {max_time} seconds")

        return wrapper

    return timeout_decorator
