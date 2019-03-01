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

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

# given a lat/lon and a geotransform, extract the yx coordinates of the location
def getYXValsFromLatLon(gt, lat, lon, counter):
	# gt: geotransform, 6-tuple
	# lat: float
	# lon: float
	# counter: int, used only for verbose output

	#note that gt[5], the YRes, is a negative value. That's why this works the same as finding x
	x = (lon - gt[0])//gt[1]
	y = (lat - gt[3])//gt[5]

	if args.verbose and counter == 0:
		print()
		print('Site at coordinates {red}{coords}{end} is located at point {red}x={x}, y={x}{end} in the image'.format(coords=(lat,lon), x=int(x), y=int(y),red=color.DARKCYAN,end=color.END))
		print()

	# returns (y,x) because data comes as x=lon, y=lat, and we use lat/lon not lon/lat
	return int(y), int(x)

# checks to see if a given set of coordinates is within the bounds of a raster file
def inRaster(raster, gt, coords):
	# raster: raster data object
	# gt: geotransform, 6-tuple
	# coords: (lat, lon)

	Rlon = gt[0] + (raster.RasterXSize * gt[1])
	Llat = gt[3] + (raster.RasterYSize * gt[5])
	UR, LL = np.array([gt[3], Rlon]), np.array([Llat, gt[0]])

	# Returns False if the input coordinates are Nort or East of the Upper Right Corner
	# Returns False if the input coordinate are South or West of the Lower Left Corner
	if not np.all(UR > coords):
		return False
	elif not np.all(LL < coords):
		return False
	else:
		return True

# given a raster, restricts it to a box centered around a certain pixel.
# for even sized boxes, snaps to the left.
def restrictToBox(raster, siteY, siteX, buff, flip, counter):
	# raster: raster data object
	# siteY, siteX: ints
	# buff: int
	# flip = bool
	# counter: int, used only for verbose output

	# flips the image if necessary
	if flip:
		rasterArray = np.flip(raster.ReadAsArray(),axis=0)

	# adds buffer pixels around the target site
	rasterArray = rasterArray[siteY - buff : siteY + buff + 1,
							  siteX - buff : siteX + buff + 1]		    		  

	rasterArray[rasterArray == -9999] = np.nan

	if args.verbose and counter == 0:
		U  = siteY + buff
		Le = siteX - buff
		Lo = siteY - buff
		R  = siteX + buff

		print()
		print('Restricted to box with corners (formatted as (x,y)) at: \n {dc}UL = ({Le},{U}), UR = ({R},{U}) \n LL = ({Le},{Lo}), LR = ({R},{Lo}){end}'.format(U=U,Le=Le,Lo=Lo,R=R,dc=color.DARKCYAN,end=color.END))
		print()
		print('Sub-raster to pull from:\n', color.DARKCYAN, rasterArray, color.END)

	# returns a 2d array of the raster, cropped around the buffer pixels
	return rasterArray

# given a site_ID and year, returns a daily list of variable values to plot
def getFluxData(site_ID, years, *fluxVars):
	# site_ID: string
	# years: tuple of ints
	# fluxVars: strings representing variable names

	# yyyymmdd


	# retrieves the the daily fluxnet2015 data file at the specified site ID
	path     = os.path.join(args.fluxDir, '{}.csv'.format(site_ID))
	fileName = glob.glob(path)

	try:
		fileName = fileName[0]

	# if no file is found, return an empty dataframe of the correct size
	except IndexError as err:

		print('{red}WARNING: Could not find file {}, skipping flux data collection for this site{end}'.format(path,red=color.RED,end=color.END))
		FluxDict        = {}
		FluxDict['DOY'] = []
		for var in fluxVars:
			FluxDict[var] = []

		for year in years:
			if isleap(year):

				FluxDict['DOY'] = FluxDict['DOY'] + [d for d in range(1,367)]
				for var in fluxVars:
					FluxDict[var] = FluxDict[var] + [np.nan for d in range(1,367)]

			else:

				FluxDict['DOY'] = FluxDict['DOY'] + [d for d in range(1,366)]
				for var in fluxVars:
					FluxDict[var] = FluxDict[var] + [np.nan for d in range(1,366)]

			numDays = len(FluxDict['DOY'])
			FluxDict['DOY'] = [day for day in range(1,numDays+1)]

		FluxData = pd.DataFrame.from_dict(FluxDict)
		FluxData = FluxData.set_index('DOY')
		FluxData = FluxData.reindex(columns=[var for var in fluxVars])
		
		return FluxData

	if args.verbose:

			print()
			print('\nFound Flux data file: ', color.DARKCYAN, fileName.split('/')[-1], color.END)

			# January 1 of year 1 to Dec. 31 of the final year (inclusive)
			startDate = int('{:04d}{:04d}'.format(years[0],101))
			endDate   = int('{:04d}{:04d}'.format(years[-1]+1,101))
			
			# read a csv file with flux data
			# access the timestamp column and the needed variables columns
			# reindex by the timestamp column
			# crop to the dates we need
			# reindex again, but by DOY for consistancy with other dataframes used in script
			FluxData = (pd.read_csv(fileName)
						  .loc[:,['TIMESTAMP',*fluxVars]]
						  .set_index('TIMESTAMP')
						  .loc[startDate:endDate])

			# to account for leap year, set the DOY column to the length of data pulled from 1/1 to 12/31
			FluxData['DOY'] = range(1,len(FluxData.index)+1)

			FluxData = FluxData.set_index('DOY')

			FluxData[FluxData == -9999] = np.nan
			
			# returns a dataframe of the data from the Flux File
			return FluxData

		

	

