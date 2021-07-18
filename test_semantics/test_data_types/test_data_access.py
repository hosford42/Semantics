import contextlib
import threading
import time
from unittest import TestCase

from semantics.data_types.data_access import ControllerThreadAccessManager
from semantics.data_types.exceptions import ResourceUnavailableError
from semantics.data_types.indices import PersistentDataID


def threaded_call(callback, *args, **kwargs):
    """Call the function in another thread. After the other thread finishes, return the result or
    raise the exception in the original thread. Basically we are just pretending this is
    multi-threaded so we can test code that looks at thread context."""
    thread_result = thread_error = None

    def catch(*args, **kwargs):
        nonlocal thread_result, thread_error
        try:
            thread_result = callback(*args, **kwargs)
        except BaseException as e:
            thread_error = e

    thread = threading.Thread(target=catch, args=args, kwargs=kwargs)
    thread.start()
    thread.join()
    if thread_error:
        raise thread_error
    else:
        return thread_result


@contextlib.contextmanager
def threaded_context(context, *args, **kwargs):
    """Enter the context manager in another thread. Then return control to the original thread for
    the body of the with statement. Finally, when the with statement completes, exit the context
    from other thread. Basically we are just pretending this is multi-threaded so we can test code
    that looks at thread context."""
    thread_error = yielded_value = None
    entered = done = False

    primary_thread = threading.current_thread()

    def catch():
        nonlocal thread_error, entered, yielded_value
        try:
            with context as yielded_value:
                # Signal to the primary thread that we have finished entering the context.
                entered = True
                # Wait for the primary thread to signal that it's time to exit the context.
                while not done:
                    primary_thread.join(0.001)
        except BaseException as e:
            thread_error = e

    secondary_thread = threading.Thread(target=catch, args=args, kwargs=kwargs)
    secondary_thread.start()

    # Wait for the secondary thread to signal that it has finished entering the context.
    while not entered:
        # Immediately report any unhandled errors in the secondary thread.
        if thread_error:
            raise thread_error
        secondary_thread.join(0.001)
    # Immediately report any unhandled errors in the secondary thread.
    if thread_error:
        raise thread_error

    try:
        # Yield the value
        yield yielded_value
    finally:
        # Signal the secondary thread that it is time to exit the context.
        done = True
        # Wait for the secondary thread to exit the context.
        secondary_thread.join()
        # Immediately report any unhandled errors in the secondary thread.
        if thread_error:
            raise thread_error


class TestThreadAccessManager(TestCase):

    def test_read_lock(self):
        manager = ControllerThreadAccessManager(PersistentDataID(0))
        with manager.read_lock:
            with manager.read_lock:  # Nested read locks work
                pass
            with manager.write_lock:  # Write lock works if only this thread holds read lock
                pass
            # We can also acquire a read lock in another thread while we hold one
            threaded_call(manager.acquire_read)
            with self.assertRaises(ResourceUnavailableError):
                # But a write lock request fails if there are multiple readers
                threaded_call(manager.acquire_write)

    def test_write_lock(self):
        manager = ControllerThreadAccessManager(PersistentDataID(0))
        with manager.write_lock:  # We don't have to hold a read lock to acquire a write lock
            with self.assertRaises(ResourceUnavailableError):
                with manager.read_lock:  # We can't read while we are writing
                    pass
            with self.assertRaises(ResourceUnavailableError):
                with manager.write_lock:  # Nested write locks don't work
                    pass
            with self.assertRaises(ResourceUnavailableError):
                threaded_call(manager.acquire_read)  # Other threads can't read if we are writing
            with self.assertRaises(ResourceUnavailableError):
                threaded_call(manager.acquire_write)  # Other threads can't write if we are writing
        threaded_call(manager.acquire_write)  # Other threads can do stuff once we are done
