import pandas as pd
import plotly.express as px
import streamlit as st

from utils import PROGRESS_FILE, QUIZ_FILE, compute_stats, load_progress, load_quizzes


def show_dashboard():
    progress = load_progress()
    quizzes = load_quizzes(progress)

    total = len(quizzes[0]) + len(quizzes[1]) + len(quizzes[2])
    _, correct, wrong, _ = compute_stats(progress)
    unanswered = total - (correct + wrong)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total questions", total)
    col2.metric("Unanswered", unanswered)
    col3.metric("Correct", correct)
    col4.metric("Wrong", wrong)
    show_topic_distribution()
    if PROGRESS_FILE.exists() and len(PROGRESS_FILE.read_text().strip()) > 0:
        show_knowledge_gaps(topic_field="gcp_topics")
        show_knowledge_gaps(topic_field="gcp_products")
        show_knowledge_gaps(topic_field="ml_topics")
    else:
        st.info("No progress found. Answer some quizzes to see your knowledge gaps.", icon="ℹ️")

    return {"total": total, "correct": correct, "wrong": wrong, "unanswered": unanswered}


def show_topic_distribution():
    questions = pd.read_json(QUIZ_FILE, lines=True)
    df = questions[["id", "gcp_topics"]].explode("gcp_topics").rename(columns={"gcp_topics": "topic"})
    df.dropna(subset=["topic"], inplace=True)
    st.title("📚 Topic Distribution")

    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1, 2], vertical_alignment="center")

        top_n = c1.slider("Top N topics", 5, 50, 20)
        total_rows = len(df)
        unique_topics = df["topic"].nunique(dropna=True)
        c3.metric("Rows (topic tags)", f"{total_rows:,}", help="After explode(); one row per (question, topic) tag.")
        c2.metric("Unique topics", f"{unique_topics:,}")

    # --- Compute topic stats ---
    topic_stats = df["topic"].dropna().astype(str).value_counts().rename_axis("topic").reset_index(name="count")
    topic_stats["percent"] = (topic_stats["count"] / topic_stats["count"].sum()) * 100.0

    # Keep top N
    plot_df = topic_stats.head(top_n).copy()

    # Sort so largest is on top (nice for horizontal bars)
    plot_df = plot_df.sort_values("count", ascending=True)

    value_col = "count"
    value_label = "Count"

    # --- Plotly: modern horizontal bar chart ---
    fig = px.bar(
        plot_df,
        x=value_col,
        y="topic",
        orientation="h",
        text=value_col,
        hover_data={
            "topic": True,
            "count": ":,",
            "percent": ":.2f",
            value_col: False,  # avoid duplicate in hover
        },
        title="Topics (Top N)",
    )

    # Modern styling tweaks
    fig.update_traces(
        texttemplate="%{text:,}",
        textposition="outside",
        cliponaxis=False,
    )

    fig.update_layout(
        height=max(450, 28 * len(plot_df) + 200),
        margin=dict(l=20, r=20, t=70, b=20),
        template="plotly_white",
        title=dict(x=0.01, xanchor="left"),
        xaxis_title=value_label,
        yaxis_title="",
        bargap=0.25,
        hoverlabel=dict(namelength=-1),
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, zeroline=False)
    fig.update_yaxes(showgrid=False)

    st.plotly_chart(fig, width="stretch")


