# ALEXI Rapid Eval Tool Beta

This is a draft package of the alexi rapid eval tool. To use the tool, run the bash script RunRapidEval.sh 

The tool is written in python 3.6.6, and has the following python dependencies:

    gdal
    pandas
    numpy
    matplotlib

**Instructions**

* In order to run, the tool needs to know where the daily ALEXI data files are, as well as a file prefix to identify them. Open the RunRapidEval.sh bash file and input the filepath to the data files where the variable "etdir" is declared.
    * Example: The prefix for the global dataset CERES_EDAY_yyyyddd would be CERES_EDAY
    
* Extracts daily timeseries of modeled and observed daily ET at a user-selected set of flux tower sites. The tool assumes that flux and ET data is stored locally.
    * Flux data files are assumed to follow the naming convention <SITE_ID>.csv, but otherwise unchanged compared to those downloaded from the official Fluxnet site.

* User can specify a range of years, a box size to pull ET data from, and a collection of fluxnet data sites.

* Outputs a CSV file and an optional figure containing ET and flux timeseries data. 

**Input Options**
The python file AverageET can take a number of input options. Append them to the final line of the bash file to use them. 

For a full list of different input arguments, run the following command:

        python3 AverageET.py -h
        
Recommended optional arguments:

    -g to generate quick-look graphs of your output data
    -v for more detailed command line output and error messages
    
*Further Questions?*   Check out the wiki: https://github.com/alextsfox/AlexiRapidEval/wiki
        
         

