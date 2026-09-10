
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from io import BytesIO

st.set_page_config(page_title="Project Material Intelligence", page_icon="📦", layout="wide")
st.title("📦 Project Material Intelligence & Early-Warning Tracker")
st.caption("Pilot model: Primavera baseline + procurement follow-up + schedule-risk alerts")

@st.cache_data
def load_default():
    return pd.read_csv("sample_material_tracker.csv")

uploaded = st.sidebar.file_uploader("Upload tracker CSV", type=["csv"])
if uploaded:
    df = pd.read_csv(uploaded)
else:
    df = load_default()

date_cols = ["PR_Baseline","PO_Baseline","MR_Baseline","QC_Finish","Required_Date","Vendor_Forecast"]
for c in date_cols:
    if c in df.columns:
        df[c] = pd.to_datetime(df[c], errors="coerce")

st.sidebar.subheader("Risk settings")
yellow_days = st.sidebar.number_input("Yellow if buffer ≤ days", min_value=1, max_value=30, value=7)
red_days = st.sidebar.number_input("Red if forecast delay ≥ days", min_value=0, max_value=30, value=0)
today = st.sidebar.date_input("Evaluation date", value=date.today())

def calc_row(r):
    baseline = r.get("MR_Baseline")
    forecast = r.get("Vendor_Forecast")
    required = r.get("Required_Date")
    qc_finish = r.get("QC_Finish")

    # Use vendor forecast if entered, else baseline material receipt.
    effective = forecast if pd.notna(forecast) else baseline
    if pd.isna(effective) or pd.isna(required):
        return pd.Series(["UNKNOWN", None, None, "Missing dates", "Enter forecast/required date"])

    delivery_delay = (effective - baseline).days if pd.notna(baseline) else None
    buffer_days = (required - effective).days

    # If a QC finish is specified, penalize if effective delivery arrives after QC window.
    qc_risk = pd.notna(qc_finish) and effective > qc_finish

    if effective > required or qc_risk:
        risk = "RED"
    elif buffer_days <= yellow_days:
        risk = "YELLOW"
    else:
        risk = "GREEN"

    if risk == "RED":
        reason = "Forecast threatens QC/downstream activity"
        action = "Immediate procurement expediting + recovery/resequence review"
    elif risk == "YELLOW":
        reason = "Low remaining schedule buffer"
        action = "Obtain firm vendor commitment and follow up daily"
    else:
        reason = "Sufficient current buffer"
        action = "Continue routine monitoring"

    return pd.Series([risk, delivery_delay, buffer_days, reason, action])

calc = df.apply(calc_row, axis=1)
calc.columns = ["Risk","Delivery_Delay_Days","Buffer_to_Required_Days","Risk_Reason","Recommended_Action"]
view = pd.concat([df, calc], axis=1)

# KPIs
c1,c2,c3,c4 = st.columns(4)
c1.metric("Materials", len(view))
c2.metric("🔴 Critical", int((view["Risk"]=="RED").sum()))
c3.metric("🟡 Watch", int((view["Risk"]=="YELLOW").sum()))
c4.metric("🟢 Safe", int((view["Risk"]=="GREEN").sum()))

st.subheader("Live Material Risk Register")
risk_filter = st.multiselect("Filter risk", ["RED","YELLOW","GREEN","UNKNOWN"], default=["RED","YELLOW","GREEN"])
display_cols = [
    "Material","PO_ID","PO_Baseline","MR_Baseline","Vendor_Forecast","QC_Finish",
    "Required_Date","Downstream_Activity","Delivery_Delay_Days","Buffer_to_Required_Days",
    "Risk","Risk_Reason","Recommended_Action"
]
filtered = view[view["Risk"].isin(risk_filter)].copy()

def style_risk(v):
    if v == "RED": return "background-color:#ffcccc"
    if v == "YELLOW": return "background-color:#fff2cc"
    if v == "GREEN": return "background-color:#d9ead3"
    return ""

st.dataframe(
    filtered[display_cols].style.map(style_risk, subset=["Risk"]),
    use_container_width=True,
    hide_index=True
)

st.subheader("Update Vendor Forecasts")
edit_cols = ["Material","Vendor_Forecast","Status"]
editable = df[edit_cols].copy()
edited = st.data_editor(
    editable,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Vendor_Forecast": st.column_config.DateColumn("Vendor Forecast", format="DD-MMM-YYYY"),
        "Status": st.column_config.SelectboxColumn("Status", options=["Open","RFQ","PO Placed","In Production","Ready","Dispatched","Received"])
    }
)

