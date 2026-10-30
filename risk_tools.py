"""Calculation tools for the Financial Risk Briefing Agent.

load_portfolio() reads one fictional portfolio from a CSV file. The two tools,
check_concentration() and check_price_changes(), work on the loaded portfolio
and return results in the same shape as the Agent Airways tools:
{'ok': True or False, 'message': '...', 'data': {...}}.

All arithmetic happens in this file. The model never sees the CSV rows, only
the results below. When a value is missing, the tools leave out any number
that would need it (a weight, a portfolio total) instead of computing it from
the rows that happen to be complete.
"""

import csv
import math
import re
from pathlib import Path

DATE_COLUMN = re.compile(r'^\d{4}-\d{2}-\d{2}$')
REQUIRED_COLUMNS = ('ticker', 'name', 'sector', 'shares')

# Reference limits behind the flags. I picked these for the project; they are
# not regulatory or industry rules.
SINGLE_HOLDING_LIMIT_PCT = 20
SECTOR_LIMIT_PCT = 40
HOLDING_DROP_LIMIT_PCT = 20
MONTHLY_DROP_LIMIT_PCT = 5


def result(ok, message, data=None):
    if data is None:
        data = {}
    return {'ok': ok, 'message': message, 'data': data}


def pct(fraction):
    # One decimal place, and never "-0.0".
    value = round(100 * fraction, 1)
    return 0.0 if value == 0 else value


def data_problem(holding, problem):
    return {'ticker': holding['ticker'], 'name': holding['name'], 'problem': problem}


def move(change_pct):
    # Spelled out so the model copies the direction instead of guessing it from a sign.
    if change_pct is None:
        return None
    if change_pct == 0:
        return 'no change'
    return ('rose ' if change_pct > 0 else 'fell ') + str(abs(change_pct)) + '%'


# ------------------------------------------------------------------------
# 1. Read the portfolio file
# ------------------------------------------------------------------------

