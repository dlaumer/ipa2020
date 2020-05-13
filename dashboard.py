#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 10:09:23 2020

Authors:    Daniel Laumer (laumerd@ethz.ch)
            Haojun Cai (caihao@ethz.ch)
"""

import pandas as pd
import json
import shutil

from statistics import median 
from shapely.geometry import Point

import plotly.io as pio
pio.renderers.default = "browser"

# Local files
import main_functions as main
import help_functions as hlp
import api_call as api

#import noiserm_functions as nrm

dataName = '1'
SELECT_RANGE =      False
FIND_STAY_POINTS =  True
FIND_PLACES =       True
FIND_TRIPS =        True
CLUSTER_TRPS =      True
EXPORT_GPX =        True
API_CALL =          True
CHECK_NB_POINTS =   False


exportShp =         True
loadTh =            False


#%%
thresholds = {
    "accuracy_threshold" : 70,
    "dist_threshold" : 170,
    "time_threshold" : 15*60,
    "minDist" : 150,
    "minPoints" : 4,
    "minDistTh" : 0.05, 
    "factorTh" : 2,
    "dateStart": "2019-12-01",
    "dateEnd": "2019-12-31"
    }

#with open('../data/thresholds/' + dataName + '.json', 'w') as outfile:
#    json.dump(thresholds, outfile)

if loadTh:   
    with open('../data/thresholds/' + dataName + '.json', 'r') as file:
        thresholds = json.load(file)


#%% IMPORT DATA %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
print("-> Loading the data")
dataPathLocs,dataPathTrips = hlp.getDataPaths(dataName)

if SELECT_RANGE:    
    
    dataPathLocs,dataPathTrips = hlp.selectRange(dataPathLocs, dataPathTrips, dateStart = thresholds["dateStart"], dateEnd = thresholds["dateEnd"])
    #dataPathLocs,dataPathTrips = hlp.selectLastMonth(dataPathLocs, dataPathTrips)
    
locs, locsgdf = hlp.parseLocs(dataPathLocs)
trips, tripdf, tripsgdf = hlp.parseTrips(dataPathTrips)

# add location data to the trips file
tripsgdf = hlp.parseTripsWithLocs(dataPathTrips, locsgdf)

# export to shapefile
if exportShp:
    hlp.loc2shp(locsgdf, dataName)
    hlp.trip2shp(tripsgdf, dataName)

#%% FIND STAY POINTS
if FIND_STAY_POINTS:
    print("-> Finding stay points ")
    # NOTE: Delete csv file if range is changed!!!!!!
    pfs,stps = main.findStayPoints(locs, dataName, thresholds["accuracy_threshold"], thresholds["dist_threshold"], thresholds["time_threshold"])
  
    if exportShp: 
        stps_shp = stps.copy()
        stps_shp['started_at'] = stps_shp['started_at'].astype(str)
        stps_shp['finished_at'] = stps_shp['finished_at'].astype(str)
        stps_shp.to_file('../data/shp/'+dataName +'/Staypoints.shp')
        
#%% FIND PLACES (CLUSTER OF STAY POINTS)
if FIND_PLACES:
    print("-> Finding the places ")

    plcs = main.findPlaces(stps, dataName, thresholds["minDist"], thresholds["minPoints"])
    
    if exportShp:
        plcs_shp = plcs.copy()
        plcs_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places.shp')
        #plcs_shp.geometry = plcs_shp['extent']
        #plcs_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places_extent.shp')

    
#%% Find trips from staypoints
if FIND_TRIPS:
    print("-> Finding the trips ")

    tpls, trps, trpsCount = main.findTrips(pfs, stps, plcs, dataName)
    
    if exportShp:
        tpls_shp = tpls.copy()
        tpls_shp['started_at'] = tpls_shp['started_at'].astype(str)
        tpls_shp['finished_at'] = tpls_shp['finished_at'].astype(str)
        tpls_shp.to_file('../data/shp/'+dataName +'/Triplegs.shp')
        
        #trps_shp = trps.copy()
        #trps_shp['started_at'] = trps_shp['started_at'].astype(str)
        #trps_shp['finished_at'] = trps_shp['finished_at'].astype(str)
        #trps_shp.to_file('../data/shp/'+dataName +'/Trips.shp')
        
        trpsCount_shp = trpsCount.copy()
        trpsCount_shp['count'] = trpsCount_shp['count'].astype(int)
        trpsCount_shp = trpsCount_shp.drop(["trpIds"], axis = 1)
        trpsCount_shp.to_file('../data/shp/'+dataName +'/TripsCount.shp')
        
      
#%% Cluster the trips
if CLUSTER_TRPS:
    print("-> Cluster the trips")

    trps, trpsAgr = main.clusterTrips(trps, trpsCount, thresholds["minDistTh"], thresholds["factorTh"], dataName)

    if exportShp:
        trps_shp = trps.copy()
        trps_shp['started_at'] = stps_shp['started_at'].astype(str)
        trps_shp['finished_at'] = stps_shp['finished_at'].astype(str)
        trps_shp.to_file('../data/shp/'+dataName +'/Trips.shp')
        
        trpsAgr_shp = trpsAgr.copy()
        trpsAgr_shp['weight'] = trpsAgr_shp['weight'].astype(int)
        trpsAgr_shp.to_file('../data/shp/'+dataName +'/TripsAggregated.shp')

    
 #%% EXPORT GPX %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if EXPORT_GPX:
    print("-> Export to GPX")
    for idx in trpsAgr.index:
        if trpsAgr.loc[idx,'start_plc'] == trpsAgr.loc[idx,'end_plc']:
            trpsAgr = trpsAgr.drop([idx])
        elif float(trpsAgr.loc[idx,'weight']) < 1:
            trpsAgr = trpsAgr.drop([idx])
    #hlp.savecsv4js(plcs, trpsAgr)
    shutil.rmtree("../data/gpx/" + dataName)
    hlp.trip2gpx(trpsAgr,dataName)   
    
#%%
if API_CALL:
    print("-> Calling the API from Hitouch")

    api.apiCall(int(dataName))
    tripsAgrSchematic = api.readApiCall(trpsAgr.copy(), int(dataName))
    
    trpsAgrSchematic_shp = tripsAgrSchematic.copy()
    trpsAgrSchematic_shp['weight'] = trpsAgrSchematic_shp['weight'].astype(int)
    trpsAgrSchematic_shp.to_file('../data/shp/'+dataName +'/TripsAggregatedSchemtic.shp')

#%%
    drops = []
    for i in plcs.index:
        if plcs.loc[i,'place_id'] not in set(trpsAgr['start_plc']) and plcs.loc[i,'place_id'] not in set(trpsAgr['end_plc']):
            drops.append(i)
    plcs = plcs.drop(drops)  
    
    plcs['centerSchematic'] = None
    for i in range(len(tripsAgrSchematic)):
        plcs.loc[tripsAgrSchematic.loc[i,'start_plc']-1, 'centerSchematic'] = Point(tripsAgrSchematic.loc[i,'geom'].coords[0])
        plcs.loc[tripsAgrSchematic.loc[i,'end_plc']-1, 'centerSchematic'] = Point(tripsAgrSchematic.loc[i,'geom'].coords[-1])

    # Read the gpx response and convert to csv
    hlp.savecsv4js(plcs, trpsAgr, tripsAgrSchematic)    

