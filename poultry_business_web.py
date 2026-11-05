import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

st.set_page_config(page_title="Poultry Business Manager", page_icon="🐔", layout="wide")

st.title("🐔 Poultry Business Manager")
st.caption("Keep your poultry records organised and accessible from your browser.")

# Add these values in Streamlit's Secrets settings when deploying.
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_ANON_KEY"]
except Exception:
    st.error(
        "The database connection is not configured yet. Add SUPABASE_URL and "
        "SUPABASE_ANON_KEY in Streamlit Secrets. See SETUP_GUIDE.md."
    )
    st.stop()

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

if "auth_session" not in st.session_state:
    st.session_state.auth_session = None
if "user" not in st.session_state:
    st.session_state.user = None

def sign_out():
    try:
        supabase.auth.sign_out()
    finally:
        st.session_state.auth_session = None
        st.session_state.user = None
        st.rerun()

def show_auth():
    st.subheader("Welcome")
    login_tab, signup_tab = st.tabs(["Log in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email address", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", use_container_width=True)
        if submitted:
            if not email.strip() or not password:
                st.error("Enter your email address and password.")
            else:
                try:
                    result = supabase.auth.sign_in_with_password(
                        {"email": email.strip(), "password": password}
                    )
                    st.session_state.auth_session = result.session
                    st.session_state.user = result.user
                    st.rerun()
                except Exception:
                    st.error("Login failed. Check your details and try again.")

    with signup_tab:
        with st.form("signup_form"):
            name = st.text_input("Your name")
            email = st.text_input("Email address", key="signup_email")
            password = st.text_input("Create a password", type="password", key="signup_password")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            if not name.strip() or not email.strip() or not password:
                st.error("Complete all the fields.")
            elif password != confirm:
                st.error("The passwords do not match.")
            elif len(password) < 8:
                st.error("Use a password with at least 8 characters.")
            else:
                try:
                    result = supabase.auth.sign_up({
                        "email": email.strip(),
                        "password": password,
                        "options": {"data": {"full_name": name.strip()}}
                    })
                    if result.session and result.user:
                        st.session_state.auth_session = result.session
                        st.session_state.user = result.user
                        st.success("Account created.")
                        st.rerun()
                    else:
                        st.success(
                            "Account created. Check your email for a confirmation link, "
                            "then return here and log in."
                        )
                except Exception:
                    st.error(
                        "Could not create the account. The email may already be registered, "
                        "or the password may not meet the database provider's rules."
                    )

def save_record(user_id, values):
    payload = {
        "user_id": user_id,
        "batch": values["batch"].strip(),
        "record_date": values["record_date"].isoformat(),
        "birds": int(values["birds"]),
        "eggs": int(values["eggs"]),
        "feed_kg": float(values["feed_kg"]),
        "feed_cost": float(values["feed_cost"]),
        "eggs_sold": int(values["eggs_sold"]),
        "price_per_egg": float(values["price_per_egg"]),
    }
    supabase.table("daily_records").insert(payload).execute()

def load_records(user_id):
    response = (
        supabase.table("daily_records")
        .select("id,batch,record_date,birds,eggs,feed_kg,feed_cost,eggs_sold,price_per_egg,created_at")
        .eq("user_id", user_id)
        .order("record_date", desc=True)
        .execute()
    )
    return response.data or []

def delete_record(record_id, user_id):
    # Row-level security also checks ownership in the database.
    supabase.table("daily_records").delete().eq("id", record_id).eq("user_id", user_id).execute()

user = st.session_state.user
if user is None:
    show_auth()
    st.info("Create your own account to keep your poultry records private.")
    st.stop()

user_id = user.id
email = getattr(user, "email", "") or "Signed-in user"

with st.sidebar:
    st.write(f"**Signed in as**")
    st.write(email)
    st.button("Log out", on_click=sign_out, use_container_width=True)
    st.divider()
    st.caption("Your records are linked to your account.")

st.subheader("Add a daily record")
with st.form("record_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        batch = st.text_input("Batch name", placeholder="e.g. Layers A")
        record_date = st.date_input("Record date", value=date.today())
        birds = st.number_input("Number of birds", min_value=1, step=1, value=100)
    with col2:
        eggs = st.number_input("Eggs collected", min_value=0, step=1, value=0)
        feed_kg = st.number_input("Feed used (kg)", min_value=0.0, step=0.5, value=0.0)
        feed_cost = st.number_input("Feed cost", min_value=0.0, step=1.0, value=0.0)
    with col3:
        eggs_sold = st.number_input("Eggs sold", min_value=0, step=1, value=0)
        price_per_egg = st.number_input("Selling price per egg", min_value=0.0, step=0.01, value=0.0)
        st.caption("Use the same currency throughout your records.")
    submitted = st.form_submit_button("Save record", type="primary", use_container_width=True)

if submitted:
    if not batch.strip():
        st.error("Enter a batch name.")
    elif eggs_sold > eggs:
        st.error("Eggs sold cannot be greater than eggs collected.")
    else:
        try:
            save_record(user_id, {
                "batch": batch,
                "record_date": record_date,
                "birds": birds,
                "eggs": eggs,
                "feed_kg": feed_kg,
                "feed_cost": feed_cost,
                "eggs_sold": eggs_sold,
                "price_per_egg": price_per_egg,
            })
            st.success("Record saved to your account.")
            st.rerun()
        except Exception:
            st.error("The record could not be saved. Check the database setup and try again.")

st.divider()
st.subheader("Your poultry dashboard")

try:
    records = load_records(user_id)
except Exception:
    st.error("Could not load your records. Check the database setup guide.")
    st.stop()

if not records:
    st.info("You have not saved any records yet.")
else:
    df = pd.DataFrame(records)
    df["record_date"] = pd.to_datetime(df["record_date"]).dt.date
    df["laying_rate_%"] = (df["eggs"] / df["birds"] * 100).round(2)
    df["revenue"] = df["eggs_sold"] * df["price_per_egg"]
    df["estimated_profit"] = df["revenue"] - df["feed_cost"]

    total_eggs = int(df["eggs"].sum())
    total_sold = int(df["eggs_sold"].sum())
    total_revenue = float(df["revenue"].sum())
    total_feed_cost = float(df["feed_cost"].sum())
    total_profit = total_revenue - total_feed_cost

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Eggs collected", f"{total_eggs:,}")
    m2.metric("Eggs sold", f"{total_sold:,}")
    m3.metric("Revenue", f"{total_revenue:,.2f}")
    m4.metric("Estimated profit", f"{total_profit:,.2f}")

    st.dataframe(
        df[[
            "record_date", "batch", "birds", "eggs", "laying_rate_%",
            "feed_kg", "feed_cost", "eggs_sold", "price_per_egg",
            "revenue", "estimated_profit"
        ]],
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download my records as CSV",
        data=df.drop(columns=["created_at"], errors="ignore").to_csv(index=False).encode("utf-8"),
        file_name="my_poultry_records.csv",
        mime="text/csv",
    )

    st.subheader("Delete a record")
    options = {
        f"ID {row['id']} — {row['record_date']} — {row['batch']} ({row['eggs']} eggs)": row["id"]
        for row in records
    }
    selected_label = st.selectbox("Choose one of your records", list(options.keys()))
    if st.button("Delete selected record"):
        try:
            delete_record(options[selected_label], user_id)
            st.success("Record deleted.")
            st.rerun()
        except Exception:
            st.error("Could not delete that record.")

st.caption(
    "Estimated profit = egg revenue − feed cost only. It does not include wages, "
    "transport, medicine, electricity, packaging or other operating expenses."
)