def read_number(cell):
    """Return a finite, non-negative number from a CSV cell, or None."""
    text = (cell or '').strip().replace(',', '')
    try:
        value = float(text)
    except ValueError:
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def load_portfolio(path):
    """Read holdings and month-end prices. Blank or invalid cells become None."""
    path = Path(path)
    with open(path, newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []
        missing = [name for name in REQUIRED_COLUMNS if name not in columns]
        if missing:
            raise ValueError(path.name + ' is missing column(s): ' + ', '.join(missing))
        dates = sorted(name for name in columns if DATE_COLUMN.match(name))
        if len(dates) < 2:
            raise ValueError(path.name + ' needs at least two price columns named YYYY-MM-DD')

        holdings = []
        for row in reader:
            ticker = (row['ticker'] or '').strip().upper()
            if not ticker:
                continue
            prices = {}
            for day in dates:
                price = read_number(row[day])
                prices[day] = price if price else None  # a zero price counts as missing
            holdings.append({
                'ticker': ticker,
                'name': (row['name'] or '').strip(),
                'sector': (row['sector'] or '').strip() or None,
                'shares': read_number(row['shares']),
                'prices': prices,
            })

    if not holdings:
        raise ValueError(path.name + ' has no holdings')
    tickers = [holding['ticker'] for holding in holdings]
    if len(set(tickers)) != len(tickers):
        raise ValueError(path.name + ' lists the same ticker more than once')
    return {'file': path.name, 'dates': dates, 'holdings': holdings}


# ------------------------------------------------------------------------
# 2. Tool 1: concentration by holding and by sector
# ------------------------------------------------------------------------

def check_concentration(portfolio, argument):
    """Weight of each holding and sector on the last date in the file."""
    if argument:
        return result(False, 'check_concentration has no settings. Send {}.')

    as_of = portfolio['dates'][-1]
    rows = []
    problems = []
    for holding in portfolio['holdings']:
        price = holding['prices'][as_of]
        value = None
        if holding['shares'] is None:
            problems.append(data_problem(holding, 'share count is missing, so its value and weight are unknown'))
        elif price is None:
            problems.append(data_problem(holding, 'price on ' + as_of + ' is missing, so its value and weight '
                                                  'are unknown'))
        else:
            value = holding['shares'] * price
        rows.append({'ticker': holding['ticker'], 'name': holding['name'],
                     'sector': holding['sector'] or 'Unknown', 'value': value})
        if holding['sector'] is None:
            problems.append(data_problem(holding, 'sector is blank, so it is counted under Unknown'))

    known = [row for row in rows if row['value'] is not None]
    unknown = [row['ticker'] for row in rows if row['value'] is None]
    known_value = sum(row['value'] for row in known)
    for row in rows:
        if row['value'] is not None:
            row['value'] = round(row['value'], 2)

    if known_value <= 0 and not unknown:
        return result(False, 'Every holding has a value of 0, so weights cannot be calculated.')

    # A weight is a share of the whole portfolio. If one value is unknown the
    # total is unknown too, so every weight would be wrong. Report values only.
    if unknown:
        message = ('Weights cannot be calculated: ' + ', '.join(unknown)
                   + (' has' if len(unknown) == 1 else ' have') + ' no known value on ' + as_of
                   + ', so the total value of the portfolio is unknown. Values are shown for the other '
                   + str(len(known)) + ' holdings. This result cannot show whether any holding or sector '
                   + 'is above the limits.')
        per_sector = {}
        for row in rows:
            per_sector[row['sector']] = per_sector.get(row['sector'], 0) + 1
        return result(True, message, {
            'as_of': as_of,
            'weights_available': False,
            'holdings_in_file': len(rows),
            'holdings_with_value': len(known),
            'known_value': round(known_value, 2),
            'holdings_per_sector': per_sector,
            'holdings': rows,
            'data_problems': problems,
        })

    rows.sort(key=lambda row: row['value'], reverse=True)
    sector_values = {}
    sector_counts = {}
    for row in rows:
        row['weight_pct'] = pct(row['value'] / known_value)
        sector_values[row['sector']] = sector_values.get(row['sector'], 0) + row['value']
        sector_counts[row['sector']] = sector_counts.get(row['sector'], 0) + 1
    sectors = []
    for sector, value in sorted(sector_values.items(), key=lambda item: item[1], reverse=True):
        sectors.append({'sector': sector, 'weight_pct': pct(value / known_value), 'holdings': sector_counts[sector]})

    weights = [row['value'] / known_value for row in rows]
    effective_holdings = 1 / sum(weight * weight for weight in weights)

    flags = []
    for row in rows:
        if row['weight_pct'] > SINGLE_HOLDING_LIMIT_PCT:
            flags.append(row['ticker'] + ' is ' + str(row['weight_pct']) + '% of the portfolio, above the '
                         + str(SINGLE_HOLDING_LIMIT_PCT) + '% single-holding limit.')
    for row in sectors:
        if row['weight_pct'] > SECTOR_LIMIT_PCT:
            flags.append(row['sector'] + ' is ' + str(row['weight_pct']) + '% of the portfolio, above the '
                         + str(SECTOR_LIMIT_PCT) + '% sector limit.')

    message = 'Weights of all ' + str(len(rows)) + ' holdings on ' + as_of + '.'
    if not flags:
        message += ' No holding or sector is above the limits.'
    return result(True, message, {
        'as_of': as_of,
        'weights_available': True,
        'holdings_in_file': len(rows),
        'total_value': round(known_value, 2),
        'largest_holding': {'ticker': rows[0]['ticker'], 'weight_pct': rows[0]['weight_pct']},
        'top_3_weight_pct': pct(sum(weights[:3])),
        'largest_sector': {'sector': sectors[0]['sector'], 'weight_pct': sectors[0]['weight_pct']},
        'effective_holdings': round(effective_holdings, 1),
        'holdings': rows,
        'sectors': sectors,
        'limits': {'single_holding_pct': SINGLE_HOLDING_LIMIT_PCT, 'sector_pct': SECTOR_LIMIT_PCT},
        'flags': flags,
        'data_problems': problems,
        'note': ('effective_holdings is 1 divided by the sum of squared weights (the inverse Herfindahl index). '
                 'If it is close to holdings_in_file, the holdings are of similar size; if it is much lower, '
                 'value sits in a few holdings.'),
    })


# ------------------------------------------------------------------------
# 3. Tool 2: price changes over the period and month by month
# ------------------------------------------------------------------------

def monthly_changes(dates, values):
    return [{'month_ending': dates[i], 'change_pct': pct(values[i] / values[i - 1] - 1)}
            for i in range(1, len(dates))]


def fall_from_peak(dates, values):
    """Largest fall from an earlier month-end high, or None if there was no fall."""
    peak_value, peak_date = values[0], dates[0]
    largest = None
    for day, value in zip(dates, values):
        if value > peak_value:
            peak_value, peak_date = value, day
        fall = value / peak_value - 1
        if fall < 0 and (largest is None or fall < largest[0]):
            largest = (fall, peak_date, day)
    return largest


def check_price_changes(portfolio, argument):
    """Price change of each holding and of the whole portfolio from the first to the last date."""
    dates = portfolio['dates']
    start, end = dates[0], dates[-1]
    if argument:
        # Say what the tool already covers, so the model does not keep guessing settings.
        return result(False, 'check_price_changes has no settings. It always covers every holding over the '
                      'whole file, ' + start + ' to ' + end + '. Send {}.')

    rows = []
    problems = []
    for holding in portfolio['holdings']:
        prices = holding['prices']
        shares = holding['shares']
        gaps = [day for day in dates if prices[day] is None]
        row = {
            'ticker': holding['ticker'],
            'name': holding['name'],
            'start_price': prices[start],
            'end_price': prices[end],
            'period_change_pct': None,
            'period_move': None,
            'value_change': None,
            'worst_month_change_pct': None,
            'worst_month_move': None,
            'worst_month_ending': None,
            'contribution_pct_points': None,
        }
        if prices[start] is not None and prices[end] is not None:
            row['period_change_pct'] = pct(prices[end] / prices[start] - 1)
            row['period_move'] = move(row['period_change_pct'])
            if shares is not None:
                row['value_change'] = round(shares * (prices[end] - prices[start]), 2)
        if gaps:
            problem = 'no price on ' + ', '.join(gaps) + ', so '
            if row['period_change_pct'] is None:
                problem += 'its change from ' + start + ' to ' + end + ' is unknown and '
            problems.append(data_problem(holding, problem + 'the portfolio totals cannot be calculated'))
        else:
            worst = min(monthly_changes(dates, [prices[day] for day in dates]),
                        key=lambda change: change['change_pct'])
            row['worst_month_change_pct'] = worst['change_pct']
            row['worst_month_move'] = move(worst['change_pct'])
            row['worst_month_ending'] = worst['month_ending']
            if shares is None:
                problems.append(data_problem(holding, 'share count is missing, so its value change and the '
                                                      'portfolio totals cannot be calculated; its price change '
                                                      'is known'))
        rows.append(row)

    # Portfolio totals need every holding: a total built from the complete rows
    # only would describe a different portfolio.
    portfolio_data = None
    portfolio_flags = []
    holdings = portfolio['holdings']
    values = []
    if not problems:
        values = [sum(holding['shares'] * holding['prices'][day] for holding in holdings) for day in dates]
    if values and min(values) > 0:  # all share counts could be 0
        for holding, row in zip(holdings, rows):
            gain = holding['shares'] * (holding['prices'][end] - holding['prices'][start])
            row['contribution_pct_points'] = pct(gain / values[0])
        months = monthly_changes(dates, values)
        worst = min(months, key=lambda change: change['change_pct'])
        fall = fall_from_peak(dates, values)
        for change in months:
            change['move'] = move(change['change_pct'])
        portfolio_data = {
            'start_value': round(values[0], 2),
            'end_value': round(values[-1], 2),
            'period_change_value': round(values[-1] - values[0], 2),
            'period_change_pct': pct(values[-1] / values[0] - 1),
            'period_move': move(pct(values[-1] / values[0] - 1)),
            'monthly_changes': months,
            'worst_month_change_pct': worst['change_pct'],
            'worst_month_ending': worst['month_ending'],
            'fall_from_peak_pct': pct(fall[0]) if fall else None,
            'peak_date': fall[1] if fall else None,
            'low_date': fall[2] if fall else None,
        }
        for change in months:
            if change['change_pct'] <= -MONTHLY_DROP_LIMIT_PCT:
                portfolio_flags.append('The portfolio fell ' + str(-change['change_pct']) + '% in the month ending '
                                       + change['month_ending'] + ' (monthly drop limit: '
                                       + str(MONTHLY_DROP_LIMIT_PCT) + '%).')

    rows.sort(key=lambda row: (row['period_change_pct'] is None, row['period_change_pct'] or 0))  # biggest fall first
    flags = []
    for row in rows:
        if row['period_change_pct'] is not None and row['period_change_pct'] <= -HOLDING_DROP_LIMIT_PCT:
            flags.append(row['ticker'] + ' fell ' + str(-row['period_change_pct']) + '% from ' + start
                         + ' to ' + end + ' (holding drop limit: ' + str(HOLDING_DROP_LIMIT_PCT) + '%).')
    flags += portfolio_flags
    fallen = [row for row in rows if row['period_change_pct'] is not None and row['period_change_pct'] < 0]
    risen = [row for row in reversed(rows) if row['period_change_pct'] is not None and row['period_change_pct'] > 0]
    unknown_change = [row['ticker'] for row in rows if row['period_change_pct'] is None]
    largest_fall = None
    if fallen:
        largest_fall = {'ticker': fallen[0]['ticker'], 'period_change_pct': fallen[0]['period_change_pct']}

    message = ('Price changes from ' + start + ' to ' + end + ' (' + str(len(dates) - 1) + ' months, '
               + str(len(dates)) + ' month-end prices).')
    if problems:
        message += (' Portfolio totals are not calculated because ' + str(len({p['ticker'] for p in problems}))
                    + ' holding(s) lack a price or a share count; see data_problems.')
    elif portfolio_data is None:
        message += ' Portfolio totals are not calculated because the portfolio value is 0 on at least one date.'
    if unknown_change:
        # Same rule as the weights: a "largest fall" that skips an unknown change is not the largest fall.
        message += (' The largest fall cannot be identified, because the change of ' + ', '.join(unknown_change)
                    + ' is unknown.')
    data = {
        'period': {'start': start, 'end': end, 'months_covered': len(dates) - 1, 'month_end_prices': len(dates)},
        'portfolio_totals_available': portfolio_data is not None,
        'portfolio': portfolio_data,
        'largest_period_fall': None if unknown_change else largest_fall,
    }
    if unknown_change:
        data['largest_fall_among_known_changes'] = largest_fall
    data.update({
        'holdings_that_rose': [row['ticker'] for row in risen],
        'holdings_that_fell': [row['ticker'] for row in fallen],
        'holdings_with_unknown_change': unknown_change,
        'holdings': rows,
        'limits': {'holding_drop_pct': HOLDING_DROP_LIMIT_PCT, 'portfolio_monthly_drop_pct': MONTHLY_DROP_LIMIT_PCT},
        'flags': flags,
        'data_problems': problems,
        'notes': [
            'period_change_pct runs from the first to the last date; worst_month_change_pct is the worst single month.',
            'contribution_pct_points is how many percentage points of the portfolio change came from that holding.',
            'Share counts are treated as fixed over the whole period. Dividends, interest, fees, and trades are not in the file.',
            'Prices are month-end closes, so moves inside a month are not visible.',
        ],
    })
    return result(True, message, data)


TOOLS = {
    'check_concentration': check_concentration,
    'check_price_changes': check_price_changes,
}
