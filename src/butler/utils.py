import dataclasses
import inspect
import os
import pathlib
import shutil
import subprocess
from typing import Any, Mapping, Protocol

from . import context
from .typing import AnyPath, ModuleType

__all__ = ['Result', 'include', 'proc']

_MODULE_CACHE: dict[AnyPath, ModuleType] = {}


@dataclasses.dataclass
class Result:
    """Task result indicating its provided data and whether it changed anything.

    Tasks can also return a mapping, a bool or None. They are converted to
    Result as follows:
    - Mapping: `Result(x)`
    - bool: `Result({}, changed=x)`
    - None: `Result({})`
    """

    attrs: Mapping[str, Any]
    changed: bool = True


def include(path: AnyPath) -> ModuleType:
    """Imports any file as a module if it is not imported yet.

    include() behaves similarely to the `import` statement. It evaluates
    relative paths in the context of the module in which the calling
    function is defined and not where the calling function itself may be
    called from.

    Parameters
    ----------
    path : pathlib.Path
        The path of the file to load. If the path is relative it is
        resolved relative to the parent directory of the importing module.

    Returns
    -------
    ModuleType
        A python module.

    Raises
    ------
    ImportError
        If the module generation fails.
    """
    import importlib.util

    path = pathlib.Path(os.fspath(path))
    if not path.is_absolute():
        basedir = pathlib.Path(inspect.stack(context=0)[1].filename).parent
        path = basedir / path
    path = path.resolve()
    name = path.parent.stem

    if (module := _MODULE_CACHE.get(path)) is not None:
        return module

    # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None:
        raise ImportError(f'Could not load spec for task file at: {path}')
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except FileNotFoundError as e:
        raise ImportError(f'{e.strerror}: {path}') from e
    _MODULE_CACHE[path] = module
    return module


class Process:
    """Syntax sugar for calling subprocesses."""

    class Signature(Protocol):
        def __call__(
            self,
            *params: tuple[str, ...],
            cwd: AnyPath | None = None,
            env: Mapping[str, str] | None = None,
            input: str | None = None,
            timeout: float | None = None,
        ) -> str: ...

    _CACHE: dict[str, Signature] = {}

    def __getitem__(self, cmd: str) -> Signature:
        return self.__getattr__(cmd)

    def __getattr__(self, cmd: str) -> Signature:
        if (cmd := shutil.which(cmd)) is None:
            raise ValueError(f'Unknown executable {cmd}')
        if (cached := self._CACHE.get(cmd)) is not None:
            return cached

        def process(
            cmd: str,
            *params: tuple[str, ...],
            cwd: AnyPath | None = None,
            env: Mapping[str, str] | None = None,
            input: str | None = None,
            timeout: float | None = None,
        ) -> str:
            if cwd is None:
                cwd = context.cwd()
            return subprocess.run(
                [cmd] + params,
                cwd=cwd,
                env=env,
                input=input,
                timeout=timeout,
                check=True,
                encoding='utf-8',
            ).stdout.rstrip()

        self._CACHE[cmd] = process
        return process


proc = Process()


def bash(
    cmdline: str,
    cwd: AnyPath | None = None,
    env: Mapping[str, str] | None = None,
    input: str | None = None,
    timeout: float | None = None,
) -> str:
    return proc.bash('-c', cmdline)
