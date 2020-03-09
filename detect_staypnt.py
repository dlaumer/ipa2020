# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 11:44:35 2020

Authors:    Haojun Cai (caihao@ethz.ch)
            Daniel Laumer (laumerd@ethz.ch)
"""

#%%
import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt
import matplotlib.pyplot as plt
import plotly.express as px
from haversine import haversine, Unit

# Local files
import help_functions as hlp

# Read data
dataPathLocs = '../Takeout_Lauro_Mar/Standortverlauf/Standortverlauf.json'
dataPathTrips = '../Takeout_Lauro_Mar/Standortverlauf/Semantic Location History/'
    
# dataPathLocs = '../Takeout_Haojun_Feb/Location History/Location History.json'
# dataPathTrips = '../Takeout_Haojun_Feb/Location History/Semantic Location History/'

locsdf, locsgdf = hlp.parseLocs(dataPathLocs)
trips, tripdf, tripgdf = hlp.parseTrips(dataPathTrips)

#%%
# Calculate time and distance difference
locsdf['t_diff'] = 0
locsdf['t_diff'] = locsdf.index.to_series().diff().dt.seconds.shift(-1)

# Convert decimal degrees to radians 
lat1 = locsdf['latitudeE7'].iloc[:-1]
lon1 = locsdf['longitudeE7'].iloc[:-1]
lat2 = locsdf['latitudeE7'].iloc[1:]
lon2 = locsdf['longitudeE7'].iloc[1:]

# haver_vec = np.vectorize(hlp.haversine_built, otypes=[np.int16])
# locsdf['d_diff'] = 0
# locsdf['d_diff'].iloc[:-1] = (haver_vec(lat1,lon1,lat2,lon2))

locsdf['d_diff_py'] = 0
for i in range(0,len(locsdf)-1):
    lat1 = locsdf['latitudeE7'].iloc[i]
    lon1 = locsdf['longitudeE7'].iloc[i]
    lat2 = locsdf['latitudeE7'].iloc[i+1]
    lon2 = locsdf['longitudeE7'].iloc[i+1]
    
    locsdf['d_diff_py'].iloc[i] = haversine((lat1,lon1), (lat2,lon2))*1000

# drop last row
# locsdf.drop(locsdf.tail(1).index,inplace=True) 

#%%
# hist and set t_diff and d_diff thresholds
fig, axs = plt.subplots(1, 2, sharey=True, tight_layout=True)
axs[0].hist(locsdf['t_diff'])
axs[1].hist(locsdf['d_diff'])
plt.show()

# locsdf.describe()

# filter
filter_tdiff = locsdf.loc[locsdf['t_diff']>30]
stayPnt = filter_tdiff.loc[filter_tdiff['d_diff']<30]

#%%
# why negative values for distance
selectRow = locsdf[locsdf['d_diff']<0]

