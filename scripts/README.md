# Scripts inventory and analysis

## Scope and method

This index covers the 47 files and 3 submodule pointers tracked under
`scripts/` before this report was added. The inventory includes source code,
package markers, documentation, fixtures, and generated/example data. The
history fields are the oldest and newest commits affecting each current path,
using `git log --follow`; dates are commit dates and names are the Git author
identities as recorded (aliases are not consolidated). `LOC` is the current
line count; submodule pointers do not have a local line count.

For code, “static findings” means Ruff findings for Python plus TODO markers;
it does not claim that a clean lint run proves the code defect-free. Data and
documentation are marked N/A unless a parser was run. Security observations
are listed separately and linked by ID in the inventory.

## At a glance

- 50 pre-existing tracked entries across 9 directories: 47 files (31 Python,
  3 Perl, 1 shell script, 5 Markdown documents, 3 JSON files, 1 JSON-LD
  template, 1 CSV, and 2 text lists) plus 3 submodule pointers.
- The three submodule directories are empty in this checkout, so their
  referenced schemas/contexts could not be inspected as part of this report.
- Main concerns are credential handling in the legacy Zenodo flow, a cleartext
  GitHub API request, shell interpolation in legacy Perl crawlers, and
  user-controlled URL fetching in the DATS validator. Details and conditions
  are in [Security and maintenance findings](#security-and-maintenance-findings).
- Ruff reported **0 findings** across `scripts/`; all Python files parsed
  successfully. JSON and CSV inputs parsed; checked Perl/shell syntax results
  and the test-suite limitation are in [Validation](#validation).

## File-by-file index

### Crawler framework: `scripts/Crawlers/`

| File | Purpose / contents | LOC | Static findings | Git history: first → latest |
|---|---|---:|---|---|
| `scripts/Crawlers/BaseCrawler.py` | Shared crawler workflow: repository setup, metadata/DATS handling, file operations, and GitHub publishing. | 645 | Ruff 0; S2 | joeyzhou98 (2020-03-12) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/Crawlers/BaseCrawlerTest.py` | Test-oriented counterpart to the base crawler, including repository and GitHub operations used by crawler tests. | 602 | Ruff 0; S2 | joeyzhou98 (2020-03-12) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/Crawlers/OSFCrawler.py` | Crawls OSF nodes, metadata, components, and files into DataLad datasets. | 758 | Ruff 0 | joeyzhou98 (2020-03-26) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/Crawlers/OSFCrawlerTest.py` | Test-oriented OSF crawler implementation. | 626 | Ruff 0 | joeyzhou98 (2020-03-26) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/Crawlers/ZenodoCrawler.py` | Discovers Zenodo records and imports dataset metadata/files; uses per-dataset tokens for restricted records. | 437 | Ruff 0; S1 | joeyzhou98 (2020-03-12) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/Crawlers/constants.py` | Shared DATS field names, required fields, license codes, and modalities. | 60 | Ruff 0 | Joey Zhou (2021-04-30) → Anthony Hatzopoulos (2026-11-07) |
| `scripts/Crawlers/__init__.py` | Python package marker. | 0 | Ruff 0 | Tristan Glatard (2018-05-10) → CONP bot (2021-11-24) |

### DATS to CSV: `scripts/DATS2csv/`

| File | Purpose / contents | LOC | Static findings | Git history: first → latest |
|---|---|---:|---|---|
| `scripts/DATS2csv/DATS2csv.pl` | Reads a list of DATS files, selects configured fields, and writes a consolidated CSV. | 442 | Perl syntax OK | emmetaobrien (2023-03-27) → Anthony Hatzopoulos (2026-11-16) |
| `scripts/DATS2csv/DATS.json-summary.csv` | Example/exported summary of DATS metadata (77 CSV rows). | 77 | CSV parse OK | emmetaobrien (2023-03-27) → emmetaobrien (2023-03-30) |
| `scripts/DATS2csv/fieldlist.txt` | Field-selection configuration consumed by the Perl exporter. | 44 | N/A (text data) | emmetaobrien (2023-03-27) → emmetaobrien (2023-03-27) |
| `scripts/DATS2csv/inputJSONlist.txt` | File-path list for DATS JSON inputs to the exporter. | 76 | N/A (text data) | emmetaobrien (2023-03-27) → emmetaobrien (2023-03-27) |

### Term reports and JSON-LD: `scripts/conp_to_nidm_terms/`

| File | Purpose / contents | LOC | Static findings | Git history: first → latest |
|---|---|---:|---|---|
| `scripts/conp_to_nidm_terms/functions.py` | Shared value collection, duplicate detection, NIF API lookup, and JSON-LD generation. | 215 | Ruff 0 | zxenia (2021-02-18) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/conp_to_nidm_terms/jsonld_generator.py` | CLI to generate JSON-LD records for distinct DATS values, optionally matching InterLex/NIF terms. | 78 | Ruff 0 | zxenia (2021-02-22) → Anthony Hatzopoulos (2026-11-07) |
| `scripts/conp_to_nidm_terms/report_generator.py` | CLI to report distinct metadata values and duplicates by DATS property. | 84 | Ruff 0 | zxenia (2021-02-22) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/conp_to_nidm_terms/template.jsonld` | JSON-LD template used by the term generator. | 10 | JSON parse OK | zxenia (2021-02-18) → Tristan Kuehn (2023-01-31) |
| `scripts/conp_to_nidm_terms/api_key.json` | NIF API key configuration file; the tracked key value is empty. | 4 | JSON parse OK; credential-handling note S5 | zxenia (2021-02-18) → Joey Zhou (2021-04-08) |
| `scripts/conp_to_nidm_terms/README.md` | Usage instructions for reports and term annotation, including API-key setup. | 16 | N/A (documentation); S5 | zxenia (2021-02-22) → Joey Zhou (2021-04-08) |
| `scripts/conp_to_nidm_terms/__init__.py` | Python package marker. | 0 | Ruff 0 | Tristan Glatard (2018-05-10) → zxenia (2021-02-22) |

### Dataset and tool summaries: `scripts/data_aggregation_summary_scripts/`

| File | Purpose / contents | LOC | Static findings | Git history: first → latest |
|---|---|---:|---|---|
| `scripts/data_aggregation_summary_scripts/create_data_provenance_summary.py` | Produces a CSV of dataset provenance fields such as investigator, institution, and location. | 153 | Ruff 0 | Cécile (2020-09-18) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/data_aggregation_summary_scripts/create_dataset_statistcs_per_data_providers.py` | Aggregates dataset statistics by data provider. The filename’s `statistcs` spelling is the tracked spelling. | 203 | Ruff 0 | Cécile (2020-09-24) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/data_aggregation_summary_scripts/create_tools_statistics_per_domain.py` | Aggregates tool metadata and statistics by domain. | 189 | Ruff 0 | Cécile (2020-09-25) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/data_aggregation_summary_scripts/lib/Utility.py` | Shared dataset/DATS and cached-tool readers plus CSV writer. | 129 | Ruff 0 | Cécile (2020-09-25) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/data_aggregation_summary_scripts/lib/__init__.py` | Package marker and historical package documentation. | 9 | Ruff 0 | Cécile (2020-09-25) → Joey Zhou (2021-03-03) |
| `scripts/data_aggregation_summary_scripts/README.md` | Documents dependencies and provenance-summary usage. | 29 | N/A (documentation) | Cécile (2020-10-08) → Joey Zhou (2021-04-08) |

### DATS JSON-LD annotator: `scripts/dats_jsonld_annotator/`

| File | Purpose / contents | LOC | Static findings | Git history: first → latest |
|---|---|---:|---|---|
| `scripts/dats_jsonld_annotator/annotator.py` | CLI that loads DATS schema/context data and emits annotated JSON-LD. | 312 | Ruff 0; 3 TODO markers | Sebastian Urchs (2021-07-05) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/dats_jsonld_annotator/README.md` | Usage and behavior for annotating one DATS file or a directory tree. | 29 | N/A (documentation) | Sebastian Urchs (2021-07-05) → CONP bot (2021-11-24) |
| `scripts/dats_jsonld_annotator/__init__.py` | Python package marker. | 0 | Ruff 0 | Tristan Glatard (2018-05-10) → CONP bot (2021-11-24) |
| `scripts/dats_jsonld_annotator/schema` | Git submodule pointer to `CONP-PCNO/schema`; checkout is empty. Pinned commit `0e35ef6989042f66db3cf3139a52ba0d46daefe4`. | N/A (gitlink) | Not inspected | Sebastian Urchs (2021-07-05) → Sebastian Urchs (2021-07-05) |
| `scripts/dats_jsonld_annotator/context` | Git submodule pointer to `CONP-PCNO/context`; checkout is empty. Pinned commit `2cab2643b83436f98852aa402650c2bbeed7fab9`. | N/A (gitlink) | Not inspected | Sebastian Urchs (2021-07-05) → surchs (2021-11-11) |

### DATS validator: `scripts/dats_validator/`

| File | Purpose / contents | LOC | Static findings | Git history: first → latest |
|---|---|---:|---|---|
| `scripts/dats_validator/validator.py` | CLI validating DATS against schema and additional rules, including external OSF/derived-from checks. | 517 | Ruff 0; S4 | zxenia (2020-01-14) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/dats_validator/examples/valid_dats.json` | Positive DATS validation fixture. | 2887 | JSON parse OK | zxenia (2020-01-14) → CONP bot (2021-11-24) |
| `scripts/dats_validator/examples/invalid_dats.json` | Negative DATS validation fixture; “invalid” describes its DATS/schema content, not JSON syntax. | 2883 | JSON parse OK | zxenia (2020-01-14) → CONP bot (2021-11-24) |
| `scripts/dats_validator/README.md` | Validator workflow, invocation, and fixture/test pointers. | 14 | N/A (documentation) | zxenia (2020-01-14) → ksenia1zaytseva (2020-07-14) |
| `scripts/dats_validator/__init__.py` | Python package marker. | 0 | Ruff 0 | Tristan Glatard (2018-05-10) → Tristan Glatard (2020-07-29) |
| `scripts/dats_validator/conp-dats` | Git submodule pointer to `CONP-PCNO/schema`; checkout is empty. Pinned commit `2c1b0de2c93fdde52f7657d9a88d50ce29dbc575`. | N/A (gitlink) | Not inspected | zxenia (2020-01-14) → conp-bot (2025-05-23) |

### DataLad helpers and crawlers

| File | Purpose / contents | LOC | Static findings | Git history: first → latest |
|---|---|---:|---|---|
| `scripts/datalad_crawlers/ftp_crawler.py` | CLI for crawling/downloading files from an FTP endpoint into a DataLad dataset. | 64 | Ruff 0 | mathdugre (2021-05-06) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/datalad_crawlers/sftp-crawler.pl` | Legacy SFTP listing-to-`git annex addurl` helper. | 54 | Perl syntax OK; S3 | Emmet A. O'Brien (2022-01-05) → Emmet A. O'Brien (2022-04-26) |
| `scripts/datalad_helper_scripts/batch_remove_deprecated_URLs.py` | Finds and removes deprecated URLs from repository/DataLad metadata in batches. | 226 | Ruff 0 | Cécile (2021-02-12) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/datalad_utils.py` | Shared retry and install/get/uninstall wrappers for DataLad datasets, with typed failure classes. | 80 | Ruff 0 | Mathieu Dugré (2021-07-07) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/unlock.py` | Adds Zenodo access tokens to annex URLs for restricted datasets. | 112 | Ruff 0; S1 | joeyzhou98 (2020-02-28) → Anthony Hatzopoulos (2026-11-17) |

### Root-level commands and shared files

| File | Purpose / contents | LOC | Static findings | Git history: first → latest |
|---|---|---:|---|---|
| `scripts/crawl.py` | Parses crawler options/configuration and runs OSF and/or Zenodo crawlers. | 154 | Ruff 0 | joeyzhou98 (2020-03-12) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/crawl.sh` | Scheduled crawl wrapper: creates logs/lock file, pulls the repository, and runs `crawl.py`. | 29 | Bash syntax OK | joeyzhou98 (2020-03-12) → CONP bot (2023-11-29) |
| `scripts/auto_archive.py` | Finds recently modified datasets and produces DataLad archive exports. | 259 | Ruff 0; 1 TODO marker | Mathieu Dugré (2021-07-07) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/check_dataset_filenames.py` | Checks tracked paths and Git trees for Windows filename incompatibilities. | 337 | Ruff 0 | Anthony Hatzopoulos (2026-11-16) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/import_single_osf_to_local_datalad.py` | Imports one OSF node and its components/files locally; generates README/DATS metadata and configures DataLad. | 533 | Ruff 0 | kongtiaowang (2026-11-05) → Anthony Hatzopoulos (2026-11-23) |
| `scripts/import_single_zenodo_to_local_datalad.py` | Imports one Zenodo record locally, downloads files, and generates README/DATS metadata. | 362 | Ruff 0 | kongtiaowang (2026-11-05) → Anthony Hatzopoulos (2026-11-23) |
| `scripts/how_to_use_import_single_scripts.md` | Example command lines for the one-record OSF and Zenodo importers. | 5 | N/A (documentation) | kongtiaowang (2026-11-05) → Anthony Hatzopoulos (2026-11-07) |
| `scripts/log.py` | Small shared logger factory. | 21 | Ruff 0 | Mathieu Dugré (2021-07-07) → Anthony Hatzopoulos (2026-11-17) |
| `scripts/sftp-crawler.pl` | Legacy SFTP crawler using `Net::SFTP::Foreign` and `git annex addurl`. | 56 | Not checked: `Net::SFTP::Foreign` is unavailable in this environment; S3 | emmetaobrien (2023-04-24) → emmetaobrien (2023-11-03) |
| `scripts/__init__.py` | Root Python package marker. | 0 | Ruff 0 | Tristan Glatard (2018-05-10) → CONP bot (2021-11-24) |

### Usage documentation and additional generated outputs

| File | Purpose / contents | LOC | Static findings | Git history: first → latest |
|---|---|---:|---|---|
| `scripts/README.md` | This inventory, purpose index, history, diagnostics, and risk analysis. | New | Added by this change | New |

## Security and maintenance findings

These are code-review observations, not proof of exploitation. They are kept
separate from Ruff and syntax diagnostics.

| ID | Severity / concern | Evidence and impact |
|---|---|---|
| S1 | **Credential exposure risk** | `Crawlers/ZenodoCrawler.py` prints the dataset token in verbose output when configuring `DATALAD_ZENODO_token` (around lines 357–359). It also adds credentials as `access_token` query parameters to file URLs. `unlock.py` similarly writes tokenized URLs into annex metadata. Query strings and verbose logs can be retained or propagated; avoid printing secrets and ensure these records/logs are access-controlled. The tracked `conp_to_nidm_terms/api_key.json` currently has an empty value, but its README instructs users to place a real API key in that tracked file, which risks accidental secret commits. |
| S2 | **Cleartext API request** | `Crawlers/BaseCrawler.py` (line 451) and its test-oriented counterpart call `http://api.github.com`. An on-path party could modify the unauthenticated repository metadata response; use HTTPS. |
| S3 | **Shell interpolation in legacy Perl crawlers** | Both `scripts/sftp-crawler.pl` and `scripts/datalad_crawlers/sftp-crawler.pl` interpolate remote/local paths into a single-string Perl `system` command. If the input list contains shell metacharacters, the command may be interpreted by a shell. Prefer list-form `system` and validate path inputs. |
| S4 | **Potential SSRF and unbounded request** | `dats_validator/validator.py` passes `derived_from_url` from DATS metadata directly to `requests.get` (around line 503), without an explicit timeout or destination restriction. When validating untrusted metadata in a service or privileged network, this can allow requests to unintended internal/public destinations and can hang the validation process. Restrict allowed schemes/hosts and set a timeout if the validator is used in that context. |

Other maintenance notes: `auto_archive.py` has one unfinished notification TODO;
`dats_jsonld_annotator/annotator.py` has three TODO markers. Several crawler
requests do not set explicit timeouts, including the OSF request helper. This is
an availability/reliability concern rather than a confirmed security defect.

## Validation

- `ruff check scripts --output-format json`: **passed, 0 findings**.
- Python AST parsing: **31/31 Python files parsed**.
- `bash -n scripts/crawl.sh`: **passed**.
- `perl -c scripts/DATS2csv/DATS2csv.pl` and
  `perl -c scripts/datalad_crawlers/sftp-crawler.pl`: **passed**.
- `perl -c scripts/sftp-crawler.pl`: **not completed** because the environment
  does not have the `Net::SFTP::Foreign` Perl module; this is an environment
  dependency gap, not a syntax verdict.
- JSON/JSON-LD parse: **4/4 passed**; CSV parse: **passed, 77 rows**.
- `pytest -q --disable-warnings`: **blocked during collection** because
  `html2markdown` is not installed (`tests/test_zenodo_crawler.py` imports
  `scripts/Crawlers/ZenodoCrawler.py`). The package is declared in
  `pyproject.toml`; tests did not run.

## Git authors and contribution history

The per-file history above records first and latest authors. The repository
history also contains these author identities across `scripts/` (spelling and
aliases preserved as Git records them): Anthony Hatzopoulos; Cécile, Cécile
Madjar, Cecile Madjar, and cmadjar; CONP bot, CONP robot, and conp-bot;
dependabot[bot]; Emmet A. O'Brien; Joey Zhou and joeyzhou98; kongtiaowang;
Ksenia Zaytseva and ksenia1zaytseva; Mathieu Dugré and mathdugre; Patrick
Bermudez; Sebastian Urchs and surchs; Shen; Tristan Glatard; Tristan Kuehn;
and zxenia.

The oldest recorded history in this subtree dates to 2018-05-10 (package
markers); the newest file updates are the two single-record importers on
2026-11-23.
