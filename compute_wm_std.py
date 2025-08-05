#!/usr/bin/env python3
#
# Quantifies standard deviation (STD) by computing the slice-wise STD inside the white matter (WM) mask. The maximum and mean of those
# metrics are combined in a single CSV file with the following structure:
#
# | Subject-ID/Session-ID/Acquisition | max rec-standard | max rec-navigated | mean rec-standard | mean rec-navigated |
# |     sub-01/ses-01/acq-lowerT     |     0.000000      |      0.000000     |      0.000000     |      0.000000      |
# |     sub-02/ses-01/acq-upperT     |     0.000000      |      0.000000     |      0.000000     |      0.000000      |
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
# 6. wm_mask: The white matter mask in which the STD is computed
# It will create and/or add data to the following file:
#   /PATH/TO/PROCESSED/DATA/results/std.csv
# 
# How to use:
#   ./compute_std.py <path_processed_data> <subject_id> <session_id> <acquisition_region> <rec> <wm_mask>

import os
import numpy as np
import nibabel as nib
import argparse

# Define variables
ext = ".nii.gz"
contrast = "T2starw"

parser = argparse.ArgumentParser(
  description="Quantifies standard deviation (STD) by computing the slice-wise STD inside the white matter (WM) mask. The maximum and\
  mean of those metrics are combined in a single CSV file with the following columns:\
  | Subject-ID/Session-ID/Acquisition | max rec-standard | max rec-navigated | mean rec-standard | mean rec-navigated |"
)
parser.add_argument("path_processed_data", help="The path to the processed data directory (output path).")
parser.add_argument("subject_id", help="ID of the subject (e.g., sub-01).")
parser.add_argument("session_id", help="ID of the session (e.g., ses-01).")
parser.add_argument("acquisition_region", choices=["acq-upperT", "acq-lowerT", "acq-LSE"], 
                    help="Region of acquisition: acq-upperT, acq-lowerT, or acq-LSE.")
parser.add_argument("rec", choices=["rec-standard", "rec-navigated"],
                    help="Reconstruction type: rec-standard or rec-navigated.")
parser.add_argument("wm_mask", help="The white matter mask in which the STD is computed.")
args = parser.parse_args()

# Define arguments
path_processed_data = args.path_processed_data
subject = args.subject_id
session = args.session_id
acq = args.acquisition_region
rec = args.rec
wm_mask = args.wm_mask

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

def write_csv(path_processed_data, subject, session, acq, rec, max_std='nan', mean_std='nan'):
     # Create or update the CSV file
    csv_path = os.path.join(path_processed_data, "..", "results", "wm_std.csv")

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
                                'max_standard': parts[1],
                                'max_navigated': parts[2], 
                                'mean_standard': parts[3],
                                'mean_navigated': parts[4]
                            }

    # Update data for current subject/session/acq
    subject_session_acq = f"{subject}/{session}/{acq}"
    if subject_session_acq not in existing_data:
        existing_data[subject_session_acq] = {
            'max_standard': 'nan',
            'max_navigated': 'nan',
            'mean_standard': 'nan', 
            'mean_navigated': 'nan'
        }

    # Update with current measurements
    if rec == "rec-standard":
        existing_data[subject_session_acq]['max_standard'] = max_std
        existing_data[subject_session_acq]['mean_standard'] = mean_std
    else:  # rec == "rec-navigated"
        existing_data[subject_session_acq]['max_navigated'] = max_std
        existing_data[subject_session_acq]['mean_navigated'] = mean_std

    # Write the complete file
    with open(csv_path, 'w') as f:
        # Write header
        f.write("Subject-ID/Session-ID/Acquisition,max rec-standard,max rec-navigated,mean rec-standard,mean rec-navigated\n")
        # Write data
        for sub_ses_acq, data in existing_data.items():
            max_std = format_value(data['max_standard'])
            max_nav = format_value(data['max_navigated'])
            mean_std = format_value(data['mean_standard'])
            mean_nav = format_value(data['mean_navigated'])
            
            f.write(f"{sub_ses_acq},{max_std},{max_nav},{mean_std},{mean_nav}\n")

def main():
    # Define file names
    file_anat = f"{subject}_{session}_{acq}_{rec}_{contrast}"
    file_wm_mask = wm_mask

    # Define paths
    path_sub_session = os.path.join(path_processed_data, subject, session, "anat")
    path_anat = os.path.join(path_sub_session, file_anat + ext)
    path_wm_mask = os.path.join(path_sub_session, file_wm_mask + ext)

    # Load the nifti files
    mask_nii = nib.load(path_wm_mask)
    mask_data = mask_nii.get_fdata()
    anat_nii = nib.load(path_anat)
    anat_data = anat_nii.get_fdata()

    # Mask the anatomical data
    # This will keep only the data inside the WM mask
    anat_masked = np.ma.masked_array(anat_data, mask=(mask_data == 0))

    # Compute slice-wise standard deviation
    nslices = anat_data.shape[2] 
    slice_wise_std = np.zeros(nslices)
    for z in range(nslices):
        slice_wise_std[z] = np.ma.std(anat_masked[:, :, z])

    # Compute max and mean STDs
    max_std = np.nanmax(slice_wise_std)
    mean_std = np.nanmean(slice_wise_std)

    # Write the results to the CSV file
    write_csv(path_processed_data, subject, session, acq, rec, max_std, mean_std)


if __name__ == "__main__":
    main()
