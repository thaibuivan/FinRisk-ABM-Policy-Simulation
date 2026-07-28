# Scenario Comparison Summary

This table compares simulated policy outcomes across fraud pressure and analyst capacity scenarios.

| scenario      | fraud_rate | alerts_sent_to_analyst | precision_flagged | recall_flagged | review_overflow | fraud_loss_prevented | fraud_loss_realized | false_positive_cost | analyst_cost | net_benefit |
| ------------- | ---------- | ---------------------- | ----------------- | -------------- | --------------- | -------------------- | ------------------- | ------------------- | ------------ | ----------- |
| low_fraud     | 0.001676   | 867.0                  | 0.0208            | 0.383          | 0.0             | 10718.79             | 3049.17             | 5981.24             | 2835.38      | -1147.0     |
| baseline      | 0.010642   | 884.0                  | 0.1233            | 0.3695         | 0.0             | 79815.84             | 19008.27            | 5677.89             | 2896.08      | 52233.6     |
| stress_fraud  | 0.030247   | 1027.0                 | 0.3009            | 0.3606         | 0.0             | 247481.21            | 52692.78            | 5494.2              | 3494.7       | 185799.53   |
| low_capacity  | 0.010642   | 884.0                  | 0.1233            | 0.3695         | 289.0           | 67373.77             | 35597.67            | 5677.89             | 2093.25      | 24004.96    |
| high_capacity | 0.010642   | 884.0                  | 0.1233            | 0.3695         | 0.0             | 79815.84             | 19008.27            | 5677.89             | 2896.08      | 52233.6     |

## How to read this table

- `precision_flagged`: among transactions sent to analyst, how many are truly simulated fraud.
- `recall_flagged`: among all simulated fraud transactions, how many are sent to analyst.
- `review_overflow`: transactions that should be reviewed but exceed daily analyst capacity.
- `net_benefit`: fraud loss prevented minus realized fraud loss, false positive cost, and analyst cost.

The goal is not only to maximize model recall, but to find a decision mechanism that balances risk reduction, analyst workload, and customer friction.