if st.button("Apply edited forecasts"):
    for i in edited.index:
        df.loc[i, "Vendor_Forecast"] = pd.to_datetime(edited.loc[i, "Vendor_Forecast"], errors="coerce")
        df.loc[i, "Status"] = edited.loc[i, "Status"]
    st.session_state["updated_df"] = df
    st.success("Forecasts applied for this session. Re-run/refresh after saving CSV if needed.")

st.subheader("Early-Warning Notifications")
alerts = view[view["Risk"].isin(["RED","YELLOW"])].copy()
if alerts.empty:
    st.success("No current RED/YELLOW material risks.")
else:
    for _, r in alerts.iterrows():
        icon = "🔴" if r["Risk"]=="RED" else "🟡"
        with st.expander(f"{icon} {r['Material']} — {r['Risk']}"):
            st.write(f"**PO:** {r['PO_ID']} | **Baseline PO:** {r['PO_Baseline'].date() if pd.notna(r['PO_Baseline']) else '-'}")
            st.write(f"**Baseline receipt:** {r['MR_Baseline'].date() if pd.notna(r['MR_Baseline']) else '-'}")
            st.write(f"**Vendor forecast:** {r['Vendor_Forecast'].date() if pd.notna(r['Vendor_Forecast']) else 'Not entered'}")
            st.write(f"**Required for:** {r['Downstream_Activity']}")
            st.write(f"**Required date:** {r['Required_Date'].date() if pd.notna(r['Required_Date']) else '-'}")
            st.write(f"**Reason:** {r['Risk_Reason']}")
            st.write(f"**Recommended action:** {r['Recommended_Action']}")
            subject = f"{icon} Material Schedule Risk - {r['Material']}"
            body = (
                f"Material: {r['Material']}\n"
                f"PO: {r['PO_ID']}\n"
                f"Baseline receipt: {r['MR_Baseline'].date() if pd.notna(r['MR_Baseline']) else '-'}\n"
                f"Vendor forecast: {r['Vendor_Forecast'].date() if pd.notna(r['Vendor_Forecast']) else 'Not entered'}\n"
                f"Required date: {r['Required_Date'].date() if pd.notna(r['Required_Date']) else '-'}\n"
                f"Downstream activity: {r['Downstream_Activity']}\n"
                f"Risk: {r['Risk']}\n"
                f"Action: {r['Recommended_Action']}"
            )
            st.text_area("Notification draft", f"Subject: {subject}\n\n{body}", height=220, key=f"msg_{r['Material']}")

st.subheader("What-if Simulation")
material = st.selectbox("Choose material", view["Material"].tolist())
row = view[view["Material"]==material].iloc[0]
sim_date = st.date_input(
    "Simulated vendor delivery",
    value=(row["MR_Baseline"].date() if pd.notna(row["MR_Baseline"]) else date.today()),
    key="sim_date"
)
required = row["Required_Date"]
if pd.notna(required):
    sim_ts = pd.Timestamp(sim_date)
    sim_buffer = (required - sim_ts).days
    st.write(f"**Downstream activity:** {row['Downstream_Activity']}")
    st.write(f"**Required date:** {required.date()}")
    st.write(f"**Simulated buffer:** {sim_buffer} days")
    if sim_ts > required or (pd.notna(row["QC_Finish"]) and sim_ts > row["QC_Finish"]):
        st.error("RED — simulated delivery threatens the planned downstream activity.")
    elif sim_buffer <= yellow_days:
        st.warning("YELLOW — very limited buffer remains.")
    else:
        st.success("GREEN — sufficient buffer remains under current rule.")

# Export calculated register
export = view.copy()
for c in date_cols:
    if c in export.columns:
        export[c] = export[c].dt.strftime("%Y-%m-%d")
st.download_button(
    "Download calculated risk register (CSV)",
    data=export.to_csv(index=False).encode("utf-8"),
    file_name="material_risk_register.csv",
    mime="text/csv"
)

st.info(
    "Pilot scope: rule-based early warning. For a future AI/ML stage, historical vendor delay, "
    "material category, supplier performance, float, progress and manpower data can be used to train a predictive model."
)
