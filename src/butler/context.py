"""Helpfull classes and functions for exploring the context in which a task is executed."""

import inspect
import pathlib


def cwd() -> pathlib.Path:
    """Returns the parent directory of the file in which cwd() is called.

    Returns
    -------
    pathlib.Path
        The parent directory of the enclosing file or '.' if called
        interactively.
    """
    return pathlib.Path(inspect.stack(context=0)[1].filename).parent


cmdlineargs = {}
"""A mapping of commandline arguments provided via -d or --define"""
