# 06. Calibration Assumptions from Reference Dataset Profiling

## 1. Purpose

This file converts the profiling results from public reference datasets into concrete assumptions for the synthetic simulation.

Reference datasets profiled:

1. ULB Credit Card Fraud Detection
2. BankSim
3. PaySim

The project will not copy these datasets as the main experimental data. Instead, the simulation will use their high-level statistical patterns to calibrate assumptions about:

- fraud rarity
- class imbalance
- transaction amount skew
- transaction category/type mix
- differences between legitimate and fraudulent transaction behavior

## 2. Profiling summary

### 2.1. ULB Credit Card Fraud Detection

Rows: 284,807

Fraud count: 492

Fraud rate: 0.1727 percent

Amount distribution:

- Mean amount: 88.35
- Median amount: 22.00
- P95 amount: 365.00
- P99 amount: 1,017.97
- Max amount: 25,691.16

Amount by label:

Legitimate transactions:

- Mean: 88.29
- Median: 22.00
- P95: 364.41
- P99: 1,016.97
- Max: 25,691.16

Fraud transactions:

- Mean: 122.21
- Median: 9.25
- P95: 640.91
- P99: 1,357.43
- Max: 2,125.87

Interpretation:

ULB shows extreme class imbalance. Fraud is rare. Fraud amount is not always higher than legitimate amount; in fact, fraud median amount is lower than legitimate median. This is important because the simulation should not assume that all fraud is simply high-amount fraud.

### 2.2. BankSim

Rows: 594,643

Fraud count: 7,200

Fraud rate: 1.2108 percent

Amount distribution:

- Mean amount: 37.89
- Median amount: 26.90
- P95 amount: 79.28
- P99 amount: 236.76
- Max amount: 8,329.96

Amount by label:

Legitimate transactions:

- Mean: 31.85
- Median: 26.61
- P95: 72.81
- P99: 153.76
- Max: 2,144.86

Fraud transactions:

- Mean: 530.93
- Median: 319.18
- P95: 1,889.59
- P99: 4,774.79
- Max: 8,329.96

Top categories:

- es_transportation: 84.94 percent
- es_food: 4.42 percent
- es_health: 2.71 percent
- es_wellnessandbeauty: 2.54 percent
- es_fashion: 1.09 percent

Interpretation:

BankSim is useful for merchant/category-based transaction simulation. Fraud amount is much higher than legitimate amount in this dataset, so it supports a high-amount fraud strategy. However, because ULB shows another pattern, high amount should be only one fraud strategy, not the only fraud strategy.

### 2.3. PaySim

Rows: 6,362,620

Fraud count: 8,213

Fraud rate: 0.1291 percent

Amount distribution:

- Mean amount: 179,861.90
- Median amount: 74,871.94
- P95 amount: 518,634.20
- P99 amount: 1,615,979.47
- Max amount: 92,445,516.64

Amount by label:

Legitimate transactions:

- Mean: 178,197.04
- Median: 74,684.72
- P95: 515,610.42
- P99: 1,586,064.17
- Max: 92,445,516.64

Fraud transactions:

- Mean: 1,467,967.30
- Median: 441,423.44
- P95: 8,006,429.04
- P99: 10,000,000.00
- Max: 10,000,000.00

Top transaction types:

- CASH_OUT: 35.17 percent
- PAYMENT: 33.81 percent
- CASH_IN: 21.99 percent
- TRANSFER: 8.38 percent
- DEBIT: 0.65 percent

Interpretation:

PaySim supports the use of synthetic data for financial fraud simulation. It also shows strong class imbalance and a heavy-tailed amount distribution. Fraud transactions are much larger on average, especially in transfer/cash-out-like behavior.

## 3. Calibration decisions for the thesis simulation

### 3.1. Fraud rate scenarios

Instead of using one fraud rate, the simulation should run multiple scenarios.

Recommended scenarios:

1. Low fraud scenario: 0.15 percent
   - Inspired by ULB and PaySim.
   - Represents highly imbalanced transaction fraud.

2. Medium fraud scenario: 1.0 percent
   - Inspired by BankSim.
   - Useful for clearer policy comparison in MVP.

3. Stress fraud scenario: 3.0 percent
   - Not a claim about real-world base rate.
   - Used to stress-test analyst capacity and policy robustness.

Reasoning:

A single fraud rate can hide policy trade-offs. Multiple scenarios allow the thesis to test whether a policy remains useful when the risk environment changes.

### 3.2. Amount distribution

The simulation should use a skewed distribution, preferably log-normal or mixture log-normal.

Recommended design:

- Normal transaction amount should be right-skewed.
- Median should be much lower than P95/P99.
- Customer segments should have different amount distributions.
- Fraud transactions should include both high-amount fraud and low/medium-amount fraud.

Why:

