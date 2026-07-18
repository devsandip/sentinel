# The prod deploy crashed on a missing dependency. The smoke test caught it, and it is fixed.

Date: 2026-07-18 07:50
Previous: [2026-07-18-0723-v0-v3-merged-and-shipped-to-prod.md](2026-07-18-0723-v0-v3-merged-and-shipped-to-prod.md)

The previous entry said the deploy was verified, not assumed. It was not. I checked
the health endpoint and the source bundle key, both green, and called that verified.
Neither one runs app.py. The first session to load the page got a stack trace:
ModuleNotFoundError, no module named sqlglot.

The cause is a split I missed. Local development installs from pyproject.toml and
uv.lock through uv, and every test passed there. Prod installs from requirements.txt,
which Elastic Beanstalk pip-installs on the instance. requirements.txt is a uv
export, and it was exported before v1 and v2 added their base dependencies. So it was
missing four packages the deployed code imports: fairlearn from v1, and sqlglot,
duckdb, and openlineage-python from v2. sqlglot was just the first import to fail.
Health returned 200 the whole time because that endpoint is Streamlit's server-level
check and answers before the app script ever runs.

The fix is one line of dependency hygiene. I regenerated requirements.txt from the
lock with the same export command named in its own header, which pulled in all four
packages and their transitives, committed it, and redeployed. Prod is on bundle
sentinel-20260718-073829.zip.

This time I did not trust green. I loaded the site and ran the flow. The benign SQL
request runs the whole pipeline, Ask through Attest, and Execute passes, which means
ctx.sql parsed through sqlglot and executed on DuckDB on the instance. The evidence
pack renders with its finding, its confidence interval, its provenance, its six
attested controls, its negative statement, and its two OpenLineage events. The
registry shows the certified agent and the refused one, and assigning the author of
the refused agent as its own validator is refused live with CTL-SOD-01. All three new
surfaces work in prod.

The lesson is small and worth keeping. Health is necessary, not sufficient. A deploy
is verified when a page renders and a flow runs, not when a probe returns 200. And
requirements.txt is a second dependency list that drifts from pyproject unless
something regenerates it, so the next improvement is to generate it at deploy time or
diff it in CI.
