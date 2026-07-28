# Policy Comparison Summary

Input simulation run: `D:\Đề án\FinRisk-Decision-Simulation\data\simulation_runs\baseline_20260721_094112`
Analyst capacity per day: `20`

## Base Cost Scenario

| policy_name         | alerts_sent_to_analyst | analyst_reviewed | review_overflow | precision_flagged | recall_flagged | precision_reviewed | recall_reviewed | false_positive_cost | analyst_cost | net_benefit |
| ------------------- | ---------------------- | ---------------- | --------------- | ----------------- | -------------- | ------------------ | --------------- | ------------------- | ------------ | ----------- |
| balanced_threshold  | 884                    | 595              | 289             | 0.1233            | 0.3695         | 0.1546             | 0.3119          | 5677.74             | 2157.3       | 24295.57    |
| sensitive_threshold | 1645                   | 600              | 1045            | 0.0833            | 0.4644         | 0.1533             | 0.3119          | 9382.5              | 2170.8       | 20577.31    |
| strict_threshold    | 411                    | 408              | 3               | 0.1873            | 0.261          | 0.1887             | 0.261           | 2664.75             | 1652.4       | 16126.93    |
| capacity_aware      | 1645                   | 600              | 1045            | 0.0833            | 0.4644         | 0.1533             | 0.3119          | 9382.5              | 2170.8       | 20577.31    |
| cost_sensitive      | 10105                  | 600              | 9505            | 0.0231            | 0.7898         | 0.1317             | 0.2678          | 44530.88            | 1995.3       | 8382.91     |

## Interpretation

- `sensitive_threshold` tends to increase recall but can create more false positives and analyst workload.
- `strict_threshold` reduces workload and false positive cost but may miss more fraud.
- `capacity_aware` makes the capacity constraint explicit by ranking candidates before review.
- `cost_sensitive` uses expected utility, so it is closest to the mechanism-design framing of the thesis.

## Important caveat

Net benefit is a simulated utility under explicit assumptions, not real profit. Use it to compare policies under the same assumptions, not as a production financial claim.