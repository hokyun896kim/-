"""실시간 시총 캐시 및 라이브 캡 랭킹 테스트."""
from datetime import date, timedelta

from stocksystem.data import SampleProvider
from stocksystem.data import marketcap as mc
from stocksystem.data.universe import filter_universe, effective_cap, load_universe


def test_refresh_and_load(tmp_path):
    path = tmp_path / "caps.json"
    provider = SampleProvider()
    caps = mc.refresh(provider, symbols=["AAPL", "MSFT", "NVDA"], path=path)
    assert set(caps) == {"AAPL", "MSFT", "NVDA"}
    assert all(v > 0 for v in caps.values())

    loaded = mc.get_caps(path)
    assert loaded.keys() == caps.keys()
    assert mc.last_updated(path) == date.today().isoformat()


def test_is_stale(tmp_path):
    path = tmp_path / "caps.json"
    assert mc.is_stale(path=path) is True          # 파일 없음 → stale
    mc.refresh(SampleProvider(), symbols=["AAPL"], path=path)
    assert mc.is_stale(path=path) is False         # 방금 갱신 → fresh


def test_progress_callback(tmp_path):
    path = tmp_path / "caps.json"
    calls = []
    mc.refresh(SampleProvider(), symbols=["AAPL", "MSFT"],
               progress=lambda d, t, s: calls.append((d, t, s)), path=path)
    assert calls[-1][0] == calls[-1][1] == 2        # done == total == 2


def test_effective_cap_prefers_live():
    stock = load_universe()[0]
    snap = stock.market_cap_b * 1e9
    # 라이브 캡이 있으면 그것을 사용
    assert effective_cap(stock, {stock.symbol: 999e9}) == 999e9
    # 없으면 스냅샷
    assert effective_cap(stock, {}) == snap
    assert effective_cap(stock, None) == snap


def test_live_caps_change_ranking():
    # 스냅샷상 최하위 종목을 거대 시총으로 올리면 상위 10%에 들어와야
    snap_sorted = filter_universe(top_pct=100)
    smallest = snap_sorted[-1].symbol
    live = {smallest: 9e12}   # 9조 달러로 강제
    top10 = filter_universe(top_pct=10, live_caps=live)
    assert smallest in [s.symbol for s in top10]


def test_market_cap_provider_method():
    cap = SampleProvider().market_cap("AAPL")
    assert cap is not None and cap > 0
