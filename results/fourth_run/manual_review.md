# Manual review of the briefings

The Python checks decide whether an answer is accepted, but they only look at
numbers, names, and wording patterns. To see what they miss, I printed every
accepted answer with `tools/print_answers.py` and compared each sentence with the
tool results in the trace. Quotes are copied from the traces.

## How I counted

An answer has a **major error** if it states something as fact that the tool
results contradict or do not support. This covers four kinds of statement:

- **A wrong detail.** This includes a wrong number, direction, period, count, rank,
  or sector, and a number that belongs to another holding.
- **A false statement about the data or the tools.** An example is "the file does
  not provide data on all holdings' changes" for Portfolio A, which has a change for
  every holding.
- **A conclusion the data cannot support.** Examples are calling Portfolio C
  diversified or concentrated, naming its largest holding or biggest loser, and
  calling a 3.9% fall "close to the 20% threshold".
- **Advice wording.**

A **minor problem** is loose wording that does not state a wrong fact outright. This
covers three cases:

- "Within acceptable limits" for the top-three weight, which has no limit.
- A vague plural such as "some holdings" where only one holding is affected.
- "The largest holding cannot be identified because its value is unknown". This
  reads as if the largest holding were the one without a value, but it does not say
  which holding that is.

I did not count limitations that are generic but true.

## Final run (seeds 31 to 35, the code as submitted)

75 runs, 69 accepted.

### The six rejected runs

In five of the six, the last answer still had a content error. The sixth was over the
word limit.

| Run | Problem in the last answer |
|---|---|
| C-Q2, seed 31 | "Among holdings with a known value, Northwind Semiconductor's price rose 6.3%" (NWSC is the holding without a value), and "Granite Ridge Energy fell 3.9% over the period, but this is not the largest fall among holdings with a known change" (it is) |
| C-Q4, seed 31 | "The holding that lost the most value over the last six months is GRNE", with CLDN's change unknown, in all four tries |
| C-Q4, seed 33 | "The only holding that lost value over the last six months was GRNE" |
| C-Q5, seed 31 | Names no holding with missing data. It also lists HLSW as the largest of the known values, ahead of BWBF |
| C-Q5, seed 32 | "The largest holding, Northwind Semiconductor, has an unknown value", in all four tries |
| B-Q5, seed 35 | 185 words, 5 over the limit. The content was correct |

### Accepted briefings with problems

11 of the 69 accepted briefings had a major error, and 10 more had only a minor
problem.

Major errors:

| Run | Problem | Quote |
|---|---|---|
| C-Q3, seeds 31, 32, 34, 35 | Wrong ranking among the known values. BWBF ($8,418.00) is larger than HLSW ($7,302.00) | "The largest holding by value is Harbor Lane Software with $7,302.00, but this is among holdings with a known value." (seed 31) |
| A-Q4, seeds 31, 33, 35 | False statement about the data. Portfolio A has a price change for every holding | "Whether other holdings had larger losses than CLDN, since the file does not provide data on all holdings' changes." (seed 33) |
| B-Q4, seed 35 | False statement about the data. Portfolio B has every price | "The file does not show whether other holdings might have lost more value if their prices were known." |
| B-Q5, seed 32 | A portfolio number given to a holding, and a false claim. BWBF rose 1.1%, and three holdings fell more than 20% | "The largest holding, Bluewater Bond Fund, fell 10.4% over the period, but no holding exceeded the 20% drop limit." |
| B-Q1, seed 33 | Unsupported risk. No sector in Portfolio B is above 13.6% | "The main risks in this portfolio include significant price declines in several holdings and concentration in certain sectors." |
| C-Q1, seed 32 | Wrong sector. GRNE is Energy | "Granite Ridge Energy, a Technology holding, fell by 3.9% over the period" |

Minor problems:

| Run | Problem | Quote |
|---|---|---|
| C-Q2, seeds 32, 33, 35, and C-Q5, seeds 33, 34, 35 | Writes as if the largest holding were the one without a value | "The largest position cannot be identified because its value is unknown." (C-Q2, seed 33); "because the value of the largest holding is unknown" (C-Q5, seed 34) |
| C-Q1, seeds 31, 33, 34, 35 | "Some holdings" have unknown price changes. Only CLDN's is unknown, and NWSC's price change is known | "The price changes for some holdings are unknown due to missing data" (seed 31) |

