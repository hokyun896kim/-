"""Streamlit 대시보드.

실행:  streamlit run stocksystem/app/dashboard.py

탭 구성:
  1) 관심종목 스코어보드 — 종합점수/추천 한눈에
  2) 종목 상세 — 캔들차트 + 지표 + 기술/펀더멘털 분해
  3) 모의매매 — 매수/매도/포트폴리오 현황
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# 패키지 임포트 경로 확보 (streamlit run 직접 실행 대응)
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stocksystem.config import load_config
from stocksystem.data import get_provider
from stocksystem.analysis import analyze_symbol, analyze_watchlist
from stocksystem.analysis.scoring import RECO_LABELS
from stocksystem.portfolio import (
    PaperBroker, InsufficientFundsError, InsufficientSharesError,
)
from stocksystem.portfolio.paper_broker import DEFAULT_STATE

st.set_page_config(page_title="미국주식 분석 시스템", layout="wide",
                   page_icon="📈")

cfg = load_config()

# 추천 → 색상
RECO_COLOR = {
    "strong_buy": "#0b7d3e", "buy": "#3aa76d", "hold": "#b9912a",
    "sell": "#d2603a", "strong_sell": "#b3261e",
}


def score_bg(val) -> str:
    """0~100 점수를 빨강→노랑→초록 배경색으로 (matplotlib 불필요)."""
    if val is None or (isinstance(val, float) and val != val):
        return ""
    v = max(0.0, min(100.0, float(val))) / 100.0
    if v < 0.5:                       # 빨강 → 노랑
        r, g = 210, int(60 + 150 * (v / 0.5))
    else:                             # 노랑 → 초록
        r, g = int(210 - 200 * ((v - 0.5) / 0.5)), 200
    return f"background-color: rgb({r},{g},70); color: black;"


def ret_bg(val) -> str:
    """수익률(%)을 음수=빨강 / 양수=초록 배경색으로."""
    if val is None or (isinstance(val, float) and val != val):
        return ""
    v = max(-30.0, min(30.0, float(val))) / 30.0
    if v >= 0:
        return f"background-color: rgba(58,167,109,{0.15 + 0.55*v:.2f});"
    return f"background-color: rgba(211,38,30,{0.15 + 0.55*abs(v):.2f});"


@st.cache_data(ttl=600, show_spinner=False)
def cached_watchlist(symbols, provider_name, period):
    provider = get_provider(provider_name)
    results = analyze_watchlist(list(symbols), provider, cfg, period)
    return [r.summary_row() for r in results], [r.symbol for r in results]


@st.cache_data(ttl=600, show_spinner=False)
def cached_symbol(symbol, provider_name, period):
    provider = get_provider(provider_name)
    res = analyze_symbol(symbol, provider, cfg, period)
    # 차트용 직렬화
    ind = res.technical.indicators if res.technical else pd.DataFrame()
    return res, ind


def get_broker() -> PaperBroker:
    if "broker" not in st.session_state:
        st.session_state.broker = PaperBroker.load(
            DEFAULT_STATE,
            initial_cash=cfg.paper_trading.initial_cash,
            commission=cfg.paper_trading.commission,
        )
    return st.session_state.broker


# ----------------------------- 사이드바 -----------------------------
st.sidebar.title("📈 미국주식 분석")
provider_name = st.sidebar.selectbox(
    "데이터 소스", ["yahoo", "sample"],
    index=0 if cfg.data_provider == "yahoo" else 1,
    help="yahoo=실시간(로컬 권장), sample=오프라인 데모 데이터",
)
period = st.sidebar.selectbox("조회 기간", ["6mo", "1y", "2y", "5y"], index=1)
watch_text = st.sidebar.text_area(
    "관심종목 (쉼표/줄바꿈 구분)",
    value=", ".join(cfg.watchlist), height=100,
)
watchlist = [s.strip().upper() for s in watch_text.replace("\n", ",").split(",")
             if s.strip()]
if st.sidebar.button("🔄 캐시 새로고침"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(
    "※ 본 시스템은 교육/연구용입니다. 투자 판단과 책임은 본인에게 있습니다.")

tab1, tab2, tab3 = st.tabs(["📊 스코어보드", "🔍 종목 상세", "💰 모의매매"])

# ============================ 탭 1: 스코어보드 ============================
with tab1:
    st.subheader("관심종목 스코어보드")
    if not watchlist:
        st.info("사이드바에 관심종목을 입력하세요.")
    else:
        with st.spinner("분석 중..."):
            rows, _ = cached_watchlist(tuple(watchlist), provider_name, period)
        df = pd.DataFrame(rows)

        def color_reco(val):
            for key, label in RECO_LABELS.items():
                if val == label:
                    return f"background-color: {RECO_COLOR[key]}; color: white;"
            return ""

        def fmt(spec):
            return lambda v: "—" if v is None or (isinstance(v, float) and v != v) else spec.format(v)

        styled = (df.style
                  .map(color_reco, subset=["추천"])
                  .map(score_bg, subset=["종합점수", "기술점수", "펀더멘털점수"])
                  .format({"현재가": fmt("{:.2f}"), "종합점수": fmt("{:.1f}"),
                           "기술점수": fmt("{:.1f}"), "펀더멘털점수": fmt("{:.1f}")}))
        st.dataframe(styled, width='stretch', height=460)

        c1, c2, c3 = st.columns(3)
        c1.metric("평균 종합점수", f"{df['종합점수'].mean():.1f}")
        buys = df["추천"].isin(["적극 매수", "매수"]).sum()
        c2.metric("매수 추천 종목", f"{buys} / {len(df)}")
        c3.metric("최고 점수", df.loc[df['종합점수'].idxmax(), '종목'])

# ============================ 탭 2: 종목 상세 ============================
with tab2:
    sel = st.selectbox("종목 선택", watchlist or ["AAPL"])
    if sel:
        with st.spinner(f"{sel} 분석 중..."):
            res, ind = cached_symbol(sel, provider_name, period)

        head = st.columns([2, 1, 1, 1])
        head[0].markdown(f"### {res.symbol} — {res.name or ''}")
        head[1].metric("종합점수", f"{res.total_score:.1f}")
        head[2].metric("기술", f"{res.technical.score:.1f}"
                       if res.technical else "—")
        head[3].metric("펀더멘털", f"{res.fundamental.score:.1f}"
                       if res.fundamental else "—")

        key = res.recommendation
        st.markdown(
            f"<div style='padding:10px;border-radius:8px;"
            f"background:{RECO_COLOR[key]};color:white;font-size:20px;"
            f"text-align:center;'><b>추천: {res.recommendation_label}</b></div>",
            unsafe_allow_html=True,
        )

        if res.reasons:
            with st.expander("📌 판단 근거", expanded=True):
                for r in res.reasons:
                    st.write("•", r)

        # ---- 차트 ----
        if not ind.empty:
            c = cfg.technical
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=ind.index, open=ind["Open"], high=ind["High"],
                low=ind["Low"], close=ind["Close"], name="가격"))
            for col, color in [(f"SMA{c.sma_short}", "#1f77b4"),
                               (f"SMA{c.sma_long}", "#ff7f0e")]:
                if col in ind:
                    fig.add_trace(go.Scatter(
                        x=ind.index, y=ind[col], name=col,
                        line=dict(width=1, color=color)))
            if "bb_upper" in ind:
                fig.add_trace(go.Scatter(x=ind.index, y=ind["bb_upper"],
                              name="BB상단", line=dict(width=0.5, color="gray"),
                              opacity=0.4))
                fig.add_trace(go.Scatter(x=ind.index, y=ind["bb_lower"],
                              name="BB하단", line=dict(width=0.5, color="gray"),
                              fill="tonexty", opacity=0.4))
            fig.update_layout(height=420, xaxis_rangeslider_visible=False,
                              margin=dict(l=10, r=10, t=30, b=10),
                              legend=dict(orientation="h"))
            st.plotly_chart(fig, width='stretch')

            # RSI + MACD
            cc1, cc2 = st.columns(2)
            with cc1:
                rfig = go.Figure()
                rfig.add_trace(go.Scatter(x=ind.index, y=ind["RSI"], name="RSI"))
                rfig.add_hline(y=c.rsi_overbought, line_dash="dash",
                               line_color="red")
                rfig.add_hline(y=c.rsi_oversold, line_dash="dash",
                               line_color="green")
                rfig.update_layout(title="RSI", height=250,
                                   margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(rfig, width='stretch')
            with cc2:
                mfig = go.Figure()
                mfig.add_trace(go.Bar(x=ind.index, y=ind["hist"], name="히스토그램"))
                mfig.add_trace(go.Scatter(x=ind.index, y=ind["macd"], name="MACD"))
                mfig.add_trace(go.Scatter(x=ind.index, y=ind["signal"],
                               name="시그널"))
                mfig.update_layout(title="MACD", height=250,
                                   margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(mfig, width='stretch')

        # ---- 펀더멘털 분해 ----
        if res.fundamental and res.fundamental.metric_scores:
            st.markdown("#### 펀더멘털 지표 점수")
            ms = res.fundamental.metric_scores
            st.dataframe(pd.DataFrame(
                {"지표": list(ms.keys()), "점수": list(ms.values())}
            ).set_index("지표").T, width='stretch')

# ============================ 탭 3: 모의매매 ============================
with tab3:
    broker = get_broker()
    st.subheader("모의매매 계좌")

    # 현재가 수집 (보유종목 + 거래대상)
    @st.cache_data(ttl=300, show_spinner=False)
    def price_of(symbol, provider_name):
        try:
            res, _ = cached_symbol(symbol, provider_name, "6mo")
            return res.technical.latest.get("close") if res.technical else None
        except Exception:
            return None

    held = list(broker.positions.keys())
    prices = {s: price_of(s, provider_name) or broker.positions[s].avg_price
              for s in held}

    m = st.columns(4)
    m[0].metric("현금", f"${broker.cash:,.0f}")
    m[1].metric("평가금액", f"${broker.position_value(prices):,.0f}")
    eq = broker.equity(prices)
    m[2].metric("총자산", f"${eq:,.0f}",
                f"{broker.total_return(prices)*100:+.2f}%")
    m[3].metric("실현손익", f"${broker.realized_pnl():,.0f}")

    st.markdown("#### 주문")
    oc = st.columns([1.5, 1, 1, 1, 1])
    order_sym = oc[0].text_input("종목", value=(watchlist[0] if watchlist else "AAPL")).upper()
    qty = oc[1].number_input("수량", min_value=0.0, value=10.0, step=1.0)
    live_px = price_of(order_sym, provider_name)
    default_px = float(live_px) if live_px else 100.0
    px = oc[2].number_input("가격", min_value=0.0, value=round(default_px, 2),
                            step=0.01)
    oc[3].write("")
    if oc[3].button("🟢 매수", width='stretch'):
        try:
            broker.buy(order_sym, qty, px)
            broker.save()
            st.success(f"{order_sym} {qty}주 매수 @ ${px:.2f}")
        except (InsufficientFundsError, ValueError) as e:
            st.error(str(e))
    oc[4].write("")
    if oc[4].button("🔴 매도", width='stretch'):
        try:
            broker.sell(order_sym, qty, px)
            broker.save()
            st.success(f"{order_sym} {qty}주 매도 @ ${px:.2f}")
        except (InsufficientSharesError, ValueError) as e:
            st.error(str(e))

    st.markdown("#### 보유 종목")
    holdings = broker.holdings_table(prices)
    if holdings:
        hdf = pd.DataFrame(holdings)
        st.dataframe(
            hdf.style.map(ret_bg, subset=["수익률"]),
            width='stretch')
    else:
        st.info("보유 종목이 없습니다. 위에서 매수해보세요.")

    with st.expander("거래 내역"):
        if broker.trades:
            tdf = pd.DataFrame([t.__dict__ for t in broker.trades])
            st.dataframe(tdf, width='stretch')
        else:
            st.write("거래 내역이 없습니다.")

    if st.button("⚠️ 계좌 초기화"):
        st.session_state.broker = PaperBroker(
            cfg.paper_trading.initial_cash, cfg.paper_trading.commission)
        st.session_state.broker.save()
        st.rerun()
