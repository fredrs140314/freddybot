import streamlit as st
import pandas as pd
import plotly.express as px
from backend import run_audit

st.set_page_config(page_title="SEO Anchor Text Auditor", layout="wide")

st.title("SEO Anchor Text Auditor")
st.markdown("Upload a keyword list and crawl a domain to analyze optimized anchor texts.")

# Sidebar
st.sidebar.header("Settings")

uploaded_file = st.sidebar.file_uploader(
    "Upload keyword Excel file",
    type=["xlsx"]
)

start_url = st.sidebar.text_input(
    "Domain URL",
    placeholder="https://example.com"
)

max_pages = st.sidebar.number_input(
    "Max Pages",
    min_value=10,
    max_value=5000,
    value=100,
    step=10
)

crawl_button = st.sidebar.button("Start Crawl")

if crawl_button:

    if not uploaded_file:
        st.error("Please upload an Excel file with keywords.")
        st.stop()

    if not start_url:
        st.error("Please enter a domain URL.")
        st.stop()

    with st.spinner("Running SEO anchor text audit..."):

        keywords_df, links_df, summary = run_audit(
            uploaded_file,
            start_url,
            max_pages
        )

    st.success("Audit completed successfully.")

    # Summary Metrics
    st.header("Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Links", summary["total_links"])
    col2.metric("Optimized Anchors", summary["optimized_links"])
    col3.metric("Unoptimized Anchors", summary["unoptimized_links"])
    col4.metric("Unique Keywords Found", summary["unique_keywords_found"])

    # Chart
    chart_df = pd.DataFrame({
        "Type": ["Optimized", "Unoptimized"],
        "Count": [
            summary["optimized_links"],
            summary["unoptimized_links"]
        ]
    })

    fig = px.pie(
        chart_df,
        names="Type",
        values="Count",
        title="Optimized vs Unoptimized Anchor Texts"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Detailed Results
    st.header("Detailed Link Analysis")
    st.dataframe(links_df, use_container_width=True)

    # Keyword Summary
    st.header("Keyword Summary")
    st.dataframe(keywords_df, use_container_width=True)

    # Downloads
    st.header("Export Results")

    csv_links = links_df.to_csv(index=False).encode("utf-8")
    csv_keywords = keywords_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Link Analysis CSV",
        data=csv_links,
        file_name="link_analysis.csv",
        mime="text/csv"
    )

    st.download_button(
        label="Download Keyword Summary CSV",
        data=csv_keywords,
        file_name="keyword_summary.csv",
        mime="text/csv"
    )
