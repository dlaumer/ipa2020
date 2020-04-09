#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 10:09:23 2020

Authors:    Daniel Laumer (laumerd@ethz.ch)
            Haojun Cai (caihao@ethz.ch)
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import math
import json
import os
import time

from shapely.geometry import LineString
from statistics import median 


import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
pio.renderers.default = "browser"
import trackintel as ti
from trackintel.geogr.distances import meters_to_decimal_degrees
from haversine import haversine
from trackintel.geogr.distances import haversine_dist

# Local files
import help_functions as hlp
import trackintel_modified as tim
#import noiserm_functions as nrm

dataName = '4'
SELECT_RANGE =      False
EXPORT_GPX =        False
SAVE_SHP =          True
CHECK_VELO =        False
FIND_STAY_POINTS =  True
FIND_TRIPS =        True
CHECK_NB_POINTS =   True
CHECK_ACCURACY =    True
PLOT =              False



#%% IMPORT DATA %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

dataPathLocs,dataPathTrips = hlp.getDataPaths(dataName)

if SELECT_RANGE:    
    dateStart = '2020-02-01'
    dateEnd = '2020-02-29'
    dataPathLocs,dataPathTrips = hlp.selectRange(dataPathLocs, dataPathTrips, dateStart = dateStart, dateEnd = dateEnd)
    
locs, locsgdf = hlp.parseLocs(dataPathLocs)
#trips, tripdf, tripsgdf = hlp.parseTrips(dataPathTrips)
tripsgdf = hlp.parseTripsWithLocs(dataPathTrips, locsgdf)

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

#%%
if FIND_STAY_POINTS:
    #%% TIME AND DISTANCE DIFF
    # Calculate time and distance difference

    locs['d_diff'] = np.append(haversine_dist(locs.longitudeE7[1:], locs.latitudeE7[1:], locs.longitudeE7[:-1], locs.latitudeE7[:-1]),0)
    
    locs = locs[locs['accuracy']<70]
    #locs = locs[locs['accuracy']<locs['d_diff']]

    if not(os.path.exists('../data/shp/'+ dataName + '/')):
        os.mkdir('../data/shp/'+ dataName + '/')
                
    hlp.loc2csv4ti(locs, dataName)
    pfs = ti.read_positionfixes_csv('../data/csv/'+dataName +'/' + dataName + '.csv', sep=';')
    
    # Find staypoints
    #stps = pfs.as_positionfixes.extract_staypoints(method='sliding',dist_threshold=100, time_threshold=5*60)
    stps = tim.extract_staypoints_ipa(pfs, method='sliding',dist_threshold=100, time_threshold=5*60)

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

if FIND_TRIPS:
    # Find the trips between the PLACES!!
    tpls = tim.extract_triplegs_ipa(pfs, stps)
    
    tpls_shp = tpls.copy()
    tpls_shp['started_at'] = tpls_shp['started_at'].astype(str)
    tpls_shp['finished_at'] = tpls_shp['finished_at'].astype(str)
    tpls_shp.to_file('../data/shp/'+dataName +'/Triplegs.shp')
    
    trps = pd.DataFrame(columns=['id', 'started_at', 'finished_at','start_plc', 'end_plc', 'geom'])
    generated_trips = []
    count = 0;
    for i in range(len(tpls)):
        startPlace = stps.loc[tpls.loc[i,'start_stp'],'place_id']
        endPlace = stps.loc[tpls.loc[i,'end_stp'],'place_id']

        if (startPlace != -1) and (endPlace!= -1):
            coords = tpls.loc[i,'geom'].coords[1:-1]
            startCoord = stps.loc[tpls.loc[i,'start_stp'],'geom'].coords[:]
            endCoord = stps.loc[tpls.loc[i,'end_stp'],'geom'].coords[:]
            coords = startCoord + coords + endCoord
            
            generated_trips.append({
                        'id': count,
                        'started_at': tpls.loc[i,'started_at'],  # pfs_tripleg['tracked_at'].iloc[0],
                        'finished_at': tpls.loc[i,'finished_at'],  # pfs_tripleg['tracked_at'].iloc[-1],
                        'geom': LineString(coords),
                        'start_stp': startPlace,
                        'end_stp': endPlace
                    })
            count = count + 1
    trps = trps.append(generated_trips)
    trps = gpd.GeoDataFrame(trps, geometry='geom')
    
    trps_shp = trps.copy()
    trps_shp['started_at'] = stps_shp['started_at'].astype(str)
    trps_shp['finished_at'] = stps_shp['finished_at'].astype(str)
    trps_shp.to_file('../data/shp/'+dataName +'/Trips.shp')

#%%Accuracy
if CHECK_ACCURACY:
    #for i in [30,40,50,60,70]:
    #    print('Lower then '+str(i)+'m: '+str(round(100*len(locs[locs['accuracy'].lt(i)])/len(locs),2)))
    
    accuracyPerMode = {}
    for i in range(len(tripsgdf)):
        if (tripsgdf.loc[i,'Type'] == 'activitySegment'):
            if (tripsgdf.loc[i,'actType'] not in list(accuracyPerMode)):
                accuracyPerMode[tripsgdf.loc[i,'actType']] = []
            accuracies = list(locsgdf['accuracy'][tripsgdf.loc[i,'correspondingLocs'][0]:tripsgdf.loc[i,'correspondingLocs'][-1]])
            accuracyPerMode[tripsgdf.loc[i,'actType']] = accuracyPerMode[tripsgdf.loc[i,'actType']] + accuracies
    infoPerModeTemp = []
    infoPerMode = pd.DataFrame(columns=['mode', 'averageAccuracy', 'numberOfPoints'])
    for mode in list(accuracyPerMode):
        infoPerModeTemp.append({
            'mode': mode,
            'averageAccuracy': float(median(accuracyPerMode[mode])),
            'numberOfPoints': len(accuracyPerMode[mode])
            })
    infoPerMode = infoPerMode.append(infoPerModeTemp)

    
# Number of points per day
if CHECK_NB_POINTS:
    idx = pd.date_range(locs.index[0].date(), locs.index[-1].date())
    perDay = (locs.groupby(locs.index.date).count()['timestampMs'])
    perDay = perDay.reindex(idx, fill_value=0)

#hlp.checkTrips(trips)

#%% PLOT %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if PLOT:
    labels, values = hlp.pieChartInfoPlus(tripsgdb)

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