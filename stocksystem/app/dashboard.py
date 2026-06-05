"""미국주식 분석 대시보드 (Streamlit).

실행:  streamlit run stocksystem/app/dashboard.py

탭 구성:
  1) 스크리너   — 시가총액 상위 기업을 종합점수로 필터/정렬
  2) 종목 상세  — 차트·점수·실적·이벤트·뉴스 분위기까지 한 화면에
  3) 모의매매   — 가상 자본으로 매수/매도 연습
  4) 투자 가이드 — 지표 해설과 체크리스트
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# 패키지 임포트 경로 확보 (streamlit run 직접 실행 대응)
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stocksystem.config import load_config
from stocksystem.data import get_provider
from stocksystem.data.universe import filter_universe, load_universe, sectors
from stocksystem.data import marketcap as mcache
from stocksystem.analysis import analyze_full, analyze_symbol
from stocksystem.analysis import technical as ta
from stocksystem.analysis.scoring import RECO_LABELS
from stocksystem.backtest import STRATEGIES, run_backtest
from stocksystem.portfolio import (
    PaperBroker, InsufficientFundsError, InsufficientSharesError,
)
from stocksystem.portfolio.paper_broker import DEFAULT_STATE

st.set_page_config(page_title="미국주식 분석 시스템", layout="wide",
                   page_icon="📈")

cfg = load_config()

# 차트 기본 템플릿: 다크
pio.templates.default = "plotly_dark"

# 터미널 팔레트
C_UP = "#26a69a"       # 상승 (청록 그린)
C_DOWN = "#f23645"     # 하락 (레드)
C_PANEL = "#131722"    # 패널 배경
C_GRID = "#222631"     # 그리드
C_ACCENT = "#2dd4bf"   # 시안
C_AMBER = "#f5a623"    # 앰버

MONO = ("'JetBrains Mono','SF Mono','Roboto Mono',"
        "'DejaVu Sans Mono',Consolas,monospace")

# ---- 다크 트레이딩 터미널 CSS ----
st.markdown(f"""
<style>
.block-container {{ padding-top: 1.4rem; max-width: 1560px; }}
html, body, [class*="css"] {{ font-size: 15px; }}
.stApp {{ background: #0a0e17; }}

/* 숫자는 모노스페이스 (가격/지표/표) */
[data-testid="stMetricValue"], [data-testid="stMetricDelta"],
[data-testid="stDataFrame"], .ticker-tape {{ font-family: {MONO}; }}

/* 탭: 터미널 느낌 */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {C_GRID};
    background: #0d1119; }}
.stTabs [data-baseweb="tab"] {{
    font-size: 1.0rem; font-weight: 700; padding: 9px 16px; color: #8b93a7;
    border-radius: 6px 6px 0 0; letter-spacing: .3px; }}
.stTabs [aria-selected="true"] {{
    background: #131722; color: {C_ACCENT} !important;
    box-shadow: inset 0 -2px 0 {C_ACCENT}; }}

/* 지표(metric) 패널 */
[data-testid="stMetric"] {{
    background: linear-gradient(180deg,#161b27,#10141d);
    border: 1px solid {C_GRID}; border-radius: 8px;
    padding: 10px 14px 8px; }}
[data-testid="stMetricValue"] {{ font-size: 1.7rem; font-weight: 800;
    color: #f0f3fa; line-height: 1.1; }}
[data-testid="stMetricLabel"] p {{ font-size: .82rem; font-weight: 700;
    color: #8b93a7; text-transform: uppercase; letter-spacing: .5px; }}

/* 섹션 제목 — 시안 좌측 바 */
.main h2, .main h3 {{ font-weight: 800; color: #e8ecf5; letter-spacing: .3px; }}
.main h4 {{
    font-size: 1.12rem !important; font-weight: 800; color: #e8ecf5;
    margin: 1.0rem 0 .4rem; padding: 3px 0 3px 11px;
    border-left: 4px solid {C_ACCENT}; text-transform: uppercase;
    letter-spacing: .4px; }}

.main p, .main li {{ font-size: .98rem; line-height: 1.6; color: #c2c8d6; }}
.main small, .main .stCaption {{ color: #6b7280 !important; }}

/* 입력 라벨 */
.stSelectbox label, .stSlider label, .stNumberInput label,
.stTextInput label, .stToggle label {{
    font-weight: 700; color: #9aa3b8; text-transform: uppercase;
    font-size: .8rem; letter-spacing: .4px; }}

/* 사이드바 */
[data-testid="stSidebar"] {{ background: #0d1119; border-right: 1px solid {C_GRID}; }}

/* 티커 테이프 */
.ticker-tape {{
    display: flex; gap: 18px; flex-wrap: wrap; align-items: center;
    background: #0d1119; border: 1px solid {C_GRID}; border-radius: 8px;
    padding: 8px 14px; margin-bottom: 10px; font-size: .95rem; }}
.tt-item {{ white-space: nowrap; }}
.tt-sym {{ color: #e8ecf5; font-weight: 800; }}
.tt-px {{ color: #c2c8d6; margin: 0 5px; }}
.tt-up {{ color: {C_UP}; font-weight: 700; }}
.tt-down {{ color: {C_DOWN}; font-weight: 700; }}
</style>
""", unsafe_allow_html=True)

# ---- 추천 색상 (다크 배경용 형광 톤) ----
RECO_COLOR = {
    "strong_buy": "#16c784", "buy": "#0fa968", "hold": "#f5a623",
    "sell": "#ff7043", "strong_sell": "#f23645",
}
# 점수 → 다크 셀 배경 (어두운 빨강→앰버→초록) + 밝은 글자
_GRAD = [(94, 30, 36), (92, 74, 22), (20, 78, 50)]  # dark red, amber, green


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def score_bg(val) -> str:
    if val is None or (isinstance(val, float) and val != val):
        return ""
    v = max(0.0, min(100.0, float(val))) / 100.0
    if v < 0.5:
        c = _lerp(_GRAD[0], _GRAD[1], v / 0.5)
    else:
        c = _lerp(_GRAD[1], _GRAD[2], (v - 0.5) / 0.5)
    return f"background-color: rgb{c}; color: #f0f3fa; font-weight: 700;"


def ret_bg(val) -> str:
    if val is None or (isinstance(val, float) and val != val):
        return ""
    v = max(-30.0, min(30.0, float(val))) / 30.0
    if v >= 0:
        return f"background-color: rgba(38,166,154,{0.18 + 0.5*v:.2f}); color:#eafff7;"
    return f"background-color: rgba(242,54,69,{0.18 + 0.5*abs(v):.2f}); color:#ffecec;"


def fmt(spec):
    return lambda v: "—" if v is None or (isinstance(v, float) and v != v) \
        else spec.format(v)


def human_cap(v) -> str:
    if not v:
        return "—"
    if v >= 1e12:
        return f"${v/1e12:.2f}조"
    if v >= 1e9:
        return f"${v/1e9:.1f}B"
    if v >= 1e6:
        return f"${v/1e6:.0f}M"
    return f"${v:,.0f}"


# ----------------------------- 캐시 -----------------------------
@st.cache_data(ttl=300, show_spinner=False)
def cached_ticker(symbols, provider_name):
    """티커 테이프용: 심볼별 (현재가, 일간 변동률%)."""
    provider = get_provider(provider_name)
    out = []
    for s in symbols:
        try:
            df = provider.price_history(s, period="1mo")
            last = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            pct = (last / prev - 1) * 100 if prev else 0.0
            out.append((s, last, pct))
        except Exception:
            continue
    return out


def render_ticker(symbols, provider_name):
    data = cached_ticker(tuple(symbols), provider_name)
    if not data:
        return
    chips = []
    for sym, px, pct in data:
        cls = "tt-up" if pct >= 0 else "tt-down"
        arrow = "▲" if pct >= 0 else "▼"
        chips.append(
            f"<span class='tt-item'><span class='tt-sym'>{sym}</span>"
            f"<span class='tt-px'>{px:,.2f}</span>"
            f"<span class='{cls}'>{arrow}{pct:+.2f}%</span></span>")
    st.markdown(f"<div class='ticker-tape'>{''.join(chips)}</div>",
                unsafe_allow_html=True)


@st.cache_data(ttl=600, show_spinner=False)
def cached_screener(symbols, provider_name, period):
    provider = get_provider(provider_name)
    rows = []
    for s in symbols:
        r = analyze_symbol(s, provider, cfg, period)
        row = r.summary_row()
        row["시가총액"] = r.market_cap
        row["섹터"] = r.sector
        rows.append(row)
    return rows


@st.cache_data(ttl=600, show_spinner=False)
def cached_full(symbol, provider_name, period):
    provider = get_provider(provider_name)
    res = analyze_full(symbol, provider, cfg, period)
    ind = res.technical.indicators if res.technical else pd.DataFrame()
    return res, ind


@st.cache_data(ttl=600, show_spinner=False)
def cached_backtest(symbol, provider_name, strategy, period, commission,
                    buy_th, sell_th):
    provider = get_provider(provider_name)
    df = provider.price_history(symbol, period=period)
    ind = ta.compute_indicators(df, cfg.technical)
    strat = STRATEGIES[strategy]
    if strategy == "종합 기술점수":
        pos = strat(ind, cfg.technical, buy=buy_th, sell=sell_th)
    else:
        pos = strat(ind, cfg.technical)
    return run_backtest(ind, pos, symbol=symbol.upper(), strategy=strategy,
                        initial_cash=10_000.0, commission=commission)


@st.cache_data(ttl=300, show_spinner=False)
def price_of(symbol, provider_name):
    try:
        res, _ = cached_full(symbol, provider_name, "6mo")
        return res.technical.latest.get("close") if res.technical else None
    except Exception:
        return None


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
    help="yahoo=실시간(로컬 권장) · sample=오프라인 데모 데이터")
period = st.sidebar.selectbox("차트 기간", ["6mo", "1y", "2y", "5y"], index=1)
if st.sidebar.button("🔄 데이터 새로고침", width='stretch'):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption(
    "※ 본 시스템은 교육·연구용입니다. 점수·추천은 투자자문이 아니며 "
    "최종 판단과 책임은 본인에게 있습니다.")

# 상단 실시간 티커 테이프 (관심종목)
render_ticker(cfg.watchlist, provider_name)

tab1, tab2, tab5, tab3, tab4 = st.tabs(
    ["📊 스크리너", "🔍 종목 상세", "🧪 백테스트", "💰 모의매매", "📖 투자 가이드"])

# ============================ 탭 1: 스크리너 ============================
with tab1:
    st.subheader("시가총액 상위 기업 스크리너")
    cc = st.columns([1.2, 1.4, 1.2, 1])
    top_pct = cc[0].select_slider(
        "시가총액 상위", options=[10, 25, 50, 75, 100], value=50,
        format_func=lambda x: f"상위 {x}%")
    sector = cc[1].selectbox("섹터", ["전체"] + sectors())
    max_n = cc[2].slider("분석 종목 수", 5, 60, 25, step=5,
                         help="실시간(yahoo) 모드에서 많을수록 느려집니다")
    sort_by = cc[3].selectbox("정렬", ["종합점수", "시가총액", "기술점수",
                                       "펀더멘털점수"])

    # --- 실시간 시총으로 랭킹 정확도 높이기 ---
    rc = st.columns([1.4, 1, 2])
    use_live = rc[0].toggle("실시간 시총으로 랭킹", value=True,
                            help="현재 시가총액을 받아 상위 N%를 정확히 계산합니다")
    refresh_caps = rc[1].button("🔄 시총 갱신")

    live_caps = mcache.get_caps() if use_live else None
    if use_live and refresh_caps:
        prog = st.progress(0.0, text="시가총액 갱신 중...")
        provider = get_provider(provider_name)

        def _cb(done, total, sym):
            prog.progress(done / total, text=f"시총 갱신 {done}/{total} · {sym}")
        live_caps = mcache.refresh(provider, progress=_cb)
        prog.empty()
        st.cache_data.clear()

    if use_live:
        upd = mcache.last_updated()
        if upd:
            rc[2].caption(f"📌 실시간 시총 기준 · 마지막 갱신 **{upd}** "
                          f"({len(live_caps)}종목)"
                          + ("  ·  ⏳ 갱신 권장" if mcache.is_stale() else ""))
        else:
            rc[2].caption("📌 아직 실시간 시총이 없습니다. **시총 갱신**을 눌러주세요. "
                          "(없으면 번들 스냅샷 사용)")

    universe = filter_universe(top_pct=top_pct, sector=sector,
                               live_caps=live_caps)
    symbols = [u.symbol for u in universe][:max_n]
    src = "실시간" if (use_live and live_caps) else "스냅샷"
    st.caption(f"유니버스 {len(universe)}종목 중 시총({src}) 상위 "
               f"{len(symbols)}종목 분석")

    with st.spinner("분석 중..."):
        rows = cached_screener(tuple(symbols), provider_name, period)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["시가총액"] = df["시가총액"].apply(human_cap)
        df = df.sort_values(
            sort_by if sort_by in df else "종합점수", ascending=False)
        display_cols = ["종목", "이름", "섹터", "현재가", "종합점수",
                        "기술점수", "펀더멘털점수", "추천"]
        df = df[[c for c in display_cols if c in df.columns]]

        def color_reco(val):
            for key, label in RECO_LABELS.items():
                if val == label:
                    return f"background-color:{RECO_COLOR[key]};color:white;"
            return ""

        styled = (df.style
                  .map(color_reco, subset=["추천"])
                  .map(score_bg, subset=[c for c in
                       ["종합점수", "기술점수", "펀더멘털점수"] if c in df])
                  .format({"현재가": fmt("${:.2f}"), "종합점수": fmt("{:.0f}"),
                           "기술점수": fmt("{:.0f}"),
                           "펀더멘털점수": fmt("{:.0f}")}))
        st.dataframe(styled, width='stretch', height=520, hide_index=True)

        m = st.columns(3)
        valid = pd.to_numeric(df["종합점수"], errors="coerce")
        m[0].metric("평균 종합점수", f"{valid.mean():.0f}")
        buys = df["추천"].isin(["적극 매수", "매수"]).sum()
        m[1].metric("매수 추천", f"{buys} / {len(df)}")
        m[2].metric("최고 점수 종목",
                    df.loc[valid.idxmax(), "종목"]
                    if valid.notna().any() else "—")

# ============================ 탭 2: 종목 상세 ============================
with tab2:
    uni_syms = [u.symbol for u in load_universe()]
    csel = st.columns([2, 3])
    sel = csel[0].selectbox("유니버스에서 선택", uni_syms)
    typed = csel[1].text_input("또는 티커 직접 입력", value="").strip().upper()
    symbol = typed or sel

    if symbol:
        with st.spinner(f"{symbol} 분석 중..."):
            res, ind = cached_full(symbol, provider_name, period)

        # ---- 헤더 ----
        st.markdown(f"### {res.symbol} — {res.name or ''}")
        meta = []
        if res.sector:
            meta.append(f"섹터: {res.sector}")
        if res.market_cap:
            meta.append(f"시가총액: {human_cap(res.market_cap)}")
        if meta:
            st.caption("  ·  ".join(meta))

        h = st.columns(4)
        price = res.technical.latest.get("close") if res.technical else None
        h[0].metric("현재가", f"${price:,.2f}" if price else "—")
        h[1].metric("종합점수", f"{res.total_score:.0f}")
        h[2].metric("기술 / 펀더멘털",
                    f"{res.technical.score:.0f} / {res.fundamental.score:.0f}"
                    if res.technical and res.fundamental else "—")
        h[3].metric("뉴스 분위기",
                    f"{res.news.score:.0f}" if res.news else "—",
                    res.news.label if res.news else None)

        key = res.recommendation
        st.markdown(
            f"<div style='padding:16px;border-radius:14px;"
            f"background:{RECO_COLOR[key]};color:white;font-size:24px;"
            f"text-align:center;margin:10px 0;letter-spacing:.3px;"
            f"box-shadow:0 2px 8px rgba(16,24,40,.15);'>"
            f"<b>추천: {res.recommendation_label}</b>"
            f"<span style='font-size:17px;opacity:.92;'>"
            f"&nbsp;&nbsp;· 종합 {res.total_score:.0f}점</span></div>",
            unsafe_allow_html=True)

        if res.reasons:
            with st.expander("📌 이렇게 판단했어요 (근거)", expanded=True):
                for r in res.reasons:
                    st.write("•", r)

        # ---- 가격 차트 ----
        if not ind.empty:
            c = cfg.technical
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=ind.index, open=ind["Open"], high=ind["High"],
                low=ind["Low"], close=ind["Close"], name="가격",
                increasing_line_color=C_UP,
                decreasing_line_color=C_DOWN))
            for col, color in [(f"SMA{c.sma_short}", "#2f6fed"),
                               (f"SMA{c.sma_long}", "#e0883a")]:
                if col in ind:
                    fig.add_trace(go.Scatter(x=ind.index, y=ind[col], name=col,
                                  line=dict(width=1.3, color=color)))
            if "bb_upper" in ind:
                fig.add_trace(go.Scatter(x=ind.index, y=ind["bb_upper"],
                              name="볼린저 상단", line=dict(width=0.5,
                              color="#3a4150"), showlegend=False))
                fig.add_trace(go.Scatter(x=ind.index, y=ind["bb_lower"],
                              name="볼린저 밴드", line=dict(width=0.5,
                              color="#3a4150"), fill="tonexty",
                              fillcolor="rgba(120,130,150,0.12)"))
            fig.update_layout(height=420, xaxis_rangeslider_visible=False,
                              margin=dict(l=10, r=10, t=10, b=10),
                              legend=dict(orientation="h", y=1.05),
                              plot_bgcolor=C_PANEL, paper_bgcolor=C_PANEL)
            st.plotly_chart(fig, width='stretch')

            cc1, cc2 = st.columns(2)
            with cc1:
                rf = go.Figure()
                rf.add_trace(go.Scatter(x=ind.index, y=ind["RSI"], name="RSI",
                             line=dict(color="#7b5cd6")))
                rf.add_hline(y=c.rsi_overbought, line_dash="dash",
                             line_color=C_DOWN,
                             annotation_text="과매수")
                rf.add_hline(y=c.rsi_oversold, line_dash="dash",
                             line_color=C_UP, annotation_text="과매도")
                rf.update_layout(title="RSI (상대강도)", height=240,
                                 margin=dict(l=10, r=10, t=34, b=10),
                                 plot_bgcolor=C_PANEL, paper_bgcolor=C_PANEL)
                st.plotly_chart(rf, width='stretch')
            with cc2:
                mf = go.Figure()
                colors = [C_UP if v >= 0 else C_DOWN
                          for v in ind["hist"].fillna(0)]
                mf.add_trace(go.Bar(x=ind.index, y=ind["hist"], name="히스토그램",
                             marker_color=colors))
                mf.add_trace(go.Scatter(x=ind.index, y=ind["macd"], name="MACD",
                             line=dict(color="#2f6fed")))
                mf.add_trace(go.Scatter(x=ind.index, y=ind["signal"],
                             name="시그널", line=dict(color="#e0883a")))
                mf.update_layout(title="MACD (추세 전환)", height=240,
                                 margin=dict(l=10, r=10, t=34, b=10),
                                 plot_bgcolor=C_PANEL, paper_bgcolor=C_PANEL)
                st.plotly_chart(mf, width='stretch')

        # ---- 핵심 재무 지표 ----
        if res.fundamental and res.fundamental.fundamentals:
            st.markdown("#### 💵 핵심 재무 지표")
            f = res.fundamental.fundamentals
            ms = res.fundamental.metric_scores
            # (표시라벨, 값, 포맷, 설명, metric_scores 키)
            specs = [
                ("PER", f.trailing_pe, "{:.1f}", "주가수익비율 (낮을수록 저평가)", "PER"),
                ("PBR", f.price_to_book, "{:.1f}", "주가순자산비율", "PBR"),
                ("ROE", f.return_on_equity, "{:.1%}", "자기자본이익률 (높을수록 우량)", "ROE"),
                ("순이익률", f.profit_margin, "{:.1%}", "매출 대비 순이익", "순이익률"),
                ("매출성장", f.revenue_growth, "{:+.1%}", "전년 대비 매출 성장", "매출성장"),
                ("이익성장", f.earnings_growth, "{:+.1%}", "전년 대비 이익 성장", "이익성장"),
                ("부채비율", f.debt_to_equity, "{:.0f}", "부채/자본 (낮을수록 안정)", "부채비율"),
                ("배당수익률", f.dividend_yield, "{:.2%}", "연 배당 / 주가", "배당"),
            ]
            frows = []
            for label, val, vfmt, desc, key in specs:
                frows.append({
                    "지표": label,
                    "값": vfmt.format(val) if val is not None else "—",
                    "점수": ms.get(key),
                    "설명": desc,
                })
            fdf = pd.DataFrame(frows)
            st.dataframe(
                fdf.style.map(score_bg, subset=["점수"])
                .format({"점수": fmt("{:.0f}")}),
                width='stretch', hide_index=True)

        # ---- 최근 실적 & 이벤트 ----
        ec1, ec2 = st.columns([1.3, 1])
        with ec1:
            st.markdown("#### 📑 최근 실적 (분기 EPS)")
            if res.earnings:
                erows = []
                for e in res.earnings:
                    erows.append({
                        "발표일": e.period,
                        "예상 EPS": e.eps_estimate,
                        "실제 EPS": e.eps_actual,
                        "서프라이즈": e.surprise_pct,
                        "매출": human_cap(e.revenue) if e.revenue else "—",
                    })
                edf = pd.DataFrame(erows)

                def surp_bg(v):
                    if v is None or (isinstance(v, float) and v != v):
                        return ""
                    return ("background-color:rgba(92,185,138,0.25);"
                            if v >= 0 else
                            "background-color:rgba(217,106,94,0.25);")
                st.dataframe(
                    edf.style.map(surp_bg, subset=["서프라이즈"])
                    .format({"예상 EPS": fmt("{:.2f}"),
                             "실제 EPS": fmt("{:.2f}"),
                             "서프라이즈": fmt("{:+.1f}%")}),
                    width='stretch', hide_index=True)
                st.caption("서프라이즈 = (실제−예상)/예상. 양수면 시장 기대치 상회.")
            else:
                st.info("실적 데이터가 없습니다.")
        with ec2:
            st.markdown("#### 📅 다가오는 이벤트")
            ev = res.events
            today = pd.Timestamp.today().normalize()
            if ev and ev.next_earnings_date:
                try:
                    d = pd.Timestamp(ev.next_earnings_date).normalize()
                    dday = (d - today).days
                    st.metric("다음 실적 발표", ev.next_earnings_date,
                              f"D-{dday}" if dday >= 0 else "발표 완료")
                except Exception:
                    st.write("다음 실적 발표:", ev.next_earnings_date)
            if ev and ev.ex_dividend_date:
                st.write(f"💰 배당락일: **{ev.ex_dividend_date}**"
                         + (f" (주당 ${ev.dividend_amount})"
                            if ev.dividend_amount else ""))
            if not ev or (not ev.next_earnings_date and not ev.ex_dividend_date):
                st.info("예정된 이벤트 정보가 없습니다.")
            st.caption("⚠️ 실적 발표 전후로는 주가 변동성이 커집니다.")

        # ---- 뉴스 분위기 ----
        st.markdown("#### 📰 해외 뉴스 분위기")
        if res.news and res.news.n_articles:
            nc = st.columns([1, 3])
            nc[0].metric("종합 분위기", res.news.label,
                         f"{res.news.score:.0f} / 100")
            nc[0].caption(f"긍정 {res.news.n_positive} · 중립 "
                          f"{res.news.n_neutral} · 부정 {res.news.n_negative}")
            nc[0].caption(f"신뢰도: **{res.news.confidence}**  ·  "
                          f"엔진: {res.news.engine}")
            with nc[1]:
                for it in res.news.items:
                    emo = ("🟢" if (it.sentiment or 0) > 0.05 else
                           "🔴" if (it.sentiment or 0) < -0.05 else "⚪")
                    title = it.title
                    if it.link:
                        title = f"[{title}]({it.link})"
                    src = f" · _{it.publisher}_" if it.publisher else ""
                    when = f" · {it.published}" if it.published else ""
                    st.markdown(f"{emo} {title}{src}{when}")
            st.caption("※ VADER 규칙기반 엔진 + 금융 전용 사전으로 분석합니다. "
                       "최신 기사일수록 비중이 높습니다. 참고용으로만 보세요.")
        else:
            st.info("뉴스 데이터가 없습니다. (실시간 모드에서 더 잘 동작합니다)")

# ============================ 탭 5: 백테스트 ============================
with tab5:
    st.subheader("전략 백테스트")
    st.caption("과거 데이터에 매매 전략을 적용해 '실제로 돈을 벌었을지' 검증하고 "
               "단순 보유(Buy&Hold)와 비교합니다.")
    bc = st.columns([1.4, 1.8, 1, 1])
    bt_sym = bc[0].selectbox("종목", [u.symbol for u in load_universe()],
                             key="bt_sym")
    strategy = bc[1].selectbox("전략", list(STRATEGIES.keys()))
    bt_period = bc[2].selectbox("기간", ["2y", "5y", "max"], index=1)
    commission = bc[3].number_input("수수료(%)", 0.0, 1.0, 0.1, step=0.05,
                                    help="편도 거래 수수료") / 100

    buy_th, sell_th = 60.0, 40.0
    if strategy == "종합 기술점수":
        tc = st.columns(2)
        buy_th = tc[0].slider("매수 기준 점수", 50, 90, 60)
        sell_th = tc[1].slider("매도 기준 점수", 10, 50, 40)

    with st.spinner("백테스트 실행 중..."):
        try:
            res = cached_backtest(bt_sym, provider_name, strategy, bt_period,
                                  commission, buy_th, sell_th)
        except Exception as e:
            res = None
            st.error(f"백테스트 실패: {e}")

    if res:
        m = res.metrics
        beat = m["초과수익률"] >= 0
        r1 = st.columns(4)
        r1[0].metric("전략 총수익률", f"{m['총수익률']:+.1f}%",
                     f"단순보유 대비 {m['초과수익률']:+.1f}%p",
                     delta_color="normal" if beat else "inverse")
        r1[1].metric("단순보유 수익률", f"{m['단순보유수익률']:+.1f}%")
        r1[2].metric("연복리(CAGR)", f"{m['연복리수익률(CAGR)']:+.1f}%")
        r1[3].metric("최종 자산", f"${m['최종자산']:,.0f}", "초기 $10,000")
        r2 = st.columns(4)
        r2[0].metric("최대낙폭(MDD)", f"{m['최대낙폭(MDD)']:.1f}%",
                     f"보유 {m['단순보유MDD']:.1f}%", delta_color="off")
        r2[1].metric("샤프지수", f"{m['샤프지수']:.2f}",
                     help="위험 대비 수익. 1 이상이면 양호")
        r2[2].metric("승률", f"{m['승률']:.0f}%", f"거래 {m['거래횟수']}회")
        r2[3].metric("시장 노출", f"{m['시장노출']:.0f}%",
                     help="기간 중 주식을 보유한 비율")

        # 자산곡선 비교
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=res.equity.index, y=res.equity,
                      name=f"전략: {strategy}", line=dict(color="#2f6fed",
                      width=2)))
        fig.add_trace(go.Scatter(x=res.benchmark.index, y=res.benchmark,
                      name="단순 보유", line=dict(color="#9aa5b1", width=1.5,
                      dash="dash")))
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10),
                          title="자산 성장 곡선 (초기 $10,000)",
                          legend=dict(orientation="h", y=1.12),
                          plot_bgcolor=C_PANEL, paper_bgcolor=C_PANEL)
        st.plotly_chart(fig, width='stretch')

        if not beat:
            st.info("💡 이 전략은 이 종목에서 단순 보유보다 못했습니다. "
                    "매매 타이밍이 늘 이득은 아니라는 점을 보여줍니다.")

        with st.expander(f"거래 내역 ({len(res.trades)}건)"):
            if res.trades:
                tdf = pd.DataFrame([{
                    "진입일": t.entry_date, "청산일": t.exit_date or "보유중",
                    "진입가": round(t.entry_price, 2),
                    "청산가": round(t.exit_price, 2) if t.exit_price else None,
                    "수익률": round(t.return_pct * 100, 2)
                    if t.return_pct is not None else None,
                } for t in res.trades])
                st.dataframe(
                    tdf.style.map(ret_bg, subset=["수익률"])
                    .format({"수익률": fmt("{:+.2f}%")}),
                    width='stretch', hide_index=True)
            else:
                st.write("거래가 없었습니다.")
        st.caption("⚠️ 과거 성과가 미래 수익을 보장하지 않습니다. 수수료·세금·"
                   "슬리피지를 단순화한 모델입니다.")

# ============================ 탭 3: 모의매매 ============================
with tab3:
    broker = get_broker()
    st.subheader("모의매매 계좌")
    held = list(broker.positions.keys())
    prices = {s: price_of(s, provider_name) or broker.positions[s].avg_price
              for s in held}

    m = st.columns(4)
    m[0].metric("현금", f"${broker.cash:,.0f}")
    m[1].metric("평가금액", f"${broker.position_value(prices):,.0f}")
    m[2].metric("총자산", f"${broker.equity(prices):,.0f}",
                f"{broker.total_return(prices)*100:+.2f}%")
    m[3].metric("실현손익", f"${broker.realized_pnl():,.0f}")

    st.markdown("#### 주문")
    oc = st.columns([1.5, 1, 1, 1, 1])
    order_sym = oc[0].text_input("종목", value=(held[0] if held else "AAPL")).upper()
    qty = oc[1].number_input("수량", min_value=0.0, value=10.0, step=1.0)
    live_px = price_of(order_sym, provider_name)
    px = oc[2].number_input("가격", min_value=0.0,
                            value=round(float(live_px), 2) if live_px else 100.0,
                            step=0.01)
    oc[3].write(""); oc[4].write("")
    if oc[3].button("🟢 매수", width='stretch'):
        try:
            broker.buy(order_sym, qty, px); broker.save()
            st.success(f"{order_sym} {qty}주 매수 @ ${px:.2f}")
        except (InsufficientFundsError, ValueError) as e:
            st.error(str(e))
    if oc[4].button("🔴 매도", width='stretch'):
        try:
            broker.sell(order_sym, qty, px); broker.save()
            st.success(f"{order_sym} {qty}주 매도 @ ${px:.2f}")
        except (InsufficientSharesError, ValueError) as e:
            st.error(str(e))

    st.markdown("#### 보유 종목")
    holdings = broker.holdings_table(prices)
    if holdings:
        st.dataframe(
            pd.DataFrame(holdings).style.map(ret_bg, subset=["수익률"]),
            width='stretch', hide_index=True)
    else:
        st.info("보유 종목이 없습니다. 위에서 매수해보세요.")

    with st.expander("거래 내역"):
        if broker.trades:
            st.dataframe(pd.DataFrame([t.__dict__ for t in broker.trades]),
                         width='stretch', hide_index=True)
        else:
            st.write("거래 내역이 없습니다.")

    if st.button("⚠️ 계좌 초기화"):
        st.session_state.broker = PaperBroker(
            cfg.paper_trading.initial_cash, cfg.paper_trading.commission)
        st.session_state.broker.save()
        st.rerun()

# ============================ 탭 4: 투자 가이드 ============================
with tab4:
    st.subheader("📖 개인투자자를 위한 사용 가이드")
    st.markdown("""
이 시스템은 **기술적 분석(차트)** 과 **기본적 분석(재무)** 을 합쳐 0~100점
**종합점수**를 매기고, 매수/보유/매도 의견을 제시합니다. 아래 순서로 쓰면 좋아요.

##### 1️⃣ 스크리너로 후보 찾기
- **시가총액 상위 50%** 처럼 우량주 위주로 좁히고, 관심 **섹터**를 고릅니다.
- 종합점수가 높은(초록색) 종목부터 살펴봅니다.

##### 2️⃣ 종목 상세로 검증하기
- **추천 배너**와 **판단 근거**로 왜 이 점수인지 확인합니다.
- **차트**(이동평균·RSI·MACD·볼린저)로 추세와 과열 여부를 봅니다.
- **재무 지표**로 회사가 실제로 돈을 잘 버는지 확인합니다.
- **최근 실적·이벤트·뉴스 분위기**로 단기 재료를 점검합니다.

##### 3️⃣ 모의매매로 연습하기
- 실제 돈 없이 매수/매도를 연습하고 수익률을 추적합니다.
""")
    with st.expander("📊 지표 한눈에 이해하기", expanded=True):
        st.markdown("""
| 지표 | 의미 | 읽는 법 |
|---|---|---|
| **이동평균(SMA)** | 일정 기간 평균 가격 | 단기선이 장기선 위 → 상승 추세(골든크로스) |
| **RSI** | 과매수/과매도 강도 | 70↑ 과열(조정 주의) · 30↓ 과매도(반등 기대) |
| **MACD** | 추세 전환 신호 | 히스토그램 0 위 → 상승 모멘텀 |
| **볼린저밴드** | 변동성 범위 | 하단 근접 → 저평가 · 상단 근접 → 고평가 |
| **PER** | 이익 대비 주가 | 낮을수록 저평가 (업종별 비교 필수) |
| **PBR** | 자산 대비 주가 | 1 근처면 자산가치 수준 |
| **ROE** | 자기자본이익률 | 15%↑면 우량 |
| **부채비율** | 재무 안정성 | 100%↓ 권장 |
""")
    with st.expander("✅ 매수 전 체크리스트"):
        st.markdown("""
- [ ] 종합점수가 60점 이상인가?
- [ ] 기술·펀더멘털 점수가 한쪽만 치우치지 않았나?
- [ ] 곧 **실적 발표**가 있나? (변동성 ↑ → 분할매수 고려)
- [ ] 뉴스 분위기에 큰 악재(소송·규제)는 없나?
- [ ] 한 종목에 자산을 몰지 않고 **분산**했나?
- [ ] **손절 기준**(예: -8%)을 미리 정했나?
""")
    st.warning("⚠️ 모든 점수와 추천은 참고 지표일 뿐 투자 자문이 아닙니다. "
               "최종 투자 판단과 그 결과의 책임은 전적으로 본인에게 있습니다.")
