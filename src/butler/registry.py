import collections
import dataclasses
from typing import Callable, Iterable, Iterator

import rustworkx as rwx


@dataclasses.dataclass
class Task:
    """Dumb collection of task metadata."""

    name: str
    action: Callable


class Registry:
    """Task store and dependency graph."""

    def __init__(self):
        self._by_name: dict[str, int] = {}
        self._by_action: dict[Callable, int] = {}
        self._graph = rwx.PyDAG(check_cycle=True, multigraph=False)

    def _index(self, key: str | Callable) -> int:
        match key:
            case str():
                return self._by_name[key]
            case collections.abc.Callable():
                return self._by_action[key]
            case _:
                raise TypeError(key)

    def __getitem__(self, key: str | Callable) -> Task:
        return self._graph[self._index(key)]

    def __iter__(self) -> Iterator[Task]:
        yield from self._graph.nodes()

    def _index_layers(self, targets: Iterable[str | Callable]) -> list[list[int]]:
        """Sorts the sub graph starting from `targets` into layers such that
        each layer only contains nodes which do not depend on each other.

        Parameters
        ----------
        targets : Iterable[str | Callable]
            The collection of nodes to take as a starting point to create
            layers.

        Returns
        -------
        list[list[int]]
            A list of layers of independent nodes.
        """
        index_stack = [set(self._index(t) for t in targets)]
        while parent_layer := index_stack[-1]:
            child_layer = set()
            for parent in parent_layer:
                child_layer |= set(self._graph.successor_indices(parent))
            for layer in index_stack:
                layer -= child_layer
            index_stack.append(child_layer)
        index_stack.pop()
        return index_stack

    def _layers(self, targets: Iterable[str | Callable]) -> list[list[Task]]:
        """Sorts the sub graph starting from `targets` into layers such that
        each layer only contains tasks which do not depend on each other.

        Parameters
        ----------
        targets : Iterable[str | Callable]
            The collection of tasks to take as a starting point to create
            layers.

        Returns
        -------
        list[list[Task]]
            A list of layers of independent tasks.
        """
        return [[self._graph[node] for node in layer] for layer in self._index_layers(targets)]

    def register(
        self,
        name: str,
        action: Callable,
        depends: Iterable[Callable] | None = None,
        extends: Iterable[Callable] | None = None,
    ) -> Callable:
        depends = [] if depends is None else depends
        extends = [] if extends is None else extends

        if name in self._by_name:
            raise ValueError(f'Name is already registered: {name}')
        if action in self._by_action:
            raise ValueError(f'Action already registered: {action.__qualname__} ({str(action)})')
        node = self._graph.add_node(Task(name, action))
        self._by_name[name] = node
        self._by_action[action] = node
        try:
            self._graph.add_edges_from_no_data([(node, self._by_action[dep]) for dep in depends])
        except KeyError as e:
            dep = e.args[0]
            raise ValueError(f'Unregistered dependency: {dep.__qualname__} ({str(dep)})')
        try:
            self._graph.add_edges_from_no_data([(self._by_action[ext], node) for ext in extends])
        except KeyError as e:
            ext = e.args[0]
            raise ValueError(f'Unregistered hook: {ext.__qualname__} ({str(ext)})')
        return action

    def task(
        self,
        name: str = '',
        *,
        depends: Iterable[Callable] | None = None,
        extends: Iterable[Callable] | None = None,
    ) -> Callable[[Callable], Callable]:
        def closure(action: Callable) -> Callable:
            realname = name or action.__qualname__
            return self.register(realname, action, depends, extends)

        return closure
