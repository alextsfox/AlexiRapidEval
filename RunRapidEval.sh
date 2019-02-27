#!/usr/bin/bash

# Path to the data file downloaded from fluxnet
flux_file=US-UMd.csv

# Directory containing ALEXI/ET data files
et_dir=ALEXI_DATA

# the prefix for the ET files. 
# example, global data files are named EDAY_CERES_yyyyddd, so the prefix would be 'EDAY_CERES'
et_prefix=EDAY_CERES

# Directory you would like the results output to
out_dir=results
mkdir -p $out_dir/fig


# ET box size, in pixels
boxY=3
boxX=3

# Year to compare
year=2014

# Variables to pull from flux data file. 
# Usage: (<var1> <var2> <var3>...)
vars=(TA_F RECO_NT_VUT_25)

# Fluxnet site ID to compare
site1=US-UMd

python3 AverageET.py \
$et_dir/$et_prefix \
$flux_file $out_dir \
-y $year \
-by $boxY \
-bx $boxX \
-s $site1 \
-vars ${vars[*]} \
-f -g --verbose

