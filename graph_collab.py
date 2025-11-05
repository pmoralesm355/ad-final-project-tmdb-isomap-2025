from __future__ import annotations
from typing import Dict, Set, Tuple

class Graph:
    def __init__(self)->None:
        self.nodes: Dict[int,str] = {}
        self.edges: Set[Tuple[int,int]] = set()
        self._degree: Dict[int,int] = {}

    def add_node(self, node: Tuple[int,str])->None:
        i,name = node
        if i not in self.nodes:
            self.nodes[i] = name
            self._degree.setdefault(i,0)

    def add_edge(self, edge: Tuple[int,int])->None:
        a,b = edge
        if a==b: return
        e = (a,b) if a<b else (b,a)
        if e not in self.edges:
            self.edges.add(e)
            self._degree[e[0]] = self._degree.get(e[0],0)+1
            self._degree[e[1]] = self._degree.get(e[1],0)+1

    def total_nodes(self)->int: return len(self.nodes)
    def total_edges(self)->int: return len(self.edges)
    def max_degree_nodes(self)->Dict[int,int]:
        if not self._degree: return {}
        m = max(self._degree.values())
        return {n:d for n,d in self._degree.items() if d==m}
