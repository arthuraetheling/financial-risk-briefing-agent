"""Print the tools and the answer of every saved run, for reading them one by one.

For an accepted run this is the accepted answer. A rejected run has none, so the
last answer that was sent back is printed instead.

Usage: python tools/print_answers.py results/traces [case prefix ...]
Example: python tools/print_answers.py results/traces A-missing-Q3 A-missing-Q4
"""

import json
import sys
from pathlib import Path


def last_answer(record):
    answer = None
    for step in record['trace']:
        try:
            proposal = json.loads(step.get('model_reply') or '')
        except ValueError:
            continue
        if isinstance(proposal, dict) and proposal.get('action') == 'final_answer':
            answer = proposal.get('argument')
    return answer


traces = sorted(Path(sys.argv[1]).glob('*.json'))
only = sys.argv[2:]
for path in traces:
    if only and not any(path.stem.startswith(prefix) for prefix in only):
        continue
    record = json.loads(path.read_text(encoding='utf-8'))
    calls = ' > '.join(call['tool'] + (json.dumps(call['argument']) if call['argument'] else '')
                       + ('' if call['ok'] else ' (rejected)') for call in record['tool_calls'])
    print('###', path.stem, '|', record['status'], '|', calls, '| final answers:', record['final_attempts'])
    answer = record['final_answer']
    if not answer:
        answer = last_answer(record)
        if isinstance(answer, dict):
            print('   (last answer, sent back)')
    if isinstance(answer, dict):
        print('   summary:', answer.get('summary'))
        for key, label in (('findings', 'finding'), ('cannot_establish', 'cannot establish')):
            items = answer.get(key)
            for item in items if isinstance(items, list) else [items]:
                print('   ' + label + ':', item)
