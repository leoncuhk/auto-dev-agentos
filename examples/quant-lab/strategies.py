"""
Quant Lab — Strategy Implementations
The active_strategy function is called by run_backtest.py.
Modify or swap strategies here to run experiments.

Strategy evolution (see .state/journal.json for details):
  dual_ma_crossover   → Baseline, Sharpe ~0.84
  optimized_ma        → EXP-001, parameter optimization, Sharpe ~1.37
  ma_momentum         → EXP-005, momentum confirmation, Sharpe ~1.89
"""
import numpy as np
import pandas as pd


def dual_ma_crossover(data, fast=10, slow=20):
    """
    Baseline strategy: Dual Moving Average Crossover.
    Buy when fast MA crosses above slow MA, sell when below.
    Baseline Sharpe Ratio: ~0.84
    """
    fast_ma = data["close"].rolling(window=fast).mean()
    slow_ma = data["close"].rolling(window=slow).mean()
    signals = pd.Series(0.0, index=data.index)
    signals[fast_ma > slow_ma] = 1.0
    signals[fast_ma <= slow_ma] = -0.5  # partial short
    return signals


def optimized_ma(data, fast=8, slow=25):
    """
    EXP-001: Optimized MA parameters + reduced short exposure.
    Sharpe: 0.84 → 1.37
    """
    fast_ma = data["close"].rolling(window=fast).mean()
    slow_ma = data["close"].rolling(window=slow).mean()
    signals = pd.Series(0.0, index=data.index)
    signals[fast_ma > slow_ma] = 1.0
    signals[fast_ma <= slow_ma] = -0.3  # reduced short exposure
    return signals


def ma_momentum(data, fast=8, slow=25, mom_period=10):
    """
    EXP-005: MA crossover + momentum confirmation + asymmetric sizing.
    Uses 10-day momentum to scale position size by conviction level.
    Sharpe: 1.37 → 1.89 (exceeds target of 1.5)
    """
    fast_ma = data["close"].rolling(window=fast).mean()
    slow_ma = data["close"].rolling(window=slow).mean()
    momentum = data["close"].pct_change(mom_period).fillna(0)

    bull = fast_ma > slow_ma
    bear = fast_ma <= slow_ma

    signals = pd.Series(0.0, index=data.index)
    # Strong buy: uptrend confirmed by strong momentum
    signals[bull & (momentum > 0.01)] = 1.0
    # Moderate buy: uptrend with neutral momentum
    signals[bull & (momentum > -0.01) & (momentum <= 0.01)] = 0.6
    # Cautious: uptrend but negative momentum — small position
    signals[bull & (momentum <= -0.01)] = 0.2
    # Confirmed downtrend: short
    signals[bear & (momentum < 0)] = -0.3
    # Downtrend but positive momentum: stay flat (conflicting signals)
    signals[bear & (momentum >= 0)] = 0.0
    return signals


# === Active strategy (this is what run_backtest.py calls) ===
# Change this to test different strategies:
#   active_strategy = dual_ma_crossover   # baseline ~0.84
#   active_strategy = optimized_ma        # EXP-001  ~1.37
#   active_strategy = ma_momentum         # EXP-005  ~1.89
active_strategy = ma_momentum
