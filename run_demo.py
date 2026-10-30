"""Run the demonstration cases and write a record of what happened.

Usage:
    python run_demo.py                      # every case, seeds 31 to 35 (the reported run)
    python run_demo.py --seeds 31 --cases A-Q1 B-Q1
    python run_demo.py --rebuild            # redo the summary files from saved traces, no model calls

Writes results/traces/<case>-s<seed>.json, results/runs.csv, and
results/run_record.md (the first seed's run of each case, step by step, plus a
summary table over all seeds).
"""

import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path

import requests

import briefing_agent

HERE = Path(__file__).resolve().parent

PORTFOLIOS = {
    'A': ('data/portfolio_a.csv', 'Portfolio A'),
    'B': ('data/portfolio_b.csv', 'Portfolio B'),
    'C': ('data/portfolio_c.csv', 'Portfolio C'),
}

QUESTIONS = {
    'Q1': 'What are the main risks in this portfolio?',
    'Q2': 'How big is the largest position, and how has its price moved?',
    'Q3': 'Is this portfolio too dependent on one company or one sector?',
    'Q4': 'Which holdings lost the most value over the last six months?',
    'Q5': 'Should I sell part of my largest holding?',
}

# Which tools each question needs. 'exact' means those tools and no others;
# 'includes' means at least those tools. A case can override its question.
EXPECTED_TOOLS = {
    'Q1': ('exact', {'check_concentration', 'check_price_changes'}),
    'Q2': ('exact', {'check_concentration', 'check_price_changes'}),
    'Q3': ('exact', {'check_concentration'}),
    'Q4': ('exact', {'check_price_changes'}),
    'Q5': ('includes', {'check_concentration'}),
    # In Portfolio C the largest position cannot be identified, so the price tool is optional.
    'C-Q2': ('includes', {'check_concentration'}),
}

# Facts I expect a correct briefing to state, written as patterns over the
# final answer. I took the numbers from the tool results, not from the model.
EXPECTED_FACTS = {
    'A-Q1': [r'\bNWSC\b|Northwind', r'\b44(\.0)?\s*%', r'\b67\.9\s*%'],
    'B-Q1': [r'\b10\.4\s*%', r'\bSFHM\b|Summit|\bOKRT\b|Oak Street|\bRVBK\b|Riverbend'],
    'C-Q1': [r'\bNWSC\b|Northwind', r'\bCLDN\b|Cloudline'],
    'A-Q2': [r'\bNWSC\b|Northwind', r'\b44(\.0)?\s*%', r'\b6\.3\s*%|\b11\.5\s*%'],
    'B-Q2': [r'\bBWBF\b|Bluewater', r'\b13\.6\s*%', r'\b1\.1\s*%'],
    'C-Q2': [r'\bNWSC\b|Northwind'],
    'A-Q3': [r'\b44(\.0)?\s*%', r'\b67\.9\s*%'],
    'B-Q3': [r'\b13\.6\s*%'],
    'C-Q3': [r'\bNWSC\b|Northwind'],
    'A-Q4': [r'\bCLDN\b|Cloudline', r'\b8(\.0)?\s*%'],
    'B-Q4': [r'\b34\.1\s*%', r'\b26\.9\s*%', r'\b22(\.0)?\s*%'],
    'C-Q4': [r'\bCLDN\b|Cloudline', r'\bGRNE\b|Granite', r'\b3\.9\s*%'],
    'A-Q5': [r'\bNWSC\b|Northwind', r'\b44(\.0)?\s*%'],
    'B-Q5': [r'\bBWBF\b|Bluewater', r'\b13\.6\s*%'],
    'C-Q5': [r'\bNWSC\b|Northwind'],
}

ALL_CASES = ['A-Q1', 'B-Q1', 'C-Q1', 'A-Q2', 'B-Q2', 'C-Q2', 'A-Q3', 'B-Q3', 'C-Q3',
             'A-Q4', 'B-Q4', 'C-Q4', 'A-Q5', 'B-Q5', 'C-Q5']


def tools_match(case, record):
    mode, expected = EXPECTED_TOOLS.get(case) or EXPECTED_TOOLS[case.split('-')[1]]
    used = {call['tool'] for call in record['tool_calls'] if call['ok']}
    return used == expected if mode == 'exact' else expected <= used


def facts_found(case, record):
    if not record['final_answer']:
        return 0, len(EXPECTED_FACTS[case])
    answer = record['final_answer']
    text = ' '.join([answer['summary']] + answer['findings'] + answer['cannot_establish'])
    found = sum(1 for pattern in EXPECTED_FACTS[case] if re.search(pattern, text, re.IGNORECASE))
    return found, len(EXPECTED_FACTS[case])


def tool_sequence(record):
    parts = []
    for call in record['tool_calls']:
        text = call['tool'] + (' ' + json.dumps(call['argument']) if call['argument'] else '')
        parts.append(text if call['ok'] else text + ' (rejected)')
    return ' > '.join(parts)


def first_problems(record):
    for step in record['trace']:
        outcome = step.get('result', {})
        if outcome.get('message', '').startswith('Final answer not accepted'):
            return ' | '.join(outcome['data']['problems'])
    return ''


# ------------------------------------------------------------------------
# Record of what happened, in Markdown
# ------------------------------------------------------------------------

