#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Help Functions
    This file holds all the small helper functions or inventory functions.
    
    Created on Thu Feb 27 09:20:41 2020
    Authors:    Daniel Laumer (laumerd@ethz.ch)
                Haojun Cai (caihao@ethz.ch)
    
"""

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
    df.drop(['timestampMs'], axis=1, inplace=True)
    return df

def parseTrips(dataPath):
    with open(dataPath) as f:
        data = json.load(f)
    f.close()
    df = json_normalize(data, 'locations')
    df['datetime'] = pd.to_datetime(df['timestampMs'],  unit='ms')
    df = df.set_index('datetime')
    df.drop(['timestampMs'], axis=1, inplace=True)
    return df