ULB shows that fraud is not always high amount. BankSim and PaySim show that high-amount fraud is still an important strategy. Therefore, the simulation should include multiple fraud strategies rather than a single amount rule.

### 3.3. Customer segments

Recommended customer segments:

1. Low value customers
   - Smaller amount.
   - Lower frequency.
   - Lower false positive risk from high amount.

2. Medium value customers
   - Stable transaction pattern.
   - Useful baseline group.

3. High value customers
   - Larger normal amount.
   - Important for testing false positives because a simple amount threshold can wrongly flag them.

### 3.4. Fraud strategies

Recommended fraud strategies:

1. High amount fraud
   - Calibrated by BankSim and PaySim fraud amount patterns.

2. Low amount probing fraud
   - Inspired by the ULB finding that fraud median amount can be low.
   - Represents small test transactions before larger attacks.

3. Burst velocity fraud
   - Multiple transactions in a short time window.

4. Late/unusual hour fraud
   - Transactions outside a customer normal activity window.

5. Merchant/category abuse
   - Certain merchant categories/types have higher risk.

6. Mixed strategy fraud
   - Combines amount, velocity, timing and category signals.

### 3.5. Transaction type/category

Use PaySim transaction types and BankSim categories as references.

Minimal transaction categories for MVP:

- payment
- transfer
- cash_out
- transportation
- food
- health
- retail
- digital_services
- travel
- high_risk_other

Risk assumptions:

- transfer and cash_out-like transactions can have higher risk in some scenarios.
- certain categories can be assigned higher merchant risk.
- transportation/payment categories should dominate normal transactions if using BankSim-inspired distribution.

### 3.6. Risk score design

Risk score should not be based only on amount.

Recommended drivers:

- amount_anomaly_signal
- txn_count_1h
- txn_count_24h
- unusual_hour_signal
- merchant_risk_signal
- device_or_channel_risk_signal
- customer_segment_baseline_risk

Reasoning:

Public datasets show class imbalance and amount skew, but the thesis question is about decisioning. Therefore, risk score must produce evidence that can be used by policy and analyst review.

### 3.7. Policy comparison

The first simulation should compare at least 3 policies:

1. Rule-based only
   - amount threshold plus velocity threshold.

2. Risk score threshold
   - approve/review/high-priority review by score.

3. Risk score + analyst review + AI explanation
   - review queue with analyst capacity and reduced review time when AI explanation is enabled.

Optional fourth policy:

4. Risk score + analyst review without AI explanation

This fourth policy is useful because it isolates the incremental value of AI explanation.

## 4. Recommended MVP simulation parameters

Initial config:

- n_customers: 1,000
- simulation_days: 30
- average_transactions_per_customer_per_day: 0.5 to 1.2 depending on segment
- fraud_rate: run scenarios at 0.15 percent, 1.0 percent and 3.0 percent
- analyst_capacity_per_day: 50, 100 and 200 cases depending on scenario
- cost_per_false_positive: configurable
- cost_per_review: configurable
- cost_per_ai_call: configurable
- customer_friction_cost: configurable

Risk levels:

- Low: 0-39
- Medium: 40-69
- High: 70-84
- Critical: 85-100

## 5. Key warnings for the thesis

### 5.1. Do not claim real production fraud accuracy

The simulation is not proof that the model detects real-world fraud. It is a controlled environment for studying decision mechanisms.

### 5.2. Do not make fraud equal to high amount only

This would be too simplistic and contradicted by ULB profiling.

### 5.3. Do not optimize only PR-AUC or recall

The thesis should show that model metrics are not enough. Business and operational metrics matter.

### 5.4. Do not hide synthetic assumptions

The report should clearly state how data is generated and why each assumption is chosen.

## 6. How to write this in the report

Suggested paragraph:

To calibrate the synthetic simulation, this study profiles three public fraud transaction datasets: ULB Credit Card Fraud Detection, BankSim and PaySim. These datasets show that transaction fraud is highly imbalanced, with fraud rates ranging from around 0.13 percent to 1.21 percent in the profiled sources. They also show strongly right-skewed transaction amount distributions. However, the relationship between fraud and transaction amount is not uniform across datasets: BankSim and PaySim show fraud transactions with substantially higher amounts, while ULB shows that fraud median amount can be lower than legitimate median amount. Therefore, the simulation models fraud as a mixture of strategies, including high-amount attacks, low-amount probing, burst velocity, unusual-hour behavior and merchant/category abuse.

## 7. Next step

The next step is to implement the first data generator using these calibration assumptions.

Target script:

scripts/generate_simulation_data.py

Expected outputs:

- customers.csv
- transactions.csv
- behavior_features.csv
- risk_scores.csv
- policy_decisions.csv
- analyst_reviews.csv
- outcomes.csv
- simulation_metrics.csv
- case_examples.json
