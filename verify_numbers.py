"""Check the numbers in this project with a second, separate calculation.

risk_tools.py works with floats. This script reads the CSV files again with the
csv module, redoes the arithmetic with Decimal (exact for share counts and prices
in cents), and compares the result with what the two tools report: every value,
weight, change, total, count, ranking and flag, the direction text such as
"rose 1.1%", and which numbers are left out when data is missing. A reported
number passes if it is within half a unit of its last decimal place, so 44.0
passes for an exact 43.984...

It also rebuilds the README's Data section from the exact numbers and checks that
every table row and every figure in the two lists appears there as written.

Usage:
    python verify_numbers.py
    python verify_numbers.py --traces results/traces   # also rerun the tools for every saved tool result

Prints each mismatch and exits with code 1 if there is one.
"""

import argparse
import csv
import json
import re
import sys
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from pathlib import Path

import risk_tools

HERE = Path(__file__).resolve().parent
FILES = ['portfolio_a.csv', 'portfolio_b.csv', 'portfolio_a_missing.csv']
HUNDRED = Decimal(100)
MONTHS = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']
# The four limits as the README states them. They are not taken from risk_tools.py, so
# a changed limit in the tool code shows up as a mismatch.
HOLDING_LIMIT, SECTOR_LIMIT, DROP_LIMIT, MONTH_DROP_LIMIT = 20, 40, 20, 5


def to_decimal(cell):
    cell = cell.strip()
    return Decimal(cell) if cell else None


