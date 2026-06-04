"""유니버스 로딩/필터 및 공급자 확장 기능 테스트."""
from stocksystem.data import SampleProvider
from stocksystem.data.universe import (filter_universe, load_universe,
                                       market_cap_of, sectors)


def test_universe_loads_and_sorted():
    u = load_universe()
    assert len(u) > 50
    caps = [s.market_cap_b for s in u]
    assert caps == sorted(caps, reverse=True)   # 시총 내림차순


def test_top_pct_filter_halves():
    full = filter_universe(top_pct=100)
    half = filter_universe(top_pct=50)
    assert len(half) <= len(full) / 2 + 1
    # 상위 절반은 전부 중앙값 이상의 시총
    assert half[-1].market_cap_b >= full[len(full) // 2].market_cap_b


def test_sector_filter():
    tech = filter_universe(top_pct=100, sector="Technology")
    assert all(s.sector == "Technology" for s in tech)
    assert len(tech) > 0


def test_sectors_listed():
    secs = sectors()
    assert "Technology" in secs
    assert "Healthcare" in secs


def test_market_cap_lookup():
    assert market_cap_of("AAPL") is not None
    assert market_cap_of("NONEXISTENT") is None


def test_sample_provider_news():
    news = SampleProvider().news("AAPL")
    assert len(news) > 0
    assert all(n.title for n in news)


def test_sample_provider_earnings():
    rows = SampleProvider().earnings_history("MSFT")
    assert len(rows) == 4
    assert rows[0].eps_actual is not None
    # 서프라이즈 계산 가능
    assert rows[0].surprise_pct is not None


def test_sample_provider_events():
    ev = SampleProvider().events("NVDA")
    assert ev.next_earnings_date is not None


def test_sample_fundamentals_use_universe_cap():
    f = SampleProvider().fundamentals("AAPL")
    # 유니버스 스냅샷(3300B)과 일치
    assert f.market_cap == 3300 * 1e9
    assert f.sector == "Technology"
