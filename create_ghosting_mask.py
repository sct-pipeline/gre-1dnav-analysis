#!/usr/bin/env python3

import os
import sys
import numpy as np
import nibabel as nib
import argparse
import subprocess

parser = argparse.ArgumentParser(
  description="Create a mask for ghosting analysis (2cm-wide band centered on the spinal cord)."
)
parser.add_argument("path_data")
parser.add_argument("subject_id")
parser.add_argument("session_id")
parser.add_argument("acquisition_region", choices=["acq-upperT", "acq-lowerT", "acq-LSE"])
parser.add_argument("smooth_coeff", type=int)
parser.add_argument("bins", type=int)
args = parser.parse_args()

path_data = args.path_data
subject = args.subject_id
session = args.session_id
acq = args.acquisition_region
smooth_coeff = args.smooth_coeff
bins = args.bins

if not os.path.isdir(path_data):
  print(f"Error: Provided path does not exist.\nProvided path: {path_data}")
  sys.exit(1)

# Define functions
def convert_mm_to_pix(mm_value, nii_img, axis=0):
    """Convert a value in millimeters to pixels."""
    pixdim = nii_img.header.get_zooms()[axis]
    return int(round((mm_value) / pixdim))

# Define variables
ext = ".nii.gz"
contrast = "T2starw"

# Define file names
file_standard = f"{subject}_{session}_{acq}_rec-standard_{contrast}"
file_navigated = f"{subject}_{session}_{acq}_rec-navigated_{contrast}"
file_seg = f"{file_navigated}_seg"
file_centerline = f"{file_navigated}_centerline"
file_smoothed = f"{file_navigated}_smoothed{smooth_coeff}"
file_binarized = f"{file_smoothed}_otsu{bins}"
file_ghosting_mask = f"{file_navigated}_ghosting_mask"

# Define paths
path_anat = os.path.join(path_data, subject, session, "anat")
path_derivatives = os.path.join(path_data, "derivatives", "labels", subject, session, "anat")

path_standard = os.path.join(path_anat, file_standard + ext)
path_navigated = os.path.join(path_anat, file_navigated + ext)
path_seg = os.path.join(path_derivatives, file_seg + ext)
path_centerline = os.path.join(path_derivatives, file_centerline + ext)
path_smoothed = os.path.join(path_derivatives, file_smoothed + ext)
path_binarized = os.path.join(path_derivatives, file_binarized + ext)
path_ghosting_mask = os.path.join(path_derivatives, file_ghosting_mask + ext)

# Get the centerline of the spinal cord
subprocess.run(['sct_get_centerline', '-i', path_seg, '-method', 'fitseg', '-extrapolation', '1', '-o', path_centerline], text=True, check=True)

# Create the binarized mask
subprocess.run(['sct_maths', '-i', path_navigated, '-smooth', f'{smooth_coeff},{smooth_coeff},{smooth_coeff}', '-o', path_smoothed], text=True, check=True)
subprocess.run(['sct_maths', '-i', path_smoothed, '-otsu', str(bins), '-o', path_binarized], text=True, check=True)

# Create the ghosting mask
# Loop through each slice along the z-axis
nii_binarized = nib.load(path_binarized)
data_binarized = nii_binarized.get_fdata()
nslices = data_binarized.shape[2] 
for z in range(nslices):
  # Find the coordinates of the centerline for this slice
  nii_centerline = nib.load(path_centerline)
  data_centreline = nii_centerline.get_fdata()
  centerline_coords = np.argwhere(data_centreline[:, :, z] > 0)
  if centerline_coords.size == 0:
    continue  # No centerline found for this slice

  # Define the center of the mask with the centerline coordinates
  x_center = int(centerline_coords[0][0])

  # Find the posterior limit of the body in this slice
  slice_bin = data_binarized[:, :, z]
  y_posterior = np.min(np.argwhere(slice_bin[x_center, :])) if np.any(slice_bin > 0) else 0
  # Add an extension to the posterior limit
  posterior_extension_pix = convert_mm_to_pix(2, nii_binarized, axis=1)
  y_limit = y_posterior - posterior_extension_pix

  # Define the size of the mask
  half_width_pix = convert_mm_to_pix(10, nii_binarized, axis=0)
  x_start = x_center - half_width_pix
  x_end = x_center + half_width_pix
  y_start = 0
  y_end = y_limit

  # Create the ghosting mask for this slice
  if z == 0:
    ghosting_mask = np.zeros_like(data_binarized, dtype=np.uint8)
  ghosting_mask[x_start:x_end, y_start:y_end, z] = 1

# Save the ghosting mask
nii_ghosting_mask = nib.Nifti1Image(ghosting_mask, nii_binarized.affine, nii_binarized.header)
nib.save(nii_ghosting_mask, path_ghosting_mask)
