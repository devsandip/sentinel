# Model Card — German Credit default-risk baseline (logistic regression)

**Model ID:** sentinel-german-credit-logreg  
**Version:** 0.1.0  
**Generated:** 2026-07-12 05:33 UTC  
**Question:** Build a credit-default risk model and report performance.

## Purpose
Estimate the probability that a retail credit applicant defaults ('bad' credit risk), to support a loan adjudication decision. Baseline model for demonstration of a governed analysis workflow.

## Intended use
Decision support only, under human review. Outputs a calibrated risk score for a credit officer; does not auto-decline.

**Out-of-scope use:**
- Fully automated adverse action without human review
- Use on populations outside the training distribution
- Any use of the excluded protected attribute as a decision input

## Data lineage
- **Dataset:** UCI Statlog German Credit (statlog-1994)
- **Source:** https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data
- **Rows:** 1000  **Features used:** 19
- **Class balance:** {'good': 700, 'bad': 300}  (default rate 0.3)
- **Transforms:**
  - Stratified train/test split (750 train / 250 test, seed 42)
  - Numeric features standardized (zero mean, unit variance)
  - Categorical features one-hot encoded (unknown categories ignored)
  - Protected attribute 'age_band' excluded from model features (age_years)

## Methodology
- **Algorithm:** Logistic regression (scikit-learn, L2, max_iter=1000)
- **Target:** y = 1 if credit_risk == 'bad' (default event), else 0
- **Validation:** Single stratified holdout; metrics on the test split (seed 42)

## Performance (held-out test)
| Metric | Value |
| --- | --- |
| auc | 0.8018 |
| accuracy | 0.756 |
| precision | 0.6129 |
| recall | 0.5067 |
| f1 | 0.5547 |

Confusion matrix: TN=151 FP=24 FN=37 TP=38

**Top features (|coefficient|):**
- `cat__purpose_A46` +1.008 (increases default risk)
- `cat__checking_status_A14` -0.893 (decreases default risk)
- `cat__credit_history_A34` -0.815 (decreases default risk)
- `cat__purpose_A41` -0.704 (decreases default risk)
- `cat__property_type_A124` +0.700 (increases default risk)
- `cat__savings_status_A61` +0.699 (increases default risk)
- `cat__checking_status_A11` +0.674 (increases default risk)
- `cat__savings_status_A64` -0.588 (decreases default risk)

## Fairness
- **Protected attribute:** age_band (excluded from features)
- **Disparity ratio:** 0.569 (threshold 0.8) — **FLAGGED for review**

| Group | n | Selection rate | TPR | FPR | Base rate |
| --- | --- | --- | --- | --- | --- |
| 26-40 | 122 | 0.238 | 0.562 | 0.122 | 0.262 |
| 41-60 | 58 | 0.190 | 0.429 | 0.114 | 0.241 |
| 60+ | 16 | 0.250 | 0.500 | 0.214 | 0.125 |
| <=25 | 54 | 0.333 | 0.481 | 0.185 | 0.500 |

_Protected attribute 'age_band' was excluded from model features (age_years). Disparity ratio is min/max selection rate across groups. Below the 0.8 threshold (0.57) — flag for review._

## Assumptions
- Training data is representative of the applicant population.
- Historical labels are unbiased ground truth for default.
- Feature relationships are stable over the decision horizon.

## Limitations
- Single holdout split; no cross-validation or temporal validation.
- Baseline model, not tuned; intended to demonstrate the workflow.
- Fairness assessed on one protected attribute at a time, not jointly.
- German Credit is a small (1000-row) benchmark, not live bank data.

## Governance
- **human_in_the_loop:** Model proposal requires explicit approval before promotion (approval gate).
- **audit:** Every agent action emits an immutable audit event.
- **eval_gate:** Golden-set checks must pass before promotion.
- **protected_attribute_excluded:** ['age_years']
- **framework:** Framed against SR 11-7 model risk management guidance.