# a pretty progress bar
def update_progress(progress):
	# progress: float/int

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

	# loop through locations
	for i in range(len(LOCS)):

		if args.verbose:
			print()
			print('\n\n{}Now processing site {}{}'.format(color.BOLD ,SITE_IDS[i], color.END))
			print('~~~~~~~~~~~~~~~~~~~~~~~~')
		
		# used for giving specific verbose output options
		errorMessages = []
		counter       = 0
		hdrWarn       = 0
		notFound      = 0
		outOfRaster   = 0

		# for storing data
		vals    = []
		yearCol = []
		doyCol  = []

		for year in years:
			# loop through 366 in case there's a leao year
			for doy in range(1,367):

				# retrieve the ET filepath. Each .dat file has an associated header file.
				date = "%d%03d" % (year, doy)
				filename = '{}_{:04d}{:03d}.dat'.format(args.etPathAndPrefix, year, doy)

				# average ET values within a box
				if os.path.exists(filename):			
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
							counter     += 1
							outOfRaster += 1

					# a nice looking progress bar.	
					update_progress(doy/(366*len(years)))
					
					 
				else:
					vals.append(np.nan)
					if args.verbose:
						if doy == 366:
							errorMessages.append("Error: I couldn't find file {} (this may be because {} is not a leap year)".format(filename, year))
						else:
							errorMessages.append("Error: I couldn't find file {}".format(filename))
						notFound += 1

				# generate the year, doy
				if doy != 366:
					yearCol.append(year)
					doyCol.append(doy)
				elif doy == 366 and isleap(year):
					yearCol.append(year)
					doyCol.append(doy)

		# generates an error log
		errorFile = open('errors/{}_{}_Errors.txt'.format(time(),SITE_IDS[i]), 'w')
		for error in errorMessages:
			errorFile.write(error)
		print('\n')
		print('{red}{} errors were encountered when processing raster data:'.format(len(errorMessages),red=color.RED))
		print('    {} missing .hdr files'.format(hdrWarn))
		print('    {} raster files could not be found'.format(notFound))
		print('    {} locations were not within the bounds of the raster files'.format(outOfRaster))
		print('Saved output log to errors/{}_{}_Errors.txt{end}'.format(time(),SITE_IDS[i], end=color.END))
		
		# create a pandas dataframe of the averaged ET values over time, print to CSV
		
		ETdct  = {'DOY': range(1,len(vals)+1), 'ET': vals}
		ETData = pd.DataFrame.from_dict(ETdct)
		#ETData = ETData.set_index('DOY')
		
		# get a pandas dataframe of the needed fluxtower variable data

		fluxData = getFluxData(SITE_IDS[i], years, *fluxVars)

		# dataframe comparing ALEXI and Fluxtower data
		ET_and_Flux_Compared = pd.DataFrame()
		ET_and_Flux_Compared['Year'] = yearCol
		ET_and_Flux_Compared['DOY']  = doyCol
		ET_and_Flux_Compared['ET']   = ETData['ET']
		for var in fluxVars:
			ET_and_Flux_Compared[var] = fluxData[var]

		# save to csv
		ET_and_Flux_Compared = ET_and_Flux_Compared.fillna(-9999).astype(int)
		ET_and_Flux_Compared.to_csv(os.path.join(args.outPath,'{0}_{1}px.csv'.format(SITE_IDS[i], args.buff)), index=False)
		if args.verbose:
			print("\n{green}File {} saved successfully{end}".format(os.path.join(args.outPath,'{0}_{1}px.csv'.format(SITE_IDS[i],args.buff)),green=color.GREEN,end=color.END))

		# generate figures
		if args.genFigs:

			figPath = os.path.join(args.outPath, 'fig')

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
				print("{green}Figure {} saved successfully{end}".format(os.path.join(figPath,'{0}_{1}px.png'.format(SITE_IDS[i], args.buff)),green=color.GREEN,end=color.END))

