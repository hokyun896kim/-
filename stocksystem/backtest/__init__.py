"""백테스트 계층: 전략을 과거 데이터로 검증."""
from .engine import BacktestResult, Trade, run_backtest
from .strategies import STRATEGIES

__all__ = ["BacktestResult", "Trade", "run_backtest", "STRATEGIES",
           "backtest_symbol"]


def backtest_symbol(symbol, provider, cfg, strategy_name, *, period="2y",
                    initial_cash=10_000.0, commission=0.001, **strat_kwargs):
    """심볼 + 전략 이름으로 한 번에 백테스트를 실행하는 헬퍼."""
    from ..analysis import technical as ta

    df = provider.price_history(symbol, period=period)
    ind = ta.compute_indicators(df, cfg.technical)
    strat = STRATEGIES[strategy_name]
    position = strat(ind, cfg.technical, **strat_kwargs)
    return run_backtest(ind, position, symbol=symbol.upper(),
                        strategy=strategy_name, initial_cash=initial_cash,
                        commission=commission)
