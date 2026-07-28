# 05. Reference Data Sources and Assumption Calibration

## 1. Purpose

This file records public and research-oriented datasets that can be used to calibrate assumptions for the personal thesis/project:

Agent-Based Simulation and Mechanism Design for Transaction Risk Decisioning in Digital Finance.

The project should not depend on a real bank dataset. The main dataset will be synthetic, generated from an agent-based simulation. However, public datasets and papers are useful to make the simulation assumptions more credible.

The role of external data sources is:

- Calibrate transaction amount distribution.
- Calibrate fraud rate/class imbalance.
- Understand common transaction features.
- Compare with known fraud detection benchmarks.
- Justify why synthetic simulation is reasonable for sensitive financial domains.

## 2. Recommended primary direction

The best direction is:

Synthetic data as the main research data, calibrated by public fraud/transaction datasets.

This means:

- Do not copy a Kaggle dataset as the thesis core.
- Do not claim the synthetic data is real bank data.
- Use public datasets to justify assumptions such as fraud rarity, skewed amount distribution, transaction time, class imbalance and fraud/risk behavior.
- Make the simulation mechanism transparent.

Suggested wording for the report:

Due to the sensitive and private nature of real financial transaction data, this project uses synthetic transaction data generated through an agent-based simulation framework. Public fraud detection datasets and related studies are used only as references to calibrate high-level assumptions such as class imbalance, transaction amount distribution and feature design.

## 3. Source 1: PaySim

Name:

PaySim: A Financial Mobile Money Simulator for Fraud Detection

Type:

Research simulator and synthetic mobile money transaction dataset.

Why it is relevant:

PaySim is highly aligned with this thesis because it was created exactly to address the lack of public legitimate transaction datasets in fraud detection. It simulates mobile money transactions based on an original dataset and uses agent-based simulation plus statistical methods.

Useful ideas for this thesis:

- Financial fraud data is hard to access due to privacy.
- Synthetic data can be created through simulation rather than random generation.
- Agent-based simulation is suitable for modeling financial transaction behavior.
- Fraud behavior can be modeled as specific agent strategies.

How to use it:

- Use PaySim as a methodological reference, not necessarily as the exact dataset.
- Borrow the idea of generating transaction flows from agent behavior.
- Use its transaction fields as inspiration: transaction type, amount, origin account, destination account, balances, fraud label.

Reference URL:

https://www.msc-les.org/proceedings/emss/emss2016/emss2016_249.html

## 4. Source 2: BankSim

Name:

BankSim: Bank Payment Simulation for Fraud Detection Research

Type:

Agent-based synthetic bank payment simulator/dataset.

Why it is relevant:

BankSim is close to the thesis direction because it simulates bank payments using agent-based behavior and anonymized transactional patterns. It is often used in fraud detection research when real banking data cannot be shared.

Useful ideas for this thesis:

- Simulate customer-bank payment behavior.
- Generate legitimate and fraudulent transaction patterns.
- Use a simulation environment to evaluate fraud detection methods.
- Represent months of transaction behavior rather than isolated rows.

How to use it:

- Use BankSim as evidence that synthetic bank transaction simulation is an accepted approach.
- Use its logic to justify why agent-based data generation is suitable.
- Use high-level class imbalance and transaction flow ideas if needed.

Reference URL:

https://www.kaggle.com/datasets/ntnu-testimon/banksim1

Secondary discussion/reference:

https://pmc.ncbi.nlm.nih.gov/articles/PMC11016795/

## 5. Source 3: ULB Credit Card Fraud Detection Dataset

Name:

Credit Card Fraud Detection Dataset by Machine Learning Group, ULB

Type:

Real-world anonymized credit card fraud benchmark.

Why it is relevant:

This dataset is one of the most widely used public benchmarks for credit card fraud detection. It contains European card transactions from September 2013. Due to privacy, most features are PCA-transformed, but Time, Amount and Class are available.

Known characteristics:

- 284,807 transactions.
- 492 fraud cases.
- Fraud rate about 0.172 percent.
- Strong class imbalance.
- Features are anonymized except Time and Amount.

Useful ideas for this thesis:

- Fraud is rare and highly imbalanced.
- Amount and time can be used as realistic calibration references.
- A fraud decisioning system should be evaluated under extreme imbalance.

Limitations:

- Most features are PCA-anonymized.
- Not suitable for rich behavior simulation by itself.
- No explicit analyst workflow, policy action or business cost data.

How to use it:

- Use as a benchmark reference for fraud rarity and class imbalance.
- Use Amount and Time distributions as rough references.
- Do not rely on it alone for mechanism design.

