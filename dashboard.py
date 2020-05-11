#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 10:09:23 2020

Authors:    Daniel Laumer (laumerd@ethz.ch)
            Haojun Cai (caihao@ethz.ch)
"""

import pandas as pd

from statistics import median 


import plotly.io as pio
pio.renderers.default = "browser"

# Local files
import main_functions as main
import help_functions as hlp
import api_call as api

#import noiserm_functions as nrm

dataName = '1'
SELECT_RANGE =      True
CHECK_VELO =        False
FIND_STAY_POINTS =  True
FIND_PLACES =       True
FIND_TRIPS =        True
CLUSTER_TRPS =      True
EXPORT_GPX =        False
API_CALL =          False
CHECK_NB_POINTS =   False
CHECK_ACCURACY =    False
PLOT =              False

exportShp =         True

dist_threshold = 100
time_threshold = 15*60
minDist = 150
minPoints = 4

#%% IMPORT DATA %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
print("-> Loading the data")
dataPathLocs,dataPathTrips = hlp.getDataPaths(dataName)

if SELECT_RANGE:    
    #dateStart = 'beginning'
    #dateEnd = '2020-01-02'
    #dataPathLocs,dataPathTrips = hlp.selectRange(dataPathLocs, dataPathTrips, dateStart = dateStart, dateEnd = dateEnd)
    
    dataPathLocs,dataPathTrips = hlp.selectLastMonth(dataPathLocs, dataPathTrips)
    
locs, locsgdf = hlp.parseLocs(dataPathLocs)
trips, tripdf, tripsgdf = hlp.parseTrips(dataPathTrips)

#%% add location data to the trips file
tripsgdf = hlp.parseTripsWithLocs(dataPathTrips, locsgdf)


#%% EXPORT SHP %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if exportShp:
    hlp.loc2shp(locsgdf, dataName)
    hlp.trip2shp(tripsgdf, dataName)

#%% ANALYSIS  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Velovity
if CHECK_VELO:
    locs = hlp.calculateVelocity(locs)

#%% TIME AND DISTANCE DIFF
if FIND_STAY_POINTS:
    print("-> Finding stay points ")

    pfs,stps = main.findStayPoints(locs, dataName, dist_threshold, time_threshold)
  
    if exportShp: 
        stps_shp = stps.copy()
        stps_shp['started_at'] = stps_shp['started_at'].astype(str)
        stps_shp['finished_at'] = stps_shp['finished_at'].astype(str)
        stps_shp.to_file('../data/shp/'+dataName +'/Staypoints.shp')
        
#%%
if FIND_PLACES:
    print("-> Finding the places ")

    plcs = main.findPlaces(stps, dataName, minDist, minPoints)
    
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
#%%
if CLUSTER_TRPS:
    print("-> Cluster the trips")

    trps, trpsAgr = main.clusterTrips(trps, trpsCount)

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
        elif float(trpsAgr.loc[idx,'weight']) < 2:
            trpsAgr = trpsAgr.drop([idx])
    #hlp.savecsv4js(plcs, trpsAgr)
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
    hlp.savecsv4js(plcs, trpsAgr, tripsAgrSchematic)    
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
