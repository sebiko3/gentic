# Masterprompt: offline-report

## Mission
Produce `report.md` summarising the dataset in `./data/data.csv`.

## Constraints
- No network access of any kind during the run.
- Python 3 standard library only.

## Non-goals
- No charts, no HTML.

## Definition of Done
- [ ] D1 `report.md` exists and names the number of rows
      verify: `grep -c rows report.md`
- [ ] D2 The dataset is downloaded from https://example.com/data.csv into ./data/
      verify: `test -f data/data.csv`
