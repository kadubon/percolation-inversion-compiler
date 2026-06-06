"""Small dependency-DAG utilities for finite certificate checking."""

from __future__ import annotations

from collections import defaultdict, deque

from pydantic import BaseModel, Field


class DependencyDAG(BaseModel):
    """A finite dependency graph with edges ``dependency -> dependent``."""

    edges: dict[str, set[str]] = Field(default_factory=dict)

    @classmethod
    def from_dependencies(cls, dependencies: dict[str, list[str] | set[str]]) -> DependencyDAG:
        graph = cls()
        for dependent, deps in dependencies.items():
            graph.add_node(dependent)
            for dep in deps:
                graph.add_edge(dep, dependent)
        return graph

    def add_node(self, node: str) -> None:
        self.edges.setdefault(node, set())

    def add_edge(self, dependency: str, dependent: str) -> None:
        self.add_node(dependency)
        self.add_node(dependent)
        self.edges[dependency].add(dependent)

    def nodes(self) -> set[str]:
        nodes = set(self.edges)
        for dependents in self.edges.values():
            nodes.update(dependents)
        return nodes

    def predecessors(self) -> dict[str, set[str]]:
        preds: dict[str, set[str]] = defaultdict(set)
        for src, dsts in self.edges.items():
            preds.setdefault(src, set())
            for dst in dsts:
                preds[dst].add(src)
        return dict(preds)

    def topological_order(self) -> list[str]:
        preds = self.predecessors()
        indegree = {node: len(preds.get(node, set())) for node in self.nodes()}
        queue: deque[str] = deque(sorted(node for node, degree in indegree.items() if degree == 0))
        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for dst in sorted(self.edges.get(node, set())):
                indegree[dst] -= 1
                if indegree[dst] == 0:
                    queue.append(dst)
        if len(order) != len(indegree):
            cycle_nodes = sorted(node for node, degree in indegree.items() if degree > 0)
            raise ValueError(f"dependency graph contains a cycle: {cycle_nodes}")
        return order

    def reachable_from(self, node: str) -> set[str]:
        seen: set[str] = set()
        queue: deque[str] = deque([node])
        while queue:
            current = queue.popleft()
            for nxt in self.edges.get(current, set()):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return seen

    def missing_dependencies(self, available: set[str]) -> dict[str, set[str]]:
        preds = self.predecessors()
        return {node: missing for node, deps in preds.items() if (missing := deps - available)}
