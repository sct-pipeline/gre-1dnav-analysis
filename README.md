# gre-1dnav-analysis
Analysis pipeline for FFE 1d retrospective navigator correction for spinal cord imaging on Philips scanners. 

## Download data

See: https://openneuro.org/datasets/ds006347/download

Some notes about the data:
- Contrast: `_T2starw`
- Varying number of sessions across participants: ses-01, ses-02, etc.
- With | without navigator: `*_rec-navigated` | `*_rec-standard`
- Varying location: `acq-lowerT` | `acq-upperT` | `acq-LSE`

Organization of files:


## Run analysis script

TODO: complete below:
```bash
sct_run_batch -script process_data.sh -path-data <PATH_TO_DATA> -path-output <PATH_TO_OUTPUT>
```

Example:
```bash
sct_run_batch -script process_data.sh -path-data ~/data/ds006347/ -path-output ~/temp/ds006347_20250612_144520
```
