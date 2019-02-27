#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
@author: Alex.Fox
'''

from __future__ import print_function
from __future__ import division

import os
import glob
import argparse
import gdal
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from calendar import isleap
from time import time
import sys

# import matplotlib.animation as anim

# gt: geotransform, formatted as (ULLon, X Pixel Res (deg), ULX, ULLat, ULY, Y Pixel Res (deg))
def getYXValsFromLatLon(gt, lat, lon, counter):
	# gt = geotransform, 6-tuple
	# lat = float
	# lon = float
	# counter = int, used only for verbose output

	x = (lon - gt[0])//gt[1]

	#note that gt[5], the YRes, is a negative value. That's why this works the same as finding x
	y = (lat - gt[3])//gt[5]

	# returns x,y because data comes as x=lon, y=lat, and we use lat/lon not lon/lat

	if args.verbose and counter == 0:
		print('~~~~~~~~~~~~~~~')
		print('Site at coordinates {} is located at point x={}, y={} in the image'.format((lat,lon), int(x), int(y)))
		print()

	return int(y), int(x)

# given a tile #, returns the LLLat/LLLon association with that tile
def tile2LatLon(tile):
	# tile = int

	row = tile//24
	col = tile - (row*24)
	lat = (75. - row*15.) - 15.
	lon = (col*15. - 180.) - 15.
	return lat, lon

# checks to see if a given set of coordinates is within the bounds of a raster file
def inRaster(raster, gt, coords):
	# raster = raster data
	# gt = geotransform, 6-tuple
	# coords = [lat, lon]

	Rlon = gt[0] + (raster.RasterXSize * gt[1])
	Llat = gt[3] + (raster.RasterYSize * gt[5])
	UR, LL = np.array([gt[3], Rlon]), np.array([Llat, gt[0]])
	if not np.all(UR > coords):
		return False
	elif not np.all(LL < coords):
		return False
	else:
		return True

# given a raster, restricts it to a box centered around a certain pixel.
# for even sized boxes, snaps to the left.
def restrictToBox(raster, siteY, siteX, buff, flip, counter):
	# raster = raster data
	# siteY, siteX, boxY, boxX = ints
	# flip = bool
	# returns a 2d array
	# counter = int, used only for verbose output

	if flip:
		rasterArray = np.flip(raster.ReadAsArray(),axis=0)

	rasterArray = rasterArray[siteY - buff : siteY + buff + 1,
							  siteX - buff : siteX + buff + 1]

	U =  siteY + buff + 1
	Le = siteX - buff
	Lo = siteY - buff
	R = siteX + buff + 1		    		  

	rasterArray[rasterArray == -9999] = np.nan

	if args.verbose and counter == 0:
		print("~~~~~~~~~~~~~~~")
		print('Restricted to box with corners (formatted as (x,y)) at: \n UL = ({Le},{U}), UR = ({R},{U}) \n LL = ({Le},{Lo}), LR = ({R},{Lo})'.format(U=U,Le=Le,Lo=Lo,R=R))
		print()

	return rasterArray

# given a site_ID and year, returns a daily list of variable values to plot
def getFluxData(site_ID, years, *fluxVars):
	# site_ID = string
	# year = int
	# fluxVars = strings representing variable names
	# returns a pandas dataframe of the fluxnet data for that year at that site of those variables, indexed by doy (365 days)

	# yyyymmdd


	# retrieves the the daily fluxnet2015 data file at the specified site ID
	path = args.Flux_File
	fileName = glob.glob(args.Flux_File)

	fileName = fileName[0]
	if args.verbose:
		print("~~~~~~~~~~~~~~~")
		print('Found Flux data file: ', fileName.split('/')[-1])

	startDate = int('{:04d}{:04d}'.format(years[0],101))
	endDate   = int('{:04d}{:04d}'.format(years[-1],1231))
	
	# read a csv file with flux data
	# access the timestamp column and the needed variables columns
	# reindex by the timestamp column
	# crop to the dates we need
	# reindex again, but by DOY for consistancy with other dataframes used in script
	FluxData = (pd.read_csv(fileName)
				  .loc[:,['TIMESTAMP',*fluxVars]]
				  .set_index('TIMESTAMP')
				  .loc[startDate:endDate])

	# account for leap year, don't set to 365 days, just the length of that year.
	FluxData['DOY'] = range(1,len(FluxData.index)+1)
	FluxData = FluxData.set_index('DOY')

	FluxData[FluxData == -9999] = np.nan
	
	return FluxData
	
def update_progress(progress):
    barLength = 63 # Modify this to change the length of the progress bar
    status = ""
    if isinstance(progress, int):
        progress = float(progress)
    if not isinstance(progress, float):
        progress = 0
        status = "error: progress var must be float\r\n"
    if progress < 0:
        progress = 0
        status = "Halt...\r\n"
    if progress >= 1:
        progress = 1
        status = "Done...\r\n"
    block = int(round(barLength*progress))
    text = "\r[{0}] {1}% {2}".format( "#"*block + "-"*(barLength-block), int(progress*100), status)
    sys.stdout.write(text)
    sys.stdout.flush()

def main():

	for i in range(len(LOCS)):

		if args.verbose:
			print()
			print('\n\nNow processing site {}'.format(SITE_IDS[i]))
		
		# used for giving specific verbose output options
		counter = 0

		vals = []
		errorMessages=[]
		hdrWarn = 0
		notFound = 0
		outOfRaster = 0
		yearCol=[]
		doyCol=[]
		for year in years:
			# in case of leap years
			for doy in range(1,367):

				# retrieve the ET filepath. Each .dat file has an associated header file.
				date = "%d%03d" % (year, doy)
				filename = '{}_{:04d}{:03d}.dat'.format(args.ET_Path, year, doy)

				# average ET values within a box
				if os.path.exists(filename):

					# get geotransform from the raster file and find the YX of the site given lat/lon
					
					# catch missing .hdr files
					gdal.UseExceptions()
					try:
						raster = gdal.Open(filename)
					except RuntimeError as err:
						errorMessages.append('\n !!! WARNING: Missing .hdr file for {}. Could not load image !!!\n'.format(fn))
						hdrWarn += 1

					gt = raster.GetGeoTransform()

					# check to see if the location is in the bounds of the raster, then average ET values inside the box
					if inRaster(raster, gt, LOCS[i]):

						siteYX = getYXValsFromLatLon(gt, *LOCS[i], counter)

						rasterArray = restrictToBox(raster, *siteYX, args.buff, FLIP, counter)
						counter += 1

						meanET = np.nanmean(rasterArray)

						vals.append(meanET)

					# if not in raster, set ET val to np.nan, print a warning
					else:

						vals.append(np.nan)
						if counter == 1:
							errorMessages.append('Error: Site_ID %s at %s is not within the bounds of the raster file.' % (SITE_IDS[i], LOCS[i]))
							counter += 1
							outOfRaster += 1

					# a nice looking progress bar.	
					update_progress(doy/(366*len(years)))

					# will be added to the .csv file
					
					 
				else:
					vals.append(np.nan)
					if args.verbose:
						if doy == 366:
							errorMessages.append("Error: I couldn't find file {} (this may be because {} is not a leap year)".format(filename, year))
						else:
							errorMessages.append("Error: I couldn't find file {}".format(filename))
						notFound += 1
				
				if doy != 366:
					yearCol.append(year)
					doyCol.append(doy)
				if doy == 366 and isleap(year):
					yearCol.append(year)
					doyCol.append(doy)

		# generates an error log
		errorFile = open('errors/{}_{}_Errors.txt'.format(time(),SITE_IDS[i]), 'w')
		for error in errorMessages:
			errorFile.write(error)

		print()
		print()
		print('~~~~~~~~~~~~~~~')
		print('Saved errors/{}_{}_Errors.txt'.format(time(),SITE_IDS[i]))
		print('{} errors were encountered when processing raster data:'.format(len(errorMessages)))
		print('    {} missing .hdr files'.format(hdrWarn))
		print('    {} raster files could not be found'.format(notFound))
		print('    {} locations were not within the bounds of the raster files'.format(outOfRaster))
		print()

		# create a pandas dataframe of the averaged ET values over time, print to CSV
		ETdct = {'DOY': range(1,len(vals)+1), 'ET': vals}
		ETData = pd.DataFrame.from_dict(ETdct)
		#ETData = ETData.set_index('DOY')
		
		# get a pandas dataframe of the needed fluxtower variable data
		fluxData = getFluxData(SITE_IDS[i], years, *fluxVars)

		# dataframe comparing ALEXI and Fluxtower data
		ET_and_Flux_Compared = pd.DataFrame()
		ET_and_Flux_Compared['Year'] = yearCol
		ET_and_Flux_Compared['DOY'] = doyCol
		ET_and_Flux_Compared['ET'] = ETData['ET']
		for var in fluxVars:
			ET_and_Flux_Compared[var] = fluxData[var]

		# save to csv
		ET_and_Flux_Compared = ET_and_Flux_Compared.fillna(-9999).astype(int)
		ET_and_Flux_Compared.to_csv(os.path.join(args.Out_Path,'{0}_{1}px.csv'.format(SITE_IDS[i], args.buff)), index=False)
		if args.verbose:
			print("File {} saved successfully".format(os.path.join(args.Out_Path,'{0}_{1}px.csv'.format(SITE_IDS[i],args.buff))))

		# generage figures
		if args.genfigs:

			figPath = os.path.join(args.Out_Path, 'fig')

			plt.plot(ETData.index ,ETData['ET'], linewidth=2, c=(1,0,0))
			for var in fluxVars:
				plt.scatter(fluxData.index, fluxData[var], s=2)

			plt.xlim(0,len(ETData.index))
			plt.legend()
			plt.xlabel('DOY')
			plt.ylabel('Value')
			plt.title(['{0}_{1}px.png'.format(SITE_IDS[i], args.buff)])
			plt.savefig(os.path.join(figPath,'{0}_{1}px.png'.format(SITE_IDS[i],args.buff)))
			plt.clf()

			if args.verbose:
				print("Figure {} saved successfully".format(os.path.join(figPath,'{0}_{1}px.png'.format(SITE_IDS[i], args.buff))))

if __name__ == '__main__':

	#parsing arguments
	parser = argparse.ArgumentParser()
	parser.add_argument("ET_Path", help="Directory containing ET data files and their associated header files. By default the working directory. Files must end in yyyyddd format.")
	parser.add_argument("Flux_File", help="File containing daily flux tower CSV data")
	parser.add_argument("Out_Path", help="Directory to output files to. By default creates a subdirectory in the working directory.")

	parser.add_argument("-b", "--buff", type=int, help="Buffer, in number of pixels. Default 0.")
	parser.add_argument("-f", "--flip", action="store_true", help="If the image data is upside down, this option flips the image when performing computations.\n ")
	parser.add_argument("-g", "--genfigs", action="store_true", help="Program will save figures to output directory\n ")
	parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
	
	req = parser.add_argument_group('Named required arguments')
	req.add_argument("-y", "--years", required=True, nargs='+', type=int, help="Year range (inclusive). Usage: <start_year> <end_year>")
	req.add_argument("-vars", "--variables", required=True, nargs='+', help='Variable names to load from flux data files. Usage: <var1> <var2>...')
	req.add_argument("-s", "--sites", required=True, nargs='+', help="Fluxnet Site IDs to evaluate, separated by spaces. Usage: list of sites <site1> <site2>... OR a sigle text file containing site IDs <site_list.txt>")
	
	args = parser.parse_args()

	#assigning variables
	if not os.path.exists(args.Out_Path):
		os.makedirs(args.Out_Path)
		print(args.Out_Path)

	if args.buff is None:
		args.buff = 0

	FLIP = False
	if args.flip:
		FLIP = True
	if args.verbose:
		if FLIP:
			print('\nFlipping images...')
		else:
			print("Will not be flipping images...")

	try:
		sitesToUse = open(args.sites, 'r')
		sitesToUse = sitesToUse.readlines()

		# removing \n character
		for i in range(len(sitesToUse)):
			if sitesToUse[-1] == '\n':
				sitesToUse[i] = sitesToUse[:-1]

		print('Opening file {}'.format(args.sites))

	except TypeError as err:
		sitesToUse = [site for site in args.sites]

	print('Looking at sites {}'.format(sitesToUse))

	fluxVars = args.variables

	# list of years
	years = [i for i in range(args.years[0], args.years[1]+1)]

	# retrieve list of fluxnet sites, reindex by site id
	SITELIST_FILENAME = 'Fluxnet_site_list.csv'
	sitesDF = pd.read_csv(SITELIST_FILENAME)
	
	# if given, limit analysis to user specified sites.
	sitesDF = sitesDF.set_index('SITE_ID')
	if args.sites is not None:	
		sitesDF = sitesDF.loc[args.sites]#sitesDF = sitesDF[sitesDF['SITE_ID'].str.match(site)]
	sitesDF = sitesDF.reset_index()

	if args.verbose:
		print('Using variables {}...'.format(fluxVars))
		print('\n',sitesDF,'\n')

	# works with either version of pandas, using either depricated .values or the newer .to_numpy()
	try:
		sitesDF = sitesDF.to_numpy()
	except AttributeError as err:
		sitesDF = sitesDF.values

	SITE_IDS = sitesDF[:,0]
	LOCS = sitesDF[:,2:4]
	SITE_NAMES = sitesDF[:,1]

	main()






