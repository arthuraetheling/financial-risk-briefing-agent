"""Count which checks sent final answers back in a run.

Usage: python tools/count_rejections.py results/traces
For every check, prints how many answers it sent back over all tries, and how many
first answers. An answer can fail more than one check.
"""

import json
import sys
from collections import Counter
from pathlib import Path

# A phrase from each check's message in briefing_agent.check_final_answer().
CHECKS = [
    ('findings or cannot_establish not a list', 'must be a list of text items'),
    ('too many items', 'items. Keep the three'),
    ('empty list', 'is empty'),
    ('number not in any tool result', 'not in any tool result'),
    ('number of another holding', 'belongs to'),
    ('wrong direction', 'Check the direction'),
    ('portfolio or sector number given to a holding', 'change of the whole portfolio'),
    ('portfolio or sector number given to a holding', 'weight of a sector or group'),
    ('weight used as a price change', 'not a price change'),
    ('wrong rank', 'by value, not'),
    ('holding without a value ranked', 'cannot be ranked'),
    ('NWSC called a holding with a known value', 'not one of the holdings with a known value'),
    ('wrong sector', 'Use the sector from'),
    ('top-three weight called within a limit', 'no limit for the top-three'),
    ('missing data not named', 'names none of these holdings'),
    ('concentration claim without weights', 'cannot say whether it is concentrated'),
    ('largest holding without weights', 'largest holding is not known'),
    ('biggest fall or rise with an unknown change', 'fell or rose the most'),
    ('portfolio move without totals', 'how the whole portfolio moved'),
    ('advice wording', 'investment advice'),
    ('buy/sell/hold question without a refusal', 'cannot answer that'),
    ('over 180 words', 'the limit is 180'),
    ('no tool called yet', 'No tool result'),
    ('same answer sent again', 'same final_answer'),
    ('no number in the findings', 'None of the findings uses a number'),
]

every, first = Counter(), Counter()
for path in sorted(Path(sys.argv[1]).glob('*.json')):
    record = json.loads(path.read_text(encoding='utf-8'))
    is_first = True
    for step in record['trace']:
        result = step.get('result', {})
        if not result.get('message', '').startswith('Final answer not accepted'):
            continue
        labels = set()
        for problem in result['data']['problems']:
            labels.update(label for label, phrase in CHECKS if phrase in problem)
        every.update(labels)
        if is_first:
            first.update(labels)
            is_first = False
print('check | answers sent back (all tries) | first answers sent back')
for label in sorted(every, key=lambda label: -every[label]):
    print(label, '|', every[label], '|', first[label])
