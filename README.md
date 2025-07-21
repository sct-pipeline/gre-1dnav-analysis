# gre-1dnav-analysis
Analysis pipeline for FFE 1d retrospective navigator correction for spinal cord imaging on Philips scanners. 

## 1 - Download data

See: https://openneuro.org/datasets/ds006347/download

Some notes about the data:
- Contrast: `_T2starw`
- Varying number of sessions across participants: ses-01, ses-02, etc.
- With | without navigator: `*_rec-navigated` | `*_rec-standard`
- Varying location: `acq-lowerT` | `acq-upperT` | `acq-LSE`

## 2 - Run data analysis scripts

### 2.1 - Clone the repository and navigate to the script directory
```bash
git clone https://github.com/sct-pipeline/gre-1dnav-analysis.git
cd <PATH_TO_CLONED_REPOSITORY>
```
>[!Note]
>Please make sure to replace `<PATH_TO_CLONED_REPOSITORY>` with the full path to the folder where the repository has been cloned

### 2.2 - Execute the data processing script for all subjects
```bash
sct_run_batch -script process_data.sh -path-data <PATH_TO_DATA> -path-output <PATH_TO_OUTPUT>
```
Example:
```bash
sct_run_batch -script process_data.sh -path-data ~/data/ds006347/ -path-output ~/temp/ds006347_20250612_144520
```
## 3 - Run figure scripts
>[!Warning]
>TODO
