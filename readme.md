# ALEXI Rapid Eval Tool Alpha

This is a draft package of the alexi rapid eval tool. To use the tool, run the bash script RunRapidEval.sh 

The tool is written in python 3.6.6, and has the following dependencies:

      gdal
	pandas
	numpy
	matplotlib

**Instructions**

* In order to run, the tool needs to know where the daily ALEXI data files are. Open the RunRapidEval.sh bash file and input the filepath to the data files where the variable "etdir" is declared.

* Extracts daily timeseries of modeled and observed daily ET at user-selected set of flux sites. Assumes that flux and ET data is stored locally.

* Should work with both CONUS/global domains, but I've only been able to test it with global data.

* Right now, only works with fluxnet 2015 data in the same format as the attached file

* User can specify the year, the box size for the ET timeseries, and provide a collection of fluxnet data sites, given by site_ID (but only if those sites are in the Fluxnet_site_list csv file)

* Outputs a CSV file and an optional figure containing ET and flux timeseries data. Right now, it compares ET values with the dummy variable "TA_F," so there isn't any meaningful output yet.

**Input Options**
The python file AverageET can take a number of input options. Append them to the final line of the bash file to use them View them with:
        python3 AverageET.py -h
        
Recommended options:
        -g to generate quick-look graphs of your output data:
        -v for more detailed command line output and error messages
        
         

