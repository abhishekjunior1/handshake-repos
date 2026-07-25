A configuration file parser/serializer pipeline at `/app/pipeline.py` reads a custom NestedConf format (`.nconf`) and produces structured JSON output. It uses modules `/app/lexer.py`, `/app/parser.py`, `/app/resolver.py`, `/app/serializer.py`, and `/app/formatter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.nconf` and writes `/app/output.json`.

The NestedConf format supports:
- Sections: `[SectionName]`
- Key-value pairs: `key = value` or `key = "quoted value"`
- Variable references: `${Section.key}` (resolved by looking up the referenced section and key)
- Escape sequences in quoted strings: `\\` (literal backslash), `\n` (newline), `\t` (tab), `\r` (carriage return), `\"` (literal quote)
- Comments: `# line comment`

The pipeline produces correct output on the current configuration file but has bugs that cause incorrect results on other configurations. Find and fix the bugs so the pipeline handles all valid NestedConf inputs correctly, including configurations with multiple sections, cross-references between sections, chained variable references, escape sequences in quoted strings, and mixed-case section names.

Do not rewrite from scratch — preserve the existing module structure and interfaces. The fixed pipeline will be tested on a different configuration file than the one at `/app/config.nconf`.

Output: `/app/output.json` — a JSON object with three top-level keys:
- `config`: mapping of section names (original casing preserved) to their resolved key-value pairs
- `resolution_info`: statistics about variable reference resolution (total_references, resolved_count, unresolved, circular)
- `document_info`: document metadata (section_count, total_keys, has_references, sections_order, dependencies)

Output conventions: `has_references` reports whether any unresolved `${...}` references remain in the final resolved output values (not whether the source document contains reference syntax). The `dependencies` field uses normalized (lowercase) section names as keys, matching the internal lookup representation used by the resolver.
