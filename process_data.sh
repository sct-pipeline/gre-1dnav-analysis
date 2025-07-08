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

# Get the path to the directory where all the scripts are located
PATH_SCRIPTS="$(dirname "$(realpath "./process_data.sh")")"

# get starting time:
start=`date +%s`


# FUNCTIONS
# ==============================================================================

# Copy all selected scripts in a folder to an output folder
copy_scripts() {
  local path_scripts="$1"
  local path_output="$2"
  local exception_file="$3"
  find "$path_scripts" -maxdepth 1 \( -name "*.py" -o -name "*.sh" \) ! -name "$exception_file" -exec rsync -avzh {} "$path_output" \;
}

# Check if manual segmentation already exists. If it does, copy it locally. If
# it does not, perform seg.
segment_if_does_not_exist(){
  local file="$1"
  # Update global variable with segmentation file name
  FILESEG="${file}_seg"
  FILESEGMANUAL="${PATH_DATA}/derivatives/labels/${SUBJECT_SLASH_SESSION}/anat/${FILESEG}-manual$EXT"
  FILESSEGPATH="${PATH_DATA}/derivatives/labels/${SUBJECT_SLASH_SESSION}/anat/${FILESEG}$EXT"
  echo
  echo "Looking for manual segmentation: $FILESEGMANUAL"
  if [[ -e $FILESEGMANUAL ]]; then
    echo "Found! Using manual segmentation."
    rsync -avzh $FILESEGMANUAL ${FILESEG}$EXT
    sct_qc -i ${file}$EXT -s ${FILESEG}$EXT -p sct_deepseg_sc -qc ${PATH_QC} -qc-subject ${SUBJECT_UNDERSCORE_SESSION}
  elif [[ -e $FILESSEGPATH ]]; then
    echo "Found segmentation!"
    rsync -avzh $FILESSEGPATH ${FILESEG}$EXT
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
  FILESEGMANUAL="${PATH_DATA}/derivatives/labels/${SUBJECT_SLASH_SESSION}/anat/${FILESEG}-manual$EXT"
  FILESSEGPATH="${PATH_DATA}/derivatives/labels/${SUBJECT_SLASH_SESSION}/anat/${FILESEG}$EXT"
  echo
  echo "Looking for manual segmentation: $FILESEGMANUAL"
  if [[ -e $FILESEGMANUAL ]]; then
    echo "Found! Using manual segmentation."
    rsync -avzh $FILESEGMANUAL ${FILESEG}$EXT
    sct_qc -i ${file}$EXT -s ${FILESEG}$EXT -p sct_deepseg_gm -qc ${PATH_QC} -qc-subject ${SUBJECT_UNDERSCORE_SESSION}
  elif [[ -e $FILESSEGPATH ]]; then
    echo "Found segmentation!"
    rsync -avzh $FILESSEGPATH ${FILESEG}$EXT
    sct_qc -i ${file}$EXT -s ${FILESEG}$EXT -p sct_deepseg_gm -qc ${PATH_QC} -qc-subject ${SUBJECT_UNDERSCORE_SESSION}
  else
    echo "Not found. Proceeding with automatic segmentation."
    # Segment spinal cord
    sct_deepseg_gm -i ${file}$EXT -qc ${PATH_QC} -qc-subject ${SUBJECT_UNDERSCORE_SESSION}
  fi
}

compute_wm_if_does_not_exist(){
   local file="$1"
   local file_seg="$2"
   local file_gmseg="$3"
   FILESEG="${PATH_DATA}/derivatives/labels/${SUBJECT_SLASH_SESSION}/anat/${file}_wmseg$EXT"
   if [[ -e $FILESEG ]]; then
       echo "Found Segmentation!"
       rsync -avzh $FILESEG ${file}_wmseg$EXT
   else
       echo "Not found. Calculate WM mask."
       sct_maths -i ${file_seg}${EXT} -sub ${file_gmseg}${EXT} -o $FILESEG
       rsync -avzh $FILESEG ${file}_wmseg$EXT
   fi
}

