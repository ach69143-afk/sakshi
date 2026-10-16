import json
import math
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple, Set, Optional
import networkx as nx

from db import get_connection, get_connection_for_case

DATA_WINDOW_LATE = "2026-09-20T00:00:00"

def pure_pagerank(G: nx.Graph, alpha: float = 0.85, max_iter: int = 100, tol: float = 1e-5, weight: str = "score") -> Dict[str, float]:
    """Pure-Python power-iteration PageRank with zero external numpy/scipy dependency."""
    nodes = list(G.nodes())
    N = len(nodes)
    if N == 0:
        return {}
    p = {n: 1.0 / N for n in nodes}
    for _ in range(max_iter):
        new_p = {n: (1.0 - alpha) / N for n in nodes}
        for u in nodes:
            neighbors = list(G.neighbors(u))
            if not neighbors:
                for v in nodes:
                    new_p[v] += alpha * p[u] / N
                continue
            total_w = sum(G[u][v].get(weight, 1.0) for v in neighbors)
            if total_w == 0:
                total_w = len(neighbors)
            for v in neighbors:
                w = G[u][v].get(weight, 1.0)
                new_p[v] += alpha * p[u] * (w / total_w)
        err = sum(abs(new_p[n] - p[n]) for n in nodes)
        p = new_p
        if err < tol:
            break
    return p

