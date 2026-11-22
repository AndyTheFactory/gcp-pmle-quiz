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
st.set_page_config(page_title="GCP Product Exam Guide", layout="wide")

st.title("☁️ GCP Product Exam Guide")
st.caption("Simplified reference guide for Google Cloud ML Engineer certification: core exam services, decision rules, and architecture connections.")

rows = to_rows(DATA)

# Core exam services that appear in ~90% of PMLE exam questions
CORE_SERVICES = {
    "Vertex AI",
    "BigQuery ML",
    "Dataflow",
    "BigQuery",
    "Cloud Storage",
    "Pub/Sub",
    "Vertex AI Pipelines",
    "Vertex AI Feature Store",
    "Vertex Explainable AI",
    "Vertex AI Prediction",
    "Document AI",
    "AutoML",
    "Cloud Data Loss Prevention",
    "Dataproc",
    "Cloud TPU",
    "Compute Engine",
    "Google Kubernetes Engine",
    "Cloud Run",
    "TensorBoard",
    "Kubeflow Pipelines",
    "TFX",
    "Bigtable",
    "Cloud SQL",
    "Cloud Spanner",
    "Vertex AI Workbench",
    "Colab Enterprise",
    "Model Garden",
    "Model Armor",
}

DOMAIN_MAPPING = {
    "🧠 Agent & Generative AI": [
        "Vertex AI", "Document AI", "Vision API", "Speech-to-Text API", "Recommendations AI",
        "Dialogflow", "Model Garden", "Model Armor", "Colab Enterprise"
    ],
    "⚙️ Model Development & MLOps": [
        "BigQuery ML", "AutoML", "AutoML Vision", "AutoML Vision Edge", "AutoML Video Intelligence",
        "AutoML Tables", "Vertex AI Pipelines", "Kubeflow Pipelines", "TFX", "Vertex AI Workbench",
        "Vertex ML Metadata", "Vertex AI Experiments", "TensorBoard", "LIT", "Cloud TPU", "TensorFlow Enterprise"
    ],
    "🚀 Serving, Scaling & Monitoring": [
        "Vertex AI Prediction", "Vertex AI Feature Store", "Vertex Explainable AI",
        "Cloud Run", "Google Kubernetes Engine", "Compute Engine"
    ],
    "📊 Data Engineering & Storage": [
        "BigQuery", "Dataflow", "Dataproc", "Pub/Sub", "Cloud Storage", "Cloud Data Loss Prevention",
        "Cloud Data Fusion", "Dataplex", "Bigtable", "Cloud SQL", "Cloud Spanner", "Filestore"
    ],
}


def get_product_domain(prod_name: str) -> str:
    for domain, prods in DOMAIN_MAPPING.items():
        if prod_name in prods:
            return domain
    return "⚙️ Model Development & MLOps"


# Sidebar controls
st.sidebar.header("🎯 Scope & Filters")
scope = st.sidebar.radio(
    "Catalog Scope",
    ["🌟 Core Exam Services (~28)", "🌐 Full Catalog (104)"],
    index=0,
)

if "Core Exam Services" in scope:
    scoped_rows = [r for r in rows if r["product_name"] in CORE_SERVICES]
else:
    scoped_rows = rows

selected_domain = st.sidebar.selectbox(
    "Filter by Domain",
    ["All Domains"] + list(DOMAIN_MAPPING.keys()),
    index=0,
)

if selected_domain != "All Domains":
    filtered = [r for r in scoped_rows if get_product_domain(r["product_name"]) == selected_domain]
else:
    filtered = scoped_rows

if not filtered:
    st.warning("No products match your filters.")
    st.stop()

filtered_names = sorted([r["product_name"] for r in filtered])

tabs = st.tabs(["📑 Product Detail & Exam Card", "⚖️ When to Use What (Decision Cheat Sheet)", "🔗 Architecture Dependencies"])

with tabs[0]:
    col_sel, col_stat = st.columns([2, 1], vertical_alignment="center")
    with col_sel:
        choice = st.selectbox("Select a Google Cloud Product to review:", options=filtered_names, index=0)
    with col_stat:
        st.metric("Products in view", len(filtered_names))

    r = next((x for x in filtered if x["product_name"] == choice), filtered[0])

    with st.container(border=True):
        c_title, c_badge = st.columns([3, 1], vertical_alignment="center")
        with c_title:
            st.markdown(f"### {r['product_name']}")
        with c_badge:
            st.info(f"**Type:** {r['entity_type'] or 'Service'}")

        st.markdown(f"*{r['short_description']}*")
        st.markdown("---")

        col_use, col_not = st.columns(2)
        with col_use:
            st.markdown("#### ✅ When to Choose (Exam Triggers)")
            if r["use_cases"]:
                for u in r["use_cases"]:
                    st.success(f"• {u}")
            else:
                st.caption("Standard Google Cloud ML component.")

        with col_not:
            st.markdown("#### ❌ NOT Used When (Distractor Traps)")
            if r["not_used_when"]:
                for nu in r["not_used_when"]:
                    st.error(f"• {nu}")
            else:
                st.caption("No specific contraindications recorded.")

        st.markdown("---")
        c_conn, c_ui = st.columns(2)
        with c_conn:
            st.markdown("#### 🔗 Commonly Connected To")
            if r["connected_to"]:
                st.write(", ".join([f"`{c}`" for c in r["connected_to"]]))
            else:
                st.caption("Independent component.")
        with c_ui:
            st.markdown("#### 💻 Access Methods & UI")
            if r["ui"]:
                st.write(", ".join([f"`{u}`" for u in r["ui"]]))
            else:
                st.caption("Standard Cloud Console & Client Libraries.")

