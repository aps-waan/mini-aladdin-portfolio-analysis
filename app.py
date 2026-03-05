# app.py - Mini Aladdin: Futuristic UI + robust export (session_state)
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import io as _io

# ---------- Page config ----------
st.set_page_config(
    page_title="Mini Aladdin — Portfolio Analysis & Rebalancing",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Dark futuristic CSS ----------
st.markdown(
    """
    <style>
    :root {
      --bg: #0b0f17;
      --panel: #0f1720;
      --muted: #94a3b8;
      --accent: #00ffd5;
      --accent-2: #7b61ff;
      --danger: #ff5c7c;
      --card-shadow: 0 10px 30px rgba(11,15,23,0.6);
    }
    html, body, #root, .css-k1vhr4 {
      background: linear-gradient(180deg, #050608 0%, #071426 100%);
      color: #e6eef8;
    }
    .stApp .css-1v3fvcr { background: linear-gradient(180deg, rgba(11,15,23,0.6), rgba(4,7,12,0.6)); }
    .block-container {
  padding-top: 1rem;
  padding-bottom: 1rem;
  padding-left: 2rem;
  padding-right: 2rem;
  max-width: 1400px;
}
   .card {
  background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 14px;
  border: 1px solid rgba(255,255,255,0.03);
}
    .kpi {
      font-size: 22px;
      font-weight: 700;
      color: var(--accent);
    }
    .kpi-sub {
      font-size: 12px;
      color: var(--muted);
    }
    .muted { color: var(--muted); }
    .ticker-tag {
      display:inline-block;
      padding:6px 10px;
      border-radius:8px;
      background: rgba(255,255,255,0.03);
      margin-right:6px;
      margin-bottom:6px;
      font-size:12px;
    }
    .risk-low { color: #6ee7b7; }
    .risk-med { color: #fbbf24; }
    .risk-high { color: #ff6b6b; }
    .neon {
      color: var(--accent);
      text-shadow: 0 0 8px rgba(0,255,213,0.12), 0 0 20px rgba(123,97,255,0.06);
    }
    /* Remove Streamlit widget shadows */

div[data-testid="stMetric"] {
    box-shadow: none !important;
}

div[data-testid="stDataFrame"] {
    box-shadow: none !important;
}

div[data-testid="stTable"] {
    box-shadow: none !important;
}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Sidebar: inputs ----------
with st.sidebar:
    st.markdown("<h2 class='neon'>Mini Aladdin</h2>", unsafe_allow_html=True)
    st.write("Stocks + Crypto Dashboard")
    st.markdown("---")
    st.subheader("Portfolio Input")
    stock_input = st.text_input("Stocks (comma separated)", value="AAPL, MSFT")
    crypto_input = st.text_input("Crypto (comma separated)", value="BTC, ETH")
    total_invest = st.number_input("Total invest amount (currency)", min_value=0.0, value=10000.0, step=1000.0)
    st.markdown("**Asset class target**")
    crypto_pct = st.slider("Crypto target %", min_value=0, max_value=100, value=20, step=1)
    period = st.selectbox("History period", ["3mo", "6mo", "1y" , "5y" , "10y" , "max"], index=0)
    st.markdown("---")
    st.subheader("Scenario / Quick Tools")
    stock_shock = st.slider("Stock shock %", -100, 100, -20, step=1)
    crypto_shock = st.slider("Crypto shock %", -100, 100, -30, step=1)
    st.markdown("---")
    st.write("Export & Share")
    st.markdown("<small class='muted'>Remember: hosted app requires proper API/data limits.</small>", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Built with Streamlit • yfinance • pandas")

# ---------- Helper: parse tickers ----------
def parse_assets(stock_input, crypto_input):
    stock_list = [t.strip() for t in stock_input.split(",") if t.strip()]
    crypto_list = [c.strip().upper() for c in crypto_input.split(",") if c.strip()]
    assets = []
    for s in stock_list:
        assets.append({"type": "Stock", "label": s, "ticker": s})
    for c in crypto_list:
        assets.append({"type": "Crypto", "label": f"{c} (Crypto)", "ticker": f"{c}-USD"})
    return assets

assets = parse_assets(stock_input, crypto_input)

# ---------- Analyze Button (Main Page) ----------

st.markdown("""
<h1 style="
font-size:42px;
font-weight:700;
color:#00ffd5;
margin-bottom:6px;
letter-spacing:0.5px;
">
Run Portfolio Analysis
</h1>
""", unsafe_allow_html=True)

st.markdown("<hr style='margin-top:4px;margin-bottom:18px;border-color:#1f2937;'>", unsafe_allow_html=True)

analyze_btn = st.button(
    "Analyze Portfolio",
    use_container_width=True
)

# ---------- Main analyze action ----------
if analyze_btn:

    if not assets:
        st.error("Add at least one stock or crypto and click Analyze.")
    else:
        # compute allocations
        num_stocks = sum(1 for a in assets if a["type"] == "Stock")
        num_crypto = sum(1 for a in assets if a["type"] == "Crypto")
        target_crypto = crypto_pct / 100.0
        target_stock = 1.0 - target_crypto
        if num_stocks == 0 and num_crypto > 0:
            eff_stock_alloc = 0.0; eff_crypto_alloc = 1.0
        elif num_crypto == 0 and num_stocks > 0:
            eff_stock_alloc = 1.0; eff_crypto_alloc = 0.0
        else:
            eff_stock_alloc = target_stock; eff_crypto_alloc = target_crypto

        stock_pool = total_invest * eff_stock_alloc
        crypto_pool = total_invest * eff_crypto_alloc

        rows = []
        for a in assets:
            t = a["ticker"]
            try:
                tk = yf.Ticker(t)
                hist = tk.history(period=period)
                if hist.empty or "Close" not in hist.columns:
                    st.warning(f"No data for {a['label']} ({t}). Skipping.")
                    continue
                price = hist["Close"].iloc[-1]
                if a["type"] == "Stock":
                    invest_amt = stock_pool / num_stocks if num_stocks > 0 else 0
                else:
                    invest_amt = crypto_pool / num_crypto if num_crypto > 0 else 0
                qty = (invest_amt / price) if price != 0 else 0
                value_now = qty * price
                dr = hist["Close"].pct_change().dropna()
                volatility = dr.std() * np.sqrt(252) if len(dr) > 1 else np.nan
                avg_daily = dr.mean() if len(dr) > 0 else 0.0
                exp_ann = (1 + avg_daily) ** 252 - 1 if len(dr) > 0 else np.nan
                if np.isnan(volatility):
                    risk = "N/A"
                elif volatility < 0.15:
                    risk = "Low"
                elif volatility < 0.30:
                    risk = "Medium"
                else:
                    risk = "High"
                rows.append({
                    "Asset Type": a["type"],
                    "Ticker": a["label"],
                    "YF_Ticker": t,
                    "Price": float(price),
                    "Quantity": float(qty),
                    "Value Now": float(value_now),
                    "Exp Annual Return %": float(exp_ann * 100) if not np.isnan(exp_ann) else np.nan,
                    "Volatility (ann.)": float(volatility) if not np.isnan(volatility) else np.nan,
                    "Risk": risk
                })
            except Exception as e:
                st.warning(f"Error {a['label']}: {e}")

        if not rows:
            st.error("No valid assets to analyze.")
        else:
            df = pd.DataFrame(rows)
            # Rebalancing targets
            total_val = df["Value Now"].sum()
            stock_val = df.loc[df["Asset Type"] == "Stock", "Value Now"].sum()
            crypto_val = df.loc[df["Asset Type"] == "Crypto", "Value Now"].sum()

            def target_per_asset(r):
                if total_val <= 0:
                    return 0.0
                if r["Asset Type"] == "Stock":
                    return total_val * eff_stock_alloc / max(1, num_stocks)
                else:
                    return total_val * eff_crypto_alloc / max(1, num_crypto)

            df["Target Value"] = df.apply(target_per_asset, axis=1)
            df["Rebalance Diff"] = df["Target Value"] - df["Value Now"]

            def action_from_diff(diff):
                if abs(diff) < max(total_val * 0.005, 1):
                    return "Hold"
                return "Buy" if diff > 0 else "Sell"

            df["Action"] = df["Rebalance Diff"].apply(action_from_diff)

            # Portfolio health heuristics
            health = 100
            tips = []
            n_assets = len(df)
            if n_assets < 3:
                health -= 20; tips.append("Add more assets to improve diversification (3-5).")
            if total_val > 0 and (crypto_val / total_val) > 0.6:
                health -= 20; tips.append("Crypto weight >60% — high risk.")
            top_weight = df["Value Now"].max() / total_val if total_val > 0 else 0
            if top_weight > 0.5:
                health -= 20; tips.append("One asset >50% — reduce concentration.")
            health -= (df["Risk"] == "High").sum() * 5
            health = max(0, min(100, health))

            # Save results in session_state
            st.session_state["df"] = df.copy()
            st.session_state["reb_df"] = df[["Asset Type", "Ticker", "Value Now", "Target Value", "Rebalance Diff", "Action"]].copy()
            st.session_state["total_val"] = float(total_val)
            st.session_state["stock_val"] = float(stock_val)
            st.session_state["crypto_val"] = float(crypto_val)
            st.session_state["health_score"] = float(health)
            st.session_state["tips_list"] = tips

            st.success("Analysis complete — results saved. Scroll down to view the dashboard and export options.")

# ---------- If analysis already done in session_state, load values ----------
df = st.session_state.get("df", None)
reb_df = st.session_state.get("reb_df", None)
total_val = st.session_state.get("total_val", 0.0)
stock_val = st.session_state.get("stock_val", 0.0)
crypto_val = st.session_state.get("crypto_val", 0.0)
health_score = st.session_state.get("health_score", None)
tips = st.session_state.get("tips_list", [])

# ---------- If results exist, show dashboard ----------
if df is not None and not df.empty:
    # KPI row
    k1, k2, k3, k4 = st.columns([2,2,2,2], gap="large")
    with k1:
        st.markdown("<div class='card'><div class='kpi'>"+f"{total_val:,.2f}"+"</div><div class='kpi-sub muted'>Total Value</div></div>", unsafe_allow_html=True)
    with k2:
        st.markdown("<div class='card'><div class='kpi'>"+f"{stock_val:,.2f}"+"</div><div class='kpi-sub muted'>Stocks Total</div></div>", unsafe_allow_html=True)
    with k3:
        st.markdown("<div class='card'><div class='kpi'>"+f"{crypto_val:,.2f}"+"</div><div class='kpi-sub muted'>Crypto Total</div></div>", unsafe_allow_html=True)
    with k4:
        st.markdown("<div class='card'><div class='kpi'>"+f"{health_score:.0f} / 100"+"</div><div class='kpi-sub muted'>Portfolio Health</div></div>", unsafe_allow_html=True)

    # Main layout
    left, right = st.columns([2,3], gap="medium")
    with left:
        st.markdown("<div class='card'><h4 class='neon'>Allocation</h4></div>", unsafe_allow_html=True)
        labels = []
        sizes = []
        if stock_val > 0:
            labels.append("Stocks"); sizes.append(stock_val)
        if crypto_val > 0:
            labels.append("Crypto"); sizes.append(crypto_val)
        fig1, ax1 = plt.subplots(figsize=(4,2.5), facecolor="none")
        if sizes:
            ax1.pie(sizes, labels=labels, autopct="%1.1f%%", colors=["#7b61ff","#00ffd5"], startangle=90, wedgeprops=dict(edgecolor='w'))
            ax1.axis("equal")
            st.pyplot(fig1, use_container_width=True)
        else:
            st.info("No allocation to show.")

        st.markdown("<div class='card' style='margin-top:12px;padding-top:10px;padding-bottom:10px;'>", unsafe_allow_html=True)
        st.write("### Price series (top assets)")
        top_assets = df.sort_values("Value Now", ascending=False).head(3)
        price_df = pd.DataFrame()
        for _, row in top_assets.iterrows():
            try:
                hist = yf.Ticker(row["YF_Ticker"]).history(period=period)["Close"]
                price_df[row["Ticker"]] = hist
            except Exception:
                continue
        if not price_df.empty:
            st.line_chart(price_df.fillna(method="ffill"))
        else:
            st.info("Price series unavailable for selected tickers.")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='card'><h3 class='neon'>Portfolio Table</h3></div>", unsafe_allow_html=True)
        display_df = df.copy()
        display_df["Price"] = display_df["Price"].map(lambda x: f"{x:,.4f}")
        display_df["Value Now"] = display_df["Value Now"].map(lambda x: f"{x:,.2f}")
        display_df["Exp Annual Return %"] = display_df["Exp Annual Return %"].map(lambda x: f"{x:,.2f}" if not np.isnan(x) else "N/A")
        display_df["Volatility (ann.)"] = display_df["Volatility (ann.)"].map(lambda x: f"{x:.3f}" if not np.isnan(x) else "N/A")
        st.dataframe(display_df.drop(columns=["YF_Ticker"]), height=360)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown("<div class='card'><h4 class='neon'>Rebalancing Suggestions</h4></div>", unsafe_allow_html=True)
        df_export_reb = reb_df.copy()
        df_export_reb["Value Now"] = df_export_reb["Value Now"].map(lambda x: f"{x:,.2f}")
        df_export_reb["Target Value"] = df_export_reb["Target Value"].map(lambda x: f"{x:,.2f}")
        df_export_reb["Rebalance Diff"] = df_export_reb["Rebalance Diff"].map(lambda x: f"{x:,.2f}")
        st.table(df_export_reb)

    # Scenario simulation (live)
    st.markdown("<div class='card' style='margin-top:18px;padding:16px;'><h4 class='neon'>Scenario Simulation (Live)</h4>", unsafe_allow_html=True)
    multipliers = np.where(df["Asset Type"]=="Stock", 1+stock_shock/100.0, 1+crypto_shock/100.0)
    df_scenario = df.copy()
    df_scenario["Scenario Value"] = df_scenario["Value Now"] * multipliers
    scenario_total = df_scenario["Scenario Value"].sum()
    delta_pct = f"{(scenario_total - total_val)/total_val*100:.1f}%" if total_val>0 else "N/A"
    st.metric("Scenario Portfolio Value", f"{scenario_total:,.2f}", delta=delta_pct)
    st.dataframe(df_scenario[["Asset Type","Ticker","Value Now","Scenario Value"]])
    st.markdown("</div>", unsafe_allow_html=True)

    # Tips & export section title
    st.markdown("<div class='card' style='margin-top:12px;padding:16px;'><h4 class='neon'>Tips to Improve</h4>", unsafe_allow_html=True)
    if tips:
        for t in tips:
            st.write(f"- {t}")
    else:
        st.write("Your portfolio looks balanced on basic heuristics ✅")
    st.markdown("</div>", unsafe_allow_html=True)

# ---------- Export UI (session_state guarded & improved) ----------
st.markdown("<div class='card' style='margin-top:12px;padding:16px;'><h4 class='neon'>Export</h4>", unsafe_allow_html=True)

df = st.session_state.get("df", None)
reb_df = st.session_state.get("reb_df", None)
total_val = st.session_state.get("total_val", None)
stock_val = st.session_state.get("stock_val", None)
crypto_val = st.session_state.get("crypto_val", None)
health_score = st.session_state.get("health_score", None)
tips = st.session_state.get("tips_list", [])

if df is None or df.empty:
    st.info("Run 'Analyze Portfolio' first to generate data before exporting.")
else:
    st.write("Preview and choose columns for export:")

    # friendly default preview column order
    preview_cols = ["Asset Type", "Ticker", "Price", "Quantity", "Value Now",
                    "Exp Annual Return %", "Volatility (ann.)", "Risk", "Target Value", "Rebalance Diff", "Action"]

    available_cols = [c for c in df.columns if c in preview_cols] + [c for c in df.columns if c not in preview_cols]
    default_cols = [c for c in preview_cols if c in df.columns]
    cols_to_show = st.multiselect("Columns to include in export & preview", options=available_cols, default=default_cols)

    # make a human-friendly preview copy
    preview_df = df.copy()
    if "Price" in preview_df.columns:
        preview_df["Price"] = preview_df["Price"].map(lambda x: f"{x:,.4f}")
    if "Value Now" in preview_df.columns:
        preview_df["Value Now"] = preview_df["Value Now"].map(lambda x: f"{x:,.2f}")
    if "Target Value" in preview_df.columns:
        preview_df["Target Value"] = preview_df["Target Value"].map(lambda x: f"{x:,.2f}")
    if "Rebalance Diff" in preview_df.columns:
        preview_df["Rebalance Diff"] = preview_df["Rebalance Diff"].map(lambda x: f"{x:,.2f}")
    if "Exp Annual Return %" in preview_df.columns:
        preview_df["Exp Annual Return %"] = preview_df["Exp Annual Return %"].map(lambda x: f"{x:,.2f}" if not pd.isna(x) else "N/A")
    if "Volatility (ann.)" in preview_df.columns:
        preview_df["Volatility (ann.)"] = preview_df["Volatility (ann.)"].map(lambda x: f"{x:.3f}" if not pd.isna(x) else "N/A")

    if cols_to_show:
        st.dataframe(preview_df[cols_to_show].reset_index(drop=True), height=300)
    else:
        st.info("Select columns to preview / export.")

    # helper: formatted CSV
    def to_csv_bytes(df_in, cols):
        csv_buf = _io.StringIO()
        df_export = preview_df[cols].copy()
        df_export.to_csv(csv_buf, index=False)
        return csv_buf.getvalue().encode("utf-8")

    if cols_to_show:
        csv_bytes = to_csv_bytes(preview_df, cols_to_show)
        st.download_button(
            "Download formatted CSV",
            csv_bytes,
            file_name="mini_aladdin_portfolio_pretty.csv",
            mime="text/csv",
        )

    # raw numeric CSV
    raw_csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download raw CSV (numeric)", raw_csv, file_name="mini_aladdin_portfolio_raw.csv", mime="text/csv")

    # Excel export (requires xlsxwriter or openpyxl)
    def to_excel_bytes(df_main, df_reb, cols_main):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            # write main sheet
            df_main.to_excel(writer, sheet_name="Portfolio", index=False, columns=cols_main)
            workbook = writer.book
            worksheet = writer.sheets["Portfolio"]
            money_fmt = workbook.add_format({"num_format": "#,##0.00", "align": "right"})
            header_fmt = workbook.add_format({"bold": True, "bg_color": "#0f1720", "font_color": "#e6eef8"})
            for col_num, value in enumerate(cols_main):
                worksheet.write(0, col_num, value, header_fmt)
                worksheet.set_column(col_num, col_num, max(12, min(30, len(value) + 5)))
            for col_num, col in enumerate(cols_main):
                if "Value" in col or "Price" in col or "Target" in col or "Diff" in col:
                    worksheet.set_column(col_num, col_num, None, money_fmt)
            # conditional formatting for Risk if exists
            try:
                risk_col_idx = cols_main.index("Risk")
                worksheet.conditional_format(1, risk_col_idx, max(1, len(df_main)), risk_col_idx, {
                    "type": "text", "criteria": "containing", "value": "High",
                    "format": workbook.add_format({"font_color": "#ff6b6b"})
                })
                worksheet.conditional_format(1, risk_col_idx, max(1, len(df_main)), risk_col_idx, {
                    "type": "text", "criteria": "containing", "value": "Medium",
                    "format": workbook.add_format({"font_color": "#fbbf24"})
                })
                worksheet.conditional_format(1, risk_col_idx, max(1, len(df_main)), risk_col_idx, {
                    "type": "text", "criteria": "containing", "value": "Low",
                    "format": workbook.add_format({"font_color": "#6ee7b7"})
                })
            except Exception:
                pass

            # rebalancing sheet
            df_reb.to_excel(writer, sheet_name="Rebalancing", index=False)
            ws2 = writer.sheets["Rebalancing"]
            for col_num, value in enumerate(df_reb.columns):
                ws2.write(0, col_num, value, header_fmt)
                ws2.set_column(col_num, col_num, max(12, min(30, len(value) + 5)))
        output.seek(0)
        return output.getvalue()

    excel_cols = cols_to_show.copy() if cols_to_show else df.columns.tolist()
    reb_export = reb_df if reb_df is not None else df.copy()
    excel_bytes = to_excel_bytes(df, reb_export, excel_cols)
    st.download_button(
        "Download formatted Excel (.xlsx)",
        excel_bytes,
        file_name="mini_aladdin_portfolio.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.markdown("</div>", unsafe_allow_html=True)

# ---------- Shareable note & footer ----------
st.info("To share this UI with others, deploy to Streamlit Community Cloud or another host (I can help).")

st.markdown(
    """
    <div style="margin-top:32px;padding:12px;border-radius:8px;background:transparent;">
        <small class="muted">Disclaimer: This is an educational demo. Not investment advice.</small>
    </div>
    """,
    unsafe_allow_html=True,
)
