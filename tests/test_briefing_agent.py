"""Tests for the agent loop and the final-answer checks, with a scripted fake model."""

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import briefing_agent  # noqa: E402
from briefing_agent import check_final_answer, is_grounded, parse_action, run_agent  # noqa: E402
from risk_tools import check_concentration, check_price_changes, load_portfolio  # noqa: E402

A_FILE = ROOT / 'data' / 'portfolio_a.csv'
A = load_portfolio(A_FILE)
B = load_portfolio(ROOT / 'data' / 'portfolio_b.csv')
A_MISSING = load_portfolio(ROOT / 'data' / 'portfolio_a_missing.csv')  # A with two cells deleted

GOOD_ANSWER = {
    'summary': 'Portfolio A depends heavily on one stock and one sector.',
    'findings': ['NWSC is 44.0% of the portfolio, above the 20% single-holding limit.',
                 'Technology is 67.9% of the portfolio.'],
    'cannot_establish': ['Whether the technology holdings tend to fall together, since this check only '
                         'looks at weights on 2026-10-30.'],
}


def answer(summary, findings, cannot_establish=('Why prices moved, since the file has prices only.',)):
    return {'summary': summary, 'findings': list(findings), 'cannot_establish': list(cannot_establish)}


class ParseActionTests(unittest.TestCase):
    def test_valid_reply(self):
        proposal, error = parse_action('{"action":"check_concentration","argument":{}}')
        self.assertEqual(error, '')
        self.assertEqual(proposal['action'], 'check_concentration')

    def test_invalid_replies(self):
        self.assertEqual(parse_action('not json')[1], 'The reply is not valid JSON.')
        self.assertEqual(parse_action('{"action":"check_concentration"}')[1], 'The reply needs action and argument.')
        self.assertTrue(parse_action('{"action":"check_concentration","argument":[]}')[1])


