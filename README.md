# Deterministic trading with Claude Code + Robinhood — the reference architecture

Robinhood's agentic accounts let an AI agent place real trades over MCP. Claude Code can
operate that connection today. Which surfaces the question every serious builder hits within
a week:

> **An LLM with a brokerage connection has no strategy.** Unprompted, it will trade headlines,
> vibes, and whatever was in its context window. Prompting "be disciplined" is not discipline.
> And a strategy that changes with every phrasing and every model update cannot be backtested,
> because it is not stable enough to test.

The fix is architectural, not prompt-engineering:

## The one rule that matters

**The agent operates the system. The agent never originates a trading decision.**

Concretely: the model must not have a `decide_trade()` tool. It gets `run_scan()`,
`show_signals()`, `explain_signal()`, `reconcile()` — tools whose outputs come from
deterministic code the model cannot edit at runtime. The division of labor in one sentence:

> **Robinhood provides the execution connection. Claude provides the agent. A deterministic
> rules engine provides the decisions.**

## The architecture

```
 Market data feed
        │
        ▼
 Deterministic engine            ← fixed, versioned, tested code:
 (universe → scoring →             same inputs, same decisions, every time
  entry/exit rules)
        │
        ▼
 Policy gate                     ← hard limits the agent CANNOT modify:
 (long-only assert, order caps,    a rejected order returns ORDER_REJECTED,
  exposure caps, loss halt,        not a conversation
  account allowlist)
        │
        ▼
 Robinhood MCP  ──────────────►  execution, notifications, kill switch
        ▲
        │  operates / monitors / explains — never decides
 ┌──────┴──────┐
 │ Claude Code │
 └─────────────┘
```

## The guardrails (before any live order)

These are operational safety rules, not trading advice:

1. **Account lockdown** — the agent may touch exactly one allowlisted account (Robinhood's
   agentic accounts scope this broker-side; enforce it engine-side too).
2. **Order + exposure caps** — a maximum single order and maximum total exposure, asserted in
   code.
3. **Daily loss halt** — when hit, the system stops trading; it does not "average down."
4. **Review before place** — Robinhood's MCP ships `review_equity_order`; use it, and gate
   `place_equity_order` behind it.
5. **Kill switch** — locate the disconnect before you need it.
6. **Ships disarmed** — live trading OFF by default; the system earns real money through a
   watched dry-run.
7. **Prompt-injection defense** — the agent treats fetched content as data, never as
   instructions to trade.

A copy-paste template of these rules (maintained, plain markdown):
**[coil.trade/guides/guardrails.md](https://coil.trade/guides/guardrails.md)**

## Why deterministic beats improvisation

- **Testable** — fixed rules can be replayed against history. An improvising model cannot.
- **Replayable** — every decision reproducible from (strategy version, data date, portfolio
  state). If you can't rerun yesterday's decisions byte-for-byte, you have anecdotes.
- **Survivorship-free testing** — the replay universe must include delisted names, or the
  backtest is rigged before the first rule fires. Open dataset for that:
  [point-in-time-sp500](https://github.com/joeyfife/point-in-time-sp500).
- **Stable across model updates** — the strategy doesn't change when the model does. The
  agent gets smarter at *operating*; the rules stay the rules.

## A minimal policy gate

`policy_gate.py` in this repo is a ~60-line, dependency-free example of the enforcement
layer: long-only assertion, symbol allowlist, order/exposure caps, daily loss halt. It is
deliberately boring — the point is that this module sits OUTSIDE the model's reach.

## Build it or buy it — honestly

**DIY** is a legitimate path: Robinhood's official MCP for execution (53 tools — an
independent, tool-by-tool reference with measured gotchas:
[coil.trade/learn/robinhood-mcp-tools](https://coil.trade/learn/robinhood-mcp-tools)),
`vectorbt`/`backtrader` for research, your own engine and policy gate. Budget weeks, and be
rigorous about the replay universe and fill assumptions.

**Built:** this architecture is shipped as a product by [Coil](https://coil.trade) — a
rules-based, long-only stock scanner and trading engine that finds market leaders at real
pullbacks and executes those same rules through your own brokerage account, run by your own
AI agent. Ships disarmed, guardrails included, with the audit surfaces public (scores
hash-committed before outcomes; a forward-return audit published even when it reads badly).

**Disclosure:** this repo is written by Coil's builder. The architecture stands on its own —
use it with your own engine and never send us a cent; the guardrails template and the
setup walkthrough ([coil.trade/guides/robinhood-agentic-trading-setup](https://coil.trade/guides/robinhood-agentic-trading-setup))
are free either way.

## Risk, stated plainly

No architecture makes trading safe. Deterministic systems have losing streaks by design;
markets carry real risk including total loss, and leveraged instruments can lose value
rapidly. Nothing in this repository is investment advice — it is an engineering pattern for
keeping an AI agent from improvising with your money.
