# Review of the accepted briefings

The Python checks decide whether an answer is accepted, but they only look at
numbers, names, and wording patterns. To see what they miss, the answer of each of
the 75 runs (the accepted answer, or the last one sent back) was printed with
`tools/print_answers.py`, and each sentence was compared with the tool results in its
trace. Quotes are copied from the traces.

## Rubric

The rubric is the one used for the previous reported run
([fourth_run/manual_review.md](fourth_run/manual_review.md)), so the counts can be
compared.

An answer has a **major error** if it states something as fact that the tool
results contradict or do not support:

- **A wrong detail:** a wrong number, direction, period, count, rank, or sector, or a
  number that belongs to another holding.
- **A false statement about the data or the tools**, such as "the file does not
  provide data on all holdings' changes" for Portfolio A, which has a change for
  every holding.
- **A conclusion the data cannot support**, such as calling the incomplete file
  diversified or concentrated, naming its largest holding or biggest loser, or
  calling a 3.9% fall "close to the 20% threshold".
- **Advice wording.**

A **minor problem** is loose wording that does not state a wrong fact outright:

- "within acceptable limits" for the top-three weight, which has no limit;
- a vague plural such as "some holdings" where only one holding is affected;
- "the largest holding cannot be identified because its value is unknown", which
  reads as if the largest holding were the one without a value.

Limitations that are generic but true are not counted.

## Reported run (seeds 41 to 45)

75 runs, 68 accepted.

### The seven rejected runs

In all seven, the last answer still had a content error. The checks caught it in
five. The other two were sent back only for length.

| Run | Problem in the last answer |
|---|---|
| A-missing-Q2, seeds 41, 44, 45 | NWSC named as the largest of the holdings with a known value, with "a value of $29,306.75". NWSC is the holding without a value, and $29,306.75 is `known_value`, the total of the five known values that the concentration tool reports. Seed 41 also says NWSC's price change is unknown; it is +6.3% |
| A-missing-Q4, seeds 41, 43 | "The holding that lost the most value over the last six months is GRNE", with CLDN's change unknown |
| B-Q1, seeds 41, 45 | 185 and 183 words, over the 180-word limit. Both also give "concentration in certain sectors" (seed 45: "specific sectors") as a risk, which no check reads for Portfolio B |

### Accepted briefings with problems

10 of the 68 accepted briefings had a major error, and 7 more had only a minor
problem. The review found nothing wrong in the other 51.

Major errors:

| Run | Problem | Quote |
|---|---|---|
| B-Q1, seeds 42, 43 | Unsupported risk. No holding or sector in Portfolio B is above 13.6%, and the concentration result has no flags | "...significant price declines in several holdings and concentration in certain sectors." (both seeds) |
| A-missing-Q3, seeds 43, 45 | False statement about the data. The total value is unknown | "The total value of the portfolio is known, but one holding, Northwind Semiconductor, has an unknown value" (seed 43) |
| A-Q3, seed 44 | False statement about the data. The concentration result gives every holding's sector and weight | "...since the file does not specify which Technology holdings contribute to the sector weight." |
| B-Q4, seed 42 | False statement about the data. The price result lists every holding's change | "The file does not show how the holdings performed relative to each other or to the overall market." |
| A-Q4, seed 42 | A limitation that the tool result answers. The price result gives every holding's change | "Whether other holdings not listed here also experienced significant price changes." |
| A-Q4, seed 45 | A limitation that the tool result answers. The price result gives each holding's contribution: NWSC added 2.7 points to a 2.3% rise | "...it is not possible to determine if any single holding's performance fully explains the portfolio's change." |
| B-Q2, seed 42 | A limitation that the tool result answers. BWBF rose 1.1% and added 0.1 points, so it did not drive the fall | "...we cannot determine if the largest position was the main driver of the portfolio's decline." |
| A-missing-Q1, seed 42 | Unsupported conclusion. Energy's only holding, GRNE, had a worst month of -6.1%; NWSC, in Technology, had -11.5% | "...the potential for sector-specific volatility, particularly in Energy." |

B-Q1 seed 43 has two more loose sentences, which do not change the count because the
answer already has a major error. It says SFHM fell 34.1% "from its peak" and that
OKRT and RVBK "fell over 22% from their peak". The tools report the change from the
first to the last date; "from their peak" happens to be right because all three fell
every month. "Over 22%" for RVBK is not supported by the tool's 22.0%.

Minor problems:

| Run | Problem | Quote |
|---|---|---|
| A-missing-Q1, seeds 41, 43 | "Some holdings" lack price data. Only CLDN does | "The price changes for some holdings, such as Cloudline Networks, are unknown due to missing data" (seed 41) |
| A-missing-Q4, seeds 42, 44, 45 | "Other holdings" might have lost value. The four other holdings with a known change all rose, so only CLDN is in doubt | "Whether other holdings lost value, since only GRNE is known to have fallen." (all three) |
| A-missing-Q2, seed 43, and A-missing-Q5, seed 45 | Writes as if the largest holding were the one without a value | "Whether the largest position's price has moved significantly, since its share count is missing" (Q2); "because the value of the largest holding is unknown" (Q5) |

Close calls that were not counted:

- A-missing-Q1, seed 44: "the potential for significant losses if any holdings fall
  below the 20% threshold". A hypothetical, and it garbles the 20% holding drop limit.
- A-missing-Q1, seed 45: "missing data on several holdings". Two holdings have
  missing data. The same answer also points to "the potential for sector-specific
  losses, such as the 3.9% drop in Granite Ridge Energy". Unlike seed 42, this names a
  loss that happened, not a volatility the tools do not measure.
