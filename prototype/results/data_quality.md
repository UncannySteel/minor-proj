# Data Quality Report

Dataset: **NLBSE'23 Tool Competition, issue report classification** ([source](https://github.com/nlbse2023/issue-report-classification)). Labels are real GitHub labels applied by project maintainers, and the train/test split is the competition's own.

## Pipeline attrition

| step | rows in | rows out | removed | % removed | note |
| --- | ---: | ---: | ---: | ---: | --- |
| raw train | 150,000 | 150,000 | 0 | 0.0% | sampled from the NLBSE'23 train file |
| [train] valid label | 150,000 | 150,000 | 0 | 0.0% | one of ['bug', 'feature', 'question', 'documentation'] |
| [train] drop null / empty title or body | 150,000 | 149,443 | 557 | 0.4% |  |
| [train] strip HTML comments | 149,443 | 149,338 | 105 | 0.1% | template boilerplate |
| [train] drop bodies under min length | 149,338 | 148,398 | 940 | 0.6% | < 10 chars |
| [train] truncate very long bodies | 148,398 | 148,398 | 0 | 0.0% | 796 truncated |
| [train] drop bot-generated issues | 148,398 | 148,236 | 162 | 0.1% | dependabot / renovate / snyk |
| [train] drop non-english bodies | 148,236 | 147,786 | 450 | 0.3% | ascii ratio < 90% |
| [train] normalise + placeholder tokens | 147,786 | 147,785 | 1 | 0.0% | code / url / email / hash / num |
| [train] exact dedup on normalised text | 147,785 | 144,751 | 3,034 | 2.1% |  |
| [train] near-dedup on first 200 chars | 144,751 | 144,396 | 355 | 0.2% |  |
| raw test | 142,320 | 142,320 | 0 | 0.0% | official held-out test file |
| [test] valid label | 142,320 | 142,320 | 0 | 0.0% | one of ['bug', 'feature', 'question', 'documentation'] |
| [test] drop null / empty title or body | 142,320 | 141,852 | 468 | 0.3% |  |
| [test] strip HTML comments | 141,852 | 141,765 | 87 | 0.1% | template boilerplate |
| [test] drop bodies under min length | 141,765 | 140,809 | 956 | 0.7% | < 10 chars |
| [test] truncate very long bodies | 140,809 | 140,809 | 0 | 0.0% | 736 truncated |
| [test] drop bot-generated issues | 140,809 | 140,653 | 156 | 0.1% | dependabot / renovate / snyk |
| [test] drop non-english bodies | 140,653 | 140,291 | 362 | 0.3% | ascii ratio < 90% |
| [test] normalise + placeholder tokens | 140,291 | 140,291 | 0 | 0.0% | code / url / email / hash / num |
| [test] exact dedup on normalised text | 140,291 | 137,446 | 2,845 | 2.0% |  |
| [test] near-dedup on first 200 chars | 137,446 | 137,132 | 314 | 0.2% |  |
| drop train rows duplicated in test | 144,396 | 142,886 | 1,510 | 1.0% | 1,510 overlapping texts found |

**Overall: 150,000 rows in -> 142,886 usable (95.3% retained).**

## Observations

- Train 142,886 rows, test 137,132 rows. The test set is the competition's own file, cleaned with exactly the same code path as train so the two are directly comparable.
- Labels are real GitHub labels applied by project maintainers - nothing here is inferred, derived or keyword-matched.
- **1,510 training rows (1.0%) had normalised text identical to a row in the official test file, and were dropped.** This is a property of the published dataset, not of our sampling - the same rate would be expected across the full training set. Any result reported on this benchmark without that check is partly measuring memorisation. Every number in `metrics.md` is computed after the overlap was removed.
- Train and test label shares differ by at most 0.4%. The competition does not document how the split was drawn; a match this close indicates a random split rather than a temporal or per-project one. That makes this an in-distribution held-out test, which is a weaker generalisation claim than an unseen-project split would be - worth naming rather than glossing over.

## Label distribution

| class | train | share | test | share |
| --- | ---: | ---: | ---: | ---: |
| bug | 77,215 | 54.0% | 73,492 | 53.6% |
| feature | 50,900 | 35.6% | 49,405 | 36.0% |
| question | 8,675 | 6.1% | 8,397 | 6.1% |
| documentation | 6,096 | 4.3% | 5,838 | 4.3% |

The imbalance is real and is why Macro-F1 and MCC are reported alongside accuracy, and why the loss is inverse-frequency weighted.

## Author association

The only provenance field the dataset carries, and a genuine metadata signal: whether the reporter is the repository owner or a drive-by.

| association | train rows | share |
| --- | ---: | ---: |
| NONE | 61,715 | 43.2% |
| CONTRIBUTOR | 27,471 | 19.2% |
| OWNER | 20,866 | 14.6% |
| MEMBER | 18,223 | 12.8% |
| COLLABORATOR | 14,594 | 10.2% |
| MANNEQUIN | 17 | 0.0% |

## Example rows

| label | title | text the model reads |
| --- | --- | --- |
| `bug` | BUG: piling up memory bloat while plotting in a loop | bug: piling up memory bloat while plotting in a loop ### bug report **bug summar... |
| `feature` | Add flag for changing contract address for reporting | add flag for changing contract address for reporting would need to have an expec... |
| `documentation` | Documentation Bug: Cylinder.get_direction() | documentation bug: cylinder.get_direction() the documentation code_span method f... |
| `bug` | Some fields in client inappropriately bring up autofill sugg | some fields in client inappropriately bring up autofill suggestions in chrome, w... |
| `question` | [BUG] Cosmos query throws exception with 'rid must not be nu | [bug] cosmos query throws exception with 'rid must not be null' **describe the b... |
| `bug` | Webpack compilation digest is written even if compilation fa | webpack compilation digest is written even if compilation fails in pr num , we c... |

## Metadata features (25)

All available the moment the issue is opened. Nothing depends on comments, assignment or anything else that happens after creation.

| feature | mean | std |
| --- | ---: | ---: |
| `log_body_chars` | 6.182 | 1.240 |
| `log_body_words` | 4.117 | 1.167 |
| `log_n_lines` | 2.200 | 1.439 |
| `has_code_block` | 0.270 | 0.444 |
| `has_traceback` | 0.043 | 0.202 |
| `log_n_urls` | 0.478 | 0.590 |
| `has_checklist` | 0.109 | 0.312 |
| `has_image` | 0.140 | 0.347 |
| `log_n_headings` | 0.473 | 0.794 |
| `is_from_template` | 0.279 | 0.448 |
| `mean_word_len` | 8.453 | 20.543 |
| `log_n_question_marks` | 0.299 | 0.530 |
| `has_version_string` | 0.318 | 0.466 |
| `upper_ratio` | 0.056 | 0.050 |
| `log_title_chars` | 3.768 | 0.531 |
| `log_title_words` | 1.995 | 0.469 |
| `title_has_question_mark` | 0.028 | 0.165 |
| `title_upper_ratio` | 0.086 | 0.099 |
| `title_has_bracket_tag` | 0.122 | 0.327 |
| `author_is_none` | 0.432 | 0.495 |
| `author_is_contributor` | 0.192 | 0.394 |
| `author_is_owner` | 0.146 | 0.353 |
| `author_is_member` | 0.128 | 0.334 |
| `author_is_collaborator` | 0.102 | 0.303 |
| `author_is_mannequin` | 0.000 | 0.011 |
