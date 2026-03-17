---
name: ict-signal-generation
description: ICT (Inner Circle Trader) 4-step framework and signal generation for OpenClaw. Use when implementing ICT concepts, 4-step confirmation, signal generation, or analyzing market structure (OB, FVG, Liquidity).
---

# ICT Signal Generation

Professional implementation of the Inner Circle Trader (ICT) 4-step confirmation framework.

## 4-Step Confirmation Framework

1. **Trend Analysis (4H)**: Identify market direction and structure (HH/HL vs LH/LL).
2. **Zone Identification (30M)**: Find high-probability entry zones (Order Blocks, Fair Value Gaps, Liquidity Pools).
3. **Volume Confirmation (5M)**: Confirm exhaustion and reversal with volume ratio > 1.5.
4. **Order Flow Confirmation**: Validate control shift using CVD alignment, DOM imbalance, and tape reading.

## Key Features
- **Signal Quality Grading**: Automated A+ to D grading based on ICT criteria.
- **Killzone Detection**: Time-based filters for London, NY AM, and NY PM sessions.
- **Premium/Discount Zones**: Context-aware direction filtering based on range equilibrium.
- **Optimal Trade Entry (OTE)**: Fibonacci-based retracement levels (0.618-0.786).

## Best Practices
- **Hard Block on Unclear Trend**: If the 4H trend is unclear, no trades are allowed.
- **5M Structure Shift**: Always wait for a structure shift on the 5M timeframe before entry.
- **Minimum Quality Threshold**: Only trade A+ and A signals in production to ensure high win rates.
- **Killzone Timing**: Prioritize trades that occur during official ICT killzones.