Reference URL:

https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud

## 6. Source 4: IEEE-CIS Fraud Detection

Name:

IEEE-CIS Fraud Detection Dataset

Type:

Real-world e-commerce/card-not-present fraud detection competition dataset provided by Vesta Corporation through Kaggle.

Why it is relevant:

IEEE-CIS is a richer fraud detection dataset than ULB because it contains transaction and identity-related variables. Many variables are anonymized, but it is useful for understanding feature families in card-not-present/e-commerce fraud.

Known characteristics from public benchmark descriptions:

- Around 590k transactions in the original competition data.
- Fraud rate in training around 3.5 percent.
- Contains anonymized transaction, card, address, email domain, device and time-related information.

Useful ideas for this thesis:

- Feature families: transaction amount, card/address/device/email/time.
- Fraud rate can vary depending on channel and sampling.
- Identity/context features are important in digital transaction fraud.

Limitations:

- Access requires Kaggle competition rules/account.
- Feature meanings are partially hidden.
- It is mainly for supervised ML benchmarking, not policy simulation.

How to use it:

- Use as a reference for feature groups.
- Use high-level fraud rate as one scenario option.
- Use it to justify adding context features such as device, merchant/channel and customer behavior.

Reference URL:

https://www.kaggle.com/competitions/ieee-fraud-detection/overview

Amazon Fraud Dataset Benchmark summary:

https://github.com/amazon-science/fraud-dataset-benchmark

## 7. Source 5: Fraud Dataset Benchmark by Amazon Science

Name:

Fraud Dataset Benchmark (FDB)

Type:

Benchmark repository that standardizes several fraud/abuse datasets.

Why it is relevant:

This source is useful because it compares multiple public fraud datasets under a standardized benchmark. It shows that fraud detection covers many domains and that class imbalance varies substantially across datasets.

Useful ideas for this thesis:

- Use FDB as evidence that fraud/risk datasets differ by domain.
- Use it to choose suitable benchmark references.
- Use it to justify why model metrics alone are not enough across settings.

Relevant datasets listed in FDB:

- IEEE-CIS Fraud Detection.
- Credit Card Fraud Detection.
- Fraud e-commerce.
- Simulated credit card transactions generated using Sparkov.
- Other fraud/abuse datasets.

Reference URL:

https://github.com/amazon-science/fraud-dataset-benchmark

## 8. How to use these sources in the thesis

The thesis should not say:

We use Kaggle data as real production data.

Better wording:

Public fraud detection datasets are used as references for calibrating assumptions, while the main experimental environment is synthetic and agent-based. This is appropriate because the research objective is to compare decision mechanisms, not to claim production-ready fraud detection accuracy.

## 9. Suggested calibration choices for the first simulation

### Fraud rate scenarios

Use multiple scenarios instead of one fixed number:

- Low fraud scenario: 0.2 percent, inspired by highly imbalanced card fraud benchmarks such as ULB.
- Medium fraud scenario: 1 percent.
- High fraud scenario: 3.5 percent, inspired by IEEE-CIS training distribution.

### Transaction amount

Use skewed distribution:

- Log-normal amount distribution for normal customers.
- Segment-specific amount distribution: low, medium, high value customers.
- Fraud transactions can have higher tail amounts or burst patterns.

### Time behavior

Use non-uniform time distribution:

- Normal customers concentrate around active hours.
- Some customers have legitimate night activity.
- Fraud strategies may include late-hour or unusual-hour behavior.

### Feature groups

Minimum feature groups:

- Amount features.
- Time features.
- Velocity features.
- Merchant/category features.
- Customer recent behavior features.
- Device/channel/context features.

### Policy scenarios

Use 3 to 4 policy types:

- Rule-based only.
- Risk score threshold.
- Risk score plus analyst review.
- Risk score plus analyst review plus AI explanation.

## 10. Recommended source priority

Priority 1:

PaySim and BankSim, because they directly support synthetic and agent-based transaction simulation.

Priority 2:

ULB and IEEE-CIS, because they are widely used benchmarks for fraud detection and provide realistic class imbalance references.

Priority 3:

Amazon Fraud Dataset Benchmark, because it provides a standardized view of multiple fraud datasets.

## 11. Final recommendation

For this thesis, the most defensible approach is:

Use PaySim/BankSim as methodological support for agent-based synthetic transaction simulation, and use ULB/IEEE-CIS/FDB as benchmark references for fraud rarity, feature families and class imbalance.

This keeps the project academically grounded while still allowing the simulation to answer mechanism-design questions that public static datasets cannot answer directly.
