# Previous reported run (seeds 31 to 35)

This was the reported run before the instructor's feedback. It was made with the
code in commit `aa01962`, when the incomplete-information file was called
`data/portfolio_c.csv` and its cases were C-Q1 to C-Q5. That file is now
`data/portfolio_a_missing.csv`, with the same contents, and the cases are
A-missing-Q1 to A-missing-Q5. The run used Ollama 0.40.3.

- `runs.csv`, `run_record.md` and `traces/`: the 75 runs of that version.
- `manual_review.md`: the review of that run, kept as it was written.
  - "The final run" and "the code as submitted" there mean this run and commit
    `aa01962`.
  - Where it says "the full counts are in the README", it means the README in that
    commit.
  - The `first_run/`, `second_run/` and `third_run/` folders it mentions are next to
    this folder, in `results/`.
- `rerun_A-Q1-s31.json`: the quick-start command rerun with seed 31.

These traces come from before the ranking fix in `check_concentration`, so the tool
results saved for the C cases list holdings in file order.

The current `run_demo.py --rebuild` and `verify_numbers.py --traces` know only the
current file names and cases, so do not point them at this folder:
`run_demo.py --rebuild --out results/fourth_run` would overwrite `runs.csv` and
`run_record.md` with the 50 A and B runs only. To work with these traces, check out
commit `aa01962`.
