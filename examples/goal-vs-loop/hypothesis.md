# Strategy Optimization — Goal vs Loop Comparison

## Goal
Improve the baseline dual MA crossover strategy's Sharpe Ratio from ~0.84 to >= 1.5.

## Baseline
- Strategy: dual_ma_crossover (fast=10, slow=20, short=-0.5)
- Data: 500-day synthetic price series with 15% momentum autocorrelation
- Baseline Sharpe: 0.84
- Run command: `python run_backtest.py`

## Search Space
1. Parameter optimization: MA window lengths (fast: 5-15, slow: 15-40), short exposure (0 to -0.5)
2. New indicators: momentum, rate-of-change, volatility-based sizing
3. Position sizing: conviction-based tiers instead of binary signals
4. Signal filtering: go flat on conflicting signals

## Target Metric
Sharpe Ratio >= 1.5 (as output by run_backtest.py)

## Rules
- Modify strategies.py to implement experiments
- Run `python run_backtest.py` to evaluate
- If Sharpe drops below 0.84, revert immediately
- Record learnings from every experiment (including failures)
