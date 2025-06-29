#!/bin/bash
#
# # Analysis script to segment the spinal cord, compute SNR and CNR, and quantify ghosting
#
# Usage:
#   ./process_data.sh <SUBJECT>
#
# Manual segmentations or labels should be located under:
# PATH_DATA/derivatives/labels/SUBJECT/<CONTRAST>/

# The following global variables are retrieved from the caller sct_run_batch
# but could be overwritten by uncommenting the lines below:
# PATH_DATA_PROCESSED="~/data_processed"
# PATH_RESULTS="~/results"
# PATH_LOG="~/log"
# PATH_QC="~/qc"

# Uncomment for full verbose
set -x

# Immediately exit if error
set -e -o pipefail

# Exit if user presses CTRL+C (Linux) or CMD+C (OSX)
trap "echo Caught Keyboard Interrupt within script. Exiting now.; exit" INT

# Retrieve input params
SUBJECT_SLASH_SESSION=$1
# Update SUBJECT variable to the prefix for BIDS file names, considering the "ses" entity
# Can be improved, see: https://github.com/sct-pipeline/gre-1dnav-analysis/issues/3
SUBJECT=`cut -d "/" -f1 <<< "$SUBJECT_SLASH_SESSION"`
SESSION=`cut -d "/" -f2 <<< "$SUBJECT_SLASH_SESSION"`

# get starting time:
start=`date +%s`


# FUNCTIONS
# ==============================================================================

# Check if manual segmentation already exists. If it does, copy it locally. If
# it does not, perform seg.
segment_if_does_not_exist(){
  local file="$1"
  # Update global variable with segmentation file name
  FILESEG="${file}_seg"
  FILESEGMANUAL="${PATH_DATA}/derivatives/labels/${SUBJECT_SLASH_SESSION}/anat/${FILESEG}$EXT"
  echo
  echo "Looking for manual segmentation: $FILESEGMANUAL"
  if [[ -e $FILESEGMANUAL ]]; then
    echo "Found! Using manual segmentation."
    rsync -avzh $FILESEGMANUAL ${FILESEG}$EXT
    sct_qc -i ${file}$EXT -s ${FILESEG}$EXT -p sct_deepseg_sc -qc ${PATH_QC} -qc-subject ${SUBJECT_UNDERSCORE_SESSION}
  else
    echo "Not found. Proceeding with automatic segmentation."
    # Segment spinal cord
    sct_deepseg spinalcord -i ${file}$EXT -qc ${PATH_QC} -qc-subject ${SUBJECT_UNDERSCORE_SESSION}
  fi
}


segment_gm_if_does_not_exist(){
  local file="$1"
  # Update global variable with segmentation file name
  FILESEG="${file}_gmseg"
  FILESEGMANUAL="${PATH_DATA}/derivatives/labels/${SUBJECT_SLASH_SESSION}/anat/${FILESEG}$EXT"
  echo
  echo "Looking for manual segmentation: $FILESEGMANUAL"
  if [[ -e $FILESEGMANUAL ]]; then
    echo "Found! Using manual segmentation."
    rsync -avzh $FILESEGMANUAL ${FILESEG}$EXT
    sct_qc -i ${file}$EXT -s ${FILESEG}$EXT -p sct_deepseg_gm -qc ${PATH_QC} -qc-subject ${SUBJECT_UNDERSCORE_SESSION}
  else
    echo "Not found. Proceeding with automatic segmentation."
    # Segment spinal cord
    sct_deepseg_gm -i ${file}$EXT -qc ${PATH_QC} -qc-subject ${SUBJECT_UNDERSCORE_SESSION}
  fi
}


# Verify presence of output files and write log file if error
check_if_exists()
{
  local acq="$1"
  local rec="$2"
  FILES_TO_CHECK=(
    "anat/${SUBJECT_UNDERSCORE_SESSION}_${acq}_${rec}_${CONTRAST}_seg${EXT}"
    "anat/${SUBJECT_UNDERSCORE_SESSION}_${acq}_${rec}_${CONTRAST}_gmseg${EXT}"
  )
  for file in ${FILES_TO_CHECK[@]}; do
    if [[ ! -e "${PATH_DATA_PROCESSED}/derivatives/labels/${SUBJECT_SLASH_SESSION}/$file" ]]; then
      echo "${PATH_DATA_PROCESSED}/derivatives/labels/${SUBJECT_SLASH_SESSION}/${file} does not exist" >> "${PATH_LOG}/_error_check_output_files.log"
    fi
  done
}


# SCRIPT STARTS HERE
# ==============================================================================
# Display useful info for the log, such as SCT version, RAM and CPU cores available
sct_check_dependencies -short

# Go to folder where data will be copied and processed
cd $PATH_DATA_PROCESSED

# Copy list of participants in processed data folder
if [[ ! -f "participants.tsv" ]]; then
  rsync -avzh $PATH_DATA/participants.tsv .
fi

# Copy source images
mkdir -p $SUBJECT
rsync -avzh $PATH_DATA/$SUBJECT_SLASH_SESSION $SUBJECT/

# Go to anat folder where all structural data are located
cd ${SUBJECT_SLASH_SESSION}/anat/

# Create new variable that will be used to fetch data according to BIDS standard
SUBJECT_UNDERSCORE_SESSION="${SUBJECT}_${SESSION}"

# Loop through the different acquisition and reconstruction options
CONTRAST="T2starw"
EXT=".nii.gz"
ACQ=("acq-upperT" "acq-lowerT" "acq-LSE")
REC=("rec-navigated" "rec-standard")
OVERWRITE_SEG=true

for acq in "${ACQ[@]}";do
  for rec in "${REC[@]}";do
    file=${SUBJECT_UNDERSCORE_SESSION}_${acq}_${rec}_${CONTRAST}
    echo "File: ${file}${EXT}"
    if [ -e "${file}${EXT}" ]; then
      echo "File found! Processing..."
      segment_if_does_not_exist ${file}
      file_seg=$FILESEG
      segment_gm_if_does_not_exist ${file}
      file_gmseg=$FILESEG
      # Register the 'standard' segmentation to the 'navigated' data
      # TODO
      # Quantify ghosting
      # TODO
      check_if_exists "${acq}" "${rec}"
    else
      echo "File not found. Skipping"
    fi
  done
done


# ------------------------------------------------------------------------------
# Display useful info for the log
end=`date +%s`
runtime=$((end-start))
echo
echo "~~~"
echo "SCT version: `sct_version`"
echo "Ran on:      `uname -nsr`"
echo "Duration:    $(($runtime / 3600))hrs $((($runtime / 60) % 60))min $(($runtime % 60))sec"
echo "~~~"
