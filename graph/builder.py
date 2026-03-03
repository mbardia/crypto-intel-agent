import networkx as nx
import sys
import os
import matplotlib.pyplot as plt
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def build_graph(txs):
    G = nx.DiGraph()
    for tx in txs:
        G.add_edge(
            tx["from"],
            tx["to"],
            value=tx["value"],
            timestamp=tx["timeStamp"]
        )
    return G

def visualize_graph(G, address):
   plt.figure(figsize=(12, 8))
   pos = nx.spring_layout(G, seed=42)
   #investigated == red
   colors = ["red" if node == address.lower() else "lightblue" for node in G.nodes()]
   nx.draw(G, pos, node_color=colors, with_labels=False, 
            node_size=100, arrows=True, edge_color="gray")
    
   plt.title(f"Transaction Graph: {address[:10]}...")
   plt.savefig("graph_output.png", dpi=150, bbox_inches="tight")
   plt.show()
   print("Graph saved to graph_output.png")

'''if __name__ == "__main__":
    from tools.etherscan import get_transactions, parse_transactions
    
    raw = get_transactions("0x098B716B8Aaf21512996dC57EB0615e2383E2f96")
    txs = parse_transactions(raw)
    G = build_graph(txs)
    print(f"Nodes: {G.number_of_nodes()}")
    print(f"Edges: {G.number_of_edges()}")
    visualize_graph(G, "0x098B716B8Aaf21512996dC57EB0615e2383E2f96")'''

