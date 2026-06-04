"""모의매매 엔진 테스트."""
import pytest

from stocksystem.portfolio import (
    PaperBroker, InsufficientFundsError, InsufficientSharesError,
)


def test_buy_reduces_cash_and_creates_position():
    b = PaperBroker(10_000)
    b.buy("AAPL", 10, 100)
    assert b.cash == pytest.approx(9_000)
    assert b.positions["AAPL"].quantity == 10
    assert b.positions["AAPL"].avg_price == 100


def test_buy_averages_price():
    b = PaperBroker(10_000)
    b.buy("AAPL", 10, 100)   # 1000
    b.buy("AAPL", 10, 200)   # 2000
    pos = b.positions["AAPL"]
    assert pos.quantity == 20
    assert pos.avg_price == pytest.approx(150)


def test_insufficient_funds():
    b = PaperBroker(500)
    with pytest.raises(InsufficientFundsError):
        b.buy("AAPL", 10, 100)


def test_sell_realizes_pnl_and_returns_cash():
    b = PaperBroker(10_000)
    b.buy("AAPL", 10, 100)
    t = b.sell("AAPL", 10, 150)
    assert t.realized_pnl == pytest.approx(500)
    assert "AAPL" not in b.positions          # 전량 매도 → 포지션 제거
    assert b.cash == pytest.approx(10_500)


def test_partial_sell_keeps_position():
    b = PaperBroker(10_000)
    b.buy("AAPL", 10, 100)
    b.sell("AAPL", 4, 120)
    assert b.positions["AAPL"].quantity == 6
    assert b.positions["AAPL"].avg_price == 100  # 평단가 유지


def test_oversell_raises():
    b = PaperBroker(10_000)
    b.buy("AAPL", 5, 100)
    with pytest.raises(InsufficientSharesError):
        b.sell("AAPL", 10, 100)


def test_commission_applied():
    b = PaperBroker(10_000, commission=0.01)
    b.buy("AAPL", 10, 100)   # gross 1000 + fee 10
    assert b.cash == pytest.approx(8_990)


def test_equity_and_return():
    b = PaperBroker(10_000)
    b.buy("AAPL", 10, 100)              # 현금 9000, 포지션 1000
    prices = {"AAPL": 150}
    assert b.equity(prices) == pytest.approx(9_000 + 1_500)
    assert b.total_return(prices) == pytest.approx(0.05)


def test_holdings_table():
    b = PaperBroker(10_000)
    b.buy("MSFT", 5, 200)
    rows = b.holdings_table({"MSFT": 220})
    assert rows[0]["종목"] == "MSFT"
    assert rows[0]["수익률"] == pytest.approx(10.0)


def test_persistence_roundtrip(tmp_path):
    b = PaperBroker(10_000, commission=0.001)
    b.buy("AAPL", 10, 100)
    b.sell("AAPL", 5, 120)
    p = tmp_path / "acct.json"
    b.save(p)

    loaded = PaperBroker.load(p)
    assert loaded.cash == pytest.approx(b.cash)
    assert loaded.positions["AAPL"].quantity == 5
    assert len(loaded.trades) == 2
    assert loaded.commission == 0.001
