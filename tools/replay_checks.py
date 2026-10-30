"""Run the current check_final_answer() again on the last final answer of each saved run.

Usage: python tools/replay_checks.py results/first_run/traces
The tool results are read from the trace, so no model is called. Prints the runs
whose last answer the current checks judge differently from the run itself.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import briefing_agent  # noqa: E402

changed = []
for path in sorted(Path(sys.argv[1]).glob('*.json')):
    record = json.loads(path.read_text(encoding='utf-8'))
    tool_results, last_answer = [], None
    for step in record['trace']:
        proposal, error = briefing_agent.parse_action(step.get('model_reply', ''))
        if error:
            continue
        if proposal['action'] == 'final_answer':
            last_answer = proposal['argument']
        elif step['result']['ok']:
            tool_results.append(step['result'])
    if last_answer is None:
        continue
    problems = briefing_agent.check_final_answer(last_answer, tool_results, record['question'])
    now = 'accepted' if not problems else 'sent back'
    if (record['status'] == 'accepted') != (now == 'accepted'):
        changed.append(path.stem)
        print('###', path.stem, '| in the run:', record['status'], '| current checks:', now)
        for problem in problems:
            print('   ', problem)
print('\nRuns judged differently now:', len(changed), changed)