with tabs[1]:
    st.subheader("⚖️ When to Use What — PMLE Decision Guide")
    st.caption("Quick-reference guide for standard exam trade-offs and decision rules.")

    with st.expander("📊 Dataflow vs. Dataproc vs. BigQuery (SQL)", expanded=True):
        st.markdown("""
| Service | Best Used When (Exam Prompt Keywords) | NOT Used When |
| :--- | :--- | :--- |
| **Dataflow** | Real-time streaming or batch distributed data preprocessing using Apache Beam; exactly-once processing; windowing. | Existing legacy Spark code; in-warehouse tabular analytics. |
| **Dataproc** | Lift-and-shift of existing Apache Spark, Hadoop, or PySpark pipelines; SparkML workflows. | Greenfield serverless streaming pipelines (prefer Dataflow). |
| **BigQuery (SQL)** | In-place tabular transformations, window functions, and `ML.TRANSFORM` directly in the data warehouse. | Unstructured data (images/video); custom C++ or Python libraries. |
""")

    with st.expander("⚙️ BigQuery ML vs. AutoML vs. Custom Containers", expanded=True):
        st.markdown("""
| Approach | Best Used When (Exam Prompt Keywords) | NOT Used When |
| :--- | :--- | :--- |
| **BigQuery ML** | Rapid modeling with SQL; tabular, ARIMA_PLUS time-series, or remote Gemini fine-tuning with zero data movement. | Custom deep learning architectures requiring custom PyTorch/TF layers. |
| **AutoML (Agent Platform)** | Tabular, vision, or NLP problems where you want high accuracy without manual feature engineering or hyperparameter tuning. | Need full control over model hyperparameters, code-level optimizations, or custom layers. |
| **Custom Containers** | Custom frameworks (PyTorch, JAX, Hugging Face, custom C++ bindings); distributed training with `TF_CONFIG`; TPU/GPU model parallelism. | Simple tabular or standard models where managed AutoML or BQML suffices with less effort. |
""")

    with st.expander("🚀 Agent Platform Endpoints vs. Batch Prediction vs. Cloud Run"):
        st.markdown("""
| Serving Pattern | Best Used When (Exam Prompt Keywords) | NOT Used When |
| :--- | :--- | :--- |
| **Agent Platform Endpoint** | Online synchronous prediction with strict latency SLA (<30ms); autoscaling; canary traffic splitting; Model Monitoring. | Asynchronous processing of millions of offline records (use Batch). |
| **Batch Prediction** | High-volume offline predictions scheduled periodically on files in Cloud Storage or BigQuery tables; zero idle cost. | Real-time interactive user-facing predictions requiring immediate response. |
| **Cloud Run** | Lightweight, CPU-based HTTP microservices packaging small models (sklearn, XGBoost); scale-to-zero cost optimization. | Heavy deep learning models requiring GPU/TPU accelerators or native Model Monitoring. |
""")

    with st.expander("📓 Colab Enterprise vs. Agent Platform Workbench"):
        st.markdown("""
| Environment | Best Used When (Exam Prompt Keywords) | NOT Used When |
| :--- | :--- | :--- |
| **Colab Enterprise** | Serverless collaborative notebooks with built-in IAM security, Gemini code completion, and native BigQuery integration. | Workloads requiring dedicated VM instances, local file systems, or root SSH access. |
| **Agent Platform Workbench** | Data scientists requiring dedicated Compute Engine instances, customizable conda environments, and persistent local disks. | Zero-maintenance collaboration across large cross-functional teams. |
""")

    with st.expander("🛡️ Cloud DLP vs. Model Armor"):
        st.markdown("""
| Security Tool | Best Used When (Exam Prompt Keywords) | NOT Used When |
| :--- | :--- | :--- |
| **Cloud DLP** | Inspecting, masking, and de-identifying PII (credit cards, names, SSNs) in datasets before ingestion/training. | Real-time LLM prompt sanitization and jailbreak defense. |
| **Model Armor** | Protecting Generative AI and LLM endpoints against prompt injection, jailbreaks, malicious prompts, and LLM data leakage. | Static dataset scanning in Cloud Storage or BigQuery. |
""")

with tabs[2]:
    st.subheader("🔗 Architecture Dependencies & Connected Services")
    df = capability_matrix(filtered)
    dep_counts = df.sum(axis=0).sort_values(ascending=False)

    st.caption("Most frequently connected services in Google Cloud ML architectures:")
    top_shared = dep_counts.head(12).reset_index()
    top_shared.columns = ["Service", "Connected Products in View"]
    st.dataframe(top_shared, width="stretch", hide_index=True)
