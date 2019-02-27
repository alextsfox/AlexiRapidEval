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
def restrictToBox(raster, siteY, siteX, boxY, boxX, flip, counter):
	# raster = raster data
	# siteY, siteX, boxY, boxX = ints
	# flip = bool
	# returns a 2d array
	# counter = int, used only for verbose output

	if flip:
		rasterArray = np.flip(raster.ReadAsArray(),axis=0)



	rasterArray = rasterArray[siteY - boxY//2 : siteY + boxY - boxY//2,
				    		  siteX - boxX//2 : siteX + boxX - boxX//2]

	rasterArray[rasterArray == -9999] = np.nan

	if args.verbose and counter == 0:
		print("~~~~~~~~~~~~~~~")
		print('Restricted to box with corners (formatted as (x,y)) at: \n UL = {}, UR = {} \n LL = {}, LR = {}'.format((siteY + boxY - boxY//2 - 1, siteX - boxX//2),
																								 (siteY + boxY - boxY//2 - 1, siteX + boxX - boxX//2 - 1),
																								 (siteY - boxY//2, siteX - boxX//2),
																								 (siteY - boxY//2, siteX + boxX - boxX//2 - 1)
																								 )
			 )
		print()

	return rasterArray

# given a site_ID and year, returns a daily list of variable values to plot
def getFluxData(site_ID, year, *fluxVars):
	# site_ID = string
	# year = int
	# fluxVars = strings representing variable names
	# returns a pandas dataframe of the fluxnet data for that year at that site of those variables, indexed by doy (365 days)

	# yyyymmdd


	# retrieves the the daily fluxnet2015 data file at the specified site ID
	path = args.Flux_File
	fileName = glob.glob(args.Flux_File)

	print(fileName)
	fileName = fileName[0]
	if args.verbose:
		print("~~~~~~~~~~~~~~~")
		print('Found Flux data file: ', fileName.split('/')[-1])

	startDate = int('{:04d}{:04d}'.format(year,101))
	endDate   = int('{:04d}{:04d}'.format(year,1231))
	
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
	FluxData['DOY'] = range(len(FluxData.index))
	FluxData = FluxData.set_index('DOY')

	FluxData[FluxData == -9999] = np.nan

	if args.verbose:
		print("~~~~~~~~~~~~~~~")
		print('Flux Data (first 15 entries)')
		print(FluxData[:15])
	
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

		for doy in range(1,366):

			# retrieve the ET filepath. Each .dat file has an associated header file.
			date = "%d%03d" % (year, doy)
			#et_path = os.path.join(args.ET_Path)#'ALEXI_DATA')#/Users/waldinian/Documents/Data/4rodnei/DAILY_EDAY_TERRA') ((
			filename = '{}_{:04d}{:03d}.dat'.format(args.ET_Path, year, doy)#os.path.join(et_path, '_%d%03d.dat' % (year,doy))

			# average ET values within a box
			if os.path.exists(filename):

				# get geotransform from the raster file and find the YX of the site given lat/lon
				raster = gdal.Open(filename)
				gt = raster.GetGeoTransform()

				# check to see if the location is in the bounds of the raster, then average ET values inside the box
				if inRaster(raster, gt, LOCS[i]):

					siteYX = getYXValsFromLatLon(gt, *LOCS[i], counter)

					rasterArray = restrictToBox(raster, *siteYX, *boxYX, FLIP, counter)
					counter += 1

					meanET = np.nanmean(rasterArray)

					vals.append(meanET)

				# if not in raster, set ET val to np.nan, print a warning
				else:

					vals.append(np.nan)
					if counter == 1:

						print('Site_ID %s at %s is not within the bounds of the raster file.' % (SITE_IDS[i], LOCS[i]))
						counter += 1

				# a nice looking progress bar.	
				update_progress(doy/365)
				 
			else:

				vals.append(np.nan)
				if args.verbose:
					print("I couldn't find file {}".format(filename))	

		# create a pandas dataframe of the averaged ET values over time, print to CSV
		ETdct = {'DOY': range(1,366), 'ET': vals}
		ETData = pd.DataFrame.from_dict(ETdct)
		ETData = ETData.set_index('DOY')
		
		# get a pandas dataframe of the needed fluxtower variable data
		fluxData = getFluxData(SITE_IDS[i], year, *fluxVars)

		# dataframe comparing ALEXI and Fluxtower data
		ET_and_Flux_Compared = pd.DataFrame()
		ET_and_Flux_Compared['ET'] = ETData['ET']
		for var in fluxVars:
			ET_and_Flux_Compared[var] = fluxData[var]

		# save to csv
		ET_and_Flux_Compared.to_csv(os.path.join(args.Out_Path,'{0}{1}_{2}x{3}.csv'.format(SITE_IDS[i], year, *boxYX)))
		if args.verbose:
			print("File {} saved successfully".format(os.path.join(args.Out_Path,'{0}{1}_{2}x{3}.csv'.format(SITE_IDS[i], year, *boxYX))))

		# generage figures
		if args.genfigs:

			if not os.path.exists(os.path.join(args.Out_Path, 'fig')):
				figPath = os.path.join(args.Out_Path, 'fig')
				os.makedirs(figPath)
			figPath = os.path.join(args.Out_Path, 'fig')

			plt.scatter(ETData.index ,ETData['ET'],s=2)
			for var in fluxVars:
				plt.scatter(fluxData.index, fluxData[var], s=2)

			plt.xlim(0,366)
			plt.legend()
			plt.title(['{0}_{1}_{2}x{3}.png'.format(SITE_NAMES[i], year, *boxYX)])
			plt.savefig(os.path.join(figPath,'{0}_{1}_{2}x{3}.png'.format(SITE_IDS[i], year, *boxYX)))
			plt.clf()

			if args.verbose:
				print("Figure {} saved successfully".format(os.path.join(figPath,'{0}_{1}_{2}x{3}.png'.format(SITE_IDS[i], year, *boxYX))))

if __name__ == '__main__':

	#parsing arguments
	parser = argparse.ArgumentParser()
	parser.add_argument("ET_Path", help="Directory containing ET data files and their associated header files. By default the working directory. Files must end in yyyyddd format.")
	parser.add_argument("Flux_File", help="File containing daily flux tower CSV data")
	parser.add_argument("Out_Path", help="Directory to output files to. By default creates a subdirectory in the working directory.")

	parser.add_argument("-s", "--sites", nargs='*', help="Fluxnet Site IDs to evaluate, separated by spaces. By default evaluates at all site locations on file.")
	parser.add_argument("-y", "--year", type=int, help="Year, default 2015.")
	parser.add_argument("-by", "--ysize", type=int, help="Y dimension of box in pixels, default 1.\n ")
	parser.add_argument("-bx", "--xsize", type=int, help="Y dimension of box in pixels, default 1.\n ")
	parser.add_argument("-f", "--flip", action="store_true", help="If the image data is upside down, this option flips the image when performing computations.\n ")
	parser.add_argument("-g", "--genfigs", action="store_true", help="Program will save figures to output directory\n ")
	parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
	args = parser.parse_args()

	#assigning variables
	if not os.path.exists(args.Out_Path):
		os.makedirs(args.Out_Path)
		print(args.Out_Path)
	
	year = 2015
	if args.year is not None:
		year = args.year
	elif args.verbose:
		print("Setting year to default...")
	boxYX = [1,1]
	if args.ysize is not None:
		boxYX[0] = args.ysize
	elif args.verbose:
		print("Setting box y size to default...")
	if args.xsize is not None:
		boxYX[1] = args.xsize
	elif args.verbose:
		print("Setting box x size to default...")
	boxYX = (boxYX[0],boxYX[1])

	FLIP = False
	if args.flip:
		FLIP = True
	if args.verbose:
		if FLIP:
			print('\nFlipping images...')
		else:
			print("Will not be flipping images...")

	fluxVars = ('TA_F',)

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

	try:
		sitesDF = sitesDF.to_numpy()
	except AttributeError as err:
		sitesDF = sitesDF.values

	SITE_IDS = sitesDF[:,0]
	LOCS = sitesDF[:,2:4]
	SITE_NAMES = sitesDF[:,1]

	main()






