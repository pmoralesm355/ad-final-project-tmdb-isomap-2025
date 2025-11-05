from __future__ import annotations
import os, csv
from typing import List, Dict, Tuple
from dotenv import load_dotenv
from tmdb_api import TMDBAPIUtils
from graph_collab import Graph
load_dotenv()

def build_for_actor(target_name: str, start_date: str|None, end_date: str|None,
                    cast_limit: int=5, exclude_ids: List[int]|None=None)->Tuple[Graph, Dict[Tuple[int,int], str]]:
    api = TMDBAPIUtils()
    results = api.search_person(target_name)
    if not results:
        raise SystemExit(f"No se encontró persona: {target_name}")
    person = max(results, key=lambda c: c.get("popularity", 0.0))
    pid, pname = str(person["id"]), person["name"]
    print(f"Actor objetivo: {pname} (id={pid})")
    credits = api.get_movie_credits_for_person(pid, start_date, end_date)
    g = Graph(); target_id = int(pid); g.add_node((target_id, pname))
    edge_last_movie: Dict[Tuple[int,int], str] = {}
    for m in credits:
        cast = api.get_movie_cast(str(m["movie_id"]), limit=cast_limit, exclude_ids=exclude_ids or [])
        for member in cast:
            cid, cname = int(member["id"]), member["name"]
            g.add_node((cid, cname)); g.add_edge((target_id, cid))
            a,b = (target_id, cid) if target_id<cid else (cid, target_id)
            if (a,b) not in edge_last_movie: edge_last_movie[(a,b)] = m["title"]
    return g, edge_last_movie

if __name__ == "__main__":
    target = os.getenv("TARGET_PERSON_NAME", "Samuel L. Jackson")
    start_date = os.getenv("START_DATE"); end_date = os.getenv("END_DATE")
    cast_limit = int(os.getenv("CAST_LIMIT","5") or "5")
    exclude_ids = [int(x) for x in (os.getenv("EXCLUDE_IDS","").split(",") if os.getenv("EXCLUDE_IDS") else []) if x.strip().isdigit()]
    g, edge_labels = build_for_actor(target, start_date, end_date, cast_limit, exclude_ids)
    os.makedirs("out", exist_ok=True)
    with open("out/nodes.csv","w",newline="",encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["id","name"])
        for nid,name in g.nodes.items(): w.writerow([nid,name])
    with open("out/edges.csv","w",newline="",encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["source","target","label_last_movie"])
        for (a,b) in g.edges: w.writerow([a,b, edge_labels.get((a,b),"")])
    print(f"Total nodos: {g.total_nodes()} | Total aristas: {g.total_edges()}")
    print("Max degree nodes:", g.max_degree_nodes()); print("Exportado: ./out")
