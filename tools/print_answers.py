"""Print the tools and the final answer of every saved run, for reading them one by one.

Usage: python tools/print_answers.py results/traces [case prefix ...]
Example: python tools/print_answers.py results/traces C-Q3 C-Q4
"""

import json
import sys
from pathlib import Path

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
    if answer:
        print('   summary:', answer['summary'])
        for item in answer['findings']:
            print('   finding:', item)
        for item in answer['cannot_establish']:
            print('   cannot establish:', item)