class FinalAnswerCheckTests(unittest.TestCase):
    def setUp(self):
        self.a_weights = check_concentration(A, {})
        self.missing_weights = check_concentration(A_MISSING, {})
        self.missing_prices = check_price_changes(A_MISSING, {})

    def test_good_answer_is_accepted(self):
        self.assertEqual(check_final_answer(GOOD_ANSWER, [self.a_weights], 'Is this portfolio concentrated?'), [])

    def test_rounding(self):
        self.assertTrue(is_grounded('44', {43.98}))
        self.assertTrue(is_grounded('52,318.75', {52318.75}))
        self.assertFalse(is_grounded('44.5', {43.98}))
        self.assertFalse(is_grounded('26', {26.9}))

    def test_invented_number_is_rejected(self):
        problems = check_final_answer(answer('NWSC is large.', ['NWSC is 45.5% of the portfolio.']),
                                      [self.a_weights], 'q')
        self.assertTrue(any('"45.5"' in problem for problem in problems))

    def test_derived_bound_is_rejected(self):
        b_prices = check_price_changes(B, {})
        problems = check_final_answer(answer('Two holdings fell sharply.', ['Two holdings fell more than 26%.']),
                                      [b_prices], 'q')
        self.assertTrue(any('"26"' in problem for problem in problems))

    def test_advice_is_rejected(self):
        problems = check_final_answer(answer('You should sell some NWSC.', GOOD_ANSWER['findings']),
                                      [self.a_weights], 'q')
        self.assertTrue(any('investment advice' in problem for problem in problems))

    def test_whether_you_should_is_not_advice(self):
        text = answer('NWSC is 44.0% of the portfolio.', GOOD_ANSWER['findings'],
                      ['This sample cannot show whether you should sell, since it says nothing about your goals.'])
        self.assertEqual(check_final_answer(text, [self.a_weights], 'q'), [])

    def test_decision_question_needs_a_refusal(self):
        question = 'Should I sell part of my largest holding?'
        problems = check_final_answer(answer('NWSC is 44.0% of the portfolio.', GOOD_ANSWER['findings']),
                                      [self.a_weights], question)
        self.assertTrue(any('cannot answer that' in problem for problem in problems))
        fixed = answer('This briefing cannot answer whether to sell. NWSC is 44.0% of the portfolio.',
                       GOOD_ANSWER['findings'])
        self.assertEqual(check_final_answer(fixed, [self.a_weights], question), [])

    def test_missing_data_must_be_mentioned(self):
        problems = check_final_answer(answer('Some values are missing.', ['Five holdings are worth $29,306.75.']),
                                      [self.missing_weights], 'q')
        self.assertTrue(any('names none of these holdings' in problem for problem in problems))
        named = answer('CLDN has no price on 2026-04-30, so its change is unknown.', ['GRNE fell 3.9%.'])
        self.assertEqual(check_final_answer(named, [self.missing_prices], 'q'), [])
        by_name = answer('The share count of Northwind Semiconductor is missing.', ['Its weight is unknown.'])
        self.assertEqual(check_final_answer(by_name, [self.missing_weights], 'q'), [])

    def test_briefing_lists_every_missing_value(self):
        named = answer('CLDN has no price on 2026-04-30, so its change is unknown.', ['GRNE fell 3.9%.'])
        text = briefing_agent.render_briefing('Portfolio A, two values missing','q', [{'tool': 'check_price_changes', 'ok': True}],
                                              [self.missing_prices], named)
        self.assertIn('Missing data reported by the tools:', text)
        self.assertIn('- NWSC (Northwind Semiconductor): share count is missing', text)
        self.assertIn('- CLDN (Cloudline Networks): no price on 2026-04-30', text)
        # The same gap reported by both tools becomes one line.
        both = briefing_agent.render_briefing('Portfolio A, two values missing','q', [], [self.missing_weights, self.missing_prices], named)
        self.assertEqual(both.count('- NWSC '), 1)
        self.assertIn('its value and weight are unknown; its value change and the portfolio totals cannot be '
                      'calculated; its price change is known', both)

    def test_no_concentration_claim_without_weights(self):
        claim = answer('The portfolio is well diversified.',
                       ['NWSC has no share count; the other five holdings are worth $29,306.75.'])
        problems = check_final_answer(claim, [self.missing_weights], 'q')
        self.assertTrue(any('cannot say whether it is concentrated' in problem for problem in problems))
        hedged = answer('It is not possible to say whether the portfolio is diversified, because NWSC has no '
                        'share count.', ['Concentration in Technology cannot be measured until NWSC is known.'])
        self.assertEqual(check_final_answer(hedged, [self.missing_weights], 'q'), [])
        # A hedge in another clause does not cover the claim (seen in a development run).
        mixed = answer('NWSC has no share count.', ['The portfolio has a high concentration in Technology with '
                                                    'multiple holdings, but the total value is unknown.'])
        problems = check_final_answer(mixed, [self.missing_weights], 'q')
        self.assertTrue(any('cannot say whether it is concentrated' in problem for problem in problems))

    def test_no_portfolio_move_without_totals(self):
        claim = answer('The portfolio fell 3.9% over the period.',
                       ['GRNE fell 3.9%. NWSC has no share count and CLDN has no price on 2026-04-30.'])
        problems = check_final_answer(claim, [self.missing_prices], 'q')
        self.assertTrue(any('cannot say how the whole portfolio moved' in problem for problem in problems))

    def test_wrong_direction_is_rejected(self):
        # From the first full run: BWBF rose 1.1%, but the summary said it fell.
        b_prices = check_price_changes(B, {})
        wrong = answer('The largest position is Bluewater Bond Fund. Its price fell by 1.1% over the period.',
                       ['BWBF is a fixed income fund that rose 1.1%.'])
        problems = check_final_answer(wrong, [b_prices], 'q')
        self.assertTrue(any('says BWBF fell 1.1%' in problem for problem in problems))
        mixed = answer('NWSC rose 6.3% over the period, but it fell 11.5% in the month ending 2026-08-31.',
                       ['NWSC fell 11.5% in its worst month and still rose 6.3% overall.'])
        self.assertEqual(check_final_answer(mixed, [check_price_changes(A, {})], 'q'), [])

    def test_false_alarms_from_the_second_run(self):
        # Both answers were correct but were sent back in the second full run (seeds 11 to 15).
        a_prices = check_price_changes(A, {})
        portfolio_it = answer('This briefing cannot answer whether to sell. NWSC is 44.0% of the portfolio. The '
                              'portfolio has generally risen, though it fell by more than 6% in two months.',
                              ['The portfolio fell 6.6% in the month ending 2026-08-31.'])
        self.assertEqual(check_final_answer(portfolio_it, [self.a_weights, a_prices],
                                            'Should I sell part of my largest holding?'), [])
        not_measurable = answer('The concentration cannot be measured because NWSC has no share count.',
                                ['The portfolio has four sectors, but the concentration in each is not measurable '
                                 'due to missing data.'])
        self.assertEqual(check_final_answer(not_measurable, [self.missing_weights], 'q'), [])

    def test_cases_from_the_independent_review(self):
        a_both = [self.a_weights, check_price_changes(A, {})]
        b_prices = check_price_changes(B, {})

        def problems_for(summary, results, findings=('NWSC is 44.0% of the portfolio.',), question='q'):
            return check_final_answer(answer(summary, findings), results, question)

        def flagged(problems, text):
            return any(text in problem for problem in problems)

        # A portfolio or sector number given to one named holding.
        self.assertTrue(flagged(problems_for('NWSC is 67.9% of the portfolio.', a_both), 'weight of a sector'))
        self.assertTrue(flagged(problems_for('NWSC fell 6.6% in August.', a_both), 'change of the whole portfolio'))
        self.assertTrue(flagged(problems_for('SFHM fell 10.4% over the period.', [b_prices], ['SFHM fell 34.1%.']),
                                'change of the whole portfolio'))
        # Two holdings in one clause.
        self.assertTrue(flagged(problems_for('SFHM fell 34.1% and BWBF fell 1.1%.', [b_prices], ['SFHM fell 34.1%.']),
                                'says BWBF fell 1.1%'))
        # A clause that starts a new subject is not tied to the last holding named.
        self.assertEqual(problems_for('NWSC is 44.0% of the portfolio; the largest fall of any holding was 8.0%.',
                                      a_both), [])
        # "Missing" is not a hedge, and "potential sector concentration" is a claim.
        missing_weights = [self.missing_weights]
        self.assertTrue(flagged(problems_for('The portfolio is concentrated in Technology even with the NWSC share '
                                             'count missing.', missing_weights, ['NWSC has no share count.']),
                                'cannot say whether it is concentrated'))
        self.assertTrue(flagged(problems_for('The main risks include potential sector concentration and the unknown '
                                             'value of NWSC.', missing_weights, ['NWSC has no share count.']),
                                'cannot say whether it is concentrated'))
        # With two values missing, the largest holding and the largest fall are unknown.
        self.assertTrue(flagged(problems_for('The largest holding is BWBF, worth $8,418.00.', missing_weights,
                                             ['NWSC has no share count.']), 'largest holding is not known'))
        self.assertEqual(problems_for('The largest holding cannot be identified, because NWSC has no share count.',
                                      missing_weights, ['Among holdings with a known value, BWBF is worth $8,418.00.']), [])
        missing_prices = [self.missing_prices]
        self.assertTrue(flagged(problems_for('The holding that lost the most value was GRNE, which fell 3.9%.',
                                             missing_prices, ['CLDN has no price on 2026-04-30.']),
                                'cannot say which holding fell or rose the most'))
        self.assertTrue(flagged(problems_for('The largest price increase was for NWSC, which rose 6.3%.',
                                             missing_prices, ['CLDN has no price on 2026-04-30.']),
                                'cannot say which holding fell or rose the most'))
        self.assertEqual(problems_for("Among holdings with a known change, GRNE fell the most (3.9%); CLDN's change "
                                      'is unknown.', missing_prices, ['CLDN has no price on 2026-04-30.']), [])
        # A refusal has to be about the decision.
        self.assertTrue(flagged(problems_for('The file does not say why NWSC rose.', a_both,
                                             question='Should I sell part of my largest holding?'),
                                'cannot answer that'))

    def test_cases_from_the_third_run(self):
        b_both = [check_concentration(B, {}), check_price_changes(B, {})]

        def problems_for(summary, results, findings=('BWBF is 13.6% of the portfolio.',)):
            return check_final_answer(answer(summary, findings), results, 'q')

        def flagged(problems, text):
            return any(text in problem for problem in problems)

        # Ranks and sectors are checked against the concentration result.
        self.assertTrue(flagged(problems_for('Summit Furnishings, the second-largest holding, fell 34.1%.', b_both),
                                'SFHM is number 10 by value, not second-largest'))
        self.assertTrue(flagged(problems_for('Summit Furnishings, the largest holding in the Fixed income sector, '
                                             'fell 34.1%.', b_both), 'SFHM is in Consumer discretionary'))
        self.assertEqual(problems_for('The largest position is Bluewater Bond Fund, which is in the Fixed income '
                                      'sector.', b_both), [])
        # A weight used as a price change ("makes up" is still a weight).
        self.assertTrue(flagged(problems_for('The largest holding, Bluewater Bond Fund, fell by 13.6% in value.',
                                             b_both), 'is the weight of BWBF, not a price change'))
        self.assertEqual(problems_for('The largest position is Bluewater Bond Fund, which makes up 13.6% of the '
                                      'portfolio. Its price rose 1.1% over the period.', b_both), [])
        # The top-three weight has no limit.
        self.assertTrue(flagged(problems_for('The top three holdings are 36.5% of the portfolio, within acceptable '
                                             'limits.', b_both), 'no limit for the top-three weight'))
        # NWSC has no value: no holding can be called the largest, and the known ranking is checked.
        missing = [self.missing_weights]
        self.assertTrue(flagged(problems_for('This briefing cannot answer that. The largest holding, Northwind '
                                             'Semiconductor, has an unknown value, so it is not possible to say if '
                                             'it is too large.', missing, ['NWSC has no share count.']),
                                'NWSC has no known value, so it cannot be ranked'))
        self.assertTrue(flagged(problems_for('Harbor Lane Software is the largest holding by value among the holdings '
                                             'with known values.', missing, ['NWSC has no share count.']),
                                'The largest holding with a known value is BWBF'))
        self.assertTrue(flagged(problems_for('No holding or sector exceeds the limits based on the available data.',
                                             missing, ['NWSC has no share count.']),
                                'cannot say whether it is concentrated'))
        self.assertEqual(problems_for('It is not possible to determine whether NWSC is the largest holding.', missing,
                                      ['NWSC has no share count.']), [])
        # NWSC cannot be "among holdings with a known value"; BWBF can.
        missing_both = [self.missing_weights, self.missing_prices]
        self.assertTrue(flagged(problems_for("Among holdings with a known value, Northwind Semiconductor's price rose "
                                             '6.3%.', missing_both, ['CLDN has no price on 2026-04-30.']),
                                'NWSC has no known value'))
        self.assertEqual(problems_for('Among holdings with a known value, BWBF is worth the most, since NWSC has no '
                                      'share count.', missing_both, ['CLDN has no price on 2026-04-30.']), [])
        # A cannot_establish item that names "the largest fall" is not a claim.
        self.assertEqual(check_final_answer(answer("Among holdings with a known change, GRNE fell 3.9%. CLDN's change "
                                                   'is unknown.', ['GRNE fell 3.9%.'],
                                                   ['The largest fall, since the change of CLDN is unknown.']),
                                            [self.missing_prices], 'q'), [])
        self.assertTrue(flagged(problems_for('The only holding that lost value was GRNE, which fell 3.9%.',
                                             [self.missing_prices], ['CLDN has no price on 2026-04-30.']),
                                'cannot say which holding fell or rose the most'))

    def test_number_of_another_holding_is_rejected(self):
        # From the first full run: -0.9 points is CLDN's contribution, not NWSC's.
        wrong = answer('NWSC fell 11.5% in August.',
                       ["NWSC's price fell by 11.5% in the month ending 2026-08-31, contributing -0.9 percentage "
                        "points to the portfolio's overall change."])
        problems = check_final_answer(wrong, [check_price_changes(A, {})], 'q')
        self.assertTrue(any('belongs to CLDN' in problem for problem in problems))

    def test_date_parts_do_not_count_as_numbers(self):
        b_weights = check_concentration(B, {})
        wrong = answer('No sector is above the 30% limit.', ['The largest sector is 13.6% of the portfolio.'])
        problems = check_final_answer(wrong, [b_weights], 'q')
        self.assertTrue(any('"30"' in problem for problem in problems))

    def test_softer_advice_is_rejected(self):
        for text in ('Selling part of NWSC could help reduce concentration risk.',
                     'The position may warrant selling part of it to manage risk.',
                     'Selling part of it might still be considered if you want to further diversify.',
                     'Selling part of this holding is not required based on concentration alone.'):
            problems = check_final_answer(answer(text, GOOD_ANSWER['findings']), [self.a_weights], 'q')
            self.assertTrue(any('investment advice' in problem for problem in problems), text)
        fine = answer('NWSC is 44.0% of the portfolio.', GOOD_ANSWER['findings'],
                      ['Whether selling part of NWSC would help depends on goals that are not in the file.'])
        self.assertEqual(check_final_answer(fine, [self.a_weights], 'q'), [])

    def test_structure_problems(self):
        empty = answer('NWSC is 44.0%.', GOOD_ANSWER['findings'], [])
        self.assertIn('cannot_establish is empty', check_final_answer(empty, [self.a_weights], 'q')[0])
        too_many = answer('NWSC is 44.0%.', GOOD_ANSWER['findings'] * 2)
        self.assertIn('findings has 4 items', check_final_answer(too_many, [self.a_weights], 'q')[0])
        wrong_keys = {'summary': 'x', 'risks': ['y'], 'cannot_establish': ['z']}
        self.assertIn('exactly three keys', check_final_answer(wrong_keys, [self.a_weights], 'q')[0])

    def test_answer_needs_a_tool_result(self):
        self.assertIn('No tool result', check_final_answer(GOOD_ANSWER, [], 'q')[0])


