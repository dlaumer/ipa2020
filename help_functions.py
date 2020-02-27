#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Help Functions
    This file holds all the small helper functions or inventory functions.
    
    Created on Thu Feb 27 09:20:41 2020
    Authors:    Daniel Laumer (laumerd@ethz.ch)
                Haojun Cai (caihao@ethz.ch)
    
"""

import os
import json
import pandas as pd
from pandas.io.json import json_normalize  


def parseLocs(dataPath):
    with open(dataPath) as f:
        data = json.load(f)
    f.close()
    df = json_normalize(data, 'locations')
    df['datetime'] = pd.to_datetime(df['timestampMs'],  unit='ms')
    df = df.set_index('datetime')
    return df

def parseTrips(dataPath):
    
    allData = {}
    d = []
    dirs = os.listdir(dataPath)
    for year in dirs:
        if year.isdigit():
            dataPathYear = os.path.join(dataPath, year)
            allData[year] = {}
            for root, dirs, files in os.walk(dataPathYear):
                for fil in files:
                    if fil.endswith('.json'):
                        dataPathFile = os.path.join(dataPathYear, fil)
                        with open(dataPathFile) as f:
                            month = fil[5:-5]
                            data = json.load(f)
                            allData[year][month] = data['timelineObjects']
                            for obj in data['timelineObjects']:
                                tempData = {'Year':year, 'Month': month, 'Type':list(obj)[0]}
                                tempData.update(obj[list(obj)[0]])
                                d.append(tempData)
                        f.close()                       
    df = pd.DataFrame(d)
    return allData, df
