"""Running tasks, scoring them, and storing the results.

    runner      one task x one arm x one model -> RunRecord (+ transcripts)
    protocol    the fingerprint of what a run was made under
    scoring     validators judge a RunRecord's output snapshot -> Scorecard
    store       results/<domain>/<category>/<task>/<arm>/<model>/r<k>/
    experiment  the spec, the grid, and the run/rescore loops
"""
