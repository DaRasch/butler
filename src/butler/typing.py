import typing
from types import ModuleType

AnyPath = str
if typing.TYPE_CHECKING:
    from _typeshed import AnyPath

__all__ = ['ModuleType', 'AnyPath']
