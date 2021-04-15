# Tools to produce aggregation summary of datasets and tools

A few tools have been developed to produce aggregated summary CSV files of
CONP datasets and tools to be used for reporting purposes.

## Dependencies

The tools use the same dependencies as the crawler. Follow the installation
instruction for the crawlers in order to install them.

## create_data_provenance_summary.py

This tool produces a data provenance summary with the following information:

- Dataset
- Principal Investigator
- Consortium
- Institution
- City
- Province
- Country

To run the script:
```bash
python create_data_provenance_summary.py -d <PATH TO conp-dataset>
```

`python create_data_provenance_summary.py -h` prints out the help and information
on how to run the script.
