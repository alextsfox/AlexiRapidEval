#!/usr/bin/bash
# Path to the data file downloaded from fluxnet
flux_dir=.

# Directory containing ALEXI/ET data files
et_dir=ALEXI_DATA

# the prefix for the ET files. 
# example, global data files are named EDAY_CERES_yyyyddd, so the prefix would be 'EDAY_CERES'
et_prefix=EDAY_CERES

# Directory you would like the results output to
out_dir=results

mkdir -p $out_dir/fig
mkdir -p errors

# Raster buffer size in pixels
b=1

# Year range to compare (inclusive)
start_year=2012
end_year=2016

# Variables to pull from flux data file. 
# Usage: (<var1> <var2> <var3>...)
vars=(TA_F RECO_NT_VUT_25)

# Fluxnet site ID to compare
# Usage: (<siteID_1> <siteID_2>...) OR (<siteID_file.txt>)
sites=(sitesToUse.txt)

# ${sites[*]} \
python3 AverageET.py \
$et_dir/$et_prefix \
$flux_dir $out_dir \
-y $start_year $end_year \
-b $b \
-s ${sites[*]} US-UMd-3 \
-vars ${vars[*]} \
-f -g --verbose

echo -e '\033[0m'
