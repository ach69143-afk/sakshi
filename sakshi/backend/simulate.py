from typing import Dict, Any, Optional
import networkx as nx
from graph import get_graph_instance

SIMULATION_EDGE_THRESHOLD = 0.30

def calculate_component_metrics(G: nx.Graph) -> Dict[str, Any]:
    """Calculates connected components, largest component size, and global network efficiency."""
    n_nodes = len(G)
    if n_nodes == 0:
        return {"components": 0, "largest": 0, "efficiency": 0.0}

    comps = list(nx.connected_components(G))
    num_components = len(comps)
    largest_size = max(len(c) for c in comps) if comps else 0

    if n_nodes > 1:
        efficiency = nx.global_efficiency(G)
    else:
        efficiency = 0.0

    return {
        "components": num_components,
        "largest": largest_size,
        "efficiency": round(efficiency, 3)
    }

def simulate_node_removal(node_id: str, edge_threshold: float = SIMULATION_EDGE_THRESHOLD) -> Dict[str, Any]:
    """
    Simulates interdiction shatter by removing node_id from a copy of the graph.
    Consistently evaluates on the largest connected component of significant network interactions (threshold >= 0.30).
    Returns {before: {components, largest, efficiency}, after: {...}, delta_pct: float}.
    Never mutates the saved graph.
    """
    kg = get_graph_instance()
    G_base = kg.nx_graph

    # Extract significant interaction subgraph (edge score >= threshold)
    H = nx.Graph()
    for u, v, d in G_base.edges(data=True):
        if d.get("score", 0.0) >= edge_threshold:
            H.add_edge(u, v, **d)

    # Ensure node_id exists in H if present in G_base
    if node_id in G_base and node_id not in H:
        H.add_node(node_id)

    # Identify largest connected component containing node_id (or largest overall)
    comps = sorted(nx.connected_components(H), key=len, reverse=True)
    target_comp = None
    for c in comps:
        if node_id in c:
            target_comp = c
            break

    if not target_comp and comps:
        target_comp = comps[0]

    if target_comp:
        subG = H.subgraph(target_comp).copy()
    else:
        subG = H.copy()

    # Pre-removal baseline metrics on the connected component
    before_metrics = calculate_component_metrics(subG)

    # Remove node on copy
    if node_id in subG:
        subG.remove_node(node_id)

    # Post-removal metrics
    after_metrics = calculate_component_metrics(subG)

    b_eff = before_metrics["efficiency"]
    a_eff = after_metrics["efficiency"]
    if b_eff > 0:
        delta_pct = round(((a_eff - b_eff) / b_eff) * 100.0, 1)
    else:
        delta_pct = 0.0

    return {
        "before": before_metrics,
        "after": after_metrics,
        "delta_pct": delta_pct
    }

if __name__ == "__main__":
    kg = get_graph_instance()
    broker_id = [n["id"] for n in kg.nodes_data.values() if "suresh" in n["label"].lower()][0]
    print(f"Simulating removal of top broker: {broker_id}")
    res = simulate_node_removal(broker_id)
    print("Result:", res)
    assert res["after"]["components"] > res["before"]["components"], "Components must increase!"
    assert res["after"]["efficiency"] < res["before"]["efficiency"], "Efficiency must drop!"
    print("Self-test check 8 passed successfully!")
