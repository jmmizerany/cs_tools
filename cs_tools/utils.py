from __future__ import annotations

from base64 import (
    urlsafe_b64decode as b64d,
    urlsafe_b64encode as b64e,
)
from collections.abc import Generator, Iterable
from typing import Any, Callable, Optional, TypeVar, Union
import collections.abc
import datetime as dt
import getpass
import io
import itertools as it
import json
import logging
import pathlib
import site
import threading
import zlib

import rich

T = TypeVar("T")
log = logging.getLogger(__name__)


def chunks(iterable: Iterable[T], *, n: int) -> Generator[Iterable[T], None, None]:
    """
    Yield successive n-sized chunks from list.
    """
    # batched('ABCDEFG', 3) --> ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")

    iterable = iter(iterable)

    while batch := tuple(it.islice(iterable, n)):
        yield batch


batched = chunks


def deep_update(old: dict, new: dict, *, ignore: Any = None) -> dict:
    """
    Update existing dictionary with new data.

    The operation dict1.update(dict2) will overwrite data in dict1 if it
    is a multilevel dictionary with overlapping keys in dict2. This
    recursive function solves that specific problem.

    Parameters
    ----------
    old : dict
      old dictionary to update

    new : dict
      new dictionary to pull values from

    ignore : anything [default: None]
      ignore values like <ignore>

    Returns
    -------
    updated : dict
      old dictionary updated with new's values
    """
    for k, v in new.items():
        if v is ignore or str(v) == str(ignore):
            continue

        if isinstance(v, collections.abc.Mapping):
            v = deep_update(old.get(k, {}), v, ignore=ignore)

        if old is None:
            old = {}

        old[k] = v

    return old


def anonymize(text: str, *, anonymizer: str = " [dim]{anonymous}[/] ") -> str:
    """Replace text with an anonymous value."""
    return text.replace(getpass.getuser(), anonymizer)


def obscure(data: bytes) -> bytes:
    """
    Encode data to obscure its text.

    This is security by obfuscation.
    """
    if data is None:
        return

    if isinstance(data, str):
        data = str.encode(data)

    return b64e(zlib.compress(data, 9))


def reveal(obscured: bytes) -> bytes:
    """
    Decode obscured data to reveal its text.

    This is security by obfuscation.
    """
    if obscured is None:
        return

    return zlib.decompress(b64d(obscured))


def find(predicate: Callable[[Any], [bool]], iterable: list[Any]) -> Any:
    """
    Return the first element in the sequence that meets the predicate.
    """
    for element in iterable:
        if predicate(element):
            return element

    return None


class State:
    """
    An object that can be used to store arbitrary state.
    """

    _state: dict[str, Any]

    def __init__(self, state: Optional[dict[str, Any]] = None):
        if state is None:
            state = {}

        super().__setattr__("_state", state)

    def __setattr__(self, key: Any, value: Any) -> None:
        self._state[key] = value

    def __getattr__(self, key: Any) -> Any:
        try:
            return self._state[key]
        except KeyError:
            cls_name = self.__class__.__name__
            raise AttributeError(f"'{cls_name}' object has no attribute '{key}'") from None

    def __delattr__(self, key: Any) -> None:
        del self._state[key]


def svg_screenshot(
    *renderables: tuple[rich.console.RenderableType],
    path: pathlib.Path,
    console: rich.console.Console = None,
    width: Optional[Union[int, str]] = None,
    centered: bool = False,
    **svg_kwargs,
) -> None:
    """
    Save a rich Renderable as an SVG to path.

    Parameters
    ----------
    *renderables: tuple[rich.console.RenderableType]
      objects to render for the screenshot

    path: pathlib.Path
      full path to where the screenshot will be saved

    console: rich.console.Console  [default: None]
      the console to use for screenshots, respects theming

    width: int or 'fit'  [default: console.width]
      maximum width of the console in the screenshot

    centered: bool  [default: False]
      whether or not to center the renderable in the screenshot

    **svg_kwargs
      passthru keyword arguments to Console.save_svg
      https://rich.readthedocs.io/en/latest/reference/console.html#rich.console.Console.save_svg
    """
    if console is None:
        console = rich.console.Console()

    renderable = rich.console.Group(*renderables)

    if centered:
        renderable = rich.align.Align.center(renderable)

    # Set up for capturing
    context = {"width": console.width, "file": console.file, "record": console.record}

    if width == "fit":
        console.width = console.measure(renderable).maximum

    if isinstance(width, (int, float)):
        console.width = int(width)

    console.record = True
    console.file = io.StringIO()
    console.print(renderable)
    console.save_svg(path, **svg_kwargs)

    for attribute, value in context.items():
        setattr(console, attribute, value)


class DateTimeEncoder(json.JSONEncoder):
    """ """

    def default(self, object_: Any) -> Any:
        if isinstance(object_, (dt.date, dt.datetime)):
            return object_.isoformat()


class ExceptedThread(threading.Thread):
    """
    Drop the level of error reporting down from `warning` to `debug`.
    """

    def run(self) -> None:
        try:
            super().run()

        except Exception:
            log.debug(f"Something went wrong in {self}", exc_info=True)


def determine_editable_install() -> bool:
    """Determine if the current CS Tools context is an editable install."""
    for site_directory in site.getsitepackages():
        for path in pathlib.Path(site_directory).iterdir():
            if not path.is_file():
                continue

            if "__editable__.cs_tools" in path.as_posix():
                return True
    return False