class KnowledgeGraph:
    def __init__(self):
        self.nx_graph = nx.Graph()
        self.nodes_data: Dict[str, Dict[str, Any]] = {}
        self.edges_data: Dict[str, Dict[str, Any]] = {}
        self.edge_explanations: Dict[str, Dict[str, Any]] = {}
        self.entity_details: Dict[str, Dict[str, Any]] = {}

    def build_from_db(self, conn) -> "KnowledgeGraph":
        """Reconstructs the full in-memory multi-modal network graph from sakshi.db."""
        cursor = conn.cursor()

        # 1. Load entities and person mapping
        cursor.execute("""
            SELECT em.entity_id, em.record_id, p.name, p.clean_name, p.phone_norm, p.plate_norm, p.org_id, p.aliases_json, p.address
            FROM entity_members em
            JOIN persons p ON em.record_id = p.record_id
        """)
        entity_rows = cursor.fetchall()

        rec_to_ent: Dict[str, str] = {}
        ent_members: Dict[str, List[Dict[str, Any]]] = {}
        ent_phones: Dict[str, Set[str]] = {}
        ent_plates: Dict[str, Set[str]] = {}
        ent_orgs: Dict[str, Set[str]] = {}

        for row in entity_rows:
            ent_id = row[0]
            rid = row[1]
            rec_to_ent[rid] = ent_id
            rec_dict = {
                "record_id": rid,
                "name": row[2],
                "clean_name": row[3],
                "phone_norm": row[4],
                "plate_norm": row[5],
                "org_id": row[6],
                "aliases": json.loads(row[7] or "[]"),
                "address": row[8]
            }
            ent_members.setdefault(ent_id, []).append(rec_dict)
            if row[4]:
                ent_phones.setdefault(ent_id, set()).add(row[4])
            if row[5]:
                ent_plates.setdefault(ent_id, set()).add(row[5])
            if row[6]:
                ent_orgs.setdefault(ent_id, set()).add(row[6])

        # Map all phones in phones table to entities
        cursor.execute("SELECT phone_norm, owner_record_id FROM phones")
        phone_to_ent: Dict[str, str] = {}
        unowned_phones: Set[str] = set()
        for r in cursor.fetchall():
            ph, owner = r[0], r[1]
            if owner and owner in rec_to_ent:
                phone_to_ent[ph] = rec_to_ent[owner]
            else:
                unowned_phones.add(ph)

        # Map accounts to entities
        cursor.execute("SELECT account_id, owner_record_id FROM accounts")
        acct_to_ent: Dict[str, str] = {}
        for r in cursor.fetchall():
            acct, owner = r[0], r[1]
            if owner and owner in rec_to_ent:
                acct_to_ent[acct] = rec_to_ent[owner]

        # 2. Extract Evidence Between Entities / Nodes
        # Structure: pair_key -> evidence_type -> list of items
        # pair_key is tuple of sorted (u, v)
        pair_evidence: Dict[Tuple[str, str], Dict[str, List[Dict[str, Any]]]] = {}

        def add_evidence(u: str, v: str, ev_type: str, item: Dict[str, Any]):
            if u == v:
                return
            pair = tuple(sorted([u, v]))
            pair_evidence.setdefault(pair, {}).setdefault(ev_type, []).append(item)

        # A. Calls
        cursor.execute("SELECT evidence_id, caller_norm, callee_norm, timestamp, duration_sec FROM calls")
        for r in cursor.fetchall():
            eid, caller, callee, ts, dur = r[0], r[1], r[2], r[3], r[4]
            u = phone_to_ent.get(caller, f"PH-{caller}" if caller in unowned_phones else None)
            v = phone_to_ent.get(callee, f"PH-{callee}" if callee in unowned_phones else None)
            if u and v:
                add_evidence(u, v, "calls", {
                    "evidence_id": eid,
                    "ts": ts,
                    "dur": dur,
                    "caller": caller,
                    "callee": callee
                })

        # B. Financial Transfers
        cursor.execute("SELECT evidence_id, from_account, to_account, amount_inr, timestamp, channel FROM transactions")
        for r in cursor.fetchall():
            eid, from_acc, to_acc, amt, ts, channel = r[0], r[1], r[2], r[3], r[4], r[5]
            u = acct_to_ent.get(from_acc)
            v = acct_to_ent.get(to_acc)
            if u and v:
                add_evidence(u, v, "transfers", {
                    "evidence_id": eid,
                    "ts": ts,
                    "amount": amt,
                    "channel": channel
                })

        # C. Hotel Stays and Co-travel
        cursor.execute("SELECT evidence_id, guest_record_id, companion_record_ids, hotel_location_id, checkin, checkout FROM stays")
        for r in cursor.fetchall():
            eid, guest, companions_raw, hotel, cin, cout = r[0], r[1], r[2], r[3], r[4], r[5]
            u = rec_to_ent.get(guest)
            if u and companions_raw:
                comp_ids = [c.strip() for c in companions_raw.split(";") if c.strip()]
                for comp in comp_ids:
                    v = rec_to_ent.get(comp)
                    if v:
                        add_evidence(u, v, "stays", {
                            "evidence_id": eid,
                            "hotel": hotel,
                            "ts": cin,
                            "checkin": cin,
                            "checkout": cout
                        })

        # D. Shared Vehicle / Organization
        # Shared organization between distinct entities
        ent_ids_list = list(ent_members.keys())
        for i in range(len(ent_ids_list)):
            for j in range(i + 1, len(ent_ids_list)):
                e1, e2 = ent_ids_list[i], ent_ids_list[j]
                shared_orgs = ent_orgs.get(e1, set()) & ent_orgs.get(e2, set())
                if shared_orgs:
                    for o in shared_orgs:
                        add_evidence(e1, e2, "shared_org", {
                            "evidence_id": f"ORG-{o}",
                            "org_id": o,
                            "ts": "2026-09-01T08:00:00"
                        })
                shared_plates = ent_plates.get(e1, set()) & ent_plates.get(e2, set())
                if shared_plates:
                    for p in shared_plates:
                        add_evidence(e1, e2, "shared_vehicle", {
                            "evidence_id": f"VEH-{p}",
                            "plate": p,
                            "ts": "2026-09-01T08:00:00"
                        })

        # E. FIR Sentence Co-mentions
        cursor.execute("SELECT evidence_id, doc_id, sentence_idx, text FROM firs_sentences")
        fir_sentences = cursor.fetchall()
        for r in fir_sentences:
            eid, doc_id, s_idx, text = r[0], r[1], r[2], r[3]
            # Check which entities are mentioned in this sentence
            mentioned_ents = set()
            for ent_id, members in ent_members.items():
                for m in members:
                    # check name or aliases
                    c_name = m["clean_name"]
                    if len(c_name) >= 4 and re.search(r"\b" + re.escape(c_name) + r"\b", text, re.IGNORECASE):
                        mentioned_ents.add(ent_id)
                        break
                    for alias in m["aliases"]:
                        if len(alias) >= 3 and re.search(r"\b" + re.escape(alias) + r"\b", text, re.IGNORECASE):
                            mentioned_ents.add(ent_id)
                            break
                    # check phone
                    if m["phone_norm"] and m["phone_norm"] in re.sub(r"\D", "", text):
                        mentioned_ents.add(ent_id)
                        break

            m_list = list(mentioned_ents)
            for i in range(len(m_list)):
                for j in range(i + 1, len(m_list)):
                    add_evidence(m_list[i], m_list[j], "mentions", {
                        "evidence_id": eid,
                        "text": text,
                        "ts": "2026-09-27T18:00:00"
                    })

        # 3. Build NetworkX Graph and Compute Explainable Noisy-OR Edge Scores
        G = nx.Graph()
        self.nx_graph = G
        self.edges_data = {}
        self.edge_explanations = {}

        # First add all entity nodes
        for ent_id, members in ent_members.items():
            primary = members[0]
            aliases = []
            for m in members:
                aliases.extend(m["aliases"])
                if m["name"] != primary["name"]:
                    aliases.append(m["name"])
            phone = primary["phone_norm"] or (members[1]["phone_norm"] if len(members) > 1 else "")

            node_dict = {
                "id": ent_id,
                "label": primary["name"],
                "type": "person",
                "community": 1,
                "priority": 0.5,
                "role_label": "",
                "aliases": list(dict.fromkeys(aliases)),
                "phone": f"+91 {phone}" if phone else ""
            }
            self.nodes_data[ent_id] = node_dict
            G.add_node(ent_id, **node_dict)

        # Add unowned phone nodes (like burner)
        for ph in unowned_phones:
            p_node_id = f"PH-{ph}"
            cursor.execute("SELECT sim_status, activation_date, deactivation_date FROM phones WHERE phone_norm = ?", (ph,))
            p_info = cursor.fetchone()
            sim_st = p_info[0] if p_info else ""
            p_label = f"Burner {ph}" if sim_st == "deactivated" else f"Phone {ph}"
            node_dict = {
                "id": p_node_id,
                "label": p_label,
                "type": "phone",
                "community": 1,
                "priority": 0.5,
                "role_label": "unassigned device",
                "aliases": [f"SIM-{sim_st}"],
                "phone": f"+91 {ph}"
            }
            self.nodes_data[p_node_id] = node_dict
            G.add_node(p_node_id, **node_dict)

        # Build Edges with Explainable Noisy-OR Score
        edge_counter = 1
        for (u, v), ev_dict in pair_evidence.items():
            components = []
            all_evidence_ids = []
            snippets = []
            all_timestamps = []

            # 1. Calls: w = 0.5, s = min(1, n_calls/10) * recency_factor
            calls_list = ev_dict.get("calls", [])
            if calls_list:
                n_calls = len(calls_list)
                c_eids = [x["evidence_id"] for x in calls_list]
                all_evidence_ids.extend(c_eids)
                has_recent = any(x["ts"] >= DATA_WINDOW_LATE for x in calls_list)
                recency = 1.0 if has_recent else 0.7
                s_calls = min(1.0, n_calls / 10.0) * recency
                w_calls = 0.5
                components.append({
                    "type": "calls",
                    "count": n_calls,
                    "weight": w_calls,
                    "s": round(s_calls, 2),
                    "contribution": round(w_calls * s_calls, 2),
                    "evidence_ids": c_eids[:5]
                })
                all_timestamps.extend([x["ts"] for x in calls_list if x.get("ts")])
                snippets.append({
                    "evidence_id": c_eids[0],
                    "text": f"Cellular interaction log records {n_calls} calls between identifiers on tower corridor."
                })

            # 2. Transfers: w = 0.7, s = min(1, n_txns/5)
            tx_list = ev_dict.get("transfers", [])
            if tx_list:
                n_tx = len(tx_list)
                t_eids = [x["evidence_id"] for x in tx_list]
                all_evidence_ids.extend(t_eids)
                s_tx = min(1.0, n_tx / 5.0)
                w_tx = 0.7
                components.append({
                    "type": "transfers",
                    "count": n_tx,
                    "weight": w_tx,
                    "s": round(s_tx, 2),
                    "contribution": round(w_tx * s_tx, 2),
                    "evidence_ids": t_eids[:5]
                })
                all_timestamps.extend([x["ts"] for x in tx_list if x.get("ts")])
                snippets.append({
                    "evidence_id": t_eids[0],
                    "text": f"Banking transactions ledger documents {n_tx} relay wire transfers totaling INR {sum(x.get('amount', 0) for x in tx_list):,.2f}."
                })

            # 3. Stays / Co-travel: w = 0.6, s = min(1, n/3)
            stay_list = ev_dict.get("stays", [])
            if stay_list:
                n_st = len(stay_list)
                s_eids = [x["evidence_id"] for x in stay_list]
                all_evidence_ids.extend(s_eids)
                s_stay = min(1.0, n_st / 3.0)
                w_stay = 0.6
                components.append({
                    "type": "co_travel",
                    "count": n_st,
                    "weight": w_stay,
                    "s": round(s_stay, 2),
                    "contribution": round(w_stay * s_stay, 2),
                    "evidence_ids": s_eids[:5]
                })
                all_timestamps.extend([x["ts"] for x in stay_list if x.get("ts")])
                snippets.append({
                    "evidence_id": s_eids[0],
                    "text": f"Hospitality lodging registry records {n_st} verified co-stay companion entries."
                })

            # 4. Shared Organization / Vehicle: w = 0.8, s = 1.0
            org_list = ev_dict.get("shared_org", []) + ev_dict.get("shared_vehicle", [])
            if org_list:
                n_org = len(org_list)
                o_eids = [x["evidence_id"] for x in org_list]
                all_evidence_ids.extend(o_eids)
                w_org = 0.8
                s_org = 1.0
                components.append({
                    "type": "shared_org_or_vehicle",
                    "count": n_org,
                    "weight": w_org,
                    "s": s_org,
                    "contribution": round(w_org * s_org, 2),
                    "evidence_ids": o_eids[:3]
                })
                snippets.append({
                    "evidence_id": o_eids[0],
                    "text": "Shared corporate registry registration and fleet vehicle association."
                })

            # 5. FIR Mentions: w = 0.5, s = min(1, n/2)
            men_list = ev_dict.get("mentions", [])
            if men_list:
                n_men = len(men_list)
                m_eids = [x["evidence_id"] for x in men_list]
                all_evidence_ids.extend(m_eids)
                s_men = min(1.0, n_men / 2.0)
                w_men = 0.5
                components.append({
                    "type": "fir_co_mention",
                    "count": n_men,
                    "weight": w_men,
                    "s": round(s_men, 2),
                    "contribution": round(w_men * s_men, 2),
                    "evidence_ids": m_eids[:3]
                })
                snippets.append({
                    "evidence_id": m_eids[0],
                    "text": men_list[0].get("text", "")
                })

            # Noisy-OR score computation: score = 1 - prod(1 - w_i * s_i)
            prod_val = 1.0
            for comp in components:
                prod_val *= (1.0 - comp["weight"] * comp["s"])
            edge_score = max(0.1, min(0.99, round(1.0 - prod_val, 2)))

            # Primary edge type and edge_kind
            if calls_list:
                p_type = "call"
                edge_kind = "observed"
            elif tx_list:
                p_type = "transfer"
                edge_kind = "observed"
            elif stay_list:
                p_type = "stay"
                edge_kind = "observed"
            elif men_list:
                p_type = "mention"
                edge_kind = "extracted"
            elif org_list:
                p_type = "owns"
                edge_kind = "inferred"
            else:
                p_type = "call"
                edge_kind = "observed"

            first_ts = min(all_timestamps) if all_timestamps else "2026-09-01T08:00:00"
            last_ts = max(all_timestamps) if all_timestamps else "2026-09-28T20:00:00"

            edge_id = f"E-{edge_counter:03d}"
            edge_counter += 1

            edge_dict = {
                "id": edge_id,
                "source": u,
                "target": v,
                "type": p_type,
                "score": edge_score,
                "edge_kind": edge_kind,
                "first_ts": first_ts,
                "last_ts": last_ts
            }
            self.edges_data[edge_id] = edge_dict
            G.add_edge(u, v, id=edge_id, score=edge_score, type=p_type, first_ts=first_ts, last_ts=last_ts)

            # Store explanation
            explanation = {
                "score": edge_score,
                "formula": "1 - prod(1 - w*s)",
                "components": components,
                "snippets": snippets
            }
            self.edge_explanations[f"{u}__{v}"] = explanation
            self.edge_explanations[f"{v}__{u}"] = explanation

        # 4. Louvain Communities & Centrality Prioritization
        self._compute_topological_metrics()
        self._build_entity_details()

        return self

    def _compute_topological_metrics(self):
        G = self.nx_graph
        if len(G) == 0:
            return

        # Seeded Louvain community detection
        communities = nx.community.louvain_communities(G, seed=42)
        node_to_comm = {}
        for comm_idx, comm_set in enumerate(communities, start=1):
            for n in comm_set:
                node_to_comm[n] = comm_idx

        # Compute edge distance for betweenness: high score means short distance (strong connection)
        for u, v, d in G.edges(data=True):
            d["dist"] = 1.0 / max(0.01, d.get("score", 0.5))

        # Betweenness (using edge distance) and PageRank (using edge strength)
        bw = nx.betweenness_centrality(G, weight="dist")
        pr = pure_pagerank(G, weight="score")

        max_bw = max(bw.values()) if bw else 1.0
        max_pr = max(pr.values()) if pr else 1.0

        for n in G.nodes():
            comm = node_to_comm.get(n, 1)
            neighbors = list(G.neighbors(n))
            deg = len(neighbors)

            # Cross community ratio
            if deg > 0:
                cross_count = sum(1 for neighbor in neighbors if node_to_comm.get(neighbor) != comm)
                cross_ratio = cross_count / deg
            else:
                cross_ratio = 0.0

            # Evidence diversity (number of distinct evidence types among incident edges / 5)
            incident_types = set()
            for neighbor in neighbors:
                e_data = G.get_edge_data(n, neighbor)
                if e_data and "type" in e_data:
                    incident_types.add(e_data["type"])
            diversity_norm = min(1.0, len(incident_types) / 5.0)

            bw_norm = bw.get(n, 0.0) / max_bw if max_bw > 0 else 0.0
            pr_norm = pr.get(n, 0.0) / max_pr if max_pr > 0 else 0.0

            # Priority formula from specification:
            # priority = 0.35*betweenness_norm + 0.25*pagerank_norm + 0.20*cross_community_ratio + 0.20*evidence_diversity_norm
            priority = (
                0.35 * bw_norm +
                0.25 * pr_norm +
                0.20 * cross_ratio +
                0.20 * diversity_norm
            )
            priority = round(max(0.05, min(0.99, priority)), 2)

            # Role label classification:
            # - "broker candidate" (top cross_community + betweenness)
            # - "high-volume peripheral" (high degree but low diversity/pagerank)
            # - "core member candidate"
            role_label = ""
            if deg >= 15 and diversity_norm <= 0.25:
                role_label = "high-volume peripheral"
            elif (bw_norm >= 0.70 and cross_ratio >= 0.20) or (cross_ratio >= 0.40 and bw_norm >= 0.40):
                role_label = "broker candidate"
            elif pr_norm >= 0.60 or deg >= 8:
                role_label = "core member candidate"

            # Update node dictionary
            if n in self.nodes_data:
                self.nodes_data[n]["community"] = comm
                self.nodes_data[n]["priority"] = priority
                self.nodes_data[n]["role_label"] = role_label
                self.nodes_data[n]["priority_breakdown"] = {
                    "betweenness": round(bw_norm, 2),
                    "pagerank": round(pr_norm, 2),
                    "cross_community": round(cross_ratio, 2),
                    "evidence_diversity": round(diversity_norm, 2)
                }
            if n in G.nodes:
                G.nodes[n]["betweenness"] = round(bw.get(n, 0.0), 4)
                G.nodes[n]["pagerank"] = round(pr.get(n, 0.0), 4)
                G.nodes[n]["priority"] = priority
                G.nodes[n]["role_label"] = role_label
                G.nodes[n]["community"] = comm

    def _build_entity_details(self):
        """Constructs detailed entity profiles with connections and evidence citations."""
        for n_id, n_data in self.nodes_data.items():
            connections = []
            for neighbor in self.nx_graph.neighbors(n_id):
                e_data = self.nx_graph.get_edge_data(n_id, neighbor)
                lbl = self.nodes_data.get(neighbor, {}).get("label", neighbor)
                score = e_data.get("score", 0.5) if e_data else 0.5
                connections.append({
                    "id": neighbor,
                    "label": lbl,
                    "score": score
                })
            connections.sort(key=lambda x: -x["score"])

            # Evidence entries
            evidence_list = []
            for neighbor in list(self.nx_graph.neighbors(n_id))[:4]:
                exp = self.edge_explanations.get(f"{n_id}__{neighbor}")
                if exp:
                    for comp in exp.get("components", []):
                        eid = comp["evidence_ids"][0] if comp.get("evidence_ids") else f"EV-{n_id}-01"
                        evidence_list.append({
                            "evidence_id": eid,
                            "kind": "observed",
                            "summary": f"Interaction component of type {comp['type']} (score {comp['contribution']}).",
                            "ts": "2026-09-27T18:00:00Z"
                        })

            if not evidence_list:
                evidence_list.append({
                    "evidence_id": f"PR-{n_id[-4:] if len(n_id) >= 4 else '0001'}",
                    "kind": "observed",
                    "summary": f"Primary case intelligence entity record for {n_data.get('label')}.",
                    "ts": "2026-09-01T08:00:00Z"
                })

            self.entity_details[n_id] = {
                "id": n_id,
                "label": n_data.get("label", n_id),
                "type": n_data.get("type", "person"),
                "aliases": n_data.get("aliases", []),
                "priority": n_data.get("priority", 0.5),
                "priority_breakdown": n_data.get("priority_breakdown", {
                    "betweenness": 0.5,
                    "pagerank": 0.5,
                    "cross_community": 0.5,
                    "evidence_diversity": 0.5
                }),
                "role_label": n_data.get("role_label", ""),
                "connections": connections[:10],
                "evidence": evidence_list[:8],
                "phone": n_data.get("phone", "")
            }

    def get_graph_data(self, until: Optional[str] = None) -> Dict[str, Any]:
        """Returns filtered nodes and edges for Cytoscape network view."""
        edges = list(self.edges_data.values())
        if until:
            edges = [e for e in edges if e["first_ts"] <= until]

        active_node_ids = set()
        for e in edges:
            active_node_ids.add(e["source"])
            active_node_ids.add(e["target"])

        nodes = [n for n in self.nodes_data.values() if not until or n["id"] in active_node_ids]
        return {
            "nodes": nodes,
            "edges": edges
        }

