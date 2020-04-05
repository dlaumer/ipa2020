#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 10:09:23 2020

Authors:    Daniel Laumer (laumerd@ethz.ch)
            Haojun Cai (caihao@ethz.ch)
"""
import pandas as pd
import numpy as np
import math
import json
import os

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
pio.renderers.default = "browser"
import trackintel as ti
from trackintel.geogr.distances import meters_to_decimal_degrees


# Local files
import help_functions as hlp
#import noiserm_functions as nrm

dataName = '1'
SELECT_RANGE =      False
EXPORT_GPX =        False
SAVE_SHP =          True
CHECK_VELO =        False
FIND_STAY_POINTS =  True
CHECK_NB_POINTS =   False
CHECK_ACCURACY =    False
PLOT =              False


#%% SELECT RANGE %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


#%% IMPORT DATA %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

dataPathLocs,dataPathTrips = hlp.getDataPaths(dataName)

if SELECT_RANGE:    
    dateStart = '2020-01-01 12:00:00'
    dateEnd = '2020-01-02'
    jsonDataOut = hlp.selectRange(dataPathLocs, dataPathTrips, dateStart = dateStart, dateEnd = dateEnd)
    dataPathLocs = dataPathLocs[:-5] + "_trimmed.json"
    
locs, locsgdf = hlp.parseLocs(dataPathLocs)
trips, tripdf, tripsgdf = hlp.parseTrips(dataPathTrips)

#%% EXPORT GPX %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if EXPORT_GPX:
    tripsgdf_test = tripsgdf.copy()
    for idx in tripsgdf_test.index:
        tripsgdf_test.loc[idx,'countPoints'] = len(tripsgdf_test.loc[idx,'geometry'].coords)
    
    tripsgdf_test = tripsgdf_test.loc[[11,13,242,350]]
    hlp.trip2gpx(tripsgdf_test,dataName)

#%% EXPORT SHP %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if SAVE_SHP:
    hlp.loc2shp(locsgdf, dataName)
    hlp.trip2shp(tripsgdf, dataName)

#%% ANALYSIS  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Velovity
if CHECK_VELO:
    locs = hlp.calculateVelocity(locs)

if FIND_STAY_POINTS:
    if not(os.path.exists('../data/shp/'+ dataName + '/')):
        os.mkdir('../data/shp/'+ dataName + '/')
                
    hlp.loc2csv4ti(locs, dataName)
    pfs = ti.read_positionfixes_csv('../data/csv/'+dataName +'.csv', sep=';')
    
    # Find staypoints
    stps = pfs.as_positionfixes.extract_staypoints(method='sliding',
        dist_threshold=100, time_threshold=5*60)
    stps_shp = stps.copy()
    stps_shp['started_at'] = stps_shp['started_at'].astype(str)
    stps_shp['finished_at'] = stps_shp['finished_at'].astype(str)
    stps_shp.to_file('../data/shp/'+dataName +'/Staypoints.shp')
    
    # Find places
    plcs = stps.as_staypoints.extract_places(method='dbscan',
        epsilon=meters_to_decimal_degrees(80, 47.5), num_samples=6)
    plcs.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places.shp')
    plcs.geometry = plcs['extent']
    plcs.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places_extent.shp')


#Accuracy
if CHECK_ACCURACY:
    for i in [30,40,50,60,70]:
        print('Lower then '+str(i)+'m: '+str(round(100*len(locs[locs['accuracy'].lt(i)])/len(locs),2)))

# Number of points per day
if CHECK_NB_POINTS:
    idx = pd.date_range(locs.index[0].date(), locs.index[-1].date())
    perDay = (locs.groupby(locs.index.date).count()['timestampMs'])
    perDay = perDay.reindex(idx, fill_value=0)

#hlp.checkTrips(trips)

#%% PLOT %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if PLOT:
    labels, values = hlp.pieChartInfoPlus(trips)

    fig = make_subplots(
    rows=2, cols=2,
    column_widths=[0.6, 0.4],
    row_heights=[0.4, 0.6],
    specs=[[{"type": "Bar", "colspan": 2}, None],
           [ {"type": "scattergeo"}    , {"type": "Pie"}]])

    fig.add_trace( 
        go.Bar(x=list(perDay.index), 
               y=list(perDay),
               name="Number of points per day"
               ),
        row=1, col=1
        )
    
    fig.add_trace( 
        go.Pie(labels=labels, values=values),
        row=2, col=2
        )
        
    fig.add_trace(
        go.Scattergeo(
            lon = locs['longitudeE7'],
            lat = locs['latitudeE7'],
            text = locs['datetimeUTC'],
            mode = 'markers',
            name="Recorded Points"
            ),
        row=2, col=1
        )
    
    fig.update_geos(
            showland = True,
            landcolor = "rgb(212, 212, 212)",
            subunitcolor = "rgb(255, 255, 255)",
            countrycolor = "rgb(255, 255, 255)",
            showlakes = True,
            lakecolor = "rgb(255, 255, 255)",
            showsubunits = True,
            showcountries = True,         
            )
    fig.show()
    
    fig2 = px.histogram(locs, x="accuracy")
    fig2.show()