# app.py
import re

import networkx as nx
import pandas as pd
import streamlit as st

# PyVis for interactive graph inside Streamlit
from pyvis.network import Network

from utils import DATA_DIR


def load_data():
    df = pd.read_json(DATA_DIR / "gcp_products.jsonl", lines=True)
    return df.to_dict(orient="records")


DATA = load_data()


# -----------------------------
# Helpers
# -----------------------------
def normalize_token(x: str) -> str:
    return re.sub(r"\s+", " ", x.strip())


def extract_ui_tags(ui_list):
    # lightweight tagging so users can filter
    tags = set()
    for ui in ui_list:
        u = ui.lower()
        if "console" in u or "web ui" in u:
            tags.add("Console / Web UI")
        if "python" in u or "sdk" in u or "client" in u:
            tags.add("SDK / Client Libraries")
        if "cli" in u or "gcloud" in u or "bq tool" in u:
            tags.add("CLI")
        if "rest" in u or "api" in u:
            tags.add("API")
        if "sql" in u:
            tags.add("SQL")
    return sorted(tags)


def to_rows(data):
    rows = []
    for p in data:
        rows.append(
            {
                "product_name": p["product_name"],
                "entity_type": p.get("entity_type", ""),
                "ui": p.get("ui", []),
                "ui_tags": extract_ui_tags(p.get("ui", [])),
                "connected_to": [normalize_token(x) for x in p.get("connected_to", [])],
                "short_description": p.get("short_description", ""),
                "use_cases": p.get("use_cases", []),
                "not_used_when": p.get("not_used_when", []),
            }
        )
    return rows


def pyvis_html(G: nx.Graph, selected=None, focus_neighbors_depth=1):
    """
    Create a PyVis HTML graph.
    - If selected is provided, we dim non-neighborhood nodes for learning focus.
    """
    net = Network(height="700px", width="100%", bgcolor="#0e1117", font_color="#e6e6e6", directed=False)
    net.barnes_hut(gravity=-20000, central_gravity=0.3, spring_length=140, spring_strength=0.03, damping=0.09)

    # neighborhood focus
    focus_set = set()
    if selected and selected in G:
        focus_set.add(selected)
        frontier = {selected}
        for _ in range(focus_neighbors_depth):
            nxt = set()
            for n in frontier:
                nxt |= set(G.neighbors(n))
            focus_set |= nxt
            frontier = nxt

    for n, attrs in G.nodes(data=True):
        node_type = attrs.get("node_type", "dependency")
        title = f"<b>{n}</b><br/>Type: {node_type}"
        if node_type == "product":
            title += f"<br/>Entity: {attrs.get('entity_type', '')}"
            shape = "box"
            size = 22
        else:
            shape = "dot"
            size = 14

        # Visual emphasis: selected + neighborhood vs dimmed
        if selected:
            if n == selected:
                opacity = 1.0
                value = 40
            elif n in focus_set:
                opacity = 0.9
                value = 22 if node_type == "product" else 16
            else:
                opacity = 0.2
                value = 10
        else:
            opacity = 0.95
            value = 22 if node_type == "product" else 14

        net.add_node(
            n,
            label=n,
            title=title,
            shape=shape,
            value=value,
            opacity=opacity,
        )

    for u, v, attrs in G.edges(data=True):
        edge_type = attrs.get("edge_type", "dependency_link")
        width = 2 if edge_type == "product_link" else 1
        net.add_edge(u, v, width=width)

    return net.generate_html()


def capability_matrix(rows):
    """
    Rows: products
    Cols: dependencies (connected_to)
    Value: True/False
    """
    deps = sorted({d for r in rows for d in r["connected_to"]})
    mat = []
    for r in rows:
        s = set(r["connected_to"])
        mat.append({"product_name": r["product_name"], **{d: (d in s) for d in deps}})
    df = pd.DataFrame(mat).set_index("product_name")
    return df


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="GCP Product Learning Map", layout="wide")

st.title("GCP Product Learning Map")
st.caption("Comparison views to learn products and understand their connections.")

rows = to_rows(DATA)

# Sidebar filters
st.sidebar.header("Filters")

product_names = sorted([r["product_name"] for r in rows])
selected_product = st.sidebar.multiselect("Focus product", options=product_names, default=product_names)


# filter rows
filtered = []
for r in rows:
    if r["product_name"] not in selected_product:
        continue

    filtered.append(r)

if not filtered:
    st.warning("No products match your filters.")
    st.stop()

tabs = st.tabs(["Product Detail", "Capability Matrix"])

with tabs[0]:
    st.subheader("Product details (learning view)")

    colA, colB = st.columns([1, 2])

    with colA:
        choice = st.selectbox("Select product", options=product_names, index=0)
    r = next(x for x in filtered if x["product_name"] == choice)

    with colB:
        st.markdown(f"### {r['product_name']}")
        st.write(r["short_description"])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### UI / Access")
        for x in r["ui"]:
            st.write(f"- {x}")
    with c2:
        st.markdown("#### Connected to")
        for x in r["connected_to"]:
            st.write(f"- {x}")
    with c3:
        st.markdown("#### Entity type")
        st.write(r["entity_type"])

    st.markdown("#### Use cases")
    for x in r["use_cases"]:
        st.write(f"- {x}")

    st.markdown("#### Not used when")
    for x in r["not_used_when"]:
        st.write(f"- {x}")

# ---- Tab 3: Capability matrix
with tabs[1]:
    st.subheader("Capability matrix (shared connections)")
    df = capability_matrix(filtered)

    # show as counts + boolean grid
    st.caption("Rows are products, columns are dependencies (connected_to). True means the product connects to it.")

    # optionally sort dependencies by popularity
    dep_counts = df.sum(axis=0).sort_values(ascending=False)
    top_n = st.slider("Show top dependencies", 5, min(50, len(dep_counts)), min(20, len(dep_counts)))
    top_cols = dep_counts.index[:top_n].tolist()

    st.dataframe(df[top_cols].astype(bool), width="stretch")

    st.markdown("##### Most shared dependencies")
    shared = dep_counts.head(10).reset_index()
    shared.columns = ["Dependency", "Connected products"]
    st.dataframe(shared, width="stretch")
