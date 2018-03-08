"""All plugins output a TreeGrid object which must then be rendered (eithe by a GUI, or as text output, html output
or in some other form.  This module defines both the output format (:class:`TreeGrid`) and the renderer interface
which can interact with a TreeGrid to produce suitable output."""

import collections
import typing
from abc import abstractmethod, ABCMeta

from volatility.framework import validity

Column = collections.namedtuple('Column', ['index', 'name', 'type'])

RenderOption = typing.Any


class Renderer(validity.ValidityRoutines, metaclass = ABCMeta):
    """Class that defines the interface that all output renderers must support"""

    def __init__(self, options: typing.List[RenderOption]) -> None:
        """Accepts an options object to configure the renderers"""
        # FIXME: Once the config option objects are in place, put the _type_check in place

    @abstractmethod
    def get_render_options(self) -> typing.List[RenderOption]:
        """Returns a list of rendering options"""

    @abstractmethod
    def render(self, grid: 'TreeGrid') -> None:
        """Takes a grid object and renders it based on the object's preferences"""


class ColumnSortKey(metaclass = ABCMeta):
    ascending = True  # type: bool

    @abstractmethod
    def __call__(self, values: typing.List[typing.Any]) -> typing.Any:
        """The key function passed as a sort key to the TreeGrid's visit function"""


class TreeNode(collections.Sequence, metaclass = ABCMeta):
    def __init__(self, path, treegrid, parent, values):
        """Initializes the TreeNode"""

    @property
    @abstractmethod
    def values(self) -> typing.Iterable['SimpleTypes']:
        """Returns the list of values from the particular node, based on column.index"""

    @property
    @abstractmethod
    def path(self) -> str:
        """Returns a path identifying string

        This should be seen as opaque by external classes,
        Parsing of path locations based on this string are not guaranteed to remain stable.
        """

    @property
    @abstractmethod
    def parent(self) -> 'TreeNode':
        """Returns the parent node of this node or None"""

    @property
    @abstractmethod
    def path_depth(self) -> int:
        """Return the path depth of the current node"""

    @abstractmethod
    def path_changed(self, path: str, added: bool = False) -> None:
        """Updates the path based on the addition or removal of a node higher up in the tree

           This should only be called by the containing TreeGrid and expects to only be called for affected nodes.
        """


class BaseAbsentValue(object):
    """Class that represents values which are not present for some reason"""


_Type = typing.TypeVar("_Type")
ColumnsType = typing.List[typing.Tuple[str, typing.Type]]
SimpleTypes = typing.Union[typing.Type[int],
                           typing.Type[str],
                           typing.Type[float],
                           typing.Type[bytes],
                           typing.Type[BaseAbsentValue]]
VisitorSignature = typing.Callable[[TreeNode, _Type], _Type]


class TreeGrid(object, metaclass = ABCMeta):
    """Class providing the interface for a TreeGrid (which contains TreeNodes)

    The structure of a TreeGrid is designed to maintain the structure of the tree in a single object.
    For this reason each TreeNode does not hold its children, they are managed by the top level object.
    This leaves the Nodes as simple data carries and prevents them being used to manipulate the tree as a whole.
    This is a data structure, and is not expected to be modified much once created.

    Carrying the children under the parent makes recursion easier, but then every node is its own little tree
    and must have all the supporting tree functions.  It also allows for a node to be present in several different trees,
    and to create cycles.
    """

    simple_types = (int, str, float, bytes)  # type: typing.ClassVar[typing.Tuple]

    def __init__(self, columns: ColumnsType, generator: typing.Generator) -> None:
        """Constructs a TreeGrid object using a specific set of columns

        The TreeGrid itself is a root element, that can have children but no values.
        The TreeGrid does *not* contain any information about formatting,
        these are up to the renderers and plugins.

        :param columns: A list of column tuples made up of (name, type).
        :param generator: A generator that populates the tree/grid structure
        """

    @abstractmethod
    def populate(self,
                 func: VisitorSignature = None,
                 initial_accumulator: typing.Any = None) \
            -> typing.Generator[typing.Tuple[SimpleTypes, ...], None, None]:
        """Generator that returns the next available Node

           This is equivalent to a one-time visit.
        """

    @property
    @abstractmethod
    def populated(self) -> bool:
        """Indicates that population has completed and the tree may now be manipulated separately"""

    @property
    @abstractmethod
    def columns(self) -> ColumnsType:
        """Returns the available columns and their ordering and types"""

    @abstractmethod
    def children(self, node: TreeNode) -> typing.List[TreeNode]:
        """Returns the subnodes of a particular node in order"""

    @abstractmethod
    def values(self, node: TreeNode) -> typing.Tuple[SimpleTypes, ...]:
        """Returns the values for a particular node

           The values returned are mutable,
        """

    @abstractmethod
    def is_ancestor(self, node: TreeNode, descendant: TreeNode) -> bool:
        """Returns true if descendent is a child, grandchild, etc of node"""

    @abstractmethod
    def max_depth(self) -> int:
        """Returns the maximum depth of the tree"""

    @staticmethod
    def path_depth(node: TreeNode) -> int:
        """Returns the path depth of a particular node"""
        return node.path_depth

    def path_is_valid(self, node: TreeNode) -> bool:
        """Returns True is a given path is valid for this treegrid"""
        return node in self.children(node.parent)

    @abstractmethod
    def visit(self,
              node: TreeNode,
              function: VisitorSignature,
              initial_accumulator: _Type = None,
              sort_key: ColumnSortKey = None) -> None:
        """Visits all the nodes in a tree, calling function on each one.

           function should have the signature function(node, accumulator) and return new_accumulator
           If accumulators are not needed, the function must still accept a second parameter.

           The order of that the nodes are visited is always depth first, however, the order children are traversed can
           be set based on a sort_key function which should accept a node's values and return something that can be
           sorted to receive the desired order (similar to the sort/sorted key).
        """
