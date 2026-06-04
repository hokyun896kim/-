"""모의매매(페이퍼 트레이딩) 엔진.

실제 돈 없이 매수/매도를 연습한다. 계좌 상태(현금, 보유종목, 거래내역)를
JSON 파일로 영속화하여 세션 간 유지된다.

핵심 개념:
- 현금(cash)과 보유 포지션(positions)을 추적
- 매수 시 평균단가 갱신, 매도 시 실현손익 기록
- 현재가를 주입하면 평가금액/수익률 계산
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_STATE = DATA_DIR / "paper_account.json"


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_price: float          # 평균 매입단가

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_price


@dataclass
class Trade:
    timestamp: str
    symbol: str
    side: str                 # "buy" / "sell"
    quantity: float
    price: float
    commission: float = 0.0
    realized_pnl: float = 0.0 # 매도 시 실현손익

    @property
    def gross(self) -> float:
        return self.quantity * self.price


class InsufficientFundsError(Exception):
    pass


class InsufficientSharesError(Exception):
    pass


class PaperBroker:
    def __init__(self, initial_cash: float = 100_000.0,
                 commission: float = 0.0):
        self.initial_cash = float(initial_cash)
        self.cash = float(initial_cash)
        self.commission = float(commission)   # 거래대금 대비 비율
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []

    # ----------------------------- 거래 -----------------------------
    def _fee(self, gross: float) -> float:
        return round(gross * self.commission, 4)

    def buy(self, symbol: str, quantity: float, price: float) -> Trade:
        symbol = symbol.upper()
        if quantity <= 0 or price <= 0:
            raise ValueError("수량과 가격은 0보다 커야 합니다.")
        gross = quantity * price
        fee = self._fee(gross)
        total = gross + fee
        if total > self.cash + 1e-9:
            raise InsufficientFundsError(
                f"현금 부족: 필요 ${total:,.2f}, 보유 ${self.cash:,.2f}")

        self.cash -= total
        pos = self.positions.get(symbol)
        if pos:
            new_qty = pos.quantity + quantity
            pos.avg_price = (pos.cost_basis + gross) / new_qty
            pos.quantity = new_qty
        else:
            self.positions[symbol] = Position(symbol, quantity, price)

        trade = Trade(_now(), symbol, "buy", quantity, price, fee)
        self.trades.append(trade)
        return trade

    def sell(self, symbol: str, quantity: float, price: float) -> Trade:
        symbol = symbol.upper()
        if quantity <= 0 or price <= 0:
            raise ValueError("수량과 가격은 0보다 커야 합니다.")
        pos = self.positions.get(symbol)
        if not pos or pos.quantity < quantity - 1e-9:
            held = pos.quantity if pos else 0
            raise InsufficientSharesError(
                f"보유 수량 부족: 매도 {quantity}, 보유 {held}")

        gross = quantity * price
        fee = self._fee(gross)
        realized = (price - pos.avg_price) * quantity - fee
        self.cash += gross - fee

        pos.quantity -= quantity
        if pos.quantity <= 1e-9:
            del self.positions[symbol]

        trade = Trade(_now(), symbol, "sell", quantity, price, fee, realized)
        self.trades.append(trade)
        return trade

    # ----------------------------- 평가 -----------------------------
    def position_value(self, prices: dict[str, float]) -> float:
        """보유 포지션의 현재 평가금액 합."""
        total = 0.0
        for sym, pos in self.positions.items():
            px = prices.get(sym, pos.avg_price)
            total += pos.quantity * px
        return total

    def equity(self, prices: dict[str, float]) -> float:
        """총 자산 = 현금 + 평가금액."""
        return self.cash + self.position_value(prices)

    def total_return(self, prices: dict[str, float]) -> float:
        """초기 자본 대비 총 수익률(소수)."""
        return self.equity(prices) / self.initial_cash - 1.0

    def realized_pnl(self) -> float:
        return round(sum(t.realized_pnl for t in self.trades
                         if t.side == "sell"), 2)

    def holdings_table(self, prices: dict[str, float]) -> list[dict]:
        """보유종목 상세 (수익률 포함)."""
        rows = []
        for sym, pos in self.positions.items():
            px = prices.get(sym, pos.avg_price)
            mkt = pos.quantity * px
            pnl = mkt - pos.cost_basis
            ret = (px / pos.avg_price - 1.0) if pos.avg_price else 0.0
            rows.append({
                "종목": sym,
                "수량": round(pos.quantity, 4),
                "평균단가": round(pos.avg_price, 2),
                "현재가": round(px, 2),
                "평가금액": round(mkt, 2),
                "평가손익": round(pnl, 2),
                "수익률": round(ret * 100, 2),
            })
        return rows

    # ----------------------------- 영속화 -----------------------------
    def to_dict(self) -> dict:
        return {
            "initial_cash": self.initial_cash,
            "cash": self.cash,
            "commission": self.commission,
            "positions": [asdict(p) for p in self.positions.values()],
            "trades": [asdict(t) for t in self.trades],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PaperBroker":
        b = cls(d.get("initial_cash", 100_000.0), d.get("commission", 0.0))
        b.cash = d.get("cash", b.initial_cash)
        b.positions = {p["symbol"]: Position(**p) for p in d.get("positions", [])}
        b.trades = [Trade(**t) for t in d.get("trades", [])]
        return b

    def save(self, path: str | Path = DEFAULT_STATE) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str | Path = DEFAULT_STATE,
             initial_cash: float = 100_000.0,
             commission: float = 0.0) -> "PaperBroker":
        path = Path(path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        return cls(initial_cash, commission)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
