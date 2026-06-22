"""Strategy file — modified by the loop to find improvements."""
import numpy as np
import pandas as pd

def dual_ma_crossover(data, fast=10, slow=20):
    """Baseline: Sharpe ~0.84"""
    fast_ma = data["close"].rolling(window=fast).mean()
    slow_ma = data["close"].rolling(window=slow).mean()
    spread = (fast_ma - slow_ma) / slow_ma
    signals = (spread * 25).clip(lower=0.0, upper=1.0).fillna(0.0)
    return signals

# Active strategy (the loop modifies this)
active_strategy = dual_ma_crossover
