from typing import List, Optional, Dict, TypeVar, Protocol, Any
from pydantic import BaseModel


class ITreeNode(Protocol):
    id: Optional[str]
    pid: Optional[str]
    children: List['ITreeNode']

T = TypeVar('T', bound=ITreeNode)

def build_tree_generic(nodes: List[T], root_pid: Any = None) -> List[T]:
    node_dict: Dict[str, T] = {node.id: node for node in nodes if node.id is not None}
    tree: List[T] = []

    for node in nodes:
        pid = node.pid
        if node.id is not None and pid == node.id:
            # A self-parented row stays visible, but must never become its own
            # child: serializing the result would recurse until it fails.
            tree.append(node)
            continue
        # Callers pass a sentinel such as "root", while freshly created rows keep
        # an empty pid and older rows can store NULL. Both describe "no parent"
        # and used to be dropped from the tree entirely.
        if pid == root_pid or pid is None or pid == "":
            tree.append(node)
        elif pid in node_dict:
            node_dict[pid].children.append(node)

    return tree