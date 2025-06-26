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

    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])

    # Sidebar filters
    with st.sidebar:
        st.header("Filters")
        min_date = df['Date'].min() if 'Date' in df.columns else None
        max_date = df['Date'].max() if 'Date' in df.columns else None
        if min_date and max_date:
            date_range = st.date_input("Date Range", [min_date, max_date])
        else:
            date_range = None
        channel_options = df['Channel'].unique().tolist() if 'Channel' in df.columns else []
        selected_channels = st.multiselect("Channel", channel_options, default=channel_options)
        trigger_options = df['Trigger Point'].unique().tolist() if 'Trigger Point' in df.columns else []
        selected_triggers = st.multiselect("Trigger Point", trigger_options, default=trigger_options)

    # Apply filters
    filtered_df = df.copy()
    if date_range and 'Date' in df.columns:
        filtered_df = filtered_df[
            (filtered_df['Date'] >= pd.to_datetime(date_range[0])) &
            (filtered_df['Date'] <= pd.to_datetime(date_range[1]))
        ]
    if 'Channel' in df.columns:
        filtered_df = filtered_df[filtered_df['Channel'].isin(selected_channels)]
    if 'Trigger Point' in df.columns:
        filtered_df = filtered_df[filtered_df['Trigger Point'].isin(selected_triggers)]

    has_CSAT = 'CSAT' in filtered_df.columns
    has_CES = 'CES' in filtered_df.columns
    has_NPS = 'NPS' in filtered_df.columns
    has_Star = 'Star' in filtered_df.columns

    st.subheader(f"Survey Results: {survey_type}")

    # Scorecards
    cols = st.columns(4)
    cols[0].metric("Responses", len(filtered_df))
    if has_CSAT:
        cols[1].metric("Avg CSAT", round(filtered_df['CSAT'].mean(), 2))
    if has_CES:
        cols[2].metric("Avg CES", round(filtered_df['CES'].mean(), 2))
    if has_NPS:
        promoters = filtered_df['NPS'][filtered_df['NPS'] >= 9].count()
        passives = filtered_df['NPS'][(filtered_df['NPS'] >= 7) & (filtered_df['NPS'] <= 8)].count()
        detractors = filtered_df['NPS'][filtered_df['NPS'] <= 6].count()
        total_nps = filtered_df['NPS'].count()
        tnps = ((promoters - detractors) / total_nps * 100) if total_nps else 0
        cols[3].metric("t-NPS", round(tnps, 2))
        st.write(f"Promoters: {promoters} ({promoters/total_nps:.0%}) | Passives: {passives} ({passives/total_nps:.0%}) | Detractors: {detractors} ({detractors/total_nps:.0%})")
    if has_Star:
        cols[1].metric("Avg Star Rating", round(filtered_df['Star'].mean(), 2))

    # Scores by Trigger Point + Reason Frequency
    st.markdown("### Scores by Trigger Point")

    if 'Trigger Point' in filtered_df.columns:
        group = filtered_df.groupby('Trigger Point')
        rows = []
        for name, group_df in group:
            row = {'Trigger Point': name, 'Responses': len(group_df)}
            if has_CSAT:
                row['CSAT'] = group_df['CSAT'].mean()
            if has_CES:
                row['CES'] = group_df['CES'].mean()
            if has_NPS:
                p = group_df['NPS'][group_df['NPS'] >= 9].count()
                pa = group_df['NPS'][(group_df['NPS'] >= 7) & (group_df['NPS'] <= 8)].count()
                d = group_df['NPS'][group_df['NPS'] <= 6].count()
                total = group_df['NPS'].count()
                row['t-NPS'] = ((p - d) / total * 100) if total else 0
                row['Promoters %'] = (p / total * 100) if total else 0
                row['Passives %'] = (pa / total * 100) if total else 0
                row['Detractors %'] = (d / total * 100) if total else 0
            if has_Star:
                row['Star'] = group_df['Star'].mean()
            if 'reason' in group_df.columns:
                reason_counts = group_df['reason'].value_counts()
                for reason, count in reason_counts.items():
                    row[f"Reason: {reason}"] = count
            rows.append(row)

        summary_df = pd.DataFrame(rows)
        st.dataframe(summary_df)

    # Monthly Trends
# Monthly Trends
st.markdown("### Trend Over Time")

if 'Date' in filtered_df.columns:
    filtered_df['Month'] = filtered_df['Date'].dt.to_period('M').dt.to_timestamp()

    agg_dict = {}
    if has_CSAT:
        agg_dict['CSAT'] = 'mean'
    if has_CES:
        agg_dict['CES'] = 'mean'
    if has_Star:
        agg_dict['Star'] = 'mean'

    monthly = filtered_df.groupby('Month').agg(agg_dict).reset_index() if agg_dict else pd.DataFrame({'Month': []})

    # NPS metrics
    if has_NPS:
        monthly_nps = filtered_df.groupby('Month').apply(
            lambda g: pd.Series({
                'Promoters %': (g['NPS'] >= 9).sum() / len(g) * 100 if len(g) else 0,
                'Passives %': ((g['NPS'] >= 7) & (g['NPS'] <= 8)).sum() / len(g) * 100 if len(g) else 0,
                'Detractors %': (g['NPS'] <= 6).sum() / len(g) * 100 if len(g) else 0,
                't-NPS': (((g['NPS'] >= 9).sum() - (g['NPS'] <= 6).sum()) / len(g) * 100) if len(g) else 0
            })
        ).reset_index()
        monthly = pd.merge(monthly, monthly_nps, on='Month', how='outer')

    if not monthly.empty:
        for col in monthly.columns:
            if col != 'Month':
                fig = px.line(monthly, x='Month', y=col, title=f"{col} over Time", markers=True)
                st.plotly_chart(fig, use_container_width=True)


    # Reasons / Improvements
    st.markdown("### Reasons / Improvement Points Frequency")

    if 'reason' in filtered_df.columns:
        reason_counts = filtered_df['reason'].value_counts().reset_index()
        reason_counts.columns = ['Reason', 'Count']
        fig = px.bar(reason_counts, x='Reason', y='Count', title="Frequency of Reasons Selected")
        st.plotly_chart(fig, use_container_width=True)

    if 'Improvement points' in filtered_df.columns:
        improvement_counts = filtered_df['Improvement points'].value_counts().reset_index()
        improvement_counts.columns = ['Improvement Point', 'Count']
        fig = px.bar(improvement_counts, x='Improvement Point', y='Count', title="Frequency of Improvement Points Selected")
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Please upload an Excel file to start.")
