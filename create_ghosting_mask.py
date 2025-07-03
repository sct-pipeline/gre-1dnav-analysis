#!/usr/bin/env python3
#
# Create a mask for ghosting analysis. The mask is a 1cm-wide rectangle centered on the spinal cord,
# extending from the posterior tip of the tissue to the posterior edge of the axial slice FOV (Field of View).
#
# It requires five arguments:
# 1. path_data: The path to the data directory.
# 2. path_processed_data : The path to the processed data directory (output path). Defaults to path_data if not provided.
# 3. subject_id: The ID of the subject. (e.g., sub-01)
# 4. session_id: The ID of the session. (e.g., ses-01)
# 5. acquisition_region: The region of acquisition, which can be one of the following:
#    - acq-upperT: Upper thoracic region
#    - acq-lowerT: Lower thoracic region
#    - acq-LSE: Lumbar-sacral region
# It will create the following file:
#   /PATH/TO/PROCESSED/DATA/SUB-ID/SES-ID/anat/SUB-ID_SES-ID_ACQ-REGION_rec-navigated_T2starw_ghosting_mask.nii.gz
# 
# How to use:
#   ./create_ghosting_mask.py <path_data> <path_processed_data> <subject_id> <session_id> <acquisition_region>
# 
# Example:
#   ./create_ghosting_mask.py /path/to/data /path/to/processed/data sub-01 ses-01 acq-lowerT
# This will create the following file:
#   /path/to/processed/data/sub-01/ses-01/anat/sub-01_ses-01_acq-lowerT_rec-navigated_T2starw_ghosting_mask.nii.gz

import os
import sys
import numpy as np
import nibabel as nib
import argparse
import subprocess
import json
from datetime import datetime

# Define variables
username = subprocess.run(['whoami'], capture_output=True, text=True).stdout.strip()
sct_version = subprocess.run(['sct_version'], capture_output=True, text=True).stdout.strip()
width_mm = 10  # Width of the mask in millimeters
ext = ".nii.gz"
contrast = "T2starw"

parser = argparse.ArgumentParser(
  description=f"Create a mask for ghosting analysis. The mask is a {int(width_mm/10)}cm-wide rectangle centered\
  on the spinal cord, extending from the posterior tip of the tissue to the posterior edge of the axial slice FOV (Field of View)."
)
parser.add_argument("path_data", help="Path to the data directory.")
parser.add_argument("path_processed_data", nargs='?', default=None, help="Path to the processed data directory (output path). Defaults to path_data if not provided.")
parser.add_argument("subject_id", help="ID of the subject (e.g., sub-01).")
parser.add_argument("session_id", help="ID of the session (e.g., ses-01).")
parser.add_argument("acquisition_region", choices=["acq-upperT", "acq-lowerT", "acq-LSE"], 
                    help="Region of acquisition: acq-upperT, acq-lowerT, or acq-LSE.")
args = parser.parse_args()

# Define arguments
path_data = args.path_data
path_processed_data = args.path_processed_data if args.path_processed_data else path_data
subject = args.subject_id
session = args.session_id
acq = args.acquisition_region

if not os.path.isdir(path_data):
  print(f"Error: Provided path does not exist.\nProvided path: {path_data}")
  sys.exit(1)

# Define functions
def convert_mm_to_pix(mm_value, nii_img, axis=0):
    """Convert a value in millimeters to pixels."""
    pixdim = nii_img.header.get_zooms()[axis]
    return int(round((mm_value) / pixdim))

# Define file names
file_anat = f"{subject}_{session}_{acq}_rec-navigated_{contrast}"
file_seg = f"{file_anat}_seg"
file_body_post_tip = f"{file_anat}_body-posterior-tip"
file_ghosting_mask = f"{file_anat}_ghosting_mask"

# Define paths
path_anat= os.path.join(path_data, subject, session, "anat", file_anat + ext)
path_body_post_tip = os.path.join(path_data, "derivatives", "labels", subject, session, "anat", file_body_post_tip + ext)
path_body_post_tip_csv = os.path.join(path_data, "derivatives", "labels", subject, session, "anat", file_body_post_tip + ".csv")
path_body_post_tip_json = os.path.join(path_data, "derivatives", "labels", subject, session, "anat", file_body_post_tip + ".json")
path_ghosting_mask = os.path.join(path_processed_data, subject, session, "anat", file_ghosting_mask + ext)

# Identify the posterior tip of the body if it does not exist
if not os.path.exists(path_body_post_tip):
  subprocess.run(['sct_get_centerline', '-i', path_anat, '-method', 'viewer', '-gap', '20.0', '-o', path_body_post_tip], text=True, check=True)
# Remove the CSV file if it exists
if os.path.exists(path_body_post_tip_csv):
  os.remove(path_body_post_tip_csv)
# Create the JSON file if it does not exist
if not os.path.exists(path_body_post_tip_json):
  with open(path_body_post_tip_json, 'w') as f:
    json_content = {
      "SpatialReference": "orig",
      "GeneratedBy": [
        {
          "Name": "sct_get_centerline -method viewer",
          "Version": f"SCT {sct_version}"
        },
        {
          "Name": "Manual",
          "Author": username,
          "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
      ]
    }
    json.dump(json_content, f, indent=4)

# Create the ghosting mask
# Loop through each slice along the z-axis
nii_anat = nib.load(path_anat)
data_anat = nii_anat.get_fdata()
nslices = data_anat.shape[2] 
for z in range(nslices):
  # Find the coordinates of the body posterior tip for this slice
  nii_body_post_tip = nib.load(path_body_post_tip)
  data_centreline = nii_body_post_tip.get_fdata()
  body_post_tip_coords = np.argwhere(data_centreline[:, :, z] > 0)
  if body_post_tip_coords.size == 0:
    continue  # No tip found for this slice

  # Define the center of the mask with the tip coordinates
  x_center = int(body_post_tip_coords[0][0])
  # Define the y-axis limit based on the tip coordinates
  y_limit = int(body_post_tip_coords[0][1])

  # Define the size of the mask
  half_width_pix = convert_mm_to_pix(width_mm, nii_anat, axis=0)
  x_start = x_center - half_width_pix
  x_end = x_center + half_width_pix
  y_start = 0
  y_end = y_limit

  # Create the ghosting mask for this slice
  if z == 0:
    ghosting_mask = np.zeros_like(data_anat, dtype=np.uint8)
  ghosting_mask[x_start:x_end, y_start:y_end, z] = 1

# Save the ghosting mask
nii_ghosting_mask = nib.Nifti1Image(ghosting_mask, nii_anat.affine, nii_anat.header)
nib.save(nii_ghosting_mask, path_ghosting_mask)

# Print output path and instructions to view the results
print(f"\nDone! The ghosting mask has been created and saved at:\n{path_ghosting_mask}\n\nTo view results, type:\nfsleyes {path_anat} -cm greyscale {path_ghosting_mask} -cm blue -a 50\n")
