import networkx as nx
import matplotlib.pyplot as plt
from map_config import nodes, edges


def generate_map_blueprint():
    G = nx.DiGraph()

    # Adăugăm nodurile cu atributele de poziție
    for node, pos in nodes.items():
        G.add_node(
            node, pos=(pos[0], -pos[1])
        )  # Inversăm Y-ul pentru că Matplotlib e invers față de Pygame

    # Adăugăm muchiile
    for u, v, weight in edges:
        G.add_edge(u, v, weight=weight)

    plt.figure(figsize=(15, 8))
    pos = nx.get_node_attributes(G, "pos")

    # Desenăm graful
    nx.draw(
        G,
        pos,
        with_labels=False,
        node_size=100,
        node_color="magenta",
        edge_color="cyan",
        width=2,
        arrows=True,
    )

    # Adăugăm etichete personalizate care includ și coordonatele
    labels = {
        node: f"{node}\n({nodes[node][0]}, {nodes[node][1]})" for node in G.nodes()
    }
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_color="black")

    plt.title("V2X Logic Graph Blueprint")
    plt.axis("equal")  # Păstrează proporțiile reale
    plt.savefig("map_logic_debug.png", dpi=300, bbox_inches="tight")
    print("Harta a fost salvată ca map_logic_debug.png!")


if __name__ == "__main__":
    generate_map_blueprint()
