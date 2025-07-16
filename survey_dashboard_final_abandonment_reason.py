
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Survey Dashboard", layout="wide")
st.title("📊 Customer Experience Dashboard")

uploaded_file = st.file_uploader("Upload your survey Excel file", type=["xlsx"])

if uploaded_file:
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    survey_type = st.selectbox("Select Survey Type", sheet_names)
    df = xls.parse(survey_type)

    if 'timestamp' in df.columns:
        df['Date'] = pd.to_datetime(df['timestamp'])
    else:
        st.warning("No 'timestamp' column found in dataset.")
        st.stop()

    ignore_columns = [col for col in df.columns if 'open_text' in col or 'SurveyID' in col]
    df = df.drop(columns=ignore_columns, errors='ignore')

    with st.sidebar:
        st.header("Filters")
        date_range = st.date_input("Date Range", [df['Date'].min(), df['Date'].max()])

        selected_filters = {}
        for filter_col in ['Channel', 'APP_TYPE', 'APP_VERSION', 'Agent']:
            if filter_col in df.columns:
                df[filter_col] = df[filter_col].astype(str).str.strip()
                options = sorted(df[filter_col].dropna().unique().tolist())
                selected = st.multiselect(filter_col, options, default=options)
                selected_filters[filter_col] = selected

    # Apply filters outside sidebar
    filtered_df = df[
        (df['Date'] >= pd.to_datetime(date_range[0])) &
        (df['Date'] <= pd.to_datetime(date_range[1]))
    ]
    for col, selected_values in selected_filters.items():
        filtered_df = filtered_df[filtered_df[col].isin(selected_values)]

    csat_cols = [col for col in filtered_df.columns if 'csat' in col.lower()]
    ces_cols = [col for col in filtered_df.columns if 'ces' in col.lower()]
    nps_cols = [col for col in filtered_df.columns if 'nps' in col.lower()]
    fixed_cols = [col for col in filtered_df.columns if 'fixed' in col.lower()]

    st.subheader(f"Survey Results: {survey_type}")
    cols = st.columns(4)
    cols[0].metric("Responses", len(filtered_df))

    if csat_cols:
        filtered_df[csat_cols[0]] = pd.to_numeric(filtered_df[csat_cols[0]], errors='coerce')
        avg_csat = filtered_df[csat_cols[0]].mean() if csat_cols else None
        cols[1].metric("Avg CSAT", round(avg_csat, 2) if avg_csat else "N/A")

    if ces_cols:
        filtered_df[ces_cols[0]] = pd.to_numeric(filtered_df[ces_cols[0]], errors='coerce')
        avg_ces = filtered_df[ces_cols[0]].mean()
        cols[2].metric("Avg CES", round(avg_ces, 2) if avg_ces else "N/A")

    if nps_cols:
        filtered_df[nps_cols[0]] = pd.to_numeric(filtered_df[nps_cols[0]], errors='coerce')
        nps_col = nps_cols[0]
        promoters = filtered_df[nps_col][filtered_df[nps_col] >= 9].count()
        passives = filtered_df[nps_col][(filtered_df[nps_col] >= 7) & (filtered_df[nps_col] <= 8)].count()
        detractors = filtered_df[nps_col][filtered_df[nps_col] <= 6].count()
        total = filtered_df[nps_col].count()
        tnps = ((promoters - detractors) / total * 100) if total else 0
        cols[3].metric("t-NPS", round(tnps, 2))
        st.markdown(f"**Promoters**: {promoters} ({promoters/total:.1%})  |  "
                    f"**Passives**: {passives} ({passives/total:.1%})  |  "
                    f"**Detractors**: {detractors} ({detractors/total:.1%})")

    st.markdown("### Scores by EntryPoint")
    if 'EntryPoint' in filtered_df.columns:
        group = filtered_df.groupby('EntryPoint')

        agg_dict = {}
        if csat_cols:
            agg_dict[csat_cols[0]] = 'mean'
        if ces_cols:
            agg_dict[ces_cols[0]] = 'mean'
        if nps_cols:
            agg_dict[nps_cols[0]] = 'mean'
        agg_dict['Date'] = 'count'

        summary = group.agg(agg_dict).rename(columns={'Date': 'Responses'}).reset_index()

        if nps_cols:
            nps_col = nps_cols[0]
            breakdown = group[nps_col].apply(
                lambda g: pd.Series({
                    'Promoters %': (g >= 9).sum() / len(g) * 100 if len(g) else 0,
                    'Passives %': ((g >= 7) & (g <= 8)).sum() / len(g) * 100 if len(g) else 0,
                    'Detractors %': (g <= 6).sum() / len(g) * 100 if len(g) else 0,
                    't-NPS': ((g >= 9).sum() - (g <= 6).sum()) / len(g) * 100 if len(g) else 0
                })
            ).reset_index()
            summary = pd.merge(summary, breakdown, on='EntryPoint', how='left')

        if "abandonment" in survey_type.lower() and fixed_cols:
            for col in fixed_cols:
                reason_freq = filtered_df.groupby('EntryPoint')[col].value_counts().unstack().fillna(0).astype(int)
                summary = pd.merge(summary, reason_freq, on='EntryPoint', how='left')

        st.dataframe(summary)

    st.markdown("### Fixed-Choice Reason Frequencies")
    for reason_col in fixed_cols:
        reason_counts = filtered_df[reason_col].value_counts().reset_index()
        reason_counts.columns = ['Reason', 'Count']
        fig = px.bar(reason_counts, x='Reason', y='Count', title=f"{reason_col} - Frequency")
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Please upload an Excel file to start.")
