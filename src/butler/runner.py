import collections
import inspect
from typing import Callable

from .registry import Registry
from .utils import Result

_ARG_KINDS = (
    inspect.Parameter.POSITIONAL_OR_KEYWORD,
    inspect.Parameter.POSITIONAL_ONLY,
    inspect.Parameter.VAR_POSITIONAL,
)
_KWARG_KINDS = (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.VAR_KEYWORD)


def _prepare_params(params: dict) -> dict[str, dict[str, dict]]:
    result = collections.defaultdict(dict)
    for key, value in params.items():
        taskname, argname = key.rsplit('.', 1)  # TODO: Error handling
        result[taskname][argname] = {'<stdin>': value}
    return result


def _execute_node(
    node: int, params: dict[str, dict], reg: Registry, result_cache: dict[int, Result]
) -> Result:
    children = reg._graph.successor_indices(node)
    if children and all(not result_cache[child].changed for child in children):
        return result_cache.get(node, Result({}))

    task = reg._graph[node]
    sig = inspect.signature(task.action)
    argnames = set(param.name for param in sig.parameters.values() if param.kind in _ARG_KINDS)
    kwargnames = set(param.name for param in sig.parameters.values() if param.kind in _KWARG_KINDS)

    args = [params.get(name, {}) for name in argnames]
    kwargs = collections.defaultdict(
        dict, {name: params[name] for name in kwargnames if name in params}
    )
    sentinel = object()
    for child in children:
        child_name = reg._graph[child].name
        child_result = result_cache[child]
        for i, name in enumerate(argnames):
            if value := child_result.get(name, sentinel) is not sentinel:
                args[i][child_name] = value
        for name in kwargnames:
            if value := child_result.get(name, sentinel) is not sentinel:
                kwargs[name][child_name] = value

    result = task.action(*args, **kwargs)
    match result:
        case Result():
            return result
        case collections.abc.Mapping():
            return Result(result)
        case bool():
            return Result({}, changed=result)
        case None:
            return Result({})
        case _:
            raise TypeError(f'Invalid return type: {type(result)}')


def run(reg: Registry, targets: tuple[str | Callable, ...], params: dict) -> None:
    # TODO: Actually cache results.
    result_cache: dict[int, Result] = {}
    params = _prepare_params(params)
    index_layers = reg._index_layers(targets)
    print(index_layers)
    for layer in index_layers[::-1]:
        for node in layer:
            task = reg._graph[node]
            yield task.name
            result = _execute_node(node, params.get(task.name, {}), reg, result_cache)
            yield result
            result_cache[node] = result
