# Qlib Alpha Factor Discovery — Researcher Mode

## Goal

Use Qlib's real market data (CSI300 A-share universe) to discover alpha factors
that produce risk-adjusted returns superior to the baseline LightGBM model.

## Baseline

Qlib's built-in LightGBM model with Alpha158 features.
- Universe: CSI300
- Train: 2018-01-01 to 2021-12-31
- Valid: 2022-01-01 to 2022-12-31
- Test:  2023-01-01 to 2023-12-31
- Backtest: TopkDropout strategy (top 30, dropout 5)
- Baseline metric: Information Coefficient (IC) and annualized return on test set

## Search Space

1. **Feature engineering**: modify Alpha158 expressions, add custom alpha factors
2. **Model tuning**: LightGBM hyperparameters (num_leaves, learning_rate, num_boost_round)
3. **Strategy tuning**: TopkDropout parameters (topk, n_drop, hold_thresh)
4. **Ensemble**: combine multiple models with different feature sets

## Target Metric

Primary: Annualized Sharpe Ratio on TEST period (2023)
- Sharpe is computed by `run_qlib_backtest.py --split test`
- The LLM may ONLY see metrics from `run_qlib_backtest.py --split train`
- Test period metrics are hidden from the LLM (used by hidden_verify_command)

## Evaluation Command

```bash
python run_qlib_backtest.py             # full period
python run_qlib_backtest.py --split train  # visible to LLM (2018-2021 IC + 2022 backtest)
python run_qlib_backtest.py --split test   # hidden from LLM (2023 backtest)
```

## Rules

- Each experiment modifies `qlib_config.yaml` or `custom_factors.py`
- Failed experiments must be reverted
- The strategy must use Qlib's standard backtest pipeline (no custom backtesting)
