#!/usr/bin/env python3
#
# Quantifies signal-to-noise (SNR) by computiing slice-wise mean and standard deviation (STD) inside the gray matter (GM) mask. The mean and median of those
# metrics are combined in a single CSV file with the following structure:
#
# | Subject-ID/Session-ID/Acquisition | mean rec-standard | mean rec-navigated | median rec-standard | median rec-navigated |
# |     sub-01/ses-01/acq-lowerT      |     0.000000      |      0.000000      |      0.000000       |      0.000000        |
# |     sub-02/ses-01/acq-upperT      |     0.000000      |      0.000000      |      0.000000       |      0.000000        |
#
# It requires six arguments:
# 1. path_processed_data : The path to the processed data directory (output path).
# 2. subject_id: The ID of the subject. (e.g., sub-01)
# 3. session_id: The ID of the session. (e.g., ses-01)
# 4. acquisition_region: The region of acquisition, which can be one of the following:
#    - acq-upperT: Upper thoracic region
#    - acq-lowerT: Lower thoracic region
#    - acq-LSE: Lumbar-sacral region
# 5. rec: The reconstruction type, which can be one of the following:
#    - rec-standard: Standard reconstruction
#    - rec-navigated: Navigated reconstruction
# 6. gm_mask: The gray matter mask in which the STD and mean is computed
# It will create and/or add data to the following file:
#   /PATH/TO/PROCESSED/DATA/results/gm_snr.csv
# 
# How to use:
#   ./compute_gm_snr.py <path_processed_data> <subject_id> <session_id> <acquisition_region> <rec> <gm_mask>

import os
import numpy as np
import nibabel as nib
import argparse

# Define variables
ext = ".nii.gz"
contrast = "T2starw"

parser = argparse.ArgumentParser(
  description="Quantifies signal-to-noise (SNR) by computiing slice-wise mean and standard deviation (STD) inside the gray matter (GM) mask. The mean and\
  median of those metrics are combined in a single CSV file with the following columns:\
  | Subject-ID/Session-ID/Acquisition | mean rec-standard | mean rec-navigated | median rec-standard | median rec-navigated |"
)
parser.add_argument("path_processed_data", help="The path to the processed data directory (output path).")
parser.add_argument("subject_id", help="ID of the subject (e.g., sub-01).")
parser.add_argument("session_id", help="ID of the session (e.g., ses-01).")
parser.add_argument("acquisition_region", choices=["acq-upperT", "acq-lowerT", "acq-LSE"], 
                    help="Region of acquisition: acq-upperT, acq-lowerT, or acq-LSE.")
parser.add_argument("rec", choices=["rec-standard", "rec-navigated"],
                    help="Reconstruction type: rec-standard or rec-navigated.")
parser.add_argument("gm_mask", help="The gray matter mask in which the STD and mean is computed.")
args = parser.parse_args()

# Define arguments
path_processed_data = args.path_processed_data
subject = args.subject_id
session = args.session_id
acq = args.acquisition_region
rec = args.rec
gm_mask = args.gm_mask

if not os.path.isdir(path_processed_data):
  raise RuntimeError(f"The provided path does not exist.\nProvided path: {path_processed_data}")

# Define functions
def format_value(val):
    if val == 'nan' or val is None:
        return 'nan'
    try:
        return f"{float(val):.6f}"
    except (ValueError, TypeError):
        return 'nan'

def write_csv(path_processed_data, subject, session, acq,rec, mean_snr='nan', median_snr='nan'):
     # Create or update the CSV file
    csv_path = os.path.join(path_processed_data, "..", "results", "gm_snr.csv")

    # Read existing data if file exists
    existing_data = {}
    header_written = False
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            lines = f.readlines()
            if lines:
                header_written = True
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.strip().split(",")
                        if len(parts) >= 5:
                            subject_session_acq = parts[0]
                            existing_data[subject_session_acq] = {
                                'mean_standard': parts[1],
                                'mean_navigated': parts[2], 
                                'median_standard': parts[3],
                                'median_navigated': parts[4]
                            }

    # Update data for current subject/session/acquisition
    subject_session_acq = f"{subject}/{session}/{acq}"
    if subject_session_acq not in existing_data:
        existing_data[subject_session_acq] = {
            'mean_standard': 'nan',
            'mean_navigated': 'nan',
            'median_standard': 'nan', 
            'median_navigated': 'nan'
        }

    # Update with current measurements
    if rec == "rec-standard":
        existing_data[subject_session_acq]['mean_standard'] = mean_snr
        existing_data[subject_session_acq]['median_standard'] = median_snr
    else:  # rec == "rec-navigated"
        existing_data[subject_session_acq]['mean_navigated'] = mean_snr
        existing_data[subject_session_acq]['median_navigated'] = median_snr

    # Write the complete file
    with open(csv_path, 'w') as f:
        # Write header
        f.write("Subject-ID/Session-ID/Acquisition,mean rec-standard,mean rec-navigated,median rec-standard,median rec-navigated\n")
        # Write data
        for sub_ses_acq, data in existing_data.items():
            mean_std = format_value(data['mean_standard'])
            mean_nav = format_value(data['mean_navigated'])
            median_std = format_value(data['median_standard'])
            median_nav = format_value(data['median_navigated'])
            
            f.write(f"{sub_ses_acq},{mean_std},{mean_nav},{median_std},{median_nav}\n")

def main():
    # Define file names
    file_anat = f"{subject}_{session}_{acq}_{rec}_{contrast}"
    file_gm_mask = gm_mask

    # Define paths
    path_sub_session = os.path.join(path_processed_data, subject, session, "anat")
    path_anat = os.path.join(path_sub_session, file_anat + ext)
    path_gm_mask = os.path.join(path_sub_session, file_gm_mask + ext)

    # Load the nifti files
    mask_nii = nib.load(path_gm_mask)
    mask_data = mask_nii.get_fdata()
    anat_nii = nib.load(path_anat)
    anat_data = anat_nii.get_fdata()

    # Mask the anatomical data
    # This will keep only the data inside the GM mask
    anat_masked = np.ma.masked_array(anat_data, mask=(mask_data == 0))

    # Compute slice-wise standard deviation, mean, and SNR
    nslices = anat_data.shape[2] 
    slice_wise_std = np.zeros(nslices)
    slice_wise_mean = np.zeros(nslices)
    slice_wise_snr = np.zeros(nslices)

    for z in range(nslices):
        slice_wise_std[z] = np.ma.std(anat_masked[:, :, z])
        slice_wise_mean[z] = np.ma.mean(anat_masked[:, :, z])
        slice_wise_snr[z] = slice_wise_mean[z] / slice_wise_std[z]
    
    # Compute max and mean STDs
    mean_snr = np.nanmean(slice_wise_snr)
    median_snr = np.nanmedian(slice_wise_snr)

    # Write the results to the CSV file
    write_csv(path_processed_data, subject, session, acq, rec, mean_snr, median_snr)


if __name__ == "__main__":
    main()
