# Scripts inventory and maintenance recommendations

This report is a static, source-level inventory of the Python, Perl, and shell
code under `scripts/`. It does not claim that a script is safe to run or that
its behavior was integration-tested. “Obsolete” is marked **not established**
unless repository evidence supports that conclusion; verify references and
owners before removing a tool.

Paths in the tables are relative to `scripts/`.

**Importance** is a relative estimate of how central the script is to routine
CONP dataset operations, not a severity score. The source set includes 29
non-package-marker files. Empty `__init__.py` package markers are omitted;
they contain no script behavior.

## Crawler and import workflows

| Script | Purpose | Obsolete? | Recommendation / upgrade need | Importance |
|---|---|---|---|---|
| `crawl.py` | Selects and runs OSF and/or Zenodo crawlers. | No evidence | Keep; document and test remote-write configuration. | High |
| `crawl.sh` | Scheduled wrapper for the crawler, including repository and log setup. | No evidence | Keep if deployed; verify its configured paths and remotes. | High |
| `Crawlers/BaseCrawler.py` | Shared dataset setup, metadata, file, and publishing workflow. | No evidence | Keep; preserve as the common provider implementation. | High |
| `Crawlers/BaseCrawlerTest.py` | Test-oriented counterpart to the shared crawler. | Unclear | Review whether tests need this duplicate before retiring. | Medium |
| `Crawlers/OSFCrawler.py` | Discovers OSF projects and imports metadata/files. | No evidence | Keep; maintain against OSF API and DataLad changes. | High |
| `Crawlers/OSFCrawlerTest.py` | Test-oriented OSF crawler implementation. | Unclear | Review overlap with the production crawler and tests before retiring. | Medium |
| `Crawlers/ZenodoCrawler.py` | Discovers Zenodo records and imports metadata/files. | No evidence | Keep; maintain against Zenodo API and DataLad changes. | High |
| `Crawlers/constants.py` | Shared DATS fields, license codes, and modality mappings. | No evidence | Keep with crawler/schema updates. | Medium |
| `import_single_osf_to_local_datalad.py` | Imports one OSF node and its components into a local dataset. | No evidence | Keep; add isolated coverage for writes and API responses. | High |
| `import_single_zenodo_to_local_datalad.py` | Imports one Zenodo record into a local dataset. | No evidence | Keep; add isolated coverage for writes and API responses. | High |

## Metadata, reporting, and validation

| Script | Purpose | Obsolete? | Recommendation / upgrade need | Importance |
|---|---|---|---|---|
| `dats_validator/validator.py` | Checks DATS against the CONP schema and additional rules. | No evidence | Keep; verify schema compatibility and external-check behavior. | High |
| `dats_jsonld_annotator/annotator.py` | Adds JSON-LD annotations to DATS documents. | No evidence | Keep if output remains in use; resolve its TODOs. | Medium |
| `DATS2csv/DATS2csv.pl` | Exports configured DATS fields into a consolidated CSV. | No evidence | Keep if reporting uses it; maintain its Perl dependencies. | Medium |
| `conp_to_nidm_terms/report_generator.py` | Reports distinct and duplicate DATS values. | No evidence | Keep for term review; check continued use of generated reports. | Low |
| `conp_to_nidm_terms/jsonld_generator.py` | Generates JSON-LD records for distinct DATS values. | No evidence | Keep if NIDM exports are required; test API-independent generation. | Medium |
| `conp_to_nidm_terms/functions.py` | Shared value collection, duplicate detection, and optional NIF lookups. | No evidence | Keep with its CLI tools; document credential handling. | Medium |
| `data_aggregation_summary_scripts/create_data_provenance_summary.py` | Writes a dataset provenance CSV. | No evidence | Keep if reporting uses it; add focused fixture coverage. | Medium |
| `data_aggregation_summary_scripts/create_dataset_statistcs_per_data_providers.py` | Aggregates dataset statistics by provider. | No evidence | Keep if reporting uses it; filename spelling is historical. | Medium |
| `data_aggregation_summary_scripts/create_tools_statistics_per_domain.py` | Aggregates cached tool statistics by domain. | No evidence | Keep if the Boutiques cache report is used; verify cache compatibility. | Low |
| `data_aggregation_summary_scripts/lib/Utility.py` | Shared data readers and CSV writer for aggregation scripts. | No evidence | Keep while aggregation commands depend on it. | Medium |

## DataLad helpers and repository checks

| Script | Purpose | Obsolete? | Recommendation / upgrade need | Importance |
|---|---|---|---|---|
| `check_dataset_filenames.py` | Checks Git-tracked paths for Windows and Unicode filename conflicts. | No evidence | Keep; use in local and CI checks. | High |
| `auto_archive.py` | Selects modified datasets and creates DataLad archive exports. | No evidence | Keep if scheduled; finish its notification TODO. | Medium |
| `unlock.py` | Adds Zenodo access tokens to annex URLs for restricted content. | No evidence | Keep for the restricted-data workflow; document credential handling. | Medium |
| `datalad_helper_scripts/batch_remove_deprecated_URLs.py` | Finds and removes deprecated URLs from annex metadata. | No evidence | Keep; use a disposable dataset for checks. | Medium |
| `datalad_crawlers/ftp_crawler.py` | Retrieves files from FTP into a DataLad dataset. | No evidence | Keep if FTP datasets use it; verify endpoint and dependencies. | Low |
| `datalad_crawlers/sftp-crawler.pl` | Registers remote SFTP files with Git-annex. | Unclear | Review legacy deployment use before modernizing or retiring. | Low |
| `sftp-crawler.pl` | Root-level legacy SFTP crawler using Perl and Git-annex. | Unclear | Review overlap with the other SFTP crawler and active use. | Low |
| `datalad_utils.py` | Retrying wrappers for DataLad install/get/uninstall operations. | No evidence | Keep while callers depend on it; test retry and failure reporting. | Medium |
| `log.py` | Shared logger factory. | No evidence | Keep while imported by scripts; low-cost maintenance. | Low |

## Summary

- **Obsolete:** no script is conclusively obsolete from this static review.
- **Review first:** the two test-oriented crawler implementations and the two
  legacy SFTP crawlers have the clearest potential for consolidation or
  retirement, subject to checking test/deployment references.
- **Maintenance priorities:** protect mutating workflows with disposable-data
  tests; keep crawler and importer behavior aligned with provider APIs; confirm
  DATS/schema and DataLad compatibility; and document credential handling.
- Data files, example fixtures, documentation, and package markers are not
  classified as scripts here. See `README.md` for navigation to the full
  directory contents.
