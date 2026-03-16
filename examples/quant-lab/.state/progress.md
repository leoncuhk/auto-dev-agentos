# Research Progress

## Session 1 — 2026-03-10T09:00:00Z
**Role**: Theorizer
**Done**: Analyzed hypothesis, established baseline, designed EXP-001
**Baseline**: Sharpe Ratio = 0.84 (dual MA crossover, fast=10, slow=20)
**Target**: Sharpe Ratio >= 1.5
**Next**: EXP-001 — Parameter optimization of MA windows + short exposure

## Session 2 — 2026-03-10T10:15:00Z
**Role**: Executor
**Experiment**: EXP-001 — Optimize MA window parameters + reduce short exposure
**Metric**: 0.84 → 1.37
**Decision**: accepted
**Learnings**: Shorter fast window (8) catches trends earlier, slow=25 better noise filtering. Reducing short from -0.5 to -0.3 was a 'free' improvement.
**Next**: Try adding confirmation indicator to reduce false signals

## Session 3 — 2026-03-10T11:30:00Z
**Role**: Executor
**Experiment**: EXP-002 — MACD confirmation for crossover signals
**Metric**: 1.37 → 0.72
**Decision**: rejected (reverted)
**Learnings**: MACD + MA creates double-lag. Need a different type of signal, not another lagging indicator.
**Next**: Try RSI-based approach instead

## Session 4 — 2026-03-11T09:45:00Z
**Role**: Executor
**Experiment**: EXP-003 — RSI-based position sizing
**Metric**: 1.37 → 1.33
**Decision**: rejected (marginal degradation, reverted)
**Learnings**: RSI extremes coincide with strong trends in momentum-driven data. RSI sizing fights the trend. Key insight: use momentum-confirming indicators, not mean-reversion ones.
**Next**: Explore risk management layer

## Session 5 — 2026-03-11T11:00:00Z
**Role**: Executor
**Experiment**: EXP-004 — Per-trade stop-loss at -2%
**Metric**: 1.37 → error
**Decision**: error (reverted)
**Learnings**: Framework limitation — vectorized backtester can't do intra-bar exits. Need event-driven architecture for stop-loss.
**Next**: Skip price-level risk management, try signal-level approach instead

## Research Review — 2026-03-11T12:00:00Z
**Experiments analyzed**: EXP-001 to EXP-004
**Progress**: 4 experiments run | 1 accepted | Best metric: 1.37
**Target**: 1.5 | Distance: 0.13

### Experiment Summary
| EXP ID | Hypothesis | Metric | Status |
|--------|-----------|--------|--------|
| EXP-001 | Optimize MA windows + reduce short | 0.84 → 1.37 | accepted |
| EXP-002 | MACD confirmation | 1.37 → 0.72 | rejected |
| EXP-003 | RSI position sizing | 1.37 → 1.33 | rejected |
| EXP-004 | Stop-loss | 1.37 → error | error |

### Patterns Detected
1. Trend-confirming indicators (momentum, rate of change) work; mean-reversion indicators (RSI, MACD) fight the trend
2. Framework constraint: no intra-bar execution — all risk management must be signal-level, not price-level
3. The biggest untapped lever is position sizing by conviction — EXP-001's full/reduced binary is simplistic

### Recommended Next Directions
1. Add momentum factor (10-day price change) as confirmation — it CONFIRMS trends rather than fighting them
2. Implement conviction-based position sizing (strong/moderate/cautious tiers)
3. Test asymmetric short logic — go flat during conflicting signals instead of always shorting

### Anti-patterns to Avoid
1. DO NOT use MACD with MA crossover (double-lag)
2. DO NOT use RSI to size trend-following positions (fights the trend)
3. DO NOT attempt intra-bar stop-loss in vectorized framework

## Session 6 — 2026-03-12T10:30:00Z
**Role**: Executor
**Experiment**: EXP-005 — Momentum confirmation + asymmetric conviction sizing
**Metric**: 1.37 → 1.89 (TARGET EXCEEDED)
**Decision**: accepted
**Learnings**: Momentum is the right confirmation for trend-following. Asymmetric sizing (full/moderate/cautious) more powerful than binary. Biggest win: going flat during conflicting signals instead of shorting.
**Next**: Target exceeded. Try adaptive parameters for further improvement.

## Session 7 — 2026-03-13T14:00:00Z
**Role**: Executor
**Experiment**: EXP-006 — Adaptive MA windows based on volatility regime
**Metric**: 1.89 → 1.15
**Decision**: rejected (reverted)
**Learnings**: Simple regime switching creates boundary instability. Target already exceeded at 1.89 — further optimization has diminishing returns.
**Next**: Research complete. Target metric (1.5) achieved with Sharpe = 1.89.

## Research Review — 2026-03-13T15:00:00Z
**Experiments analyzed**: EXP-001 to EXP-006
**Progress**: 6 experiments run | 2 accepted | 3 rejected | 1 error | Best metric: 1.89
**Target**: 1.5 | Status: ACHIEVED (1.89)

### Final Experiment Summary
| EXP ID | Hypothesis | Metric | Status |
|--------|-----------|--------|--------|
| EXP-001 | Optimize MA + reduce short | 0.84 → 1.37 | accepted |
| EXP-002 | MACD confirmation | 1.37 → 0.72 | rejected |
| EXP-003 | RSI position sizing | 1.37 → 1.33 | rejected |
| EXP-004 | Stop-loss | 1.37 → error | error |
| EXP-005 | Momentum + conviction sizing | 1.37 → 1.89 | accepted |
| EXP-006 | Adaptive MA windows | 1.89 → 1.15 | rejected |

### Key Findings
1. **Momentum confirmation is the right partner for MA crossover** — confirms rather than contradicts the trend signal
2. **Asymmetric position sizing** by conviction level is more powerful than binary on/off signals
3. **Going flat during conflicting signals** (bear trend + positive momentum) was the single largest improvement
4. **Failed experiments were essential** — EXP-002 and EXP-003 failures directly informed the design of EXP-005

### Strategy Evolution
```
dual_ma_crossover (baseline)     → Sharpe 0.84
optimized_ma (EXP-001)           → Sharpe 1.37 (+63%)
ma_momentum (EXP-005)            → Sharpe 1.89 (+125% from baseline)
```
