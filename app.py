import streamlit as st
import pandas as pd
import csv
from io import StringIO
import matplotlib.pyplot as plt

st.set_page_config(page_title="CleanSlate", page_icon="🧹", layout="wide")

# ---------- Smart CSV Loader ----------

def smart_read_csv(uploaded_file):
    uploaded_file.seek(0)
    raw = uploaded_file.read()

    for enc in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
        try:
            text = raw.decode(enc)
            sample = "\n".join(text.splitlines()[:10])
            try:
                sep = csv.Sniffer().sniff(sample).delimiter
            except:
                sep = ","
            return pd.read_csv(StringIO(text), sep=sep)
        except:
            continue
    raise ValueError("Couldn't detect CSV format.")

# ---------- UI ----------

st.title("🧹 CleanSlate")
st.caption("Upload any CSV • Analyze • Clean • Download")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:

    try:
        df = smart_read_csv(uploaded_file)

        if (
            "file" not in st.session_state
            or st.session_state.file != uploaded_file.name
        ):
            st.session_state.file = uploaded_file.name
            st.session_state.original = df.copy()
            st.session_state.clean = df.copy()

        clean_df = st.session_state.clean

        st.success("Dataset loaded.")

        # ---------- Preview ----------

        st.subheader("Preview")
        st.dataframe(clean_df.head(), use_container_width=True)

        # ---------- Dashboard ----------

        st.subheader("📊 Data Quality Dashboard")

        c1,c2,c3 = st.columns(3)

        c1.metric("Rows", f"{len(clean_df):,}")
        c2.metric("Columns", clean_df.shape[1])
        c3.metric("Missing Cells", int(clean_df.isnull().sum().sum()))

        c1.metric("Duplicates", int(clean_df.duplicated().sum()))
        c2.metric("Numeric", len(clean_df.select_dtypes(include="number").columns))
        c3.metric("Text", len(clean_df.select_dtypes(include="object").columns))

        # ---------- Smart Suggestions ----------

        st.subheader("🤖 Smart Recommendations")

        duplicate_count = clean_df.duplicated().sum()
        missing_count = clean_df.isnull().sum().sum()

        if duplicate_count > 0:
            st.warning(f"Found **{duplicate_count} duplicate rows**. Recommendation: Remove duplicates.")
        else:
            st.success("No duplicate rows detected.")

        if missing_count > 0:
            st.warning(f"Found **{missing_count} missing values**. Recommendation: Fill numeric columns with median and text columns with mode.")
        else:
            st.success("No missing values detected.")

        # ---------- Column Health ----------

        st.subheader("🔍 Column Health")

        health = pd.DataFrame({
            "Column": clean_df.columns,
            "Type": clean_df.dtypes.astype(str),
            "Missing": clean_df.isnull().sum().values,
            "Missing %": (clean_df.isnull().sum()/len(clean_df)*100).round(2).values,
            "Unique": clean_df.nunique().values
        })

        st.dataframe(health, use_container_width=True, hide_index=True)

        # ---------- Column Selector ----------

        st.subheader("🎯 Select Columns to Clean")

        text_cols = list(clean_df.select_dtypes(include="object").columns)
        numeric_cols = list(clean_df.select_dtypes(include="number").columns)

        selected_text = st.multiselect(
            "Text Columns",
            text_cols,
            default=text_cols
        )

        selected_numeric = st.multiselect(
            "Numeric Columns",
            numeric_cols,
            default=numeric_cols
        )

        # ---------- Cleaning ----------

        st.subheader("🛠 Cleaning")

        before_rows = len(clean_df)
        before_missing = clean_df.isnull().sum().sum()

        c1,c2,c3,c4 = st.columns(4)

        with c1:
            if st.button("Remove Duplicates"):
                clean_df = clean_df.drop_duplicates()
                st.session_state.clean = clean_df
                st.rerun()

        with c2:
            if st.button("Trim Spaces"):
                for col in selected_text:
                    clean_df[col] = clean_df[col].astype(str).str.strip()
                st.session_state.clean = clean_df
                st.rerun()

        with c3:
            if st.button("Fill Missing"):
                for col in selected_numeric:
                    clean_df[col] = clean_df[col].fillna(clean_df[col].median())

                for col in selected_text:
                    mode = clean_df[col].mode()
                    if not mode.empty:
                        clean_df[col] = clean_df[col].fillna(mode.iloc[0])

                st.session_state.clean = clean_df
                st.rerun()

        with c4:
            if st.button("Undo Last Cleaning"):
                st.session_state.clean = st.session_state.original.copy()
                st.rerun()

        # ---------- Cleaning Report ----------

        st.subheader("📋 Cleaning Report")

        after_rows = len(clean_df)
        after_missing = clean_df.isnull().sum().sum()

        report = pd.DataFrame({
            "Metric": [
                "Rows",
                "Missing Values",
                "Duplicate Rows"
            ],
            "Before": [
                before_rows,
                before_missing,
                st.session_state.original.duplicated().sum()
            ],
            "After": [
                after_rows,
                after_missing,
                clean_df.duplicated().sum()
            ]
        })

        st.dataframe(report, use_container_width=True, hide_index=True)

        # ---------- Charts ----------

        st.subheader("📈 Automatic Insights")

        left,right = st.columns(2)

        if text_cols:
            with left:
                fig = plt.figure(figsize=(6,4))
                clean_df[text_cols[0]].value_counts().head(10).plot(kind="bar")
                plt.title(f"Top 10 {text_cols[0]}")
                plt.xticks(rotation=45, ha="right")
                st.pyplot(fig)
                plt.close()

        if numeric_cols:
            with right:
                fig = plt.figure(figsize=(6,4))
                plt.hist(clean_df[numeric_cols[0]], bins=20)
                plt.title(f"{numeric_cols[0]} Distribution")
                st.pyplot(fig)
                plt.close()

        # ---------- Download ----------

        st.subheader("⬇ Export")

        st.download_button(
            "Download Cleaned CSV",
            clean_df.to_csv(index=False).encode("utf-8"),
            "cleaned_dataset.csv",
            "text/csv",
            use_container_width=True
        )

    except Exception as e:
        st.error(f"Error reading file: {e}")