"""Tests for the two calculation tools. No model is needed.

The expected numbers were worked out by hand from the CSV files, for example
NWSC on 2026-10-30: 220 shares x 104.60 = 23,012.00 out of a total of 52,318.75.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import risk_tools  # noqa: E402
import verify_numbers  # noqa: E402
from risk_tools import check_concentration, check_price_changes, load_portfolio, read_number  # noqa: E402

A = load_portfolio(ROOT / 'data' / 'portfolio_a.csv')
B = load_portfolio(ROOT / 'data' / 'portfolio_b.csv')
A_MISSING = load_portfolio(ROOT / 'data' / 'portfolio_a_missing.csv')  # A with two cells deleted


def by_ticker(rows):
    return {row['ticker']: row for row in rows}


class ReadFileTests(unittest.TestCase):
    def test_read_number(self):
        self.assertEqual(read_number('1,234.50'), 1234.5)
        self.assertIsNone(read_number(''))
        self.assertIsNone(read_number('n/a'))
        self.assertIsNone(read_number('-5'))
        self.assertIsNone(read_number('inf'))

    def test_blank_cells_become_none(self):
        holdings = by_ticker(A_MISSING['holdings'])
        self.assertIsNone(holdings['NWSC']['shares'])
        self.assertIsNone(holdings['CLDN']['prices']['2026-04-30'])
        self.assertEqual(holdings['CLDN']['prices']['2026-05-29'], 38.65)
        self.assertEqual(len(A_MISSING['dates']), 7)

    def write_csv(self, text):
        handle, path = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(handle, 'w', encoding='utf-8') as file:
            file.write(text)
        self.addCleanup(os.remove, path)
        return path

    def test_missing_column_is_an_error(self):
        path = self.write_csv('ticker,name,shares,2026-01-30,2026-02-27\nAAA,Alpha,10,5,6\n')
        with self.assertRaises(ValueError):
            load_portfolio(path)

    def test_duplicate_ticker_is_an_error(self):
        path = self.write_csv('ticker,name,sector,shares,2026-01-30,2026-02-27\n'
                              'AAA,Alpha,Tech,10,5,6\naaa,Alpha again,Tech,1,5,6\n')
        with self.assertRaises(ValueError):
            load_portfolio(path)


class ConcentrationTests(unittest.TestCase):
    def test_portfolio_a_is_concentrated(self):
        outcome = check_concentration(A, {})
        data = outcome['data']
        self.assertTrue(outcome['ok'])
        self.assertTrue(data['weights_available'])
        self.assertEqual(data['total_value'], 52318.75)
        self.assertEqual(by_ticker(data['holdings'])['NWSC']['value'], 23012.0)
        self.assertEqual(data['largest_holding'], {'ticker': 'NWSC', 'weight_pct': 44.0})
        self.assertEqual(data['largest_sector'], {'sector': 'Technology', 'weight_pct': 67.9})
        self.assertEqual(data['effective_holdings'], 3.8)
        self.assertEqual(len(data['flags']), 2)
        self.assertEqual(data['data_problems'], [])

    def test_portfolio_b_has_no_flags(self):
        data = check_concentration(B, {})['data']
        self.assertEqual(data['total_value'], 50947.1)
        self.assertEqual(data['largest_holding'], {'ticker': 'BWBF', 'weight_pct': 13.6})
        self.assertEqual(data['effective_holdings'], 9.7)
        self.assertEqual(data['flags'], [])
        self.assertIn('No holding or sector is above the limits', check_concentration(B, {})['message'])

    def test_weights_add_up(self):
        data = check_concentration(B, {})['data']
        self.assertAlmostEqual(sum(row['weight_pct'] for row in data['holdings']), 100, delta=0.5)

    def test_missing_share_count_gives_no_weights(self):
        outcome = check_concentration(A_MISSING, {})
        data = outcome['data']
        self.assertTrue(outcome['ok'])
        self.assertFalse(data['weights_available'])
        self.assertEqual(data['holdings_with_value'], 5)
        self.assertEqual(data['known_value'], 29306.75)  # 52,318.75 minus NWSC's 23,012.00
        self.assertEqual([p['ticker'] for p in data['data_problems']], ['NWSC'])
        self.assertNotIn('weight_pct', str(data))
        self.assertNotIn('flags', data)
        self.assertEqual(data['holdings_per_sector']['Technology'], 3)
        # Largest known value first: BWBF 230 x 36.60 = 8,418.00, HLSW 60 x 121.70 = 7,302.00.
        self.assertEqual([row['ticker'] for row in data['holdings']], ['BWBF', 'HLSW', 'CLDN', 'PMRX', 'GRNE', 'NWSC'])

    def test_rejects_arguments(self):
        self.assertFalse(check_concentration(A, {'by': 'sector'})['ok'])


class PriceChangeTests(unittest.TestCase):
    def test_portfolio_a(self):
        data = check_price_changes(A, {})['data']
        totals = data['portfolio']
        self.assertEqual(totals['start_value'], 51164.0)
        self.assertEqual(totals['end_value'], 52318.75)
        self.assertEqual(totals['period_change_pct'], 2.3)
        self.assertEqual((totals['worst_month_change_pct'], totals['worst_month_ending']), (-6.6, '2026-08-31'))
        self.assertEqual((totals['fall_from_peak_pct'], totals['peak_date'], totals['low_date']),
                         (-7.9, '2026-05-29', '2026-08-31'))
        nwsc = by_ticker(data['holdings'])['NWSC']
        self.assertEqual(nwsc['period_change_pct'], 6.3)  # 104.60 / 98.40 - 1
        self.assertEqual((nwsc['worst_month_change_pct'], nwsc['worst_month_ending']), (-11.5, '2026-08-31'))
        self.assertEqual(by_ticker(data['holdings'])['CLDN']['value_change'], -457.5)  # 150 x (34.85 - 37.90)
        self.assertEqual(data['largest_period_fall'], {'ticker': 'CLDN', 'period_change_pct': -8.0})
        self.assertEqual(len(data['flags']), 2)  # the June and August portfolio months

    def test_directions_are_spelled_out(self):
        data = check_price_changes(B, {})['data']
        rows = by_ticker(data['holdings'])
        self.assertEqual(rows['BWBF']['period_move'], 'rose 1.1%')
        self.assertEqual(rows['SFHM']['period_move'], 'fell 34.1%')
        self.assertEqual(data['portfolio']['period_move'], 'fell 10.4%')
        self.assertEqual(data['holdings_that_rose'], ['MDLN', 'CPWR', 'BWBF', 'HSTP'])
        self.assertEqual(data['period']['months_covered'], 6)
        self.assertIn('6 months, 7 month-end prices', check_price_changes(B, {})['message'])

    def test_portfolio_b(self):
        data = check_price_changes(B, {})['data']
        self.assertEqual(data['portfolio']['period_change_pct'], -10.4)
        changes = {row['ticker']: row['period_change_pct'] for row in data['holdings']}
        self.assertEqual((changes['SFHM'], changes['OKRT'], changes['RVBK']), (-34.1, -26.9, -22.0))
        self.assertEqual([row['ticker'] for row in data['holdings']][:3], ['SFHM', 'OKRT', 'RVBK'])
        self.assertEqual(len(data['flags']), 3)
        contributions = sum(row['contribution_pct_points'] for row in data['holdings'])
        self.assertAlmostEqual(contributions, data['portfolio']['period_change_pct'], delta=0.3)

    def test_rejects_arguments_and_says_what_it_covers(self):
        outcome = check_price_changes(A, {'period': '6 months'})
        self.assertFalse(outcome['ok'])
        self.assertIn('2026-04-30 to 2026-10-30', outcome['message'])
        self.assertFalse(check_price_changes(A, {'tickers': ['NWSC']})['ok'])

    def test_missing_values_stop_portfolio_totals(self):
        outcome = check_price_changes(A_MISSING, {})
        data = outcome['data']
        self.assertTrue(outcome['ok'])
        self.assertFalse(data['portfolio_totals_available'])
        self.assertIsNone(data['portfolio'])
        self.assertEqual(sorted(p['ticker'] for p in data['data_problems']), ['CLDN', 'NWSC'])
        rows = by_ticker(data['holdings'])
        self.assertEqual(rows['NWSC']['period_change_pct'], 6.3)  # prices are complete, only shares are missing
        self.assertIsNone(rows['NWSC']['value_change'])
        self.assertIsNone(rows['CLDN']['period_change_pct'])
        # CLDN's change is unknown, so the largest fall is unknown too (in Portfolio A, CLDN fell the most).
        self.assertIsNone(data['largest_period_fall'])
        self.assertEqual(data['largest_fall_among_known_changes'], {'ticker': 'GRNE', 'period_change_pct': -3.9})
        self.assertIn('largest fall cannot be identified', outcome['message'])

    def test_zero_share_counts_do_not_divide_by_zero(self):
        empty = {'file': 'x.csv', 'dates': A['dates'],
                 'holdings': [dict(holding, shares=0.0) for holding in A['holdings']]}
        data = check_price_changes(empty, {})['data']
        self.assertFalse(data['portfolio_totals_available'])
        self.assertFalse(check_concentration(empty, {})['ok'])


class SeparateCalculationTests(unittest.TestCase):
    """verify_numbers.py redoes the arithmetic with Decimal and compares it with the tools."""

    def test_tool_numbers_match_the_exact_calculation(self):
        check = verify_numbers.verify_files()
        self.assertEqual(check.mismatches, [])
        self.assertEqual(check.count, 418)  # a lower count would mean a comparison was skipped

    def test_readme_numbers_match_the_exact_calculation(self):
        check = verify_numbers.Check()
        verify_numbers.readme_checks(check)
        self.assertEqual(check.mismatches, [])

    def test_saved_tool_results_match_a_rerun(self):
        check = verify_numbers.Check()
        verify_numbers.verify_traces(check, ROOT / 'results' / 'traces')
        self.assertEqual(check.mismatches, [])
        self.assertEqual(check.count, 113)

    def test_a_missing_traces_folder_fails(self):
        check = verify_numbers.Check()
        verify_numbers.verify_traces(check, ROOT / 'results' / 'no_such_folder')
        self.assertTrue(check.mismatches)

    def test_a_wrong_tool_number_is_caught(self):
        # Every percentage off by 0.1: the separate calculation has to notice.
        with mock.patch.object(risk_tools, 'pct', lambda fraction: round(100 * fraction, 1) + 0.1):
            check = verify_numbers.verify_files()
        self.assertTrue(any('weight' in line for line in check.mismatches))
        self.assertTrue(any('six-month change' in line for line in check.mismatches))

    def test_a_changed_limit_is_caught(self):
        # The limits come from the README, not from risk_tools.py.
        with mock.patch.object(risk_tools, 'SINGLE_HOLDING_LIMIT_PCT', 25):
            check = verify_numbers.verify_files()
        self.assertTrue(any('limit' in line for line in check.mismatches))


if __name__ == '__main__':
    unittest.main()