def show_knowledge_gaps(topic_field: str = "gcp_topics"):
    questions = pd.read_json(QUIZ_FILE, lines=True)
    progress = pd.read_json(PROGRESS_FILE, orient="index").rename(columns={0: "answer_correct"})
    questions = questions.merge(progress, left_on="id", right_index=True, how="left")

    df = questions[["id", "answer_correct", topic_field]].explode(topic_field).rename(columns={topic_field: "topic"})

    df.dropna(subset=["answer_correct"], inplace=True)

    topic_field_name = topic_field.replace("_", " ").title()
    st.title(f"🧠 Knowledge Gap per {topic_field_name}")

    # --- Compute topic stats ---
    topic_stats = (
        df.dropna(subset=["topic"])
        .assign(topic=lambda d: d["topic"].astype(str))
        .groupby("topic")
        .agg(
            attempts=("answer_correct", "count"),
            correct=("answer_correct", "sum"),
            accuracy=("answer_correct", "mean"),
        )
        .reset_index()
        .rename(columns={"ml_topics": "topic"})
    )

    # Safety: ensure boolean -> numeric
    # (If answer_correct is already bool, sum/mean work; if string, fix upstream)
    topic_stats["accuracy"] = topic_stats["accuracy"].astype(float)
    topic_stats["gap"] = 1.0 - topic_stats["accuracy"]

    # --- Controls ---
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 2.4], vertical_alignment="center")

        min_question_topic = c1.slider(
            "Min questions per topic (show topics ≥ this)",
            1,
            int(max(1, topic_stats["attempts"].max())),
            5,
            key=f"min_questions_{topic_field}",
        )
        max_accuracy = c2.slider(
            "Max accuracy (show topics ≤ this)", 0.0, 1.0, 0.80, 0.01, key=f"max_accuracy_{topic_field}"
        )
        sort_by = c3.selectbox(
            "Sort by",
            ["Gap (largest first)", "Accuracy (lowest first)", "Question count (highest first)"],
            key=f"sort_by_{topic_field}",
        )

        total_topics = int(topic_stats["topic"].nunique())
        c4.metric("Topics covered", f"{total_topics:,}")

    # --- Filter by max accuracy + min attempts ---
    plot_df = topic_stats[
        (topic_stats["attempts"] >= min_question_topic) & (topic_stats["accuracy"] <= max_accuracy)
    ].copy()

    if plot_df.empty:
        st.info("No topics match the current filters. Try increasing 'Max accuracy' or lowering 'Min questions'.")
        return
    # --- Sorting ---
    if sort_by == "Gap (largest first)":
        plot_df = plot_df.sort_values("gap", ascending=True)
        x_col = "gap"
        x_label = "Gap score (1 - accuracy)"
        title = "Weak topics (highest gap)"
        text_template = "%{x:.2f}"
    elif sort_by == "Accuracy (lowest first)":
        plot_df = plot_df.sort_values("accuracy", ascending=False)
        x_col = "accuracy"
        x_label = "Accuracy"
        title = "Low-accuracy topics"
        text_template = "%{x:.2f}"
    else:
        plot_df = plot_df.sort_values("attempts", ascending=True)
        x_col = "attempts"
        x_label = "Questions"
        title = "Topics with most attempts (filtered by accuracy)"
        text_template = "%{x:,}"

    # Keep the chart readable (show top K after sorting)
    top_k = st.slider("Max topics to display", 5, 60, 25, key=f"max_topics_{topic_field}")
    plot_df = plot_df.head(top_k).copy()

    # --- Plotly chart (modern horizontal bars) ---
    fig = px.bar(
        plot_df,
        x=x_col,
        y="topic",
        orientation="h",
        text=x_col,
        hover_data={
            "topic": True,
            "attempts": ":,",
            "correct": ":,",
            "accuracy": ":.2f",
            "gap": ":.2f",
            x_col: False,  # avoid duplicate
        },
        title=title,
    )

    fig.update_traces(
        texttemplate=text_template,
        textposition="outside",
        cliponaxis=False,
    )

    fig.update_layout(
        template="plotly_white",
        height=max(500, 28 * len(plot_df) + 220),
        margin=dict(l=20, r=20, t=70, b=20),
        title=dict(x=0.01, xanchor="left"),
        xaxis_title=x_label,
        yaxis_title="",
        bargap=0.25,
        hoverlabel=dict(namelength=-1),
    )

    fig.update_xaxes(showgrid=True, gridwidth=1, zeroline=False)
    fig.update_yaxes(showgrid=False)

    st.plotly_chart(fig, width="stretch")