# Global per-case graph cache
GRAPH_CACHE: Dict[str, KnowledgeGraph] = {}
CURRENT_GRAPH = KnowledgeGraph()

def get_graph_instance(case_id: str = "SP-014") -> KnowledgeGraph:
    global GRAPH_CACHE, CURRENT_GRAPH
    if case_id not in GRAPH_CACHE or len(GRAPH_CACHE[case_id].nx_graph) == 0:
        conn = get_connection_for_case(case_id)
        kg = KnowledgeGraph().build_from_db(conn)
        GRAPH_CACHE[case_id] = kg
        if case_id == "SP-014":
            CURRENT_GRAPH = kg
    return GRAPH_CACHE[case_id]

def rebuild_graph(case_id: str = "SP-014") -> KnowledgeGraph:
    global GRAPH_CACHE, CURRENT_GRAPH
    conn = get_connection_for_case(case_id)
    kg = KnowledgeGraph().build_from_db(conn)
    GRAPH_CACHE[case_id] = kg
    if case_id == "SP-014":
        CURRENT_GRAPH = kg
    return kg

if __name__ == "__main__":
    conn = get_connection()
    kg = KnowledgeGraph().build_from_db(conn)
    print("Graph built:")
    print(f"  Nodes: {len(kg.nx_graph.nodes())}")
    print(f"  Edges: {len(kg.nx_graph.edges())}")
    
    # Check top nodes by priority
    sorted_nodes = sorted(kg.nodes_data.values(), key=lambda x: -x["priority"])
    print("\nTop 5 nodes by priority:")
    for n in sorted_nodes[:5]:
        print(f"  {n['id']}: {n['label']} | Priority: {n['priority']} | Role: '{n['role_label']}' | BD: {n.get('priority_breakdown')}")