Why the checks missed them:

- **C-Q3:** the ranking error probably starts in my tool. When a value is missing,
  `check_concentration` lists the holdings in file order instead of by value. HLSW
  is the first holding with a value, and the model seems to have taken the first row
  to be the largest. My ranking check reads "the largest holding is X" and "X, the
  largest holding", but not "the largest holding by value is X". Sorting the rows by
  value would fix this at the source.
- **A-Q4 and B-Q4:** these sentences describe what the file contains, and no check
  looks at that.
- **B-Q5, seed 32:** "fell 10.4%" comes in the clause after the holding's name. The
  check that catches a portfolio number given to a holding only runs when the
  holding is named in the same clause.
- **B-Q1, seed 33:** "concentration in certain sectors" is only checked when weights
  are unavailable. For Portfolio B they are available.
- **C-Q1, seed 32:** the sector check reads "in the X sector", but not "a Technology
  holding".
- **The minor problems:** the "its value is unknown" sentences contain "cannot",
  and the "largest" check accepts any sentence that contains such a word. No check
  counts holdings written in words.

### What did not appear

Several errors that were common in the earlier runs did not appear in this run's
accepted briefings:

- changes described in the wrong direction, except in B-Q5 seed 32 above, where
  BWBF is given the portfolio's fall;
- numbers that belong to another holding;
- a weight used as a price change;
- invented numbers;
- a wrong rank for SFHM, or SFHM placed in the wrong sector;
- "largest" or "most" claims about Portfolio C without any qualifier;
- advice wording.

Some of these no longer showed up at all. For example, no answer in this run was
sent back for a wrong direction, probably because the tool now spells out "rose
1.1%". Others did show up, but the checks sent them back. Seven answers had advice
wording. Nineteen named the biggest fall or rise in Portfolio C although CLDN's
change was unknown. The full counts are in the README.

## Earlier runs

I used these runs to find problems and change the code, so they are not in the
results table. Their traces are in `first_run/`, `second_run/` and `third_run/`.

| Run | Seeds | Accepted | Accepted with a major error | Main problems |
|---|---|---|---|---|
| First | 1 to 5 | 63 of 65 | at least 15 | BWBF "fell by 1.1%" (five times), NWSC given CLDN's -0.9 points, "seven months", a "30% limit", advice |
| Second | 11 to 15 | 63 of 65 | at least 13 | GRNE named as the biggest loser with CLDN unknown (all five C-Q4 runs), SFHM placed in Fixed income, false statements about the data, advice |
| Third | 21 to 25 | 69 of 75 | 15, plus 4 minor | SFHM "the second-largest holding", "BWBF fell by 13.6%", HLSW as the largest known holding, "the largest holding, NWSC" in Portfolio C |

The first two counts are lower bounds. I reviewed those runs before I wrote down the
rubric above. A second AI agent then fact-checked the second run and found 8 errors
I had not counted: the five C-Q4 answers and three false statements about the data.
I reviewed the third run and the final run with the rubric. My third-run count used
the earlier, shorter definition of a minor problem.

Some rejections in the earlier runs were my checks' fault:

- **Second run, two rejected runs.** In one, "the concentration in each is not
  measurable" was read as a claim. In the other, "it" in "it fell by more than 6% in
  two months" meant the portfolio, but the check took it to mean NWSC.
- **Third run, two rejected runs.** The checks read items in `cannot_establish`, such
  as "The largest fall, since the change of Cloudline Networks is unknown", as claims.

I fixed all four before the next run.

After each run I changed the checks. Before running again, I replayed the new checks
on every saved answer with `tools/replay_checks.py`, without calling the model. The
replays show that a new check catches the errors I had found and does not send back
correct answers. For example, the claim check sends back 10 of the first run's
accepted answers, and none of the 10 was correct. A replay is not a new run, though:
the model might have answered differently if it had seen the new feedback. So the
reported numbers come only from the final run.
