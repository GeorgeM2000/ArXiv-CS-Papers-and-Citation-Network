# Updated script implementation based on the new strategy

import networkx as nx
import random
from collections import defaultdict

# === Configuration ===
PER_NODE_EDGE_LIMIT = 10
GLOBAL_EDGE_TARGET = 1_000_000
TRIANGLE_SCORE_THRESHOLD = 2  # Only add edges with score >= 2 in phase 1
LOCAL_BETWEENNESS_HOPS = 4

# === Statistics ===
stats = {
    'total_edges_before': 0,
    'total_edges_after': 0,
    'total_artificial_edges': 0,
    'nodes_augmented': 0,
    'edges_added_per_node': defaultdict(int),
    'phase1_edges': 0,
    'phase2_edges': 0,
    'triangle_candidates_considered': 0,
    'triangle_candidates_selected': 0,
    'betweenness_candidates_considered': 0,
    'betweenness_candidates_selected': 0
}

# === Load graph ===
def load_graph(path):
    G = nx.read_edgelist(path, nodetype=int)
    stats['total_edges_before'] = G.number_of_edges()
    return G

# === Get two-hop candidates ===
def get_two_hop_candidates(G, node):
    one_hop = set(G.neighbors(node))
    two_hop = set()
    for neighbor in one_hop:
        two_hop.update(G.neighbors(neighbor))
    two_hop -= one_hop
    two_hop.discard(node)
    return list(two_hop)

# === Extract k-hop neighborhood ===
def extract_k_hop_subgraph(G, node, k):
    nodes = set([node])
    frontier = set([node])
    for _ in range(k):
        next_frontier = set()
        for n in frontier:
            neighbors = set(G.neighbors(n))
            next_frontier.update(neighbors)
        frontier = next_frontier - nodes
        nodes.update(frontier)
    return G.subgraph(nodes)

# === Triangle score (Phase 1) ===
def triangle_score(G, node, candidate):
    neighbors_node = set(G.neighbors(node))
    neighbors_candidate = set(G.neighbors(candidate))
    return len(neighbors_node & neighbors_candidate)

# === Approximate local betweenness (Phase 2) ===
def local_betweenness(G, subgraph, node, candidate):
    paths = 0
    for src in subgraph:
        for dst in subgraph:
            if src != dst and node in (src, dst):
                try:
                    sp = nx.shortest_path(subgraph, source=src, target=dst)
                    if candidate in sp[1:-1]:
                        paths += 1
                except:
                    continue
    return paths

# === Augment one node ===
def augment_node(G, node, artificial_edges, used_edges):
    if stats['edges_added_per_node'][node] >= PER_NODE_EDGE_LIMIT:
        return
    candidates = get_two_hop_candidates(G, node)
    if not candidates:
        return

    sub_nodes = set([node])
    for n in G.neighbors(node):
        sub_nodes.add(n)
        sub_nodes.update(G.neighbors(n))
    subgraph = G.subgraph(sub_nodes)

    # Phase 1: Add edges based on triangle score >= 2
    scored = [(c, triangle_score(G, node, c)) for c in candidates if (node, c) not in used_edges and not G.has_edge(node, c)]
    scored = [(c, s) for c, s in scored if s >= TRIANGLE_SCORE_THRESHOLD]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Process nodes with the highest triangle scores first
    for c, score in scored:
        stats['triangle_candidates_considered'] += 1
        if stats['edges_added_per_node'][node] >= PER_NODE_EDGE_LIMIT:
            break
        if stats['total_artificial_edges'] >= GLOBAL_EDGE_TARGET - stats['total_edges_before']:
            break
        G.add_edge(node, c)
        artificial_edges.append((node, c))
        used_edges.add((node, c))
        stats['edges_added_per_node'][node] += 1
        stats['total_artificial_edges'] += 1
        stats['phase1_edges'] += 1
        stats['triangle_candidates_selected'] += 1

    # Phase 2: Add edges based on betweenness centrality if there's room
    if stats['edges_added_per_node'][node] < PER_NODE_EDGE_LIMIT:
        remaining = [c for c in candidates if (node, c) not in used_edges and not G.has_edge(node, c)]
        if not remaining:
            return
        bet_scores = [(c, local_betweenness(G, subgraph, node, c)) for c in remaining]
        bet_scores.sort(key=lambda x: x[1], reverse=True)


        bet_subgraph = extract_k_hop_subgraph(G, node, LOCAL_BETWEENNESS_HOPS)
        bet_scores = [(c, local_betweenness(G, bet_subgraph, node, c)) for c in remaining]
        stats['betweenness_candidates_considered'] += len(bet_scores)
        bet_scores = [(c, s) for c, s in bet_scores if s > 0]
        stats['betweenness_candidates_selected'] += len(bet_scores)
        bet_scores.sort(key=lambda x: x[1], reverse=True)
        
        
        
        for c, score in bet_scores:
            stats['betweenness_candidates_considered'] += 1
            if stats['edges_added_per_node'][node] >= PER_NODE_EDGE_LIMIT:
                break
            if stats['total_artificial_edges'] >= GLOBAL_EDGE_TARGET - stats['total_edges_before']:
                break
            G.add_edge(node, c)
            artificial_edges.append((node, c))
            used_edges.add((node, c))
            stats['edges_added_per_node'][node] += 1
            stats['total_artificial_edges'] += 1
            stats['phase2_edges'] += 1
            stats['betweenness_candidates_selected'] += 1

# === Main Augmentation Process ===
def augment_graph(path):
    G = load_graph(path)
    artificial_edges = []
    used_edges = set()

    # Calculate the number of high triangle score neighbors for each node
    nodes_with_triangle_scores = []
    for node in G.nodes():
        candidates = get_two_hop_candidates(G, node)
        high_triangle_score_neighbors = [c for c in candidates if triangle_score(G, node, c) >= TRIANGLE_SCORE_THRESHOLD]
        nodes_with_triangle_scores.append((node, len(high_triangle_score_neighbors)))

    # Sort nodes by the number of high triangle score neighbors (descending)
    nodes_with_triangle_scores.sort(key=lambda x: x[1], reverse=True)
    nodes = [node for node, _ in nodes_with_triangle_scores]

    for node in nodes:
        if stats['total_artificial_edges'] >= GLOBAL_EDGE_TARGET - stats['total_edges_before']:
            break
        augment_node(G, node, artificial_edges, used_edges)

    stats['total_edges_after'] = G.number_of_edges()
    stats['nodes_augmented'] = sum(1 for v in stats['edges_added_per_node'].values() if v > 0)

    return G, artificial_edges


if __name__ == "__main__":
    # === Example usage ===
    G_aug, new_edges = augment_graph("path_to_graph.txt")
    print(stats)
    nx.write_edgelist(G_aug, "augmented_graph.edgelist")