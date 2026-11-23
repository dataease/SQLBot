"""Guard: resource trees keep rows whose parent is unset.

``list_resource`` builds the dashboard tree with ``root_pid="root"``, but
``CreateDashboard`` defaults ``pid`` to an empty string and rows created earlier
can store NULL. ``build_tree_generic`` only accepted the exact ``root_pid`` as a
root and ignored empty parents, so those rows disappeared from the list.
A row that points at itself additionally became its own child, which makes any
recursive serialization of the result fail.
"""

from pydantic import BaseModel, Field

from common.utils.tree_utils import build_tree_generic


class Node(BaseModel):
    id: str
    pid: str | None
    children: list["Node"] = Field(default_factory=list)


def _nodes(*rows):
    return [Node(id=node_id, pid=pid) for node_id, pid in rows]


def test_rows_without_parent_id_are_roots():
    tree = build_tree_generic(_nodes(("a", "root"), ("b", ""), ("c", None)), root_pid="root")

    assert [node.id for node in tree] == ["a", "b", "c"]


def test_children_attach_to_their_parent():
    tree = build_tree_generic(_nodes(("a", "root"), ("b", "a"), ("c", "b")), root_pid="root")

    assert [node.id for node in tree] == ["a"]
    assert [node.id for node in tree[0].children] == ["b"]
    assert [node.id for node in tree[0].children[0].children] == ["c"]


def test_self_parented_row_is_not_its_own_child():
    tree = build_tree_generic(_nodes(("a", "root"), ("x", "x")), root_pid="root")

    assert [node.id for node in tree] == ["a", "x"]
    assert tree[0].children == []
    assert tree[1].children == []


def test_rows_with_unknown_parent_stay_out_of_the_tree():
    tree = build_tree_generic(_nodes(("a", "root"), ("b", "missing")), root_pid="root")

    assert [node.id for node in tree] == ["a"]