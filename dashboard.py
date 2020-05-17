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
import math

from statistics import median 
from shapely.geometry import Point

import plotly.io as pio
pio.renderers.default = "browser"

# Local files
import main_functions as main
import help_functions as hlp
import poi_classification as poi
import thresholds_function as thred
import stat_functions as calstat
import api_call as api

from trackintel.geogr.distances import haversine_dist

#import noiserm_functions as nrm
dataNameList = ["1","2","3","4","5","6","7","17","20","25","28"]
dataName = '2'

mac = False

SELECT_RANGE =      True
FIND_STAY_POINTS =  True
FIND_PLACES =       True
FIND_TRIPS =        True
FIND_SEMANTIC_INFO =True
CLUSTER_TRPS =      True
EXPORT_GPX =        True
API_CALL =          True
CHECK_NB_POINTS =   False

exportShp =         True
loadTh =            False

TimelineStat =      True
TransmodeStat =     True
HomeWorkStat =      True

#%%
# For the first time, run the following four lines to save the data
# dateStart = '2020-01-01'
# dateEnd = 'end'
# stythred = thred.stydiffstat(dataNameList, SELECT_RANGE, dateStart, dateEnd)
# stythred.to_csv('../data/csv'+'/StayDiffStatRange.csv', index=False)

# Then read the data after the second time
# staythred = pd.read_csv('../data/csv'+'/StayDiffStat.csv') 
staythredrange = pd.read_csv('../data/csv'+'/StayDiffStatRange.csv') 

# dfStatistics = calstat.accuracyStat(dataName, dataNameList, dateStart, dateEnd)
dfStatistics = pd.read_csv('../data/statistics.csv',sep=";")

# staythredrange[staythredrange['dataName']==int(dataName)]['dist_quarter'][dataNameList.index(dataName)],
# staythredrange[staythredrange['dataName']==int(dataName)]['time_quarter'][dataNameList.index(dataName)],

thresholds = {
    "accuracy_threshold" : 0,
    "dist_threshold" : 0,
    "time_threshold" : 5*60, #staythredrange[staythredrange['dataName']==int(dataName)]['dist_quarter'][dataNameList.index(dataName)],
    "minDist" : 0,
    "minPoints" : 0,
    "minDistTh" : 0.2, 
    "factorTh" : 3,
    "dateStart": "2020-01-01",
    "dateEnd": "end"
    }

#%% Choose thresholds
dataStat = dfStatistics[dfStatistics['id']==int(dataName)]

if (dataStat['ThreeQuatile'][dataNameList.index(dataName)] < 40):
    thresholds['accuracy_threshold'] = 40
else:
    thresholds['accuracy_threshold'] = dataStat['ThreeQuatile'][dataNameList.index(dataName)]

if (thresholds['accuracy_threshold'] < 50):
    thresholds['dist_threshold'] = 50
else:
    thresholds['dist_threshold'] = thresholds['accuracy_threshold']

thresholds['minDist'] = thresholds['accuracy_threshold']

#with open('../data/thresholds/' + dataName + '.json', 'w') as outfile:
#    json.dump(thresholds, outfile)

# if loadTh:   
#     with open('../data/thresholds/' + dataName + '.json', 'r') as file:
#         thresholds = json.load(file)

 #%% IMPORT DATA %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
print("-> Loading the data")
dataPathLocs,dataPathTrips = hlp.getDataPaths(dataName)

if SELECT_RANGE:    
    dataPathLocs,dataPathTrips = hlp.selectRange(dataPathLocs, dataPathTrips, mac, dateStart = thresholds["dateStart"], dateEnd = thresholds["dateEnd"],)

    #dataPathLocs,dataPathTrips = hlp.selectLastMonth(dataPathLocs, dataPathTrips)
    
locs, locsgdf = hlp.parseLocs(dataPathLocs)
trips, tripdf, tripsgdf = hlp.parseTrips(dataPathTrips)

# add location data to the trips file
# tripsgdf = hlp.parseTripsWithLocs(dataPathTrips, locsgdf)

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
minPnts = math.ceil(len(stps)/100)
if (minPnts >= 5):
    thresholds["minPoints"] = 5
else:
    thresholds["minPoints"] = minPnts
    
if FIND_PLACES:
    print("-> Finding the places ")

    plcs = main.findPlaces(stps, dataName, thresholds["minDist"], thresholds["minPoints"])
    
    if exportShp:
        plcs_shp = plcs.copy()
        plcs_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places.shp')
        #plcs_shp.geometry = plcs_shp['extent']
        #plcs_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places_extent.shp')
    
    plcs = poi.reverseGeoCoding(plcs)

#%%    
if FIND_SEMANTIC_INFO:
    places = tripsgdf[tripsgdf['Type']=='placeVisit']
    places.drop_duplicates(subset ="placeId", keep = 'first', inplace = True) 
    
    
    plcs = hlp.findSemanticInfo(places, plcs)
            
    if exportShp:
        places['startTime'] = places['startTime'].astype(str)
        places['endTime'] = places['endTime'].astype(str)
        places.to_file('../data/shp/'+dataName +'/Places_google.shp')
 
#%%
if TimelineStat:
    plcs = calstat.plcsStayHour(stps, plcs, dataName)

#%
if HomeWorkStat:
    homeworkplcs = calstat.homeworkStay(stps, dataName, thresholds["minDist"], thresholds["minPoints"])

#%
if TransmodeStat:
    transtat = calstat.pieChartInfoPlus(trips)
    calstat.transModeCsv(transtat, dataName)

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









