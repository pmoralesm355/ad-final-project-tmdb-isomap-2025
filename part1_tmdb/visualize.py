from __future__ import annotations
import os, csv
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()  # lee .env

def load_graph(base: Path) -> nx.Graph:
    nodes_path = base / "out" / "nodes.csv"
    edges_path = base / "out" / "edges.csv"
    if not nodes_path.exists() or not edges_path.exists():
        raise SystemExit(f"Faltan CSV: {nodes_path.name} / {edges_path.name}")
    G = nx.Graph()
    with nodes_path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            G.add_node(int(r["id"]), label=r["name"])
    with edges_path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            G.add_edge(int(r["source"]), int(r["target"]),
                       label=r.get("label_last_movie", ""))
    return G

def short(s: str | None, n: int = 28) -> str:
    if not s:
        return ""
    return (s[: n - 1] + "…") if len(s) > n else s

if __name__ == "__main__":
    base = Path(__file__).parent
    out_dir = base / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    G = load_graph(base)

    # TOP_N: "all","*","max" o número; default = all
    top_env = os.getenv("TOP_N", "all").lower()
    if top_env in ("all", "*", "max"):
        top_n = len(G)
    else:
        try:
            top_n = int(top_env)
        except ValueError:
            top_n = len(G)

    deg = dict(G.degree())
    top_nodes = {n for n, _ in sorted(deg.items(), key=lambda x: x[1], reverse=True)[:top_n]}
    H = G.subgraph(top_nodes).copy()
    n = len(H)

    # Escalado auto
    k = 0.6 + min(1.0, n / 250.0)
    fig = 12 + min(16, n * 0.03)
    fnode = max(5, 9 - n // 80)
    fedge = max(4, 8 - n // 80)

    pos = nx.spring_layout(H, seed=42, k=k)

    plt.figure(figsize=(fig, fig))
    nx.draw_networkx_nodes(H, pos, node_size=120)
    nx.draw_networkx_edges(H, pos, alpha=0.25)
    nx.draw_networkx_labels(
        H, pos,
        labels={nn: H.nodes[nn].get("label", str(nn)) for nn in H},
        font_size=fnode
    )

    edge_lbls = {(u, v): short(H.edges[(u, v)].get("label", "")) for (u, v) in H.edges}
    nx.draw_networkx_edge_labels(
        H, pos, edge_labels=edge_lbls, font_size=fedge, label_pos=0.55,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none")
    )

    plt.axis("off")
    plt.tight_layout()
    plt.savefig(out_dir / "graph_matplotlib.png", dpi=300, bbox_inches="tight")
    print(f"Nodos graficados: {n} / {G.number_of_nodes()}")
    print(f"Guardado: {out_dir/'graph_matplotlib.png'}")
