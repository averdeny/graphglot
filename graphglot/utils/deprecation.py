import functools
import warnings


def deprecated(reason=None):
    def wrapper(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            msg = f"{func.__name__} is deprecated"
            if reason:
                msg += f": {reason}"
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return inner

    return wrapper
