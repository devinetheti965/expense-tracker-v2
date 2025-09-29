# expense_tracker.py
import streamlit as st
import pandas as pd
import gspread
import json
import os
from google.oauth2.service_account import Credentials
from datetime import date
import matplotlib.pyplot as plt

# ---------- config ----------
CATEGORIES = ["Food", "Rent", "Travel", "Shopping", "Bills", "Entertainment", "Other"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
# ----------------------------

st.set_page_config(page_title="Expense Tracker (Google Sheets)")

st.sidebar.header("Budget")
monthly_budget = st.sidebar.number_input("Monthly budget (₹)", value=15000, step=500)

st.title("💸 Expense Tracker (Google Sheets)")

def get_creds_dict():
    # Streamlit Cloud secret
    if "gcp_service_account_json" in st.secrets:
        return json.loads(st.secrets["gcp_service_account_json"])
    # Local dev fallback
    if os.path.exists("service_account.json"):
        with open("service_account.json", "r") as f:
            return json.load(f)
    st.error("Google service account credentials not found. Add to Streamlit secrets or place service_account.json locally.")
    st.stop()

@st.cache_resource
def get_gs_client(creds_dict):
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def open_worksheet(client):
    sheet_key = st.secrets.get("gsheet_key") or os.environ.get("GSHEET_KEY")
    if not sheet_key:
        st.error("Missing 'gsheet_key' in Streamlit secrets (or set GSHEET_KEY locally).")
        st.stop()
    workbook = client.open_by_key(sheet_key)
    return workbook.sheet1

def load_df(worksheet):
    records = worksheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=["Date","Category","Description","Amount"])
    df = pd.DataFrame(records)
    if "Amount" in df.columns:
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    return df

# create client and worksheet
creds_dict = get_creds_dict()
client = get_gs_client(creds_dict)
ws = open_worksheet(client)

# --- Expense entry form ---
with st.form("expense_form", clear_on_submit=True):
    d = st.date_input("Date", value=date.today())
    category = st.selectbox("Category", CATEGORIES)
    desc = st.text_input("Description")
    amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0)
    submit = st.form_submit_button("Add Expense")
    if submit:
        row = [d.isoformat(), category, desc, float(amount)]
        ws.append_row(row, value_input_option="USER_ENTERED")
        st.success("✅ Expense added to Google Sheet")
        st.experimental_rerun()

# --- Load & show data ---
df = load_df(ws)
st.subheader("📊 All Expenses")
st.dataframe(df)

# summary
total_spent = df["Amount"].sum() if not df.empty else 0.0
remaining = monthly_budget - total_spent
st.subheader("💰 Summary")
st.write(f"**Total Spent:** ₹{total_spent:,.2f}")
st.write(f"**Remaining Budget:** ₹{remaining:,.2f}")

# category pie chart
if not df.empty:
    st.subheader("📌 Expenses by Category")
    cat_summary = df.groupby("Category")["Amount"].sum().sort_values(ascending=False)
    fig, ax = plt.subplots()
    cat_summary.plot.pie(autopct="%.1f%%", ax=ax, ylabel="")
    st.pyplot(fig)