if __name__ == '__main__':

	#parsing arguments
	p = argparse.ArgumentParser()
	p.add_argument("etPathAndPrefix", help="Directory containing ET data files and their associated header files. Files must end in yyyyddd format.")
	p.add_argument("fluxDir", help="Directory containing flux data")
	p.add_argument("outPath", help="Directory to output files to. By default creates a subdirectory in the working directory.")

	p.add_argument("-b", "--buff", type=int, help="Buffer, in number of pixels. Default 0.")
	p.add_argument("-f", "--flip", action="store_true", help="If the image data is upside down, this option flips the image when performing computations.\n ")
	p.add_argument("-g", "--genFigs", action="store_true", help="Program will save figures to output directory\n ")
	p.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
	
	req = p.add_argument_group('Named required arguments')
	req.add_argument("-y", "--years", required=True, nargs='+', type=int, help="Year range (inclusive). Usage: <start_year> <end_year>")
	req.add_argument("-vars", "--variables", required=True, nargs='+', help='Variable names to load from flux data files. Usage: <var1> <var2>...')
	req.add_argument("-s", "--sites", required=True, nargs='+', help="Fluxnet Site IDs to evaluate, in a .txt file line-by-line, OR directly in the command line, separated by spaces. Usage: <siteFile.txt> OR <site1> <site2>... OR  a combination of both")

	# mutex = p.add_argument_group('At least one of the following must be used:')
	# req.add_argument("-sf", "--sites", help="Fluxnet Site IDs to evaluate, stored line-by-lin in a text file.")
	# req.add_argument("-sl", "--sites", nargs='+', help="Fluxnet Site IDs to evaluate, separated by spaces. Usage: list of sites <site1> <site2>... ")
	
	args = p.parse_args()

	if not os.path.exists(args.outPath):
		os.makedirs(args.outPath)
		print(args.outPath)

	# sets buffer to zero by default
	if args.buff is None:
		args.buff = 0

	FLIP = False
	if args.flip:
		FLIP = True
	if args.verbose:
		if FLIP:
			print('\nFlipping images...')
		else:
			print("\nWill not be flipping images...")

	fluxVars = args.variables

	# list of years
	years = [i for i in range(args.years[0], args.years[1]+1)]

	sitesToUse = []
	for siteName in args.sites:
		try:
			sitesFromFile = open(siteName, 'r')
			sitesFromFile = sitesFromFile.readlines()

			# removing \n character
			for i in range(len(sitesFromFile)):
				if sitesFromFile[i][-1] == '\n':
					sitesFromFile[i] = sitesFromFile[i][:-1]

				sitesToUse.append(sitesFromFile[i])

		except FileNotFoundError as err:
			sitesToUse.append(siteName)

	# retrieve list of fluxnet sites, filter out the ones we need
	SITELIST_FILENAME = 'Fluxnet_site_list.csv'
	sitesDF       = pd.read_csv(SITELIST_FILENAME)
	sitesDF.index = sitesDF['SITE_ID']
	sitesDF       = sitesDF.loc[sitesToUse]
	sitesDF.index = range(len(sitesDF.index))
	sitesDF       = sitesDF.reindex(columns=['SITE_ID','SITE_NAME','LOCATION_LAT','LOCATION_LONG'])
	
	if args.verbose:
		print('\nUsing the following variables:\n {}{}{}'.format(color.DARKCYAN, '   '.join(fluxVars), color.END))
		print('\n'+color.DARKCYAN,sitesDF,color.END+'\n')

	# works with either version of pandas, using either depricated .values or the newer .to_numpy()
	try:
		sitesDF = sitesDF.to_numpy()
	except AttributeError as err:
		sitesDF = sitesDF.values
	

	SITE_IDS = sitesDF[:,0]
	SITE_NAMES = sitesDF[:,1]
	LOCS = sitesDF[:,2:4]
	
	main()






