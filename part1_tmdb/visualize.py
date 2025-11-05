from __future__ import annotations
import csv, networkx as nx, matplotlib.pyplot as plt

def load_graph(nodes_path="out/nodes.csv", edges_path="out/edges.csv"):
    G = nx.Graph()
    with open(nodes_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            G.add_node(int(r["id"]), label=r["name"])
    with open(edges_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            G.add_edge(int(r["source"]), int(r["target"]), label=r.get("label_last_movie",""))
    return G

if __name__=="__main__":
    G = load_graph()
    deg = dict(G.degree())
    top = {n for n,_ in sorted(deg.items(), key=lambda x:x[1], reverse=True)[:40]}
    H = G.subgraph(top).copy()
    pos = nx.spring_layout(H, seed=42)
    plt.figure(figsize=(10,8))
    nx.draw_networkx_nodes(H,pos,node_size=120)
    nx.draw_networkx_edges(H,pos,alpha=0.3)
    nx.draw_networkx_labels(H,pos,labels={n:H.nodes[n].get("label",str(n)) for n in H},font_size=7)
    plt.axis("off"); plt.tight_layout(); plt.savefig("out/graph_matplotlib.png", dpi=200)
    print("Guardado: out/graph_matplotlib.png")
