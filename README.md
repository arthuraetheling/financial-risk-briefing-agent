# Financial Risk Briefing Agent

CSYE 7374 Agentic AI, Fall 2026. Three-week mini project, student ID ending 56162.
Tianle Yang.

This agent writes short risk briefings about a small fictional investment
portfolio stored in a CSV file. For a question such as "What are the main risks in
this portfolio?", a local model (qwen3:8b through Ollama) decides whether to call
a concentration tool, a price-change tool, or both. Python does all of the
arithmetic. It also checks the model's final answer before accepting it: every
number has to come from a tool result, missing data has to be mentioned, a claim
may not rest on a number the tools could not compute, and the answer may not tell
anyone to buy or sell. Every briefing has a section on what the sample cannot
establish.

All company names, tickers, share counts, and prices here are made up. The
briefings describe a fictional sample and are not investment advice.

## How the project covers the assignment

| Requirement | Where |
|---|---|
| Small fictional portfolio saved in a CSV file | [data/](data/): three files |
| The model decides whether to call a concentration tool, a price-change tool, or both | [briefing_agent.py](briefing_agent.py); tool column in [results/runs.csv](results/runs.csv) |
| Short explanation using the actual numbers | Number checks in `check_final_answer()`; briefings in [results/run_record.md](results/run_record.md) |
| Says what the sample cannot establish | Required `cannot_establish` list, printed under "What this sample cannot establish" |
| Compare two mock portfolios with different risks | [Portfolio A vs. Portfolio B](#demonstration-portfolio-a-vs-portfolio-b) |
| At least two tools; observations decide the next step | Two tools. Tool results and Python's feedback change the next step: 45 first answers sent back, 39 of those runs recovered, and different conclusions when values are missing ([details](#what-the-agent-does-with-what-it-sees)) |
| An ordinary case and an incomplete-information case | A and B have complete data; [Portfolio C](#incomplete-information-case-portfolio-c) has two values removed |
| Short record of what happened | [results/run_record.md](results/run_record.md), every step in [results/traces/](results/traces/), my review in [results/manual_review.md](results/manual_review.md) |
| Free or low-cost model | qwen3:8b running locally through Ollama. No API cost. |
| Not presented as personal investment advice | Advice checks, the buy/sell/hold rule, and a fixed closing line in every briefing |

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
python briefing_agent.py data/portfolio_a.csv "What are the main risks in this portfolio?" --label "Portfolio A" --seed 31
```

```bash
python -m unittest discover -s tests -v
```

The 43 unit tests do not need Ollama. They do three things:

- compare the tool output with numbers I worked out by hand;
- run the agent loop with a scripted fake model;
- feed the answer checks the real mistakes collected from my runs.

`python run_demo.py` repeats the reported evaluation (15 cases, seeds 31 to 35). It
took about 12 minutes on my laptop (RTX 4060 Laptop GPU, 8 GB), and it overwrites
`results/runs.csv`, `results/run_record.md` and `results/traces/`.

A fixed seed makes reruns close but not identical. Two reruns of the quick-start
command behaved differently:

- **Seed 11, during development:** reproduced the saved briefing word for word
  ([results/second_run/rerun_A-Q1-s11.json](results/second_run/rerun_A-Q1-s11.json)).
- **Seed 31, with the final code:** gave the same two tool calls and an accepted
  answer with the same facts, but different wording
  ([results/rerun_A-Q1-s31.json](results/rerun_A-Q1-s31.json)).

Ollama does not promise bit-identical output when its cache is reused, so a full
rerun gives a similar table, not the same one.

## Data

Each CSV file has one row per holding: ticker, name, sector, share count, and seven
month-end closing prices from 2026-04-30 to 2026-10-30, which covers six months.

| | Portfolio A | Portfolio B | Portfolio C |
|---|---|---|---|
| Built to show | Concentration | Losses in a spread-out portfolio | Missing data |
| Holdings | 6 | 10 | 6 (same as A) |
| Value on 2026-10-30 | $52,318.75 | $50,947.10 | unknown |
| Largest holding | NWSC, 44.0% | BWBF, 13.6% | unknown |
| Largest sector | Technology, 67.9% | Fixed income, 13.6% | unknown |
| Effective number of holdings | 3.8 | 9.7 | unknown |
| Six-month change | +2.3% | -10.4% | unknown |
| Worst month | -6.6% (August) | -3.9% (August) | unknown |

- **Portfolio A** gains only 2.3% over the six months but swings from month to month.
  - It fell 6.3% in June and 6.6% in August.
  - Most of each drop came from NWSC, which fell 10.5% and 11.5% in those months.
  - By my own calculation from the CSV, NWSC accounts for about three quarters of the
    portfolio's fall in both months.
- **Portfolio B** has no position above 14%, but it lost $5,890.65 (10.4%) over the six
  months.
  - SFHM fell 34.1%, OKRT 26.9%, and RVBK 22.0%.
  - These three account for 85% of the net loss.
- **Portfolio C** is Portfolio A with two cells deleted: the NWSC share count and the
  CLDN price on 2026-04-30.
  - I built it this way so I know what a complete answer would say.
  - NWSC is the holding that makes A concentrated, and CLDN is A's biggest loser. So
    a C answer that calls the portfolio diversified, names its largest holding, or
    names its biggest loser is unsupported.

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
    known values and says that the total is unknown.
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
Portfolio C, the model presented them as real weights.

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
- The keys are wrong, or a list is empty or has more than three items.
- None of the findings uses a number. This applies only when no data is missing.
- The answer is longer than 180 words.

**Numbers**

- A number does not appear in any tool result. Rounding is allowed, so "6%" matches
  6.3. Dates are removed first, so the 30 in 2026-04-30 cannot pass as a "30% limit".
- A percentage given for a holding belongs to a different holding.
- A percentage given for a holding belongs to the whole portfolio or a sector ("SFHM
  fell 10.4%"). This is only checked when the holding is named in the same clause
  and the clause does not mention the portfolio or a sector.
- A holding's weight is used as a price change ("BWBF fell by 13.6%").
- A change is described in the wrong direction ("fell 1.1%" for a holding that rose
  1.1%).
- A holding is given the wrong rank or sector ("SFHM, the second-largest holding").
- The top-three weight is called "within" a limit. There is no such limit.

**Missing data**

- The tools reported missing data, but the answer names none of the affected
  holdings.
- The answer makes a claim that needs a number the tools could not compute. With
  Portfolio C, that means calling it concentrated or diversified, naming its largest
  holding, naming the holding that fell or rose the most, or saying "the portfolio
  fell".
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

## Demonstration: Portfolio A vs. Portfolio B

The same question, seed 31, from [results/run_record.md](results/run_record.md). In
both runs the model called both tools.

```text
Risk briefing: Portfolio A (fictional data)
Question: What are the main risks in this portfolio?
Tools used: check_concentration, check_price_changes

The main risks in this portfolio are its high concentration in Technology, particularly in Northwind Semiconductor, and the portfolio's exposure to significant monthly drops that exceed the defined limits.

What the numbers show:
- Northwind Semiconductor is 44.0% of the portfolio, which is above the 20% single-holding limit.
- The Technology sector is 67.9% of the portfolio, exceeding the 40% sector limit.
- The portfolio fell 6.6% in the month ending 2026-08-31, which is above the 5% monthly drop limit.

What this sample cannot establish:
- The portfolio's performance over a longer period is not available.
- The reasons for the price changes of individual holdings are not provided.
- Whether the concentration in Technology will continue to be a risk cannot be determined from the data.
```

```text
Risk briefing: Portfolio B (fictional data)
Question: What are the main risks in this portfolio?
Tools used: check_concentration, check_price_changes

The main risks in this portfolio include significant price declines in several holdings and a general downward trend over the past six months. The portfolio as a whole fell by 10.4% over the period, with some holdings dropping more than 20%, which exceeds the holding drop limit.

What the numbers show:
- SFHM fell 34.1% from the start to the end of the period, which is well above the 20% holding drop limit.
- OKRT and RVBK also fell by 26.9% and 22.0%, respectively, exceeding the 20% holding drop limit.
- The portfolio as a whole fell 10.4% over the six-month period, with the worst monthly decline being a 3.9% drop in August.

What this sample cannot establish:
- Whether the portfolio will continue to decline, since there are only a few month-end prices.
- Why specific holdings dropped, since the file has only prices and not detailed reasons for price changes.
- Whether the portfolio's sectors tend to move together, since the file has no data on sector correlations.
```

(The closing line of both briefings is cut here.)

Both runs used the same tools and reached different conclusions:

- For A, the main risk is that 44.0% of the value sits in one stock and 67.9% in one
  sector, and both are flagged.
- For B, concentration is not the problem: the concentration result has no flags
  and says so. The main risk is the price losses. These are losses on paper, since
  nothing was sold.

Across the five seeds:

- All five A-Q1 briefings name the 44.0% and 67.9% weights as main risks.
- All five B-Q1 briefings lead with the losses. One of them (seed 33) also lists
  "concentration in certain sectors" as a risk, which is wrong, and I count it as an
  error in the review.
- On the direct question (Q3), all five A answers say A is too dependent on one
  company and one sector, and all five B answers say B is not.

## Incomplete-information case: Portfolio C

The concentration tool reports "Weights cannot be calculated: NWSC has no known
value on 2026-10-30". The price tool leaves out the portfolio totals and the largest
fall. Here is seed 34 of "Which holdings lost the most value over the last six
months?":

```text
Risk briefing: Portfolio C (fictional data)
Question: Which holdings lost the most value over the last six months?
Tools used: check_price_changes

Among holdings with a known change, GRNE lost the most value, falling 3.9% over the last six months. The change for CLDN is unknown due to missing data.

What the numbers show:
- GRNE, Granite Ridge Energy, fell 3.9% over the six-month period.
- The largest fall cannot be identified because the change of CLDN is unknown.
- NWSC's value change and portfolio totals cannot be calculated due to missing share count.

What this sample cannot establish:
- Whether other holdings lost more value, since the largest fall cannot be identified.
- The overall portfolio performance, since portfolio totals are not calculated due to missing data.

Missing data reported by the tools:
- NWSC (Northwind Semiconductor): share count is missing, so its value change and the portfolio totals cannot be calculated; its price change is known.
- CLDN (Cloudline Networks): no price on 2026-04-30, so its change from 2026-04-30 to 2026-10-30 is unknown and the portfolio totals cannot be calculated.
```

(The closing line is cut.) This answer was accepted on the third try. The first two
tries named GRNE as the holding that "lost the most" without the qualifier. In
Portfolio A, CLDN is in fact the biggest loser at -8.0%, so that claim would have
been wrong.

Across the 25 Portfolio C runs:

- **C-Q1 (main risks):** 5 of 5 were accepted. All five name NWSC's missing share
  count, and one also names CLDN. Seed 32 calls GRNE "a Technology holding", which
  is wrong.
- **C-Q2 (largest position):** 4 of 5 were accepted, and all four say the largest
  position cannot be identified.
- **C-Q3 (dependence):** all five say it cannot be determined. Four of them add a
  wrong ranking, naming HLSW instead of BWBF as the largest known holding. This
  probably comes from my tool's row order (see [Limitations](#limitations)).
- **C-Q4 (losses):** 3 of 5 were accepted, all with "among holdings with a known
  change". The other two kept naming GRNE as the biggest or only loser and were
  rejected.
- **C-Q5 (sell?):** 3 of 5 were accepted, and all three decline to answer and say the
  largest holding cannot be identified. Two were rejected:
  - one kept calling NWSC "the largest holding";
  - in the other, the last answer named no holding with missing data and ranked HLSW
    above BWBF.

## What the agent does with what it sees

All numbers in this section are from the final run (75 runs).

### Choosing tools

The model chose tools in line with each question:

- Q1 and Q2: both tools in 30 of 30 runs.
- Q3: only `check_concentration`, in 15 of 15.
- Q4: only `check_price_changes`, in 15 of 15.

The system prompt says which kind of question needs which tool, so for Q1 to Q4 this
mostly shows the model applying that rule to the wording of the question. It does
not show a decision driven by tool results. For Q5 the tool choice varied between
runs:

- Final run: the model checked prices for B but not for A, 5 of 5 times each.
- Second run: it was the other way round.

So I do not count Q5 as evidence of the agent checking different facts.

### Missing data

Here the tool results change the outcome. In Portfolio C, no accepted answer gave a
weight, called the portfolio diversified or concentrated, or stated a
portfolio-level change. None named a largest holding without the "known
value" qualifier, though four C-Q3 answers named the wrong one with it. The checks
hold the model to this, as the C-Q4 example above shows.

### Python's feedback

In 45 runs the first final answer was sent back, and 39 of those runs ended with an
accepted briefing. In total, 68 answers were sent back.
An answer can fail more than one check, so the counts below add up to more than 68.

| Check | Answers sent back (all tries) | First answers sent back |
|---|---|---|
| Biggest fall or rise named in Portfolio C, where CLDN's change is unknown | 19 | 9 |
| A holding without a value ranked ("the largest holding, NWSC") | 15 | 10 |
| `findings` or `cannot_establish` not sent as a list | 14 | 14 |
| "Largest holding" in Portfolio C, where weights are unavailable | 14 | 10 |
| Buy/sell/hold question without a refusal in the summary | 12 | 10 |
| The same answer sent again (always together with another problem) | 8 | 0 |
| Advice wording | 7 | 7 |
| Over 180 words | 6 | 3 |
| Top-three weight called within a limit | 2 | 2 |
| Missing data not named | 2 | 0 |
| NWSC called a holding with a known value | 2 | 0 |
| Concentration claim without weights | 1 | 1 |
| Wrong rank | 1 | 1 |
| Too many items | 1 | 1 |

No answer in this run failed the basic number check: every number the model wrote
appears somewhere in the tool results. The errors that remain are about which
holding or claim a number belongs to.

## Results

Final run: qwen3:8b, 15 cases with seeds 31 to 35, 9.2 seconds per run on average.
I froze the code before this run. The file hashes of `briefing_agent.py`,
`risk_tools.py` and `run_demo.py` were the same before and after it.

| Case | Question | Accepted | Expected tools | Expected facts | Mean model replies |
|---|---|---|---|---|---|
| A-Q1 | What are the main risks in this portfolio? | 5/5 | 5/5 | 15/15 | 4.0 |
| B-Q1 | same | 5/5 | 5/5 | 10/10 | 3.4 |
| C-Q1 | same | 5/5 | 5/5 | 6/10 | 3.6 |
| A-Q2 | How big is the largest position, and how has its price moved? | 5/5 | 5/5 | 15/15 | 3.0 |
| B-Q2 | same | 5/5 | 5/5 | 15/15 | 3.2 |
| C-Q2 | same | 4/5 | 5/5 | 4/5 | 4.4 |
| A-Q3 | Is this portfolio too dependent on one company or one sector? | 5/5 | 5/5 | 10/10 | 3.0 |
| B-Q3 | same | 5/5 | 5/5 | 5/5 | 2.4 |
| C-Q3 | same | 5/5 | 5/5 | 5/5 | 2.4 |
| A-Q4 | Which holdings lost the most value over the last six months? | 5/5 | 5/5 | 10/10 | 2.0 |
| B-Q4 | same | 5/5 | 5/5 | 15/15 | 2.0 |
| C-Q4 | same | 3/5 | 5/5 | 9/15 | 4.2 |
| A-Q5 | Should I sell part of my largest holding? | 5/5 | 5/5 | 10/10 | 3.2 |
| B-Q5 | same | 4/5 | 5/5 | 8/10 | 4.6 |
| C-Q5 | same | 3/5 | 5/5 | 3/5 | 4.0 |
| **All** | | **69/75** | **75/75** | | |

How to read the columns:

- **Expected tools:** both tools for Q1 and Q2 (for C-Q2, at least the concentration
  tool), only the concentration tool for Q3, only the price tool for Q4, and at least
  the concentration tool for Q5.
- **Expected facts:** counts facts I listed in advance for each case, matched by
  pattern (for example "44.0%" and "67.9%" for A-Q1). It measures completeness, not
  correctness. A rejected run counts 0. C-Q1 is 6/10 because all five answers named
  NWSC but only one named CLDN. Python lists both under the briefing anyway.

Six runs were rejected after four tries. In five, the last answer still had a
content error (all of them in Portfolio C). The sixth was 5 words over the limit.

**Manual review.** The checks only look at numbers, names, and wording patterns. So
I printed all 69 accepted briefings with `tools/print_answers.py` and compared each
sentence with the tool results. The rubric, details and quotes are in
[results/manual_review.md](results/manual_review.md). 11 briefings had a major error:

- **C-Q3, four answers:** HLSW named as the largest of the known values. BWBF is.
- **A-Q4, three answers, and B-Q4, one:** a `cannot_establish` item says the file
  lacks some holdings' changes or prices. It does not.
- **B-Q5, one answer:** "The largest holding, Bluewater Bond Fund, fell 10.4%". BWBF
  rose 1.1%, and 10.4% is the portfolio's fall.
- **B-Q1, one answer:** "concentration in certain sectors" given as a risk.
- **C-Q1, one answer:** GRNE called "a Technology holding". It is in Energy.

10 more briefings had only a minor problem. Six C-Q2 and C-Q5 answers write as if
the largest holding were the one without a value ("cannot be identified because its
value is unknown"). Four C-Q1 answers say "some holdings" have unknown price changes,
when only CLDN's is unknown.

## What changed during development

I tuned the system on two kinds of run, and neither is counted in the table above:

- **Short development rounds** with seeds 100 to 108. I did not keep these.
- **Three full runs**, with seeds 1 to 5, 11 to 15, and 21 to 25. These are kept in
  [results/first_run/](results/first_run/), [results/second_run/](results/second_run/)
  and [results/third_run/](results/third_run/). The review file summarizes what I
  found in each.

The changes that mattered most:

1. **The answer schema.** It first had a `risks` field, and for Portfolio B the model
   invented risks such as "13.6% is close to the 20% limit". I renamed the field to
   `findings` and told the model to say plainly when a check found nothing. That
   reduced these invented risks but did not stop them.
2. **Partial numbers.** The first tools computed weights and totals from the complete
   rows of Portfolio C, and the model presented them as the real numbers. Now the
   tools leave those numbers out.
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
   - My price tool still named a largest fall in Portfolio C, which broke my own
     missing-data rule, and the C-Q4 answers built on it. The tool no longer does this.
   - My hedge words ("missing", "unavailable") let real claims through. I removed them
     from the list.
   - A sentence like "the largest fall of any holding was 8.0%" was wrongly tied to
     the holding named before it. Now a clause only continues the previous holding if
     it refers back to it ("its", "which", or a verb that opens the clause).
   - I had changed the checks after my "final" run, so the reported table could not
     be reproduced with the submitted code. That is why the reported run is a
     separate run with frozen code.
   - I also added C-Q2 and C-Q5, since Portfolio C had not been asked about its
     largest position.
8. **After the third run.** I added the rank, sector and weight-as-change checks, the
   top-three rule, and the check on NWSC being called a holding with a known value. I
   also allowed four tries instead of three. Items in `cannot_establish` are no longer
   read as "largest" or "most" claims, because two correct answers had been rejected
   that way.
9. **A second look by the same agent after the final run.** It confirmed that
   replaying the frozen code on all 137 saved final-run answers gives the original
   verdicts. It also found places where I had applied my rubric unevenly and some
   loose claims in this README. I corrected the documents but did not change the code
   again, so the table above still matches the code.

## Limitations

- **The checks only match patterns.** In the final run they sent back 68 answers for
  14 kinds of problem, but 11 of the 69 accepted briefings still had a major error.
  - Each check covers only the phrasings it was written for. For example, it reads
    "the largest holding is X" but not "the largest holding by value is X".
  - The "largest" and "most" checks pass any sentence that contains a qualifier word.
    So these would be accepted for Portfolio C: "Among all holdings, GRNE lost the
    most value" and "GRNE lost the most value, though why cannot be known".
  - A stricter version would require "among holdings with a known change (or value)"
    in the same clause as the claim.
- **My own tool probably causes the C-Q3 error.** When a value is missing,
  `check_concentration` lists the holdings in file order instead of by value, and the
  model seems to read the first row with a value (HLSW) as the largest. Sorting those
  rows is a one-line fix. I left it out because the code was frozen for the final run.
- **Tool choice for Q1 to Q4 follows a rule in the prompt.** The model applies the
  rule well, but it is not working out on its own which tool a question needs.
- **The `cannot_establish` items are often generic.**
  - Many repeat the examples in the prompt ("whether a trend will continue, since
    there are only a few month-end prices").
  - Some are false. The A-Q4 and B-Q4 answers say the file lacks some holdings'
    changes or prices, which it does not.
  - Since the prompt supplies examples, the model is not discovering these limits on
    its own.
- **Six month-end prices are very little data.** The tools describe what happened in
  this sample. Nothing here says anything about future risk.
- **The limits are mine.** Different limits would change the flags and therefore most
  conclusions.
- **I tested one model, on one machine, with questions I wrote.** That means 5
  questions and 3 portfolios. Seeds make runs close to repeatable, but not identical
  (see [Quick start](#quick-start)).

## Possible final-project extension

The assignment suggests a product interface, stakeholder requirements, and a small
evaluation set. For the evaluation set, the 15 cases in `run_demo.py` and the review
rubric in `results/manual_review.md` are a starting point. I would add more
portfolios and reworded questions, each with a hand-labeled answer.

The bigger change would be to stop checking free text. The model would write each
finding as a structured claim (holding, field, value). Python would then verify every
claim exactly and write the sentence itself. That would remove most of the error
types that are left, because they come from free text. The C-Q3 ranking error would
also need the sorting fix above.

## Files

| Path | What it is |
|---|---|
| [risk_tools.py](risk_tools.py) | CSV loader and the two calculation tools |
| [briefing_agent.py](briefing_agent.py) | Prompt, model call, agent loop, final-answer checks, command-line entry point |
| [run_demo.py](run_demo.py) | Runs the 15 cases and writes the results; `--rebuild` redoes the summary from saved traces |
| [data/](data/) | Portfolios A, B, and C |
| [tests/](tests/) | 43 unit tests: tool numbers checked by hand, the loop with a fake model, and the checks on real mistakes from my runs |
| [results/run_record.md](results/run_record.md) | Summary table and the seed-31 run of every case, step by step |
| [results/runs.csv](results/runs.csv) | One row per run: status, tools, steps, first rejection, time |
| [results/traces/](results/traces/) | Full record of each of the 75 final runs, including every model reply |
| [results/manual_review.md](results/manual_review.md) | Review rubric, errors I found in the final run with quotes, and a summary of the earlier runs |
| [results/rerun_A-Q1-s31.json](results/rerun_A-Q1-s31.json) | The quick-start command rerun with seed 31 |
| [results/first_run/](results/first_run/), [second_run/](results/second_run/), [third_run/](results/third_run/) | The three earlier full runs, made with older versions of the checks |
| [tools/](tools/) | Scripts I used for the review: `print_answers.py` prints every answer, `replay_checks.py` runs the current checks again on saved answers, `count_rejections.py` counts which checks sent answers back |
