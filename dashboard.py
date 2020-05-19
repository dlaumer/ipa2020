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
import os

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
CLUSTER_TRPS =      False
EXPORT_GPX =        False
API_CALL =          False
EXPORT_FOR_DASHBOARD = False

exportShp =         True
loadTh =            False

TimelineStat =      True
TransmodeStat =     True
HomeWorkStat =      True

#%% LOAD ALL SAVED THRESHOLDS
import ast

inputFile = open("../data/stat/thresholds.txt", "r")
lines = inputFile.readlines()

objects = []
for line in lines:
    objects.append( ast.literal_eval(line) )

allthresholds = objects[0]

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

#allthresholds = {}

thresholds = {
    "accuracy_threshold" : 0,
    "dist_threshold" : 0,
    "time_threshold" : 5*60, #staythredrange[staythredrange['dataName']==int(dataName)]['dist_quarter'][dataNameList.index(dataName)],
    "timemax_threshold": 12*3600,
    "minDist" : 0,
    "minPoints" : 0,
    "minDistTh" : 0.2, 
    "factorTh" : 2,
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
#thresholds['accuracy_threshold'] = 3000

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
    pfs,stps = main.findStayPoints(locs, dataName,thresholds["accuracy_threshold"],thresholds["dist_threshold"],thresholds["time_threshold"],thresholds["timemax_threshold"])
  
    if exportShp: 
        stps_shp = stps.copy()
        stps_shp['started_at'] = stps_shp['started_at'].astype(str)
        stps_shp['finished_at'] = stps_shp['finished_at'].astype(str)
        stps_shp.to_file('../data/shp/'+dataName +'/Staypoints.shp')

stps['t_diff'] = stps['finished_at'] - stps['started_at']

#%% FIND PLACES (CLUSTER OF STAY POINTS)
minPnts = math.ceil(len(stps)/100)
if (minPnts >= 5):
    thresholds["minPoints"] = 5
elif (minPnts < 2):
      thresholds["minPoints"] = 2
else:
    thresholds["minPoints"] = minPnts
#thresholds["minPoints"] = 1

if FIND_PLACES:
    print("-> Finding the places ")

    plcs = main.findPlaces(stps, dataName, thresholds["minDist"], thresholds["minPoints"])
    
    if exportShp:
        plcs_shp = plcs.copy()
        plcs_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places.shp')
        #plcs_shp.geometry = plcs_shp['extent']
        #plcs_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places_extent.shp')
    
    plcs = poi.reverseGeoCoding(plcs)

#%% MATCH GOOGLE PLACES %%%%%%%
if FIND_SEMANTIC_INFO:
    places = tripsgdf[tripsgdf['Type']=='placeVisit']
    places.drop_duplicates(subset ="placeId", keep = 'first', inplace = True) 
    places = places[~places.geometry.is_empty]
    
    plcs = hlp.findSemanticInfo(places, plcs)
            
    # if exportShp:
    #     places['startTime'] = places['startTime'].astype(str)
    #     places['endTime'] = places['endTime'].astype(str)
    #     places.to_file('../data/shp/'+dataName +'/Places_google.shp')
 
#%% OUTPUT STATISTICS %%%%%%%%%%
if TimelineStat:
    plcs = calstat.plcsStayHour(stps, plcs, dataName)

#%
if HomeWorkStat:
    homeworkplcs = calstat.homeworkStay(stps, dataName, places, thresholds["minDist"], thresholds["minPoints"])
    # homeworlplcs = hlp.findSemanticInfo(places, homeworlplcs)
    
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
        
        trps_shp = trps.copy()
        trps_shp['started_at'] = trps_shp['started_at'].astype(str)
        trps_shp['finished_at'] = trps_shp['finished_at'].astype(str)
        trps_shp.to_file('../data/shp/'+dataName +'/Trips.shp')
        
        trpsCount_shp = trpsCount.copy()
        trpsCount_shp['count'] = trpsCount_shp['count'].astype(int)
        trpsCount_shp = trpsCount_shp.drop(["trpIds"], axis = 1)
        trpsCount_shp.to_file('../data/shp/'+dataName +'/TripsCount.shp')
        
      
#%% Cluster the trips
        
# thresholds["minDistTh"] = 1
# thresholds["factorTh"] = 2

# allthresholds[dataName] = thresholds
# outputFile = open("../data/stat/thresholds.txt", "w")
# outputFile.write(str(allthresholds))
# outputFile.flush()
# outputFile.close()

if CLUSTER_TRPS:
    print("-> Cluster the trips")

    trpsShort, trpsCount = hlp.removeLongTrips(trps, trpsCount)
    trpsShort, trpsAgr = main.clusterTrips(trpsShort, trpsCount, thresholds["minDistTh"], thresholds["factorTh"], dataName, saveDendogramms=True)
    #trps, trpsAgr = main.clusterTrips(trps, trpsCount, 0.2, 2, dataName, saveDendogramms=True)

    if exportShp:
        #trpsShort_shp = trpsShort.copy()
        #trpsShort_shp['started_at'] = trpsShort_shp['started_at'].astype(str)
        #trpsShort_shp['finished_at'] = trpsShort_shp['finished_at'].astype(str)
        #trpsShort_shp.to_file('../data/shp/'+dataName +'/TripsShort.shp')
        
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
    if os.path.exists("../data/gpx/" + dataName):
        shutil.rmtree("../data/gpx/" + dataName)
    hlp.trip2gpx(trpsAgr,dataName)   
    
#%%
if API_CALL:
    print("-> Calling the API from Hitouch")
    homes = homeworkplcs.loc[homeworkplcs['id']=='home']
    homeCoords = homes.loc[homes['totalStayHrs'].idxmax()].center.coords[:][0]
    
    api.apiCall(dataName, 100 + int(dataName), homeCoords)
    tripsAgrSchematic = api.readApiCall(trpsAgr.copy(), 100+int(dataName))
    
    trpsAgrSchematic_shp = tripsAgrSchematic.copy()
    trpsAgrSchematic_shp['weight'] = trpsAgrSchematic_shp['weight'].astype(int)
    trpsAgrSchematic_shp.to_file('../data/shp/'+dataName +'/TripsAggregatedSchemtic.shp')

#%%
if EXPORT_FOR_DASHBOARD:
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









