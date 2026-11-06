"""FIN43900 Lab 19 — Buffett, Cathie Wood, and Burry panel."""
from __future__ import annotations
import json
import re
from pathlib import Path
import pandas as pd
import streamlit as st
from sec_financials import build_five_year_history, print_report, find_unprinted_numbers
ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
st.set_page_config(page_title="Legend Investor Panel", layout="wide")
st.title("FIN43900 Lab 19 — Legend Investor Panel")
st.caption("Data from SEC EDGAR; built with AI help, a learning demonstration, not investment advice.")
st.sidebar.header("Company")
ticker = st.sidebar.text_input("Ticker", value="COST").strip().upper()
if st.sidebar.button("Run three-investor panel", type="primary"):
    try:
        with st.spinner(f"Retrieving five fiscal years of SEC 10-K facts for {ticker}..."):
            result = build_five_year_history(ticker)
        report = print_report(result)
        st.session_state["result"] = result
        st.session_state["report"] = report
        (OUTPUT_DIR / f"{ticker}_sec_data.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (OUTPUT_DIR / f"{ticker}_printed_report.txt").write_text(report, encoding="utf-8")
    except Exception as exc:
        st.error(f"SEC retrieval failed: {exc}")
result = st.session_state.get("result")
report = st.session_state.get("report", "")
if result:
    ticker = result["ticker"]
    st.subheader(f"{ticker} — five fiscal years")
    st.code(report, language="text")
    st.subheader("Panel table — investor × check")
    check_labels = {
        "buffett": {"roe_15_percent_every_year":"ROE ≥ 15% every year", "owner_earnings_positive_every_year":"Owner earnings positive every year", "owner_earnings_grew_first_to_last":"Owner earnings grew, first to last"},
        "cathie_wood": {"revenue_growth_15_percent_first_to_last":"Revenue growth ≥ 15% annualized, first to last", "research_and_development_5_percent_latest_year":"R&D ≥ 5% of revenue, latest year"},
        "burry": {"operating_cash_flow_at_least_net_income_every_year":"Operating cash flow ≥ net income every year", "liabilities_no_more_than_2x_equity_latest_year":"Liabilities ≤ 2× equity, latest year"},
    }
    labels = {"buffett":"Buffett", "cathie_wood":"Cathie Wood", "burry":"Burry"}
    panel_rows=[]
    for investor, checks in check_labels.items():
        for key, label in checks.items():
            panel_rows.append({"Investor":labels[investor], "Check":label, "Result":result["panel_checks"][investor][key]})
    st.dataframe(pd.DataFrame(panel_rows), hide_index=True, use_container_width=True)
    st.subheader("Three investor memos")
    cols=st.columns(3)
    flags_by_memo={}
    for col, investor in zip(cols, ("buffett","cathie_wood","burry")):
        path=OUTPUT_DIR/f"{ticker}_{investor}_memo.md"
        with col:
            st.markdown(f"**{labels[investor]}**")
            if path.exists():
                memo=path.read_text(encoding="utf-8")
                match=re.search(r"(?im)^\s*Verdict\s*:\s*(OWN|WATCH|PASS)\b",memo)
                st.markdown(f"Verdict: **{match.group(1) if match else 'missing'}**")
                st.markdown(memo)
                flags=find_unprinted_numbers(memo,report)
                flags_by_memo[labels[investor]]=flags
                if flags: st.error("Unprinted-number flag: "+", ".join(flags))
                else: st.success("No unprinted numeric values detected.")
            else:
                st.warning(f"Memo not yet created: outputs/{path.name}")
                flags_by_memo[labels[investor]]=["memo missing"]
    st.subheader("Unprinted-number flag across all memos")
    st.dataframe(pd.DataFrame([{"Memo":k,"Flagged values":", ".join(v) if v else "None"} for k,v in flags_by_memo.items()]),hide_index=True,use_container_width=True)
    st.download_button("Download SEC data JSON",data=json.dumps(result,indent=2),file_name=f"{ticker}_panel_data.json",mime="application/json")
else:
    st.info("Run COST first. After it matches the known answer, run NVDA, the largest holding in the example VT fund using Vanguard's September 30, 2026 holdings disclosure.")
