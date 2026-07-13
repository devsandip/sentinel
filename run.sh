#!/usr/bin/env bash
# Launch the Sentinel Streamlit app with a stable native-threading environment.
#
# On macOS, pyarrow's bundled mimalloc allocator faults in mi_thread_init when
# Streamlit serializes a DataFrame to Arrow (st.dataframe / charts) from its
# worker thread: a SIGSEGV with no Python traceback. Routing pyarrow to the
# system allocator avoids it. This MUST be set before pyarrow imports, hence a
# launch wrapper rather than in-code. (Empirically verified as the only fix
# needed; OpenMP/BLAS thread pinning made no difference and was removed.)
set -euo pipefail

export ARROW_DEFAULT_MEMORY_POOL=system

PORT="${PORT:-8501}"
exec uv run streamlit run app.py \
  --server.port "$PORT" \
  --server.fileWatcherType none \
  --server.headless true
