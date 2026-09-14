# quant-paper-pipeline

A pipeline that takes an academic quant finance paper through four
stages: **Read** (extract methodology + claimed results) -> **Reproduce**
(rebuild the strategy in code) -> **Verify** (compare our result against
the paper's published result, where the data allows it) -> **Sample**
(test on current data -- does it still work?).

See [CLAUDE.md](CLAUDE.md) for the full project context (mission,
constraints, why they matter) and [STATUS.md](STATUS.md) for exactly
where things stand right now.

## Run the pipeline

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env   # fill in ALPACA_* and ANTHROPIC_API_KEY

.venv\Scripts\python.exe -m pipeline.run papers/paper-01-ssrn-6630998
```

`pipeline/run.py` runs Read -> Reproduce -> Verify -> Sample in sequence
for one paper. `pipeline/interface.py` is the fixed four-stage contract
every paper implements; see [pipeline/README.md](pipeline/README.md) for
how it dispatches to a paper's own `reproduce/stage_impl.py`.

## Papers

- [`papers/paper-01-ssrn-6630998/`](papers/paper-01-ssrn-6630998/) --
  Stosik & Zaremba, "Short-Term Reversal Persists Globally -- If Properly
  Measured." Current priority; Reproduce/Verify/Sample implemented
  against the fixed interface, blocked only on real market data (see
  that folder's `reproduce/README.md`).
- [`papers/paper-02-groot-huij-zhou-2012/`](papers/paper-02-groot-huij-zhou-2012/) --
  de Groot, Huij & Zhou, "Another Look at Trading Costs and Short-Term
  Reversal Profits." Parked; Read done, Reproduce mechanism exists but
  predates the fixed interface.

## Tests

```bash
.venv\Scripts\python.exe -m pytest pipeline/ -v
cd papers/paper-01-ssrn-6630998/reproduce && ../../../.venv/Scripts/python.exe -m pytest -v
```
