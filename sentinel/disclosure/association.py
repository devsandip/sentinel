"""Association measures for proxy discovery (CTL-PROXY-01, section 5.1).

The column grant asks "is this column permitted." It cannot ask "does this
permitted column reconstruct a protected one." Zip code proxies race; first name
proxies gender. A model built entirely from permitted columns can still be
redlining. These measures answer the question the grant cannot: how strongly is
a granted feature associated with the protected attribute.

Cramer's V for categorical-vs-categorical, correlation ratio (eta) for
numeric-vs-categorical. Both are in [0, 1]: 0 is independence, 1 is a perfect
reconstruction. Cheap by design, roughly the twenty lines section 5.1 promises.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

CRAMERS_V = "cramers_v"
CORRELATION_RATIO = "correlation_ratio"


def cramers_v(x: pd.Series, y: pd.Series) -> float:
    """Cramer's V between two categorical series, in [0, 1].

    Uncorrected V: sqrt(phi^2 / min(r-1, k-1)). A single-valued column (one row
    or one column in the contingency table) carries no association and returns 0.
    """
    pair = pd.DataFrame({"x": x.reset_index(drop=True), "y": y.reset_index(drop=True)})
    pair = pair.dropna()
    if pair.empty:
        return 0.0
    confusion = pd.crosstab(pair["x"], pair["y"])
    if confusion.shape[0] < 2 or confusion.shape[1] < 2:
        return 0.0
    chi2 = float(chi2_contingency(confusion, correction=False)[0])
    n = float(confusion.to_numpy().sum())
    if n == 0:
        return 0.0
    phi2 = chi2 / n
    r, k = confusion.shape
    denom = min(r - 1, k - 1)
    if denom <= 0:
        return 0.0
    return float(np.clip(np.sqrt(phi2 / denom), 0.0, 1.0))


def correlation_ratio(categories: pd.Series, values: pd.Series) -> float:
    """Correlation ratio (eta) of a numeric series across categories, in [0, 1].

    eta = sqrt(SS_between / SS_total). Measures how much of the numeric feature's
    variance is explained by the categorical protected attribute; a high value
    means the number carries the category, i.e. it is a proxy.
    """
    frame = pd.DataFrame(
        {
            "cat": categories.reset_index(drop=True),
            "val": pd.to_numeric(values.reset_index(drop=True), errors="coerce"),
        }
    ).dropna()
    if frame.empty:
        return 0.0
    grand_mean = frame["val"].mean()
    ss_total = float(((frame["val"] - grand_mean) ** 2).sum())
    if ss_total == 0.0:
        return 0.0
    ss_between = 0.0
    for _, group in frame.groupby("cat", observed=True):
        ss_between += len(group) * (group["val"].mean() - grand_mean) ** 2
    return float(np.clip(np.sqrt(ss_between / ss_total), 0.0, 1.0))


def association(feature: pd.Series, protected: pd.Series) -> tuple[float, str]:
    """Association between a granted feature and the protected attribute.

    Picks the measure from the feature's dtype: correlation ratio for a numeric
    feature (the protected attribute is always treated as categorical), Cramer's
    V for a categorical feature. Returns (strength in [0, 1], method name).
    """
    if pd.api.types.is_numeric_dtype(feature):
        return correlation_ratio(protected, feature), CORRELATION_RATIO
    return cramers_v(feature, protected), CRAMERS_V