- A-Q2, seed 43: "The overall portfolio movement over the period does not reflect the
  movement of the largest position, since the portfolio rose 2.3% in total." Listed
  as a limitation, which it is not, and misleading: NWSC added 2.7 points to the
  2.3% rise. Not counted, because "does not reflect" states no checkable fact.
- A-Q4, seeds 42, 43, 44: "The largest single-month drop was 6.6% in August" (seed
  42; seed 43: "The largest single monthly drop was 6.6%"; seed 44: "The largest
  single month loss was 6.6%"). That is the portfolio's worst month. NWSC (-11.5%)
  and CLDN (-9.2%) had larger single-month drops, and the sentences do not say they
  mean the portfolio.
- A-Q4, seed 41, and B-Q4, seed 44: "The file does not include data on how different
  sectors performed relative to each other." The tools do not report sector changes,
  although they could be computed from the file.
- B-Q4, seeds 42 and 44: "this does not indicate which holdings caused the loss".
  This is true of the 10.4% figure itself, and both answers name the three biggest
  losers.
- B-Q5, seeds 43 and 44: "Whether the portfolio's overall decline is due to specific
  holdings or broader market trends". The contributions show which holdings made the
  loss, but not why they fell, so this is about causes the file cannot show. Compare
  B-Q2 seed 42, counted above, which asks something the tool result answers.
- A-Q5, seed 43: "its recent drop raises concerns". NWSC's last fall was in August,
  and it rose 9.2% in September and 4.3% in October. The answer does not say when
  the drop was, so this is loose rather than a wrong period.
- B-Q5, seed 45: "the decision to sell part of it should consider other factors
  beyond concentration risk". It uses "should" about the decision, but does not say
  which way to decide.
- B-Q2, seeds 41 and 43: "the 10th largest holding in the Consumer discretionary
  sector" (seed 43: "the tenth largest holding"). SFHM is tenth overall, and the only
  holding in its sector.

Why the checks missed them:

- **B-Q1:** "concentration in certain sectors" is only checked when weights are
  unavailable. For Portfolio B they are available. The same gap let one B-Q1 answer
  through in the previous run.
- **A-missing-Q3:** no check reads what an answer says about the total value. The
  concentration result includes `known_value`, a total of the five known values,
  which may have led the model to call the total known. The three rejected
  A-missing-Q2 runs gave the same number to NWSC.
- **The five false statements and limitations in A and B:** no check reads
  `cannot_establish` items, or sentences about the file, for what they claim. The
  previous run had four answers of this kind, all in A-Q4 and B-Q4.
- **A-missing-Q1, seed 42:** the tools do not measure volatility, so there is
  nothing to check the claim against.
- **The minor problems:** no check counts holdings written in words ("some
  holdings", "other holdings"). For the two "largest holding" sentences: the Q5 one
  contains "cannot", which lets a sentence pass the "largest" check, and the Q2 one
  is a `cannot_establish` item, which that check does not read.

### The ranking fix

In the previous run, four accepted answers named HLSW as the largest holding with a
known value. The tool listed holdings in file order when a value was missing, and
HLSW was the first row with a value. The tool now lists them by value. In this run,
ten accepted answers name a largest known holding, and all ten name BWBF. Two first
answers still named HLSW (A-missing-Q5, seeds 41 and 43), and the rank check sent
both back.

### Compared with the previous reported run

| | Previous run (seeds 31 to 35) | This run (seeds 41 to 45) |
|---|---|---|
| Accepted | 69 of 75 | 68 of 75 |
| Accepted with a major error | 11 | 10 |
| Accepted with only a minor problem | 10 | 7 |
| Accepted with no problem found | 48 | 51 |

The clear change is the ranking error above, which went from four answers to none.
One error type got more common: false statements about what the data can show went
from four answers to seven. Three things limit the comparison:

- With five seeds per case, a difference of one or two answers between runs can be
  chance.
- The two reviews were done separately. The previous one did not count "Whether
  other holdings lost value, since only GRNE is known to have fallen" in C-Q4 seed
  32, the sentence counted here as a minor problem in three A-missing-Q4 answers.
  Counted the same way, that run would have 11 minor problems.
- Ollama was updated between the runs: 0.40.3 for all earlier runs, 0.40.14 for
  this one.

## Earlier runs

These runs are not in the results table. The first three were development runs, and
the fourth was the reported run before the instructor's feedback.
[fourth_run/manual_review.md](fourth_run/manual_review.md) reviews the fourth in
detail, summarizes the first three, and says which counts are lower bounds.

| Run | Seeds | Accepted | Accepted with a major error | Main problems |
|---|---|---|---|---|
| First | 1 to 5 | 63 of 65 | at least 15 | BWBF "fell by 1.1%" (five times), NWSC given CLDN's -0.9 points, "seven months", a "30% limit", advice |
| Second | 11 to 15 | 63 of 65 | at least 13 | GRNE named as the biggest loser with CLDN unknown (all five C-Q4 runs), SFHM placed in Fixed income, false statements about the data, advice |
| Third | 21 to 25 | 69 of 75 | 15, plus 4 minor | SFHM "the second-largest holding", "BWBF fell by 13.6%", HLSW as the largest known holding, "the largest holding, NWSC" in the incomplete file |
| Fourth (reported before the instructor's feedback) | 31 to 35 | 69 of 75 | 11, plus 10 minor | HLSW as the largest known holding (four C-Q3 answers), false statements about the data (A-Q4 and B-Q4), BWBF given the portfolio's 10.4% fall |

In these runs the incomplete file was called `portfolio_c.csv` and its cases C-Q1 to
C-Q5. They are the same file and questions as A-missing-Q1 to A-missing-Q5 now.
