#!/usr/bin/bash

# Path to the data file downloaded from fluxnet
flux_file=FLX_US-UMd_FLUXNET2015_SUBSET_DD_2007-2014_1-3.csv

# Directory containing ALEXI/ET data files
et_dir=ALEXI_DATA

# the prefix for the ET files. 
# example, global data files are named EDAY_CERES_yyyyddd, so the prefix would be 'EDAY_CERES'
et_prefix=EDAY_CERES

# Directory you would like the results output to
out_dir=Results

# ET box size, in pixels
boxY=3
boxX=3

# Year to compare
year=2014

# Fluxnet site ID to compare
site1=US-UMd

python3 AverageET.py $et_dir/$et_prefix $flux_file $out_dir -y $year -by $boxY -bx $boxX -s $site1 -f -g --verbose

