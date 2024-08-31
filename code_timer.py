import timeit
import logging

logger = logging.getLogger(__name__)
s_to_ms = 1e3


class CodeTimer:
    def __init__(self, name=None):
        self.name = name if name else "Block"
        self.start = -1
        self.took = -1

    def __enter__(self):
        self.start = timeit.default_timer()

    def __exit__(self, exc_type, exc_value, traceback):
        self.took = (timeit.default_timer() - self.start) * s_to_ms
        logger.info(f"{self.name} took: {self.took} ms")
