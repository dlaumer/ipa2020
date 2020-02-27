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
from pandas.io.json import json_normalize

# Local files
import help_functions as hlp
#import noiserm_functions as nrm

dataPathLocs = '../Takeout/Location History/Location History.json'

locs = hlp.parseLocs(dataPathLocs)

dataPathTrips = '../Takeout/Location History/Semantic Location History'

trips = hlp.parseTrips(dataPathTrips)

#locsFiltered = nrm（locs)



