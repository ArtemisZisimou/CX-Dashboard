
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
        df = df[(df['Date'] >= pd.to_datetime(date_range[0])) & (df['Date'] <= pd.to_datetime(date_range[1]))]

        for filter_col in ['APP_TYPE', 'APP_VERSION', 'Agent', 'Channel']:
            if filter_col in df.columns:
                options = xls.parse(survey_type)[filter_col].dropna().unique().tolist()
                selected = st.multiselect(filter_col, options, default=options)
                df = df[df[filter_col].isin(selected)]

    csat_cols = [col for col in df.columns if 'csat' in col.lower()]
    ces_cols = [col for col in df.columns if 'ces' in col.lower()]
    nps_cols = [col for col in df.columns if 'nps' in col.lower()]
    fixed_cols = [col for col in df.columns if 'fixed' in col.lower()]

    st.subheader(f"Survey Results: {survey_type}")
    cols = st.columns(4)
    cols[0].metric("Responses", len(df))

    if csat_cols:
        if csat_cols:
            df[csat_cols[0]] = pd.to_numeric(df[csat_cols[0]], errors='coerce')
            avg_csat = df[csat_cols[0]].mean() if csat_cols else None
            cols[1].metric("Avg CSAT", round(avg_csat, 2))
    if ces_cols:
            df[ces_cols[0]] = pd.to_numeric(df[ces_cols[0]], errors='coerce')
            avg_ces = df[ces_cols[0]].mean()
            cols[2].metric("Avg CES", round(avg_ces, 2))

    if nps_cols:
            df[nps_cols[0]] = pd.to_numeric(df[nps_cols[0]], errors='coerce')
            nps_col = nps_cols[0]
            promoters = df[nps_col][df[nps_col] >= 9].count()
            passives = df[nps_col][(df[nps_col] >= 7) & (df[nps_col] <= 8)].count()
            detractors = df[nps_col][df[nps_col] <= 6].count()
            total = df[nps_col].count()
            tnps = ((promoters - detractors) / total * 100) if total else 0
            cols[3].metric("t-NPS", round(tnps, 2))
            st.markdown(f"**Promoters**: {promoters} ({promoters/total:.1%})  |  "
                        f"**Passives**: {passives} ({passives/total:.1%})  |  "
                        f"**Detractors**: {detractors} ({detractors/total:.1%})")

    st.markdown("### Scores by EntryPoint")
    if 'EntryPoint' in df.columns:
        group = df.groupby('EntryPoint')

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

        # For Abandonment survey, include fixed_cols as frequency counts
        if "abandonment" in survey_type.lower() and fixed_cols:
            for col in fixed_cols:
                reason_freq = df.groupby('EntryPoint')[col].value_counts().unstack().fillna(0).astype(int)
                summary = pd.merge(summary, reason_freq, on='EntryPoint', how='left')

        st.dataframe(summary)

    st.markdown("### Fixed-Choice Reason Frequencies")
    for reason_col in fixed_cols:
        reason_counts = df[reason_col].value_counts().reset_index()
        reason_counts.columns = ['Reason', 'Count']
        fig = px.bar(reason_counts, x='Reason', y='Count', title=f"{reason_col} - Frequency")
    # st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Please upload an Excel file to start.")
    