def describe_step(step):
    if 'error' in step:
        return 'model error: ' + step['error']
    outcome = step['result']
    proposal, error = briefing_agent.parse_action(step['model_reply'])
    if error:
        return 'reply could not be used (' + error + ')'
    action = proposal['action']
    if action == 'final_answer':
        if outcome['ok']:
            return '`final_answer` -> accepted by the Python check'
        return '`final_answer` -> not accepted: ' + '; '.join(outcome['data']['problems'])
    call = '`' + action + ' ' + json.dumps(proposal['argument']) + '`'
    if not outcome['ok']:
        return call + ' -> rejected: ' + outcome['message']
    data = outcome['data']
    text = call + ' -> ' + outcome['message']
    if data.get('flags'):
        text += ' Flags: ' + ' '.join(data['flags'])
    if data.get('data_problems'):
        text += ' Data problems: ' + '; '.join(p['ticker'] + ' ' + p['problem'] for p in data['data_problems']) + '.'
    return text


def write_record(rows, records, out_dir, seeds, ollama_version):
    lines = [
        '# Run record',
        '',
        'Model: ' + briefing_agent.MODEL + ' through Ollama ' + ollama_version
        + ', thinking off, JSON replies, seeds ' + ', '.join(str(s) for s in seeds) + '.',
        'Generated by run_demo.py on ' + datetime.now().strftime('%Y-%m-%d %H:%M') + '.',
        'The summary covers every run in runs.csv. Each case section shows the run with seed '
        + str(seeds[0]) + ', step by step.',
        '',
        '## Summary',
        '',
        '| Case | Question | Runs | Accepted | Expected tools | Expected facts | Mean steps | Answers rejected first |',
        '|---|---|---|---|---|---|---|---|',
    ]
    for case in dict.fromkeys(row['case'] for row in rows):
        group = [row for row in rows if row['case'] == case]
        question_id = case.split('-')[1]
        facts = sum(int(row['facts_found']) for row in group)
        facts_total = sum(int(row['facts_expected']) for row in group)
        lines.append('| {} | {} | {} | {} | {} | {} | {:.1f} | {} |'.format(
            case, QUESTIONS[question_id], len(group),
            sum(row['status'] == 'accepted' for row in group),
            sum(row['tools_match'] == 'yes' for row in group),
            str(facts) + '/' + str(facts_total),
            sum(int(row['steps']) for row in group) / len(group),
            sum(int(row['final_attempts']) > 1 for row in group)))

    for case, record in records:
        portfolio_id, question_id = case.split('-')
        lines += ['', '## ' + case + ': ' + PORTFOLIOS[portfolio_id][1] + ', "' + QUESTIONS[question_id] + '"', '']
        lines.append('Seed ' + str(record['seed']) + ', status ' + record['status'] + ', '
                     + str(record['steps']) + ' model replies, ' + str(record['seconds']) + ' s.')
        lines.append('')
        for step in record['trace']:
            lines.append(str(step['step']) + '. ' + describe_step(step))
        if record['briefing']:
            lines += ['', '```text', record['briefing'], '```']
    (out_dir / 'run_record.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def summary_row(case, record):
    portfolio_id, question_id = case.split('-')
    found, expected = facts_found(case, record)
    return {
        'case': case,
        'portfolio': PORTFOLIOS[portfolio_id][1],
        'question': QUESTIONS[question_id],
        'seed': record['seed'],
        'status': record['status'],
        'tools': tool_sequence(record),
        'tools_match': 'yes' if tools_match(case, record) else 'no',
        'facts_found': found,
        'facts_expected': expected,
        'steps': record['steps'],
        'final_attempts': record['final_attempts'],
        'first_rejection': first_problems(record),
        'model_errors': len(record.get('model_errors', [])),
        'seconds': record['seconds'],
    }


def main():
    parser = argparse.ArgumentParser(description='Run the demonstration cases.')
    parser.add_argument('--seeds', type=int, nargs='+', default=[31, 32, 33, 34, 35])
    parser.add_argument('--cases', nargs='+', default=ALL_CASES, choices=ALL_CASES)
    parser.add_argument('--out', default='results')
    parser.add_argument('--rebuild', action='store_true',
                        help='rewrite runs.csv and run_record.md from the saved traces without calling the model')
    args = parser.parse_args()

    out_dir = HERE / args.out
    traces = out_dir / 'traces'
    traces.mkdir(parents=True, exist_ok=True)
    if not args.rebuild:
        briefing_agent.prepare_ollama()
    ollama_version = '?'
    try:
        ollama_version = requests.get('http://127.0.0.1:11434/api/version', timeout=5).json().get('version', '?')
    except requests.RequestException:
        pass

    rows = []
    shown = []
    for case in args.cases:
        portfolio_id, question_id = case.split('-')
        path, label = PORTFOLIOS[portfolio_id]
        for seed in args.seeds:
            trace_file = traces / (case + '-s' + str(seed) + '.json')
            if args.rebuild:
                if not trace_file.exists():
                    print('missing trace:', trace_file.name)
                    continue
                record = json.loads(trace_file.read_text(encoding='utf-8'))
            else:
                print('\n==========', case, 'seed', seed, '==========')
                record = briefing_agent.run_agent(HERE / path, QUESTIONS[question_id], label=label,
                                                  seed=seed, verbose=False)
                record['case'] = case
                with open(trace_file, 'w', encoding='utf-8') as file:
                    json.dump(record, file, indent=2, ensure_ascii=False)
            row = summary_row(case, record)
            rows.append(row)
            print(case, 'seed', seed, '|', row['status'], '|', row['tools'], '| facts', row['facts_found'], '/',
                  row['facts_expected'], '|', row['seconds'], 's')
            if seed == args.seeds[0]:
                shown.append((case, record))

    with open(out_dir / 'runs.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_record(rows, shown, out_dir, args.seeds, ollama_version)
    print('\nWrote', out_dir / 'runs.csv', 'and', out_dir / 'run_record.md')


if __name__ == '__main__':
    main()
