import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Finance Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .main { background: #0D1117; }
  .block-container { padding: 1.5rem 2rem; }

  /* KPI cards */
  .kpi-card {
    background: linear-gradient(135deg, #161B22 0%, #1C2333 100%);
    border: 1px solid #30363D;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
  }
  .kpi-label { color: #8B949E; font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 4px; }
  .kpi-value { color: #E6EDF3; font-family: 'JetBrains Mono', monospace; font-size: 1.6rem; font-weight: 600; }
  .kpi-delta-pos { color: #3FB950; font-size: 0.8rem; }
  .kpi-delta-neg { color: #F85149; font-size: 0.8rem; }

  /* Section headers */
  .section-title {
    color: #58A6FF;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    border-left: 3px solid #58A6FF;
    padding-left: 0.6rem;
    margin: 1.5rem 0 1rem 0;
  }

  /* Table styling */
  .dataframe thead th { background: #161B22 !important; color: #58A6FF !important; font-size: 0.75rem !important; }
  .dataframe tbody tr:hover { background: #1C2333 !important; }

  /* Sidebar */
  [data-testid="stSidebar"] { background: #0D1117; border-right: 1px solid #21262D; }
  [data-testid="stSidebar"] .stSelectbox label,
  [data-testid="stSidebar"] .stSlider label { color: #8B949E; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# ── Database setup ────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    conn = sqlite3.connect("finance.db", check_same_thread=False)
    return conn

def init_db(conn):
    c = conn.cursor()

    # Stocks master table
    c.execute("""
    CREATE TABLE IF NOT EXISTS stocks (
        ticker      TEXT PRIMARY KEY,
        company     TEXT,
        sector      TEXT,
        market_cap  REAL,
        pe_ratio    REAL,
        eps         REAL,
        revenue     REAL,
        net_profit  REAL,
        roe         REAL,
        debt_equity REAL,
        price       REAL
    )""")

    # Portfolio table
    c.execute("""
    CREATE TABLE IF NOT EXISTS portfolio (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker      TEXT,
        buy_price   REAL,
        quantity    INTEGER,
        buy_date    TEXT
    )""")

    # Seed stocks if empty
    c.execute("SELECT COUNT(*) FROM stocks")
    if c.fetchone()[0] == 0:
        seed = [
            ("RELIANCE",  "Reliance Industries",    "Energy",      19200, 28.4, 98.2,  876543, 67845, 14.2, 0.45, 2850.0),
            ("TCS",       "Tata Consultancy Svc.",   "IT",          13500, 32.1, 121.5, 225458, 46098, 52.1, 0.02, 3540.0),
            ("INFY",      "Infosys Ltd.",            "IT",           6800, 27.8,  66.3, 154670, 26428, 31.4, 0.04, 1620.0),
            ("HDFCBANK",  "HDFC Bank",               "Banking",     11200, 19.5,  88.7, 210000, 58150, 16.8, 7.20, 1740.0),
            ("ICICIBANK", "ICICI Bank",              "Banking",      7800, 17.2,  72.4, 185000, 44200, 15.3, 5.80, 1120.0),
            ("WIPRO",     "Wipro Ltd.",              "IT",           2400, 21.3,  23.1,  89230, 11456, 18.2, 0.12,  480.0),
            ("TATAMOTORS","Tata Motors",             "Auto",        2900, 11.6,  54.8, 437000, 31200, 22.4, 1.35,  860.0),
            ("MARUTI",    "Maruti Suzuki",           "Auto",        3600, 26.8, 265.0, 141000, 13700, 17.6, 0.06, 12200.0),
            ("SUNPHARMA", "Sun Pharmaceutical",      "Pharma",      2800, 33.4,  28.4,  48900, 10230, 14.5, 0.22, 1165.0),
            ("DRREDDY",   "Dr. Reddy's Lab",         "Pharma",      1040, 18.9,  62.1,  27800,  5800, 12.8, 0.31,  6250.0),
            ("ONGC",      "Oil & Natural Gas Corp.", "Energy",      2600,  7.8,  22.6, 612000, 40120,  9.4, 0.54,  265.0),
            ("BHARTIARTL","Bharti Airtel",           "Telecom",     5400, 58.2,  21.4, 141000, 12350, 10.2, 2.10, 1440.0),
            ("NESTLEIND", "Nestle India",            "FMCG",        2200, 72.5, 297.0,  19800,  7140, 98.3, 0.00, 2830.0),
            ("HINDUNILVR","Hindustan Unilever",      "FMCG",        5800, 58.8,  43.2,  59700, 10300, 21.5, 0.00, 2470.0),
            ("LT",        "Larsen & Toubro",         "Infra",       4500, 35.2,  90.4, 222000, 15210, 13.8, 1.02, 3650.0),
        ]
        c.executemany("INSERT OR IGNORE INTO stocks VALUES (?,?,?,?,?,?,?,?,?,?,?)", seed)
    conn.commit()

conn = get_connection()
init_db(conn)

# ── SQL helper ────────────────────────────────────────────────────────────────
def query(sql, params=()):
    return pd.read_sql_query(sql, conn, params=params)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Finance Dashboard")
    st.markdown("---")
    page = st.radio("Navigate", ["📈 Stock Screener", "💼 Portfolio Tracker", "🔍 SQL Explorer"])
    st.markdown("---")
    st.caption("Built with SQLite · Streamlit · Python")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — STOCK SCREENER
# ═══════════════════════════════════════════════════════════════════════════════
if page == "📈 Stock Screener":
    st.markdown("# 📈 Stock Screener")
    st.markdown("Filter NSE stocks using financial fundamentals — powered by SQL queries.")

    # ── Filters ──────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sectors = ["All"] + query("SELECT DISTINCT sector FROM stocks ORDER BY sector")["sector"].tolist()
        sector_filter = st.selectbox("Sector", sectors)
    with col2:
        max_pe = st.slider("Max P/E Ratio", 5, 100, 60)
    with col3:
        min_roe = st.slider("Min ROE (%)", 0, 50, 0)
    with col4:
        max_de = st.slider("Max Debt/Equity", 0.0, 5.0, 5.0, step=0.1)

    # ── Dynamic SQL query (show it!) ─────────────────────────────────────────
    where_clauses = ["pe_ratio <= ?", "roe >= ?", "debt_equity <= ?"]
    params = [max_pe, min_roe, max_de]
    if sector_filter != "All":
        where_clauses.append("sector = ?")
        params.append(sector_filter)

    sql = f"""
    SELECT ticker, company, sector,
           price, pe_ratio, eps, roe,
           debt_equity,
           ROUND(market_cap / 1000, 0) AS market_cap_cr
    FROM stocks
    WHERE {' AND '.join(where_clauses)}
    ORDER BY market_cap_cr DESC
    """

    with st.expander("🔍 View SQL Query Running Behind This Screen"):
        st.code(sql.strip(), language="sql")

    df = query(sql, params)

    # ── KPI row ──────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Stocks Found</div><div class="kpi-value">{len(df)}</div></div>', unsafe_allow_html=True)
    with k2:
        avg_pe = f"{df['pe_ratio'].mean():.1f}x" if len(df) else "—"
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Avg P/E</div><div class="kpi-value">{avg_pe}</div></div>', unsafe_allow_html=True)
    with k3:
        avg_roe = f"{df['roe'].mean():.1f}%" if len(df) else "—"
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Avg ROE</div><div class="kpi-value">{avg_roe}</div></div>', unsafe_allow_html=True)
    with k4:
        avg_eps = f"₹{df['eps'].mean():.1f}" if len(df) else "—"
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Avg EPS</div><div class="kpi-value">{avg_eps}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Screened Stocks</div>', unsafe_allow_html=True)
    if len(df):
        st.dataframe(df.rename(columns={
            "ticker":"Ticker","company":"Company","sector":"Sector",
            "price":"Price (₹)","pe_ratio":"P/E","eps":"EPS",
            "roe":"ROE (%)","debt_equity":"D/E","market_cap_cr":"Mkt Cap (₹Cr)"
        }), use_container_width=True, hide_index=True)

        # ── Charts ────────────────────────────────────────────────────────────
        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(df.sort_values("market_cap_cr", ascending=False),
                         x="ticker", y="market_cap_cr",
                         color="sector", title="Market Cap (₹ Crore)",
                         color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font_color="#8B949E", title_font_color="#E6EDF3")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            sector_counts = query(
                f"SELECT sector, COUNT(*) as count FROM stocks WHERE pe_ratio<=? AND roe>=? AND debt_equity<=? GROUP BY sector",
                [max_pe, min_roe, max_de])
            fig2 = px.pie(sector_counts, names="sector", values="count",
                          title="Sector Distribution",
                          color_discrete_sequence=px.colors.qualitative.Bold,
                          hole=0.45)
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#8B949E", title_font_color="#E6EDF3")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No stocks match your filters. Try relaxing the criteria.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — PORTFOLIO TRACKER
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "💼 Portfolio Tracker":
    st.markdown("# 💼 Portfolio Tracker")

    # ── Add position form ─────────────────────────────────────────────────────
    with st.expander("➕ Add New Position", expanded=False):
        tickers = query("SELECT ticker FROM stocks ORDER BY ticker")["ticker"].tolist()
        col1, col2, col3, col4 = st.columns(4)
        with col1: pick = st.selectbox("Stock", tickers)
        with col2: qty = st.number_input("Quantity", min_value=1, value=10)
        with col3: buy_px = st.number_input("Buy Price (₹)", min_value=1.0, value=100.0)
        with col4: buy_dt = st.date_input("Buy Date", value=date.today())

        if st.button("Add to Portfolio", type="primary"):
            conn.execute("INSERT INTO portfolio (ticker, buy_price, quantity, buy_date) VALUES (?,?,?,?)",
                         (pick, buy_px, qty, str(buy_dt)))
            conn.commit()
            st.success(f"Added {qty} shares of {pick} at ₹{buy_px}")
            st.rerun()

    # ── Portfolio SQL join ────────────────────────────────────────────────────
    portfolio_sql = """
    SELECT p.id, p.ticker, s.company, s.sector,
           p.quantity, p.buy_price,
           s.price AS current_price,
           ROUND(p.quantity * p.buy_price, 2)       AS invested,
           ROUND(p.quantity * s.price, 2)            AS current_value,
           ROUND((s.price - p.buy_price) * p.quantity, 2) AS pnl,
           ROUND(((s.price - p.buy_price) / p.buy_price) * 100, 2) AS pnl_pct,
           p.buy_date
    FROM portfolio p
    JOIN stocks s ON p.ticker = s.ticker
    ORDER BY current_value DESC
    """

    with st.expander("🔍 SQL Query Behind Portfolio"):
        st.code(portfolio_sql.strip(), language="sql")

    pf = query(portfolio_sql)

    if len(pf) == 0:
        st.info("Your portfolio is empty. Add positions above.")
    else:
        # KPIs
        total_invested = pf["invested"].sum()
        total_value    = pf["current_value"].sum()
        total_pnl      = pf["pnl"].sum()
        pnl_pct        = ((total_value - total_invested) / total_invested) * 100

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">Total Invested</div><div class="kpi-value">₹{total_invested:,.0f}</div></div>', unsafe_allow_html=True)
        with k2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">Current Value</div><div class="kpi-value">₹{total_value:,.0f}</div></div>', unsafe_allow_html=True)
        with k3:
            delta_cls = "kpi-delta-pos" if total_pnl >= 0 else "kpi-delta-neg"
            sign = "▲" if total_pnl >= 0 else "▼"
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">Unrealised P&L</div><div class="kpi-value">₹{total_pnl:,.0f}</div><div class="{delta_cls}">{sign} {abs(pnl_pct):.2f}%</div></div>', unsafe_allow_html=True)
        with k4:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">Positions</div><div class="kpi-value">{len(pf)}</div></div>', unsafe_allow_html=True)

        # Table
        st.markdown('<div class="section-title">Holdings</div>', unsafe_allow_html=True)
        display_pf = pf.drop(columns=["id"]).rename(columns={
            "ticker":"Ticker","company":"Company","sector":"Sector",
            "quantity":"Qty","buy_price":"Buy ₹","current_price":"CMP ₹",
            "invested":"Invested","current_value":"Value","pnl":"P&L","pnl_pct":"P&L %","buy_date":"Date"
        })
        st.dataframe(display_pf, use_container_width=True, hide_index=True)

        # Charts
        c1, c2 = st.columns(2)
        with c1:
            fig = px.pie(pf, names="ticker", values="current_value",
                         title="Portfolio Allocation", hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#8B949E", title_font_color="#E6EDF3")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.bar(pf, x="ticker", y="pnl", color="pnl",
                          color_continuous_scale=["#F85149","#3FB950"],
                          title="P&L per Position (₹)")
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font_color="#8B949E", title_font_color="#E6EDF3", coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        # Delete row
        st.markdown('<div class="section-title">Remove Position</div>', unsafe_allow_html=True)
        del_id = st.selectbox("Select row ID to remove", pf["id"].tolist())
        if st.button("Remove Position", type="secondary"):
            conn.execute("DELETE FROM portfolio WHERE id=?", (del_id,))
            conn.commit()
            st.success("Removed.")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — SQL EXPLORER
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 SQL Explorer":
    st.markdown("# 🔍 SQL Explorer")
    st.markdown("Write and run any SQL query directly on the finance database. Great for learning!")

    st.markdown('<div class="section-title">Database Schema</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.code("""-- stocks table
SELECT ticker, company, sector,
       market_cap, pe_ratio, eps,
       revenue, net_profit, roe,
       debt_equity, price
FROM stocks""", language="sql")
    with c2:
        st.code("""-- portfolio table
SELECT id, ticker, buy_price,
       quantity, buy_date
FROM portfolio""", language="sql")

    st.markdown('<div class="section-title">Run a Query</div>', unsafe_allow_html=True)

    presets = {
        "-- Choose a preset --": "",
        "Top 5 by ROE": "SELECT ticker, company, roe FROM stocks ORDER BY roe DESC LIMIT 5",
        "Low PE stocks (< 20)": "SELECT ticker, company, pe_ratio, eps FROM stocks WHERE pe_ratio < 20 ORDER BY pe_ratio",
        "Sector avg PE & ROE": "SELECT sector, ROUND(AVG(pe_ratio),1) AS avg_pe, ROUND(AVG(roe),1) AS avg_roe FROM stocks GROUP BY sector ORDER BY avg_pe",
        "Debt-free stocks": "SELECT ticker, company, sector, debt_equity FROM stocks WHERE debt_equity < 0.1 ORDER BY roe DESC",
        "IT sector overview": "SELECT ticker, company, price, pe_ratio, roe FROM stocks WHERE sector='IT'",
        "Portfolio P&L summary": "SELECT p.ticker, s.price - p.buy_price AS gain_per_share, p.quantity, ROUND((s.price - p.buy_price)*p.quantity,2) AS pnl FROM portfolio p JOIN stocks s ON p.ticker=s.ticker",
    }

    preset_choice = st.selectbox("Load a preset query:", list(presets.keys()))
    default_sql = presets[preset_choice] if preset_choice != "-- Choose a preset --" else "SELECT * FROM stocks LIMIT 5"

    user_sql = st.text_area("Write your SQL:", value=default_sql, height=120)

    if st.button("▶ Run Query", type="primary"):
        try:
            result = query(user_sql)
            st.success(f"{len(result)} rows returned")
            st.dataframe(result, use_container_width=True, hide_index=True)
            if len(result) > 0 and result.select_dtypes(include="number").columns.tolist():
                num_col = result.select_dtypes(include="number").columns[0]
                if "ticker" in result.columns or "company" in result.columns:
                    label_col = "ticker" if "ticker" in result.columns else result.columns[0]
                    fig = px.bar(result, x=label_col, y=num_col, title=f"{num_col} by {label_col}",
                                 color_discrete_sequence=["#58A6FF"])
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                      font_color="#8B949E", title_font_color="#E6EDF3")
                    st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"SQL Error: {e}")
