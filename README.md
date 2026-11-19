# Financial Risk Briefing Agent

CSYE 7374 Agentic AI, Fall 2026. Three-week mini project, student ID ending 56162.
Tianle Yang.

This agent writes short risk briefings about a small fictional investment
portfolio stored in a CSV file. For a question such as "What are the main risks in
this portfolio?", a local model (qwen3:8b through Ollama) decides whether to call
a concentration tool, a price-change tool, or both. Python does all of the
arithmetic. It also checks the model's final answer before accepting it: every
number has to come from a tool result, missing data has to be mentioned, some claims
that would need a missing number are sent back (such as naming the largest holding
when a value is missing), and the answer may not tell anyone to buy or sell. Every briefing has a section on what the sample cannot
establish.

All company names, tickers, share counts, and prices here are made up. The
briefings describe a fictional sample and are not investment advice.

## How the project covers the assignment

| Requirement | Where |
|---|---|
| Small fictional portfolio saved in a CSV file | [data/](data/): Portfolios A and B, plus a copy of A with two values deleted |
| The model decides whether to call a concentration tool, a price-change tool, or both | [briefing_agent.py](briefing_agent.py); tool column in [results/runs.csv](results/runs.csv) |
| Short explanation using the actual numbers | Number checks in `check_final_answer()`; briefings in [results/run_record.md](results/run_record.md) |
| Says what the sample cannot establish | Required `cannot_establish` list, printed under "What this sample cannot establish" |
| Compare two mock portfolios with different risks | [Portfolio A vs. Portfolio B](#demonstration-portfolio-a-vs-portfolio-b) |
| At least two tools; observations decide the next step | Two tools. Tool results and Python's feedback change the next step: 42 first answers sent back, 35 of those runs ended with an accepted briefing, and different conclusions when values are missing ([details](#what-the-agent-does-with-what-it-sees)) |
| An ordinary case and an incomplete-information case | A and B have complete data; the [incomplete-information case](#incomplete-information-case-portfolio-a-with-two-values-missing) is A's file with two values deleted |
| Short record of what happened | [results/run_record.md](results/run_record.md), every step in [results/traces/](results/traces/), the review in [results/review.md](results/review.md) |
| Free or low-cost model | qwen3:8b running locally through Ollama. No API cost. |
| Not presented as personal investment advice | Advice checks, the buy/sell/hold rule, and a fixed closing line in every briefing |
| Instructor's feedback: two portfolios, two risk calculations | Portfolios A and B; `check_concentration` and `check_price_changes` ([changes](#changes-after-the-instructors-feedback)) |
| Instructor's feedback: numbers verified in Python | Python computes every number, and [verify_numbers.py](verify_numbers.py) checks them again with exact arithmetic ([details](#checking-the-numbers)) |

## Changes after the instructor's feedback

The instructor approved the topic and recommended limiting the project to two
fictional portfolios and two risk calculations, with the numbers verified in Python.

- **Two portfolios.** The first version had three CSV files and called the third one
  Portfolio C. That file was always Portfolio A with two cells deleted. It is now
  named [data/portfolio_a_missing.csv](data/portfolio_a_missing.csv) and used only as
  A's incomplete-information case, which the course's mini-project instructions ask
  for. The holdings, prices, and questions did not change.
- **Two risk calculations.** No change: `check_concentration` and
  `check_price_changes`.
- **Numbers verified in Python.** The tools already did all the arithmetic, and the
  answer checks already required every number to appear in a tool result. Nothing
  checked the tools themselves. [verify_numbers.py](verify_numbers.py) now redoes the
  arithmetic separately. It checks every value, weight, change, total, count,
  ranking and flag the tools report, and every number in the [Data](#data) section.
- **One fix to a tool.** When a value is missing, `check_concentration` now lists the
  holdings with a known value from largest to smallest. In the previous reported run,
  the listing in file order was the likely cause of the most common error: HLSW named
  as the largest known holding instead of BWBF. The previous README already described
  this one-line fix but left it out because the code was frozen.
- **A new reported run.** Because the code changed, the results below come from a new
  run with new seeds (41 to 45). The previous reported run (seeds 31 to 35) and its
  review are kept in [results/fourth_run/](results/fourth_run/).

## Quick start

You need Python 3.10 or newer (I used 3.13.5), [Ollama](https://ollama.com/), and
the qwen3:8b model, which is a 5.2 GB download.

```bash
pip install -r requirements.txt
```

```bash
ollama pull qwen3:8b
```

```bash
python briefing_agent.py data/portfolio_a.csv "What are the main risks in this portfolio?" --label "Portfolio A" --seed 44
```

```bash
python -m unittest discover -s tests -v
```

```bash
python verify_numbers.py --traces results/traces
```

The 49 unit tests do not need Ollama. They do four things:

- compare the tool output with numbers I worked out by hand;
- compare every tool number, and the numbers in this README, with the exact
  calculation in `verify_numbers.py`;
- run the agent loop with a scripted fake model;
- feed the answer checks the real mistakes collected from my runs.

`python run_demo.py` repeats the reported evaluation (15 cases, seeds 41 to 45). It
took 14 minutes on my laptop (RTX 4060 Laptop GPU, 8 GB), and it overwrites
`results/runs.csv`, `results/run_record.md` and `results/traces/`.

A fixed seed makes reruns close but not always identical. Three reruns of the
quick-start command:

- **Seed 11, during development:** reproduced the saved briefing word for word
  ([results/second_run/rerun_A-Q1-s11.json](results/second_run/rerun_A-Q1-s11.json)).
- **Seed 31, in the previous reported run:** gave the same two tool calls and an
  accepted answer with the same facts, but different wording
  ([results/fourth_run/rerun_A-Q1-s31.json](results/fourth_run/rerun_A-Q1-s31.json)).
- **Seed 44, in this run:** all four model replies were the same as in the saved
  run, so the briefing was the same word for word
  ([results/rerun_A-Q1-s44.json](results/rerun_A-Q1-s44.json)).

Ollama does not promise bit-identical output when its cache is reused, so a full
rerun gives a similar table, not necessarily the same one.

## Data

There are two portfolios, A and B, as the instructor recommended. Each CSV file has
one row per holding: ticker, name, sector, share count, and seven month-end closing
prices from 2026-04-30 to 2026-10-30, which covers six months.

| | Portfolio A | Portfolio B |
|---|---|---|
| Built to show | Concentration | Losses in a spread-out portfolio |
| Holdings | 6 | 10 |
| Value on 2026-10-30 | $52,318.75 | $50,947.10 |
| Largest holding | NWSC, 44.0% | BWBF, 13.6% |
| Largest sector | Technology, 67.9% | Fixed income, 13.6% |
| Effective number of holdings | 3.8 | 9.7 |
| Six-month change | +2.3% | -10.4% |
| Worst month | -6.6% (August) | -3.9% (August) |

- **Portfolio A** gains only 2.3% over the six months but swings from month to month.
  - It fell 6.3% in June and 6.6% in August.
  - NWSC fell 10.5% and 11.5% in those months. In dollars, it accounts for 73% of the
    June fall and 76% of the August fall.
- **Portfolio B** has no position above 14%, but it lost $5,890.65 (10.4%) over the six
  months.
  - SFHM fell 34.1%, OKRT 26.9%, and RVBK 22.0%.
  - These three account for 85% of the net loss.

`verify_numbers.py` writes every row of the table and every figure in the two lists
above from the CSV files, and checks that they appear here as written (see
[Checking the numbers](#checking-the-numbers)).

**The incomplete-information case** uses a third file,
[data/portfolio_a_missing.csv](data/portfolio_a_missing.csv). It is not a third
portfolio. It is Portfolio A's file with two cells deleted: the NWSC share count and
the CLDN price on 2026-04-30.

- Because the holdings are A's, I know what a complete answer would say.
- NWSC is the holding that makes A concentrated, and CLDN is A's biggest loser. So an
  answer that calls this portfolio diversified, names its largest holding, or names
  its biggest loser is unsupported.

## The two tools

Both tools are in [risk_tools.py](risk_tools.py). The model calls them with an empty
argument (`{}`), and each returns `{"ok": ..., "message": ..., "data": ...}`, the same
shape as the Agent Airways tools from class.

- **`check_concentration`**
  - Reports the value and weight of each holding, the weight of each sector, the
    top-three weight, and the effective number of holdings (1 divided by the sum of
    squared weights).
  - Flags any holding above 20% and any sector above 40%.
  - If any holding has no value, it does not compute weights at all. It reports the
    known values, largest first, and says that the total is unknown.
- **`check_price_changes`**
  - For each holding: the change from the first to the last date (as a number and as
    text, for example "rose 1.1%"), the dollar change, the worst single month, and
    its contribution to the portfolio change.
  - For the whole portfolio: the six-month change, each monthly change, the worst
    month, and the largest fall from a month-end high.
  - Flags any holding that fell 20% or more, and any month in which the portfolio
    fell 5% or more.
  - If any holding lacks a price or a share count, it still reports the holdings it
    can, but leaves out the portfolio totals.
  - If any holding's change is unknown, it does not name a largest fall. It reports
    the largest fall "among known changes" instead.

The four limits (20%, 40%, 20%, 5%) are reference points I chose for this project.
They are not regulatory rules, and they are set at the top of `risk_tools.py`. The
rule of leaving a number out rather than computing it from the complete rows came
from testing. When the first version reported weights for the five known holdings of
the incomplete file, the model presented them as real weights. One partial number is
still reported: when a value is missing, `check_concentration` gives `known_value`,
the total of the holdings that have a value ($29,306.75 for the incomplete file). In
three rejected runs the model gave that number to NWSC (see [Results](#results)).

## The agent loop

[briefing_agent.py](briefing_agent.py) follows the Agent Airways harness: one JSON
action per reply, and a tool result after each action.

1. The model gets a system prompt that describes the two tools and the answer rules,
   plus the question. It never sees the CSV rows or the portfolio's name.
2. Each reply must be one action. It is either a tool call, such as
   `{"action": "check_concentration", "argument": {}}`, or `final_answer` with
   `summary`, `findings`, and `cannot_establish`.
3. Python runs the tool and sends the result back as `TOOL RESULT`. If the model
   repeats a call, it gets a reminder instead of a second run.
4. Every final answer goes through `check_final_answer()`. If the answer fails, the
   model gets `PYTHON CHECK` with the list of problems and tries again. It gets four
   tries at most and eight model replies in total.
5. An accepted answer is printed as a briefing. Python adds three things: the list
   of tools used, every piece of missing data the tools reported, and a closing line
   saying the briefing is not investment advice.

`check_final_answer()` sends an answer back for any of the problems below.

**Form**

- No tool has been called yet.
- The keys are wrong, the summary is empty, or `findings` or `cannot_establish` is
  not a list of text.
- A list is empty, has an empty item, or has more than three items.
- None of the findings uses a number. This applies only when no data is missing.
- The answer is longer than 180 words.

**Numbers**

- A number does not appear in any tool result. Rounding is allowed, so "6%" matches
  6.3. Dates are removed first, so the 30 in 2026-04-30 cannot pass as a "30% limit".
- A percentage given for a holding belongs to a different holding.
- A percentage given for a holding belongs to the whole portfolio or a sector. This
  is only checked when the holding is named in the same clause, and in two forms:
  - a portfolio change given as the holding's move ("SFHM fell 10.4%"), unless the
    clause mentions the portfolio;
  - a sector or top-three weight given as the holding's share ("NWSC is 67.9% of the
    portfolio"), unless the clause names a sector or the top three.
- A holding's weight is used as a price change ("BWBF fell by 13.6%").
- A change is described in the wrong direction ("fell 1.1%" for a holding that rose
  1.1%).
- A holding is given the wrong rank or sector ("SFHM, the second-largest holding").
- The top-three weight is called "within" a limit. There is no such limit.

**Missing data**

- The tools reported missing data, but the answer names none of the affected
  holdings.
- The answer makes a claim that needs a number the tools could not compute. With
  the incomplete file, that means calling the portfolio concentrated or diversified,
  naming its largest holding, naming the holding that fell or rose the most, or
  saying "the portfolio fell".
  - The "largest" and "most" checks let a sentence through if it contains a qualifier
    word such as "among", "known", "cannot" or "whether" anywhere in it. This is a
    loose rule (see [Limitations](#limitations)).
- The answer calls NWSC one of the "holdings with a known value".

**Advice**

- The answer uses advice wording ("you should", "consider selling", "selling ... could
  help", and similar).
- The question asks whether to buy, sell, or hold, and the summary has no sentence
  like "this briefing cannot answer whether ...". The check looks for a negative
  ("cannot", "does not") with a verb such as "answer", "say" or "tell", followed by
  "whether", "buy", "sell", "hold" or "should". A refusal about something else, such
  as "cannot tell whether the trend continues", would also pass.

The model runs with thinking off and JSON output, as in the class notebook.
`num_ctx` is 8192, and each run uses a fixed Ollama seed. If Ollama returns an error,
the loop waits 5 seconds and retries up to two times. I added this after Ollama ran
out of GPU memory in one of the development runs.

## Checking the numbers

Python handles the numbers at three points.

1. **The tools compute them.** All arithmetic is in `risk_tools.py`. The model never
   computes a number, and the prompt tells it to copy numbers as the tools wrote them.
2. **Each answer is checked.** `check_final_answer()` sends an answer back if a number
   in it does not appear in any tool result, or if a number is used for the wrong
   holding (see the checks above).
3. **The tools are checked.** [verify_numbers.py](verify_numbers.py) reads the CSV
   files again and redoes the arithmetic with Python's `Decimal`, which is exact for
   these share counts and prices. Its numbers do not come from the tool code, and it
   takes the four limits from this README, not from `risk_tools.py`. It checks:
   - 418 items in the tool results for the three files: every value, weight,
     change, total, count, ranking and flag, the direction text the model copies
     ("rose 1.1%"), and, for the incomplete file, that the numbers which need the
     missing values are left out. A number passes if it is within half a unit of its
     last decimal place;
   - the [Data](#data) section of this README. The script writes each table row and
     each figure in the two lists from the exact numbers, and each must appear there
     as written;
   - with `--traces results/traces`, each of the 113 tool results saved in the
     reported run, against a fresh call of the same tool.

```bash
python verify_numbers.py --traces results/traces
```

Everything matched. The unit tests run all three checks and also fix the counts
(418 and 113), so a comparison that is silently skipped makes a test fail. Two more
tests shift every percentage the tools produce by 0.1, or change a limit in
`risk_tools.py`, and check that the comparison catches it.

## Demonstration: Portfolio A vs. Portfolio B

The same question with seed 44, from [results/traces/](results/traces/). For B, seed
44 is the only one of the five runs whose briefing has no error: seeds 41 and 45 were
rejected, and seeds 42 and 43 call "concentration in certain sectors" a risk (see
below). Seed 41 is the run shown step by step in
[results/run_record.md](results/run_record.md). In both runs below the model called
both tools.

```text
Risk briefing: Portfolio A (fictional data)
Question: What are the main risks in this portfolio?
Tools used: check_concentration, check_price_changes

The main risks in this portfolio are its high concentration in a single holding and a sector, as well as significant monthly drops that exceed the portfolio's monthly drop limit.

What the numbers show:
- Northwind Semiconductor is 44.0% of the portfolio, which is above the 20% single-holding limit.
- Technology is 67.9% of the portfolio, which is above the 40% sector limit.
- The portfolio fell 6.6% in the month ending 2026-08-31, which exceeds the 5% monthly drop limit.

What this sample cannot establish:
- The portfolio's performance over a longer period is not visible since the file only includes data from 2026-04-30 to 2026-10-30.
- The reasons for price changes in individual holdings are not provided, as the file only includes prices and not trading activity or external factors.
```

```text
Risk briefing: Portfolio B (fictional data)
Question: What are the main risks in this portfolio?
Tools used: check_concentration, check_price_changes

The main risks in this portfolio include significant price declines in several holdings and a general downward trend over the past six months. The portfolio as a whole fell by 10.4%, with some holdings falling over 20%, which exceeds the holding drop limit.

What the numbers show:
- The largest single holding, Bluewater Bond Fund, saw its price rise slightly over the period, but several other holdings fell by more than 20% in value.
- Several holdings, including Summit Furnishings and Oak Street Realty Trust, fell by more than 20% in value, exceeding the holding drop limit.
- The portfolio as a whole fell by 10.4% over the six-month period, with the worst monthly drop being 3.9% in August.

What this sample cannot establish:
- The reasons for the price declines in specific holdings are not provided in the data.
- Whether the portfolio's performance will continue in the same direction cannot be determined from the available data.
- The impact of external factors like market trends or economic conditions on the portfolio is not included in the data.
```

(The closing line of both briefings is cut here.) The B briefing was accepted on the
third try. Its first two tries said BWBF "fell by 13.6% in weight". The first was sent
back for having four `cannot_establish` items, and the second by the check on weights
used as price changes.

Both runs used the same tools and reached different conclusions:

- For A, the main risk is that 44.0% of the value sits in one stock and 67.9% in one
  sector, and both are flagged.
- For B, concentration is not the problem: the concentration result has no flags
  and says so. The main risk is the price losses. These are changes in market value:
  the file has no trades, and the tools treat the share counts as fixed.

Across the five seeds:

- All five A-Q1 briefings name the 44.0% and 67.9% weights as main risks.
- Three of the five B-Q1 runs were accepted, and all three lead with the losses. Two
  of them (seeds 42 and 43) also list "concentration in certain sectors" as a risk,
  which is wrong, and the review counts both as errors. The two rejected runs were
  over the word limit and made the same claim.
- On the direct question (Q3), all five A answers say A is too dependent on one
  company and one sector, and all five B answers say B is not.

So Q3 shows the different conclusions more reliably than Q1: all ten Q3 answers reach
the right conclusion, although one of them (A-Q3, seed 44) has a false limitation.

## Incomplete-information case: Portfolio A with two values missing

The concentration tool reports "Weights cannot be calculated: NWSC has no known
value on 2026-10-30". The price tool leaves out the portfolio totals and the largest
fall. Here is seed 45 of "Which holdings lost the most value over the last six
months?":

```text
Risk briefing: Portfolio A, two values missing (fictional data)
Question: Which holdings lost the most value over the last six months?
Tools used: check_price_changes

GRNE was the only holding with a known price change that lost value, falling 3.9% over the last six months. The largest fall cannot be identified because the change for CLDN is unknown.

What the numbers show:
- GRNE fell 3.9% over the six-month period.
- The change for CLDN is unknown, so the largest fall cannot be identified.
- The portfolio totals are not calculated because two holdings lack a price or a share count.

What this sample cannot establish:
- Whether other holdings lost value, since only GRNE is known to have fallen.
- The exact impact of the missing data on the portfolio totals.
- The reason for the price change of GRNE, since the file only has prices and no additional data.

Missing data reported by the tools:
- NWSC (Northwind Semiconductor): share count is missing, so its value change and the portfolio totals cannot be calculated; its price change is known.
- CLDN (Cloudline Networks): no price on 2026-04-30, so its change from 2026-04-30 to 2026-10-30 is unknown and the portfolio totals cannot be calculated.
```

(The closing line is cut.) This answer was accepted on the third try. The first two
tries said "The only holding that lost value over the last six months was GRNE",
without the qualifier. In the complete file, CLDN fell 8.0%, so that claim would have
been wrong. The accepted answer is not perfect either. Its first limitation, "Whether
other holdings lost value", is loose: the four other holdings with a known change all
rose, so only CLDN is in doubt. The review counts this as a minor problem.

Across the 25 runs with the incomplete file:

- **Q1 (main risks):** 5 of 5 were accepted. All five name NWSC's missing value, and
  two also name CLDN. Seed 42 singles out Energy for "sector-specific volatility",
  which the data does not support.
- **Q2 (largest position):** 2 of 5 were accepted, and both say the largest position
  cannot be identified. Seed 42 adds that BWBF is the largest of the known values,
  which is right. The three rejected runs kept naming NWSC as the largest known
  holding, with "a value of $29,306.75". That number is `known_value`, the total of
  the five known values.
- **Q3 (dependence):** all five say it cannot be determined, and four name BWBF as the
  largest known holding, which is right. Two (seeds 43 and 45) also say "The total
  value of the portfolio is known", which is false.
- **Q4 (losses):** 3 of 5 were accepted, all with a qualifier such as "only holding
  with a known loss". All three also have the loose "Whether other holdings lost
  value" limitation. The other two kept naming GRNE as the holding that "lost the
  most" and were rejected.
- **Q5 (sell?):** 5 of 5 were accepted. All five decline to answer, say the total
  value is unknown, and name BWBF as the largest known holding. Seed 45's summary
  also says "the value of the largest holding is unknown", which reads as if NWSC
  were the largest.

## What the agent does with what it sees

All numbers in this section are from the reported run (75 runs).

### Choosing tools

The model chose tools in line with each question:

- Q1 and Q2: both tools in 30 of 30 runs.
- Q3: only `check_concentration`, in 15 of 15.
- Q4: only `check_price_changes`, in 15 of 15.

The system prompt says which kind of question needs which tool, so for Q1 to Q4 this
mostly shows the model applying that rule to the wording of the question. It does
not show a decision driven by tool results. For Q5 the tool choice varied between
runs:

- This run: the model also checked prices in 4 of 5 runs for A and 4 of 5 for B,
  and in none of the 5 runs with the incomplete file.
- Previous reported run: it checked prices for B but not for A, 5 of 5 times each.
- Second development run: it was the other way round.

So I do not count Q5 as evidence of the agent checking different facts.

### Missing data

Here the tool results change the outcome. With the incomplete file, no accepted
answer gave a weight, called the portfolio diversified or concentrated, or stated a
portfolio-level change. Every accepted answer that named a largest holding added the
"known value" qualifier and named BWBF, which is right. The checks hold the model to
this, as the Q4 example above shows. Two accepted answers still said that the total
value was known, and no check reads that.

### Python's feedback

In 42 runs the first final answer was sent back, and 35 of those runs ended with an
accepted briefing. In total, 75 answers were sent back. An answer can fail more than
one check, so the counts below add up to more than 75.

| Check | Answers sent back (all tries) | First answers sent back |
|---|---|---|
| The same answer sent again (always together with another problem) | 17 | 0 |
| Buy/sell/hold question without a refusal in the summary | 15 | 11 |
| Biggest fall or rise named in the incomplete file, where CLDN's change is unknown | 13 | 5 |
| `findings` or `cannot_establish` not sent as a list | 11 | 11 |
| "Largest holding" in the incomplete file, where weights are unavailable | 11 | 9 |
| NWSC called a holding with a known value | 9 | 0 |
| Over 180 words | 9 | 3 |
| Too many items | 5 | 3 |
| Wrong rank ("The largest holding is Harbor Lane Software") | 5 | 4 |
| Advice wording | 2 | 0 |
| A number that is not in any tool result | 2 | 2 |
| Wrong sector | 2 | 1 |
| Wrong direction ("BWBF fell 1.1%") | 1 | 1 |
| A weight used as a price change | 1 | 0 |
| Top-three weight called within a limit | 1 | 1 |

Two first answers failed the basic number check. Both said some B holdings fell
"over 26%", a bound that is not in the tool results (OKRT fell 26.9%). After the
feedback, every number in every accepted briefing appears in a tool result. The
errors that remain are about what a sentence claims, not about the numbers in it.

## Results

Reported run: qwen3:8b through Ollama 0.40.14, 15 cases with seeds 41 to 45, 10.8
seconds per run on average. I froze the code before this run. The SHA-256 hashes of `briefing_agent.py`,
`risk_tools.py`, `run_demo.py` and the three data files were the same before and after
it ([results/code_hashes.txt](results/code_hashes.txt)). Running the frozen checks
again on the last answer of every run (`tools/replay_checks.py`) gives the same
verdicts.

| Case | Question | Accepted | Expected tools | Expected facts | Mean model replies |
|---|---|---|---|---|---|
| A-Q1 | What are the main risks in this portfolio? | 5/5 | 5/5 | 15/15 | 3.8 |
| B-Q1 | same | 3/5 | 5/5 | 6/10 | 4.8 |
| A-missing-Q1 | same | 5/5 | 5/5 | 7/10 | 3.6 |
| A-Q2 | How big is the largest position, and how has its price moved? | 5/5 | 5/5 | 15/15 | 3.0 |
| B-Q2 | same | 5/5 | 5/5 | 15/15 | 3.6 |
| A-missing-Q2 | same | 2/5 | 5/5 | 1/5 | 5.2 |
| A-Q3 | Is this portfolio too dependent on one company or one sector? | 5/5 | 5/5 | 10/10 | 2.2 |
| B-Q3 | same | 5/5 | 5/5 | 5/5 | 2.2 |
| A-missing-Q3 | same | 5/5 | 5/5 | 5/5 | 2.8 |
| A-Q4 | Which holdings lost the most value over the last six months? | 5/5 | 5/5 | 10/10 | 2.0 |
| B-Q4 | same | 5/5 | 5/5 | 15/15 | 2.0 |
| A-missing-Q4 | same | 3/5 | 5/5 | 9/15 | 4.2 |
| A-Q5 | Should I sell part of my largest holding? | 5/5 | 5/5 | 10/10 | 4.4 |
| B-Q5 | same | 5/5 | 5/5 | 10/10 | 4.4 |
| A-missing-Q5 | same | 5/5 | 5/5 | 5/5 | 3.0 |
| **All** | | **68/75** | **75/75** | | |

How to read the columns:

- **Expected tools:** both tools for Q1 and Q2 (for A-missing-Q2, at least the
  concentration tool), only the concentration tool for Q3, only the price tool for
  Q4, and at least the concentration tool for Q5.
- **Expected facts:** counts facts I listed in advance for each case, matched by
  pattern (for example "44.0%" and "67.9%" for A-Q1). It measures completeness, not
  correctness. A rejected run counts 0. A-missing-Q1 is 7/10 because all five answers
  named NWSC but only two named CLDN. Python lists both under the briefing anyway.
  A-missing-Q2 is 1/5 because three runs were rejected and one of the two accepted
  answers says "one holding has an unknown value" without naming NWSC.

Seven runs were rejected after four tries, and in all seven the last answer still
had a content error. The checks caught it in five, all with the incomplete file:
three named NWSC as the largest known holding, and two named GRNE as the holding
that lost the most. The other two were B-Q1 answers over the word limit that also
gave "concentration in certain sectors" as a risk.

**Review of the accepted briefings.** The checks only look at numbers, names, and
wording patterns, so each accepted briefing was also compared sentence by sentence
with the tool results in its trace, using the rubric from the previous reported run.
The rubric, details and quotes are in [results/review.md](results/review.md). 10 of
the 68 accepted briefings had a major error:

- **False statements about the data, seven answers.**
  - Two A-missing-Q3 answers say "The total value of the portfolio is known". It is
    not.
  - Two say the file does not show something that the tool results do show: which
    Technology holdings make up the sector weight (A-Q3, seed 44), and how the
    holdings performed relative to each other (B-Q4, seed 42).
  - Three list as a limit something the tool results answer: whether other holdings
    had large changes (A-Q4, seed 42), whether one holding explains the portfolio's
    change (A-Q4, seed 45), and whether BWBF drove B's fall (B-Q2, seed 42). BWBF
    rose 1.1%.
- **B-Q1, two answers:** "concentration in certain sectors" given as a risk. No
  holding or sector in B is above 13.6%.
- **A-missing-Q1, one answer:** Energy singled out for "sector-specific volatility".
  GRNE's worst month (-6.1%) was milder than NWSC's (-11.5%).

7 more briefings had only a minor problem. Five use a vague plural where only CLDN's
change is unknown: two A-missing-Q1 answers say "some holdings" have unknown price
changes, and three A-missing-Q4 answers say "Whether other holdings lost value". Two
answers write as if the largest holding were the one without a value.

The previous reported run had 11 major errors and 10 minor problems in 69 accepted
briefings. The ranking error from that run is gone: ten accepted answers name the
largest known holding, and all ten name BWBF. False statements about the data went
from four answers to seven. The comparison has limits:

- With five seeds per case, differences of one or two answers may be chance.
- The previous review did not count the "other holdings lost value" sentence, which
  also appears in C-Q4 seed 32 of that run.
- Ollama was updated between the two runs, from 0.40.3 to 0.40.14.

## What changed during development

Three kinds of earlier run are not counted in the table above:

- **Short development rounds** with seeds 100 to 108. I did not keep these.
- **Three full development runs**, with seeds 1 to 5, 11 to 15, and 21 to 25. These
  are kept in [results/first_run/](results/first_run/),
  [results/second_run/](results/second_run/) and
  [results/third_run/](results/third_run/).
- **The previous reported run**, with seeds 31 to 35, made with frozen code before
  the instructor's feedback. It is kept in [results/fourth_run/](results/fourth_run/).

[results/review.md](results/review.md) summarizes what the review found in each of
the four.

The changes that mattered most:

1. **The answer schema.** It first had a `risks` field, and for Portfolio B the model
   invented risks such as "13.6% is close to the 20% limit". I renamed the field to
   `findings` and told the model to say plainly when a check found nothing. That
   reduced these invented risks but did not stop them.
2. **Partial numbers.** The first tools computed weights and totals from the complete
   rows of the incomplete file, and the model presented them as the real numbers. Now
   the tools leave those numbers out.
3. **Clear field names and directions.**
   - The model mixed NWSC's worst month (-11.5%) with its six-month change (+6.3%).
     Separate field names (`period_change_pct`, `worst_month_change_pct`) fixed this.
   - In the first full run, all five B-Q2 summaries said BWBF "fell by 1.1%". Adding
     the direction as text ("rose 1.1%") stopped this error.
4. **The `tickers` filter.** The price tool first had an optional `tickers` argument.
   In every Q4 run the model first sent made-up tickers ("Portfolio A", and later
   "ABC"). In one development round it also repeated an invented `period` argument
   until it ran out of steps. I removed the argument and made the error messages say
   what the tool covers. It was the same kind of loop I saw in my Agent Airways
   extra-credit runs, where the model kept sending a rejected button name.
5. **Missing data in the briefing.** At first the model had to name every holding
   with missing data within three items, and it kept dropping one to stay under the
   limit. Now Python prints the full list under the briefing, and the model has to
   name at least one affected holding.
6. **The claim check**, added after reading the first full run. It checks whose
   number a percentage is and whether the direction is right.
7. **An independent review after the second run.** I had a second AI agent review the
   project. It got the code, data, results and my write-up, and fact-checked them. Its
   main findings, and what I did:
   - My price tool still named a largest fall in the incomplete file, which broke my
     own missing-data rule, and the Q4 answers for that file built on it. The tool no
     longer does this.
   - My hedge words ("missing", "unavailable") let real claims through. I removed them
     from the list.
   - A sentence like "the largest fall of any holding was 8.0%" was wrongly tied to
     the holding named before it. Now a clause only continues the previous holding if
     it refers back to it ("its", "which", or a verb that opens the clause).
   - I had changed the checks after my "final" run, so the reported table could not
     be reproduced with the submitted code. That is why the reported run is a
     separate run with frozen code.
   - I also added Q2 and Q5 for the incomplete file, since it had not been asked
     about its largest position.
8. **After the third run.** I added the rank, sector and weight-as-change checks, the
   top-three rule, and the check on NWSC being called a holding with a known value. I
   also allowed four tries instead of three. Items in `cannot_establish` are no longer
   read as "largest" or "most" claims, because two correct answers had been rejected
   that way.
9. **A second look by the same agent after the previous reported run.** It confirmed
   that replaying the frozen code on all 137 saved answers of that run gives the
   original verdicts. It also found places where I had applied my rubric unevenly and
   some loose claims in this README. I corrected the documents and did not change the
   code again until the instructor's feedback.
10. **After the instructor's feedback.** Two portfolios plus the incomplete copy of A,
    `verify_numbers.py`, the sorted listing when a value is missing, and a new
    reported run with seeds 41 to 45 (see
    [Changes after the instructor's feedback](#changes-after-the-instructors-feedback)).

## Limitations

- **The checks only match patterns.** In the reported run they sent back 75 answers
  for 15 kinds of problem, but 10 of the 68 accepted briefings still had a major
  error.
  - Each check covers only the phrasings it was written for. For example, it reads
    "the largest holding is X" but not "the largest holding by value is X".
  - The "largest" and "most" checks pass any sentence that contains a qualifier word.
    So these would be accepted for the incomplete file: "Among all holdings, GRNE
    lost the most value" and "GRNE lost the most value, though why cannot be known".
    A stricter version would require "among holdings with a known change (or value)"
    in the same clause as the claim.
  - Concentration claims are only checked when weights are unavailable. This is why
    two B-Q1 answers with "concentration in certain sectors" were accepted.
- **Nothing checks what an answer says about the data itself.** Seven accepted
  answers said something false about it, such as "The total value of the portfolio is
  known" for the incomplete file, or that the file does not show how the holdings
  performed relative to each other.
- **One partial total is still reported.** For the incomplete file,
  `check_concentration` gives `known_value`, the total of the five holdings with a
  value. It is the number the three rejected A-missing-Q2 runs gave to NWSC, and it
  may be behind the two answers that call the total value known. Leaving it out would
  follow the tools' own rule. I did not change it after the run, because the code was
  frozen.
- **Tool choice for Q1 to Q4 follows a rule in the prompt.** The model applies the
  rule well, but it is not working out on its own which tool a question needs.
- **The `cannot_establish` items are often generic.**
  - Many repeat the examples in the prompt ("whether a trend will continue, since
    there are only a few month-end prices").
  - Some are false. Three accepted answers list as a limit something the tool results
    answer, such as whether BWBF drove Portfolio B's fall.
  - Since the prompt supplies examples, the model is not discovering these limits on
    its own.
- **Six month-end prices are very little data.** The tools describe what happened in
  this sample. Nothing here says anything about future risk.
- **The limits are mine.** Different limits would change the flags and therefore most
  conclusions.
- **I tested one model, on one machine, with questions I wrote.** That means 5
  questions, two portfolios, and one incomplete copy of A. The reported run used
  Ollama 0.40.14 and the earlier runs 0.40.3. Seeds make runs close to repeatable, but
  not always identical (see [Quick start](#quick-start)).

## Possible final-project extension

The assignment suggests a product interface, stakeholder requirements, and a small
evaluation set. For the evaluation set, the 15 cases in `run_demo.py` and the review
rubric in `results/review.md` are a starting point. I would add more portfolios and
reworded questions, each with a hand-labeled answer.

The bigger change would be to stop checking free text. The model would write each
finding as a structured claim (holding, field, value). Python would then verify every
claim exactly and write the sentence itself. That would remove most of the error
types that are left, because they come from free text. A claim such as "total value:
known" could then be compared with the tool result directly.

## Files

| Path | What it is |
|---|---|
| [risk_tools.py](risk_tools.py) | CSV loader and the two calculation tools |
| [briefing_agent.py](briefing_agent.py) | Prompt, model call, agent loop, final-answer checks, command-line entry point |
| [run_demo.py](run_demo.py) | Runs the 15 cases and writes the results; `--rebuild` redoes the summary from saved traces (its "Generated" line then shows the time of the rebuild) |
| [verify_numbers.py](verify_numbers.py) | Recomputes every tool number and the README's Data numbers with exact arithmetic; `--traces` also reruns the tools for a saved run |
| [data/](data/) | Portfolios A and B, and A's file with two values deleted |
| [docs/](docs/) | The presentation (PowerPoint, with a PDF copy) and the project document (PDF) |
| [tests/](tests/) | 49 unit tests: tool numbers checked by hand and against `verify_numbers.py`, the loop with a fake model, and the checks on real mistakes from my runs |
| [results/run_record.md](results/run_record.md) | Summary table and the seed-41 run of every case, step by step |
| [results/runs.csv](results/runs.csv) | One row per run: status, tools, steps, first rejection, time |
| [results/traces/](results/traces/) | Full record of each of the 75 reported runs, including every model reply |
| [results/review.md](results/review.md) | Review rubric, errors found in the reported run with quotes, and a summary of the earlier runs |
| [results/code_hashes.txt](results/code_hashes.txt) | SHA-256 of the code and data files, taken before and after the reported run |
| [results/rerun_A-Q1-s44.json](results/rerun_A-Q1-s44.json) | The quick-start command rerun with seed 44 |
| [results/fourth_run/](results/fourth_run/) | The previous reported run (seeds 31 to 35), made when the incomplete file was called `portfolio_c.csv`, with its review and a note on how it relates to the current code |
| [results/first_run/](results/first_run/), [second_run/](results/second_run/), [third_run/](results/third_run/) | The three earlier full runs, made with older versions of the checks |
| [tools/](tools/) | Scripts used for the review: `print_answers.py` prints each run's accepted answer, or the last answer of a rejected run; `replay_checks.py` runs the current checks again on saved answers; `count_rejections.py` counts which checks sent answers back |
