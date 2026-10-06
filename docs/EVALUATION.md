# RAG Evaluation

The evaluation harness is intentionally small and reproducible. It does not
claim that the system is objectively accurate.

## Dataset

`evaluation/rag_cases.jsonl` contains:

- grounded questions tied to version-controlled sample documents
- expected source document titles
- answer terms that should be present
- an unsupported question that should trigger abstention

The dataset should grow when a real failure is found. It should not be tuned
only until the current implementation passes.

## Measures

- **Retrieval relevance:** all expected document titles appear in returned
  sources.
- **Answer term presence:** deterministic expected terms appear in the answer.
  This is a weak groundedness proxy, not semantic grading.
- **Citation validity:** every `[Source N]` marker points to a retrieved source.
- **Abstention behavior:** unsupported questions contain an explicit
  insufficient-information response.
- **Latency:** wall-clock median and maximum for this run.

No LLM judge is used. If one is added later, its scores must be labeled as
model-based judgments rather than ground truth.

## Running

Load the sample documents, obtain a member access token, and run:

```bash
python evaluation/run_evaluation.py \
  --base-url http://localhost:8000 \
  --token "$ACCESS_TOKEN"
```

The command prints raw case results and aggregate rates as JSON. Results depend
on the configured embedding and LLM models, database contents, and machine, so
the repository does not publish fabricated benchmark numbers.

## Limitations

- Six cases are enough to demonstrate methodology, not broad quality.
- Expected-term matching can miss semantically correct paraphrases.
- Source-title matching does not prove that the exact supporting passage was
  used.
- End-to-end latency includes local networking and provider variability.
- The sample documents are synthetic and contain no adversarial corpus beyond
  tests for prompt boundaries.