def read_exact(path):
    """Dates, and holdings with Decimal share counts and prices. A blank cell becomes None."""
    with open(path, newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        dates = reader.fieldnames[4:]  # ticker, name, sector, shares, then one price column per month end
        holdings = [{'ticker': row['ticker'], 'sector': row['sector'], 'shares': to_decimal(row['shares']),
                     'prices': [to_decimal(row[day]) for day in dates]} for row in reader]
    return dates, holdings


def change_pct(new, old):
    return (new / old - 1) * HUNDRED


def half_unit(decimals):
    return Decimal('0.5') * Decimal(10) ** -decimals


def read_flag(flag):
    """(name, number, limit) from a flag such as "NWSC is 44.0% of the portfolio, above the 20% ... limit."."""
    numbers = re.findall(r'(\d+(?:\.\d+)?)%', flag)
    if flag.startswith('The portfolio fell'):
        name = re.search(r'month ending (\S+) ', flag).group(1)
    else:
        name = re.split(r' (?:is|fell) ', flag, maxsplit=1)[0]
    return name, Decimal(numbers[0]), int(numbers[-1])


class Check:
    """Counts comparisons and keeps the ones that fail."""

    def __init__(self):
        self.count = 0
        self.mismatches = []

    def near(self, what, reported, exact, decimals):
        # The tools round percentages to 1 decimal and dollar amounts to 2.
        self.count += 1
        value = reported if isinstance(reported, Decimal) or reported is None else Decimal(repr(reported))
        if value is None or abs(value - exact) > half_unit(decimals):
            self.mismatches.append(what + ': tool says ' + str(reported) + ', exact value ' + str(round(exact, 4)))

    def same(self, what, reported, expected):
        self.count += 1
        if reported != expected:
            self.mismatches.append(what + ': tool says ' + str(reported) + ', expected ' + str(expected))

    def move(self, what, text, exact):
        # The direction text the model copies, such as "rose 1.1%": right word, right size.
        self.count += 1
        if text == 'no change':
            right = abs(exact) <= half_unit(1)
        else:
            word, _, size = (text or '').partition(' ')
            right = (word == ('rose' if exact > 0 else 'fell') and size.endswith('%')
                     and abs(Decimal(size[:-1]) - abs(exact)) <= half_unit(1))
        if not right:
            self.mismatches.append(what + ': tool says "' + str(text) + '", exact change ' + str(round(exact, 4)))

    def flags(self, what, flags, expected):
        # expected: {name: (exact number, limit)}. Each flag needs the right name, number and limit.
        read = [read_flag(flag) for flag in flags]
        self.same(what + ', flagged', sorted(name for name, _, _ in read), sorted(expected))
        for name, number, limit in read:
            if name in expected:
                self.near(what + ', number in the flag for ' + name, number, abs(expected[name][0]), 1)
                self.same(what + ', limit in the flag for ' + name, limit, expected[name][1])


# ------------------------------------------------------------------------
# 1. Everything the two tools report
# ------------------------------------------------------------------------

def verify_concentration(check, name, dates, holdings, data):
    values = {holding['ticker']: holding['shares'] * holding['prices'][-1] for holding in holdings
              if holding['shares'] is not None and holding['prices'][-1] is not None}
    unknown = [holding['ticker'] for holding in holdings if holding['ticker'] not in values]
    rows = {row['ticker']: row for row in data['holdings']}
    counts = {}
    for holding in holdings:
        counts[holding['sector']] = counts.get(holding['sector'], 0) + 1

    check.same(name + ', date', data['as_of'], dates[-1])
    check.same(name + ', holdings in file', data['holdings_in_file'], len(holdings))
    check.same(name + ', holdings listed by value', [row['ticker'] for row in data['holdings']],
               sorted(values, key=values.get, reverse=True) + unknown)
    check.same(name + ', holdings with a data problem', sorted(p['ticker'] for p in data['data_problems']),
               sorted(unknown))
    for holding in holdings:
        check.same(name + ', ' + holding['ticker'] + ' sector', rows[holding['ticker']]['sector'], holding['sector'])
    for ticker, value in values.items():
        check.near(name + ', ' + ticker + ' value', rows[ticker]['value'], value, 2)
    check.same(name + ', weights available', data['weights_available'], not unknown)
    if unknown:
        # One unknown value makes the total unknown, so no weight can be right.
        check.same(name + ', no weight reported', 'weight_pct' in json.dumps(data), False)
        check.same(name + ', no flags', 'flags' in data, False)
        check.same(name + ', holdings with a value', data['holdings_with_value'], len(values))
        check.same(name + ', holdings per sector', data['holdings_per_sector'], counts)
        check.near(name + ', known value', data['known_value'], sum(values.values()), 2)
        return

    total = sum(values.values())
    weights = {ticker: value / total * HUNDRED for ticker, value in values.items()}
    sectors = {}
    for holding in holdings:
        sectors[holding['sector']] = sectors.get(holding['sector'], 0) + weights[holding['ticker']]
    reported_sectors = {row['sector']: row for row in data['sectors']}
    largest, largest_sector = max(weights, key=weights.get), max(sectors, key=sectors.get)

    check.near(name + ', total value', data['total_value'], total, 2)
    for ticker, weight in weights.items():
        check.near(name + ', ' + ticker + ' weight', rows[ticker]['weight_pct'], weight, 1)
    check.same(name + ', sectors', sorted(reported_sectors), sorted(sectors))
    for sector, weight in sectors.items():
        row = reported_sectors.get(sector, {})
        check.near(name + ', ' + sector + ' weight', row.get('weight_pct'), weight, 1)
        check.same(name + ', ' + sector + ' holdings', row.get('holdings'), counts[sector])
    check.near(name + ', top-three weight', data['top_3_weight_pct'], sum(sorted(weights.values())[-3:]), 1)
    check.near(name + ', effective number of holdings', data['effective_holdings'],
               1 / sum((weight / HUNDRED) ** 2 for weight in weights.values()), 1)
    check.same(name + ', largest holding', data['largest_holding']['ticker'], largest)
    check.near(name + ', largest holding weight', data['largest_holding']['weight_pct'], weights[largest], 1)
    check.same(name + ', largest sector', data['largest_sector']['sector'], largest_sector)
    check.near(name + ', largest sector weight', data['largest_sector']['weight_pct'], sectors[largest_sector], 1)
    check.same(name + ', limits', data['limits'], {'single_holding_pct': HOLDING_LIMIT, 'sector_pct': SECTOR_LIMIT})
    over = {ticker: (weight, HOLDING_LIMIT) for ticker, weight in weights.items() if weight > HOLDING_LIMIT}
    over.update({sector: (weight, SECTOR_LIMIT) for sector, weight in sectors.items() if weight > SECTOR_LIMIT})
    check.flags(name, data['flags'], over)


def verify_price_changes(check, name, dates, holdings, data):
    rows = {row['ticker']: row for row in data['holdings']}
    totals_known = all(holding['shares'] is not None and None not in holding['prices'] for holding in holdings)
    changes = {}
    check.same(name + ', period', data['period'], {'start': dates[0], 'end': dates[-1],
                                                    'months_covered': len(dates) - 1, 'month_end_prices': len(dates)})
    check.same(name + ', holdings in the result', sorted(rows), sorted(holding['ticker'] for holding in holdings))
    for holding in holdings:
        ticker, prices, shares = holding['ticker'], holding['prices'], holding['shares']
        row = rows[ticker]
        for field, price in (('start price', prices[0]), ('end price', prices[-1])):
            if price is None:
                check.same(name + ', ' + ticker + ' ' + field + ' withheld', row[field.replace(' ', '_')], None)
            else:
                check.near(name + ', ' + ticker + ' ' + field, row[field.replace(' ', '_')], price, 2)
        if prices[0] is None or prices[-1] is None:
            check.same(name + ', ' + ticker + ' change withheld', row['period_change_pct'], None)
        else:
            changes[ticker] = change_pct(prices[-1], prices[0])
            check.near(name + ', ' + ticker + ' six-month change', row['period_change_pct'], changes[ticker], 1)
            check.move(name + ', ' + ticker + ' six-month change as text', row['period_move'], changes[ticker])
        if shares is None or ticker not in changes:
            check.same(name + ', ' + ticker + ' dollar change withheld', row['value_change'], None)
        else:
            check.near(name + ', ' + ticker + ' dollar change', row['value_change'], shares * (prices[-1] - prices[0]), 2)
        if None in prices:
            check.same(name + ', ' + ticker + ' worst month withheld', row['worst_month_change_pct'], None)
        else:
            months = [change_pct(prices[i], prices[i - 1]) for i in range(1, len(prices))]
            check.near(name + ', ' + ticker + ' worst month', row['worst_month_change_pct'], min(months), 1)
            check.move(name + ', ' + ticker + ' worst month as text', row['worst_month_move'], min(months))
            check.same(name + ', ' + ticker + ' worst month date', row['worst_month_ending'],
                       dates[months.index(min(months)) + 1])
        if not totals_known:
            check.same(name + ', ' + ticker + ' contribution withheld', row['contribution_pct_points'], None)

    unknown = [holding['ticker'] for holding in holdings if holding['ticker'] not in changes]
    by_change = sorted(changes, key=changes.get)
    check.same(name + ', holdings listed by change', [row['ticker'] for row in data['holdings']], by_change + unknown)
    check.same(name + ', holdings with an unknown change', data['holdings_with_unknown_change'], unknown)
    check.same(name + ', holdings that fell', data['holdings_that_fell'], [t for t in by_change if changes[t] < 0])
    check.same(name + ', holdings that rose', data['holdings_that_rose'],
               [t for t in reversed(by_change) if changes[t] > 0])
    problems = [holding['ticker'] for holding in holdings if holding['shares'] is None or None in holding['prices']]
    check.same(name + ', holdings with a data problem', sorted(p['ticker'] for p in data['data_problems']),
               sorted(problems))
    check.same(name + ', limits', data['limits'], {'holding_drop_pct': DROP_LIMIT,
                                                    'portfolio_monthly_drop_pct': MONTH_DROP_LIMIT})
    biggest = by_change[0] if by_change and changes[by_change[0]] < 0 else None
    if unknown:
        # With a change unknown, the tool may only name the largest fall among the known changes.
        check.same(name + ', largest fall withheld', data['largest_period_fall'], None)
        reported = data['largest_fall_among_known_changes']
    else:
        reported = data['largest_period_fall']
    check.same(name + ', largest fall', reported and reported['ticker'], biggest)
    if biggest:
        check.near(name + ', largest fall size', reported['period_change_pct'], changes[biggest], 1)

    check.same(name + ', portfolio totals available', data['portfolio_totals_available'], totals_known)
    flagged = {ticker: (change, DROP_LIMIT) for ticker, change in changes.items() if change <= -DROP_LIMIT}
    if not totals_known:
        check.same(name + ', portfolio totals withheld', data['portfolio'], None)
        check.flags(name, data['flags'], flagged)
        return

    values = [sum(holding['shares'] * holding['prices'][i] for holding in holdings) for i in range(len(dates))]
    months = [change_pct(values[i], values[i - 1]) for i in range(1, len(values))]
    totals = data['portfolio']
    check.near(name + ', start value', totals['start_value'], values[0], 2)
    check.near(name + ', end value', totals['end_value'], values[-1], 2)
    check.near(name + ', six-month change in dollars', totals['period_change_value'], values[-1] - values[0], 2)
    check.near(name + ', six-month change', totals['period_change_pct'], change_pct(values[-1], values[0]), 1)
    check.move(name + ', six-month change as text', totals['period_move'], change_pct(values[-1], values[0]))
    check.same(name + ', months listed', [change['month_ending'] for change in totals['monthly_changes']], dates[1:])
    for reported_month, exact in zip(totals['monthly_changes'], months):
        check.near(name + ', month ending ' + reported_month['month_ending'], reported_month['change_pct'], exact, 1)
        check.move(name + ', month ending ' + reported_month['month_ending'] + ' as text', reported_month['move'],
                   exact)
    check.near(name + ', worst month', totals['worst_month_change_pct'], min(months), 1)
    check.same(name + ', worst month date', totals['worst_month_ending'], dates[months.index(min(months)) + 1])
    peak, peak_day, deepest, span = values[0], dates[0], Decimal(0), (None, None)
    for day, value in zip(dates, values):
        if value > peak:
            peak, peak_day = value, day
        if change_pct(value, peak) < deepest:
            deepest, span = change_pct(value, peak), (peak_day, day)
    if deepest < 0:
        check.near(name + ', largest fall from a month-end high', totals['fall_from_peak_pct'], deepest, 1)
    else:
        check.same(name + ', no fall from a month-end high', totals['fall_from_peak_pct'], None)
    check.same(name + ', dates of that fall', (totals['peak_date'], totals['low_date']), span)
    for holding in holdings:
        gain = holding['shares'] * (holding['prices'][-1] - holding['prices'][0])
        check.near(name + ', ' + holding['ticker'] + ' contribution', rows[holding['ticker']]['contribution_pct_points'],
                   gain / values[0] * HUNDRED, 1)
    flagged.update({dates[i + 1]: (change, MONTH_DROP_LIMIT) for i, change in enumerate(months)
                    if change <= -MONTH_DROP_LIMIT})
    check.flags(name, data['flags'], flagged)


def verify_files():
    check = Check()
    for file_name in FILES:
        dates, holdings = read_exact(HERE / 'data' / file_name)
        portfolio = risk_tools.load_portfolio(HERE / 'data' / file_name)
        verify_concentration(check, file_name, dates, holdings, risk_tools.check_concentration(portfolio, {})['data'])
        verify_price_changes(check, file_name, dates, holdings, risk_tools.check_price_changes(portfolio, {})['data'])
    return check


# ------------------------------------------------------------------------
# 2. The README's Data section
# ------------------------------------------------------------------------

def one_decimal(value):
    return str(value.quantize(Decimal('0.1'), ROUND_HALF_UP))


def whole(value):
    return str(value.quantize(Decimal('1'), ROUND_HALF_UP))


def money(value):
    return '$' + format(value.quantize(Decimal('0.01'), ROUND_HALF_UP), ',f')


def signed(value):
    return ('+' if value > 0 else '') + one_decimal(value) + '%'


def month_name(day):
    return MONTHS[int(day[5:7])]


def portfolio_facts(file_name):
    """Exact numbers for a complete portfolio file."""
    dates, holdings = read_exact(HERE / 'data' / file_name)
    values = [sum(holding['shares'] * holding['prices'][i] for holding in holdings) for i in range(len(dates))]
    weight = {holding['ticker']: holding['shares'] * holding['prices'][-1] / values[-1] * HUNDRED
              for holding in holdings}
    sector_weight = {}
    for holding in holdings:
        sector_weight[holding['sector']] = sector_weight.get(holding['sector'], 0) + weight[holding['ticker']]
    return {
        'dates': dates,
        'holdings': {holding['ticker']: holding for holding in holdings},
        'values': values,
        'weight': weight,
        'sector_weight': sector_weight,
        'months': {dates[i]: change_pct(values[i], values[i - 1]) for i in range(1, len(dates))},
        'change': {holding['ticker']: change_pct(holding['prices'][-1], holding['prices'][0]) for holding in holdings},
        'effective': 1 / sum((w / HUNDRED) ** 2 for w in weight.values()),
    }


def data_section_lines():
    """The lines the README's Data section should contain, written from the exact numbers."""
    a, b = portfolio_facts('portfolio_a.csv'), portfolio_facts('portfolio_b.csv')

    def row(label, cell):
        return '| ' + label + ' | ' + cell(a) + ' | ' + cell(b) + ' |'

    def largest(weights):
        top = max(weights, key=weights.get)
        return top + ', ' + one_decimal(weights[top]) + '%'

    def worst(facts):
        day = min(facts['months'], key=facts['months'].get)
        return signed(facts['months'][day]) + ' (' + month_name(day) + ')'

    lines = [
        row('Holdings', lambda f: str(len(f['holdings']))),
        row('Value on ' + a['dates'][-1], lambda f: money(f['values'][-1])),
        row('Largest holding', lambda f: largest(f['weight'])),
        row('Largest sector', lambda f: largest(f['sector_weight'])),
        row('Effective number of holdings', lambda f: one_decimal(f['effective'])),
        row('Six-month change', lambda f: signed(change_pct(f['values'][-1], f['values'][0]))),
        row('Worst month', worst),
    ]

    # Portfolio A: the months it fell by the monthly drop limit or more, and the part of
    # each fall that came from its largest holding.
    dates = a['dates']
    falls = [day for day in dates[1:] if a['months'][day] <= -MONTH_DROP_LIMIT]
    top = a['holdings'][max(a['weight'], key=a['weight'].get)]
    top_falls, parts = [], []
    for day in falls:
        i = dates.index(day)
        top_falls.append(one_decimal(-change_pct(top['prices'][i], top['prices'][i - 1])) + '%')
        dollars = top['shares'] * (top['prices'][i] - top['prices'][i - 1])
        parts.append(whole(dollars / (a['values'][i] - a['values'][i - 1]) * HUNDRED) + '% of the '
                     + month_name(day) + ' fall')
    lines += [
        'gains only ' + one_decimal(change_pct(a['values'][-1], a['values'][0])) + '% over the six months',
        'It fell ' + ' and '.join(one_decimal(-a['months'][day]) + '% in ' + month_name(day) for day in falls) + '.',
        top['ticker'] + ' fell ' + ' and '.join(top_falls) + ' in those months. In dollars, it accounts for '
        + ' and '.join(parts) + '.',
    ]

    # Portfolio B: the size limit it stays under, the loss, and the three biggest losers.
    loss = b['values'][0] - b['values'][-1]
    losers = sorted(b['change'], key=b['change'].get)[:3]
    loser_dollars = sum(b['holdings'][t]['shares'] * (b['holdings'][t]['prices'][0] - b['holdings'][t]['prices'][-1])
                        for t in losers)
    sizes = [one_decimal(-b['change'][t]) + '%' for t in losers]
    lines += [
        'has no position above ' + str(max(b['weight'].values()).to_integral_value(ROUND_CEILING)) + '%',
        'it lost ' + money(loss) + ' (' + one_decimal(loss / b['values'][0] * HUNDRED) + '%) over the six months',
        losers[0] + ' fell ' + sizes[0] + ', ' + losers[1] + ' ' + sizes[1] + ', and ' + losers[2] + ' ' + sizes[2]
        + '.',
        'These three account for ' + whole(loser_dollars / loss * HUNDRED) + '% of the net loss.',
    ]
    return lines


def readme_checks(check, show=False):
    readme = (HERE / 'README.md').read_text(encoding='utf-8')
    section = readme[readme.index('## Data'):readme.index('## The two tools')]
    section = ' '.join(section.split())  # a sentence may wrap
    for line in data_section_lines():
        check.count += 1
        found = line in section
        if not found:
            check.mismatches.append('README Data section does not contain: ' + line)
        if show:
            print(('  ok      ' if found else '  MISSING ') + line)


# ------------------------------------------------------------------------
# 3. The tool results saved in a run
# ------------------------------------------------------------------------

def verify_traces(check, folder):
    """Rerun each successful tool call of each saved run and compare with what the run recorded."""
    paths = sorted(Path(folder).glob('*.json'))
    if not paths:
        check.mismatches.append(str(folder) + ': no saved runs found')
        return
    portfolios = {}
    before = check.count
    for path in paths:
        record = json.loads(path.read_text(encoding='utf-8'))
        file_name = record['portfolio_file']
        if file_name not in portfolios:
            if not (HERE / 'data' / file_name).exists():
                check.same(path.name + ', portfolio file', file_name, 'a file in data/')
                continue
            portfolios[file_name] = risk_tools.load_portfolio(HERE / 'data' / file_name)
        saved = {step['step']: step.get('result') for step in record['trace']}
        for call in record['tool_calls']:
            if call['ok']:
                fresh = json.loads(json.dumps(risk_tools.TOOLS[call['tool']](portfolios[file_name], call['argument'])))
                check.same(path.name + ', step ' + str(call['step']) + ' ' + call['tool'] + ' matches a rerun',
                           saved[call['step']] == fresh, True)
    if check.count == before:
        check.mismatches.append(str(folder) + ': no saved tool results found')


def main():
    parser = argparse.ArgumentParser(description='Check the tool numbers and the README numbers with exact arithmetic.')
    parser.add_argument('--traces', help='also rerun the tools for every tool result saved in this folder')
    args = parser.parse_args()

    check = verify_files()
    tool_count = check.count
    print('README Data section, written from the exact numbers:')
    readme_checks(check, show=True)
    print('\nTool results compared with the exact calculation:', tool_count)
    if args.traces:
        before = check.count
        verify_traces(check, args.traces)
        print('Saved tool results compared with a rerun:', check.count - before)
    for line in check.mismatches:
        print('MISMATCH', line)
    print(str(len(check.mismatches)) + ' mismatches')
    sys.exit(1 if check.mismatches else 0)


if __name__ == '__main__':
    main()
