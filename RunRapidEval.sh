#!/usr/bin/bash

flux_file=FLX_US-UMd_FLUXNET2015_SUBSET_DD_2007-2014_1-3.csv

et_dir=ALEXI_DATA
out_dir=Results

boxY=3
boxX=3

year=2014

site1=US-UMd

python3 AverageET.py $et_dir $flux_file $out_dir -y $year -by $boxY -bx $boxX -s $site1 -f -g --verbose

