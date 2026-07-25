A text processing pipeline at `/app/pipeline.py` analyzes document collections by normalizing text, tokenizing into sentences and words, extracting entities, and computing statistical measures. It uses modules `/app/data_loader.py`, `/app/normalizer.py`, `/app/tokenizer.py`, `/app/entity_extractor.py`, `/app/statistics.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/documents.json` and writes `/app/output.json`.

The pipeline processes each document through normalization (Unicode NFKC, whitespace collapse, case folding), tokenization (sentence splitting, word extraction, stopword removal), entity extraction (emails, dates, amounts via regex), and statistical analysis (word frequencies, bigrams, readability scores). It then computes corpus-level aggregate statistics across all documents.

The pipeline produces correct output on the current document collection but has bugs that cause incorrect statistical values on other document collections with different text characteristics. Find and fix the bugs so the pipeline handles all valid document inputs correctly.

Do not rewrite from scratch — preserve the existing module structure and function signatures. The fixed pipeline will be tested on a different document collection than the one at `/app/documents.json`.

Output: `/app/output.json` — JSON object with `document_count`, `documents` (list of per-document results with id, title, entities, and statistics including word_count, sentence_count, unique_words, top_frequencies, top_bigrams, readability), and `corpus_statistics` (total_documents, total_tokens, total_unique_tokens, corpus_frequencies, corpus_bigrams, corpus_readability).
