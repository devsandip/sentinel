# The crash was pyarrow all along, and the OpenMP fix was cruft

Previous: [2026-07-12-1145-full-governed-app-lands.md](2026-07-12-1145-full-governed-app-lands.md).

Spent this session chasing a segfault and learning I had been fixing the wrong
thing. The Streamlit app kept dying seconds after it rendered a data-heavy tab.
SIGSEGV, exit 139, no Python traceback. I had blamed sklearn calling OpenBLAS
from Streamlit's worker thread and pinned everything to one thread with
threadpoolctl and a pile of OMP env vars. It seemed to help, so I moved on.

It did not actually help. The app kept crashing on the user.

This time I read the real macOS crash report instead of guessing. The faulting
thread was unambiguous: pyarrow's bundled mimalloc allocator, faulting in
mi_thread_init, while Streamlit serialized a DataFrame to Arrow for st.dataframe.
Not sklearn. Not OpenBLAS. A known pyarrow issue on macOS arm64. The fix is one
env var, ARROW_DEFAULT_MEMORY_POOL=system, which routes pyarrow to the system
allocator. It has to be set before pyarrow imports, so it lives in a launch
wrapper, not in app code.

Then I did the thing I should have done the first time. I tested whether the
OpenMP pinning was doing anything. A standalone harness ran sklearn plus pyarrow
on fresh worker threads twenty-five times, fully unpinned, with no crash. The
real app ran the whole flow with every OpenMP mitigation removed and stayed up.
So all of it was cruft, chasing a diagnosis I never verified. I ripped it out:
the env vars, the in-code threadpool_limits wraps, the threadpoolctl dependency.
One mitigation remains, the Arrow pool, because it is the only one with a crash
report proving it matters.

The lesson is old and I keep relearning it. Read the crash report before writing
the fix. A fix that "seems to help" on an intermittent crash is worthless. And
when someone asks why an env var is there, that is a good prompt to check
whether it should be.

The app is stable now on the minimal config. Next is git history and a deploy.
