import re
import typing as t

from enum import Enum

T = t.TypeVar("T")

CAMEL_CASE_PATTERN = re.compile("(?<!^)(?=[A-Z])")


def seq_get(seq: t.Sequence[T], index: int) -> T | None:
    """Safely get an item from a sequence by index. If the index is out of range,
    return None instead of raising an IndexError.

    Args:
        seq: The sequence to get the item
        index: The index of the item to get

    Returns:
        The item at the specified index, or None if the index is out of range.
    """

    try:
        return seq[index]
    except IndexError:
        return None


def to_bool(value: str | bool | None) -> str | bool | None:
    if isinstance(value, bool) or value is None:
        return value

    # Coerce the value to boolean if it matches to the truthy/falsy values below
    value_lower = value.lower()
    if value_lower in ("true", "1"):
        return True
    if value_lower in ("false", "0"):
        return False

    return value


class AutoName(Enum):
    """
    This is used for creating Enum classes where `auto()` is the string form
    of the corresponding enum's identifier (e.g. FOO.value results in "FOO").

    Reference: https://docs.python.org/3/howto/enum.html#using-automatic-values
    """

    @staticmethod
    def _generate_next_value_(name, _start, _count, _last_values):
        return name


def camel_to_snake_case(name: str) -> str:
    """Converts `name` from camelCase to snake_case and returns the result."""
    return CAMEL_CASE_PATTERN.sub("_", name).upper()
