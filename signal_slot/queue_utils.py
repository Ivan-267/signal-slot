import multiprocessing
import os
import time
from queue import Empty, Queue


def get_queue(serial=False, buffer_size_bytes=1_000_000):
    if serial:
        # for serial execution we don't need the multiprocessing queue
        return QueueWrapper()
    else:
        return get_mp_queue(buffer_size_bytes)


def get_mp_queue(buffer_size_bytes=1_000_000):
    if os.name == "nt":
        MpQueue = MpQueueWrapper
    else:
        # noinspection PyUnresolvedReferences
        import faster_fifo_reduction
        from faster_fifo import Queue as MpQueue

    return MpQueue(max_size_bytes=buffer_size_bytes)


class QueueWrapper(Queue):
    def get_many(self, block=True, timeout=float(1e3), max_messages_to_get=int(1e9)):
        msgs = []

        while len(msgs) < max_messages_to_get:
            try:
                if len(msgs) == 0:
                    msg = self.get(block, timeout)
                else:
                    msg = self.get_nowait()

                msgs.append(msg)
            except Empty:
                break

        if not msgs:
            raise Empty
        return msgs

    def get_many_nowait(self, max_messages_to_get=int(1e9)):
        return self.get_many(block=False, max_messages_to_get=max_messages_to_get)

    def put_many(self, xs, block=True, timeout=float(1e3)):
        started = time.time()

        for x in xs:
            self.put(x, block, timeout)
            time_elapsed = time.time() - started
            timeout = max(0.0, timeout - time_elapsed)

    def put_many_nowait(self, xs):
        self.put_many(xs, block=False)


class MpQueueWrapper:
    """
    Fake implementation of faster-fifo that just routes all function calls to multiprocessing.Queue.
    Can be useful on platforms where faster-fifo does not work, e.g. Windows.
    """

    def __init__(self, max_size_bytes=200000):
        self.q = multiprocessing.Queue(max_size_bytes)

    def close(self):
        self.q.close()

    def is_closed(self):
        """Not implemented."""
        return False

    def put(self, x, block=True, timeout=float(1e3)):
        self.q.put(x, block, timeout)

    def put_nowait(self, x):
        return self.put(x, block=False)

    def get_many(self, block=True, timeout=float(1e3), max_messages_to_get=int(1e9)):
        msgs = []

        while len(msgs) < max_messages_to_get:
            try:
                if len(msgs) == 0:
                    msg = self.q.get(block, timeout)
                else:
                    msg = self.q.get_nowait()

                msgs.append(msg)
            except Empty:
                break

        return msgs

    def get_many_nowait(self, max_messages_to_get=int(1e9)):
        return self.get_many(block=False, max_messages_to_get=max_messages_to_get)

    def get(self, block=True, timeout=float(1e3)):
        return self.get_many(block=block, timeout=timeout, max_messages_to_get=1)[0]

    def get_nowait(self):
        return self.get(block=False)

    def qsize(self):
        return self.q.qsize()

    def empty(self):
        return self.q.empty()

    def full(self):
        return self.q.full()

    def join_thread(self):
        self.q.join_thread()

    def cancel_join_thread(self):
        self.q.cancel_join_thread()
