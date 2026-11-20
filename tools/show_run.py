"""Print one saved run step by step, in the same format briefing_agent.py uses for a live run.

Usage: python tools/show_run.py results/traces/A-Q1-s44.json [--full]
Example: python tools/show_run.py results/traces/A-missing-Q4-s45.json

No model is called. The model replies, the tool results and the Python checks are read
from the saved trace, so a run can be shown again without Ollama. Long results are cut
at 1500 characters, as in a live run; --full prints them whole.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from briefing_agent import parse_action  # noqa: E402


def show(path, full=False):
    with open(path, encoding='utf-8') as file:
        record = json.load(file)
    print('Saved run:', record.get('case', Path(path).stem), '| seed:', record['seed'], '| model:', record['model'])
    print('Portfolio file:', record['portfolio_file'])
    print('Question:', record['question'])

    for entry in record['trace']:
        print('\nSTEP', entry['step'])
        if 'error' in entry:
            print('MODEL ERROR:', entry['error'])
            continue
        print('MODEL PROPOSED:', entry['model_reply'])
        proposal, error = parse_action(entry['model_reply'])
        is_check = not error and proposal['action'] == 'final_answer'
        text = json.dumps(entry['result'], ensure_ascii=False)
        print(('PYTHON CHECK: ' if is_check else 'TOOL RESULT: ') + (text if full else text[:1500]))

    print('\nSTOPPED:', record['status'], '| steps:', record['steps'], '| seconds:', record['seconds'])
    if record['briefing']:
        print('\n' + record['briefing'])
    else:
        print('\nNo briefing: no final answer was accepted (the last PYTHON CHECK above says why).')


if __name__ == '__main__':
    arguments = [a for a in sys.argv[1:] if a != '--full']
    if len(arguments) != 1:
        sys.exit(__doc__)
    show(arguments[0], full='--full' in sys.argv[1:])
