#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Main
    This file is the main file, here all the main functions are called and 
    the workflow is defined
    
    Created on Thu Feb 27 09:24:51 2020
    Authors:    Daniel Laumer (laumerd@ethz.ch)
                Haojun Cai (caihao@ethz.ch)
    
"""

import json
import pandas as pd
import math
from pandas.io.json import json_normalize

# Local files
import help_functions as hlp
#import noiserm_functions as nrm

dataPathLocs = '../Takeout/Location History/Location History.json'

locs = hlp.parseLocs(dataPathLocs)

dataPathTrips = '../Takeout/Location History/Semantic Location History/'

trips, tripdf = hlp.parseTrips(dataPathTrips)

tripdf['startLat'] = ''
tripdf['startLon'] = ''
tripdf['endLat'] = ''
tripdf['endLon'] = ''

startLoc = tripdf['startLocation']
for i in range(0,len(startLoc)):
    if(type(startLoc[i]) == dict):
        tripdf['startLat'].iloc[i] = startLoc[i].get('latitudeE7')
        tripdf['startLon'].iloc[i] = startLoc[i].get('longitudeE7')
        print(i)

endLoc = tripdf['endLocation']
for i in range(0,len(endLoc)):
    if(type(endLoc[i]) == dict):
        tripdf['endLat'].iloc[i] = endLoc[i].get('latitudeE7')
        tripdf['endLon'].iloc[i] = endLoc[i].get('longitudeE7')
        print(i)
    
#flag = tripdf['startLat']
        


    