compute_snr_cnr(){
   local file="$1"
   local file_wmseg="$2"
   local file_gmseg="$3"

   # Split images, gm, and wm segs into individual slices to calculate SNR/CNR for each slice
   PATH_TMP=${PATH_DATA_PROCESSED}/tmp
   PATH_TMP_SUBJECT=${PATH_TMP}/${SUBJECT_SLASH_SESSION}
   mkdir -p ${PATH_TMP_SUBJECT}
   sct_image -i ${file_gmseg}${EXT} -split z -o "${PATH_TMP_SUBJECT}/${file_gmseg}${EXT}"
   sct_image -i ${file_wmseg}${EXT} -split z -o "${PATH_TMP_SUBJECT}/${file}_wmseg${EXT}"
   sct_image -i ${file}${EXT} -split z -o "${PATH_TMP_SUBJECT}/${file}${EXT}"
   file_gmseg_ind="${PATH_TMP_SUBJECT}/${file_gmseg}"
   file_wmseg_ind="${PATH_TMP_SUBJECT}/${file_wmseg}"
   file_ind="${PATH_TMP_SUBJECT}/${file}"

   # Find the number of slices in image
   num_slices=$(sct_image -i ${file}${EXT} -header fslhd | grep ^dim3 | awk '{print $2}')
   num_slices=$((num_slices-1))


   mkdir -p ${PATH_RESULTS}/SNR/${SUBJECT_SLASH_SESSION}
   mkdir -p ${PATH_RESULTS}/CNR/${SUBJECT_SLASH_SESSION}

   # Calculate SNR/CNR for each slice
   echo "slice,ID,wm_mean,gm_mean,wm_std,CNR" > ${PATH_RESULTS}/CNR/${SUBJECT_SLASH_SESSION}/${file}_results.csv
   echo "slice,ID,wm_mean,wm_std,SNR" > ${PATH_RESULTS}/SNR/${SUBJECT_SLASH_SESSION}/${file}_wm_results.csv
   echo "slice,ID,gm_mean,gm_std,SNR" > ${PATH_RESULTS}/SNR/${SUBJECT_SLASH_SESSION}/${file}_gm_results.csv
   for g in $(seq -w 0 ${num_slices}); do

     gmM=$(fslstats ${file_ind}_Z00${g}${EXT} -k ${file_gmseg_ind}_Z00${g}${EXT} -M)
     gmS=$(fslstats ${file_ind}_Z00${g}${EXT} -k ${file_gmseg_ind}_Z00${g}${EXT} -S)
     wmM=$(fslstats ${file_ind}_Z00${g}${EXT} -k ${file_wmseg_ind}_Z00${g}${EXT} -M)
     wmS=$(fslstats ${file_ind}_Z00${g}${EXT} -k ${file_wmseg_ind}_Z00${g}${EXT} -S)
     CNR=$(echo "scale=5; ($wmM - $gmM)/ $wmS" | bc)
     SNR_wm=$(echo "scale=5; $wmM/$wmS" | bc)
     SNR_gm=$(echo "scale=5; $gmM/$gmS" | bc)
     echo ${g}","${file_ind}","$wmM","$gmM","$wmS","$CNR >> ${PATH_RESULTS}/CNR/${SUBJECT_SLASH_SESSION}/${file}_results.csv
     echo ${g}","${file_ind}","$wmM","$wmS","$SNR_wm >> ${PATH_RESULTS}/SNR/${SUBJECT_SLASH_SESSION}/${file}_wm_results.csv
     echo ${g}","${file_ind}","$gmM","$gmS","$SNR_gm >> ${PATH_RESULTS}/SNR/${SUBJECT_SLASH_SESSION}/${file}_gm_results.csv

   done
   rm -r ${PATH_TMP}

}



compute_ghosting()
{
  local path_data="$1"
  local path_processed_data="$2"
  local subject="$3"
  local session="$4"
  local acq="$5"
  local rec="$6"
  # Create ghosting mask only on navigatd data
  if [[ $rec == "rec-navigated" ]]; then
    echo "Creating ghosting mask for ${subject} ${session} ${acq}"
    ./../../../../create_ghosting_mask.py $path_data $path_processed_data $subject $session $acq
  fi
  # Compute ghosting
  echo "Computing ghosting for ${subject} ${session} ${acq} ${rec}"
  ./../../../../compute_ghosting.py $path_processed_data $subject $session $acq $rec
}


# Verify presence of output files and write log file if error
check_if_exists()
{
  local acq="$1"
  local rec="$2"
  FILES_TO_CHECK=(
    "anat/${SUBJECT_UNDERSCORE_SESSION}_${acq}_${rec}_${CONTRAST}_seg${EXT}"
    "anat/${SUBJECT_UNDERSCORE_SESSION}_${acq}_${rec}_${CONTRAST}_gmseg${EXT}"
    "anat/${SUBJECT_UNDERSCORE_SESSION}_${acq}_${rec}_${CONTRAST}_wmseg${EXT}"
  )
  for file in ${FILES_TO_CHECK[@]}; do
    if [[ ! -e "${PATH_DATA_PROCESSED}/${SUBJECT_SLASH_SESSION}/$file" ]]; then
      echo "${PATH_DATA_PROCESSED}/${SUBJECT_SLASH_SESSION}/${file} does not exist" >> "${PATH_LOG}/_error_check_output_files.log"
    fi
  done
}


# SCRIPT STARTS HERE
# ==============================================================================
# Display useful info for the log, such as SCT version, RAM and CPU cores available
sct_check_dependencies -short

# Copy files to the processed data folder
copy_scripts ${PATH_SCRIPTS} "${PATH_DATA_PROCESSED}/../" "process_data.sh"

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
    file2=${SUBJECT_UNDERSCORE_SESSION}_${acq}_rec-navigated_${CONTRAST}
    echo "File: ${file}${EXT}"
    if [ -e "${file}${EXT}" ]; then
      echo "File found! Processing..."

      #always use the navigated segmentation (manually corrected) to calculate SNR/CNR for both standard and navigated images
      segment_if_does_not_exist ${file}
      file_seg=${file2}_seg
      segment_gm_if_does_not_exist ${file}
      file_gmseg=${file2}_gmseg

      #calculate WM mask
      compute_wm_if_does_not_exist ${file} ${file_seg} ${file_gmseg}
      file_wmseg="${file}_wmseg"

      #compute slicewise snr and cnr values
      compute_snr_cnr ${file} ${file_wmseg} ${file_gmseg}

      # Quantify ghosting
      compute_ghosting "${PATH_DATA}" "${PATH_DATA_PROCESSED}" "${SUBJECT}" "${SESSION}" "${acq}" "${rec}"
      # Check if output files exist
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