class AgentLoopTests(unittest.TestCase):
    def run_script(self, replies, question='Is this portfolio too dependent on one company?'):
        """Run the loop with a fake model that sends the given replies in order."""
        seen = []
        queue = [reply if isinstance(reply, str) else json.dumps(reply) for reply in replies]

        def fake_model(messages, seed=None):
            seen.append([dict(message) for message in messages])
            return queue.pop(0)

        with mock.patch.object(briefing_agent, 'ask_model', fake_model):
            record = run_agent(A_FILE, question, label='Portfolio A', verbose=False)
        return record, seen

    def test_tool_then_accepted_answer(self):
        record, seen = self.run_script([
            {'action': 'check_concentration', 'argument': {}},
            {'action': 'final_answer', 'argument': GOOD_ANSWER},
        ])
        self.assertEqual(record['status'], 'accepted')
        self.assertEqual(record['steps'], 2)
        self.assertEqual([call['tool'] for call in record['tool_calls']], ['check_concentration'])
        self.assertIn('What this sample cannot establish:', record['briefing'])
        self.assertIn('not personal investment advice', record['briefing'])
        # The model starts with the question only; holdings appear only after a tool result.
        self.assertNotIn('NWSC', json.dumps(seen[0]))
        self.assertTrue(seen[1][-1]['content'].startswith('TOOL RESULT: '))

    def test_rejected_answer_gets_a_second_try(self):
        wrong = answer('NWSC is large.', ['NWSC is 45.5% of the portfolio.'])
        record, seen = self.run_script([
            {'action': 'check_concentration', 'argument': {}},
            {'action': 'final_answer', 'argument': wrong},
            {'action': 'final_answer', 'argument': GOOD_ANSWER},
        ])
        self.assertEqual(record['status'], 'accepted')
        self.assertEqual(record['final_attempts'], 2)
        self.assertTrue(seen[2][-1]['content'].startswith('PYTHON CHECK: '))
        self.assertIn('45.5', seen[2][-1]['content'])

    def test_rejected_answers_stop_the_run(self):
        wrong = answer('NWSC is large.', ['NWSC is 45.5% of the portfolio.'])
        record, _ = self.run_script([{'action': 'check_concentration', 'argument': {}}]
                                    + [{'action': 'final_answer', 'argument': wrong}] * briefing_agent.MAX_FINAL_ATTEMPTS)
        self.assertEqual(record['status'], 'rejected')
        self.assertIsNone(record['briefing'])
        self.assertIn('same final_answer', json.dumps(record['trace'][-1]['result']))

    def test_repeated_bad_call_is_pointed_out(self):
        bad = {'action': 'check_price_changes', 'argument': {'period': '6 months'}}
        record, _ = self.run_script([bad, bad, {'action': 'check_price_changes', 'argument': {}},
                                     {'action': 'final_answer', 'argument': answer(
                                         'CLDN fell the most.', ['CLDN fell 8.0% from 2026-04-30 to 2026-10-30.'])}],
                                    question='Which holdings lost the most value?')
        self.assertIn('already rejected at step 1', record['trace'][1]['result']['message'])
        self.assertEqual(record['status'], 'accepted')

    def test_unusable_replies_hit_the_step_limit(self):
        record, _ = self.run_script(['not json'] * briefing_agent.MAX_STEPS)
        self.assertEqual(record['status'], 'step_limit')
        self.assertEqual(record['steps'], briefing_agent.MAX_STEPS)

    def test_model_error_is_retried(self):
        replies = [RuntimeError('500 Server Error'), json.dumps({'action': 'check_concentration', 'argument': {}}),
                   json.dumps({'action': 'final_answer', 'argument': GOOD_ANSWER})]

        def flaky_model(messages, seed=None):
            reply = replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply

        with mock.patch.object(briefing_agent, 'ask_model', flaky_model), \
                mock.patch.object(briefing_agent.time, 'sleep'):
            record = run_agent(A_FILE, 'Is this portfolio concentrated?', verbose=False)
        self.assertEqual(record['status'], 'accepted')
        self.assertEqual(len(record['model_errors']), 1)


if __name__ == '__main__':
    unittest.main()
