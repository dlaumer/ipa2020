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
import numpy as np

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
import numpy as np

from shapely.geometry import Point, LineString, Polygon

from trackintel.geogr.distances import haversine_dist

#import noiserm_functions as nrm
dataNameList = ["1","2","3","4","5","6","7","17","20","25","28"]
<<<<<<< HEAD
dataName = '17'
=======
dataName = '28'
>>>>>>> 184b7b3350fd6fafac0feececada1f138b34a516

mac = True

IMPORT_THRES =      True
CHOOSE_THRES =      False

SELECT_RANGE =      True
FIND_STAY_POINTS =  True
FIND_PLACES =       True
FIND_TRIPS =        True
FIND_SEMANTIC_INFO =True
CLUSTER_TRPS =      True
EXPORT_GPX =        True
API_CALL =          True
EXPORT_FOR_DASHBOARD = False

exportShp =         True
loadTh =            False

TimelineStat =      True
TransmodeStat =     True
HomeWorkStat =      False

#%% LOAD ALL SAVED THRESHOLDS
if IMPORT_THRES:
    import ast
    
    inputFile = open("../data/stat/thresholds.txt", "r")
    lines = inputFile.readlines()
    
    objects = []
    for line in lines:
        objects.append( ast.literal_eval(line) )
    
    allthresholds = objects[0]
    
    thresholds = allthresholds[dataName]

# thresholds['accuracy_threshold'] = 200
#%% CHOOSE THRESHOLDS - PART 1
if CHOOSE_THRES:
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
    
    # allthresholds.get('3')
    
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
    
    
    #% Choose thresholds
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

    # thresholds['accuracy_threshold'] = 200   

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

# locs['d_diff'] = np.append(haversine_dist(locs.longitudeE7[1:], locs.latitudeE7[1:], locs.longitudeE7[:-1], locs.latitudeE7[:-1]),0)
# thresholds['accuracy_threshold'] = np.quantile(locs['d_diff'], .95)

# export to shapefile
if exportShp:
    hlp.loc2shp(locsgdf, dataName)
    hlp.trip2shp(tripsgdf, dataName)



locs['d_diff'] = np.append(haversine_dist(locs.longitudeE7[1:], locs.latitudeE7[1:], locs.longitudeE7[:-1], locs.latitudeE7[:-1]),0)
thresholds['accuracy_threshold'] = np.quantile(locs['d_diff'], .95)


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
        
# stps['t_diff'] = stps['finished_at'] - stps['started_at']

#%% CHOOSE THRESHOLDS - PART 2
if CHOOSE_THRES:
    minPnts = math.ceil(len(stps)/100)
    if (minPnts >= 5):
        thresholds["minPoints"] = 5
    elif (minPnts < 2):
        thresholds["minPoints"] = 2
    else:
        thresholds["minPoints"] = minPnts
    #thresholds["minPoints"] = 1

# Write threshodls
# with open('../data/thresholds/' + dataName + '.json', 'w') as outfile:
#    json.dump(thresholds, outfile)

# if loadTh:   
#     with open('../data/thresholds/' + dataName + '.json', 'r') as file:
#         thresholds = json.load(file)

#%% FIND PLACES (CLUSTER OF STAY POINTS)

# minPnts = math.ceil(len(stps)/100)
# if (minPnts >= 5):
#     thresholds["minPoints"] = 5
# elif (minPnts < 2):
#       thresholds["minPoints"] = 2
# else:
#     thresholds["minPoints"] = minPnts
# #thresholds["minPoints"] = 1

if FIND_PLACES:
    print("-> Finding the places ")

    plcs = main.findPlaces(stps, dataName, thresholds["minDist"], thresholds["minPoints"])
    
    if exportShp:
        plcs_shp = plcs.copy()
        plcs_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places.shp')
        
                
        # plcs_shp = plcs.copy()
        # plcs_shp.geometry = plcs_shp['extent']
        # plcs_shp_polygon = plcs_shp[plcs_shp['extent'].apply(lambda x: isinstance(x, Polygon))]
        # plcs_shp_polygon.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places_extent_polygon.shp')
        
        # plcs_shp = plcs.copy()
        # plcs_shp.geometry = plcs_shp['extent']               
        # plcs_shp_polyline = plcs_shp[plcs_shp['extent'].apply(lambda x: isinstance(x, LineString))]
        # plcs_shp_polyline.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places_extent_polyline.shp')

    plcs = poi.reverseGeoCoding(plcs)


#%% HOME AND WORK ADDRESS DETECTION
# homeidx = plcs.loc[plcs['Value'].idxmax()
                  

#%% MATCH GOOGLE PLACES %%%%%%%
if FIND_SEMANTIC_INFO:
    dfStatistics = pd.read_csv('../data/statistics.csv',sep=";")
    dataStat = dfStatistics[dfStatistics['id']==int(dataName)]    
    threeQua = dataStat['ThreeQuatile'][dataNameList.index(dataName)]
    
    places = tripsgdf[tripsgdf['Type']=='placeVisit']
    places.drop_duplicates(subset ="placeId", keep = 'first', inplace = True) 
    places = places[~places.geometry.is_empty]
    
    dfStatistics = pd.read_csv('../data/statistics.csv',sep=";")
    dataStat = dfStatistics[dfStatistics['id']==int(dataName)]    
    threeQua = dataStat['ThreeQuatile'][dataNameList.index(dataName)]

    plcs = hlp.findSemanticInfo(places, plcs, threeQua)
            
    # if exportShp:
    #     places['startTime'] = places['startTime'].astype(str)
    #     places['endTime'] = places['endTime'].astype(str)
    #     places.to_file('../data/shp/'+dataName +'/Places_google.shp')
 
#%% OUTPUT STATISTICS %%%%%%%%%%
if TimelineStat:
    plcs = calstat.plcsStayHour(stps, plcs, dataName)

#%
if HomeWorkStat:
    homeworkplcs = calstat.homeworkStay(stps, dataName, places, threeQua, thresholds["minDist"], thresholds["minPoints"])
    
    # homeworlplcs = hlp.findSemanticInfo(places, homeworlplcs)
    if exportShp: 
        HomeWork_shp = homeworkplcs.copy()
        # stps_shp['started_at'] = HomeWork_shp['started_at'].astype(str)
        HomeWork_shp['location'] = HomeWork_shp['location'].astype(str)
        HomeWork_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/HomeWork.shp')
        # HomeWork_shp.to_file('../data/shp/'+dataName +'/HomeWork.shp')
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

if CLUSTER_TRPS:
    print("-> Cluster the trips")
    print("Number of trips before removing long trips " + str(len(trps)))
    trpsShort, trpsCount = hlp.removeLongTrips(trps.copy(), trpsCount.copy())
    print("Number of trips after removing long trips " + str(len(trpsShort)))

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
    version = 5
    thresholds["DP_tolerance"] = 0.08
    thresholds["fisheye_factor"] = 1
    thresholds["curver_max"] = 360
    thresholds["curver_min"] = 0
    thresholds["curver_r"] = 20000
    
    # homes = homeworkplcs.loc[homeworkplcs['id']=='work']
    # homeCoords = homes.loc[homes['totalStayHrs'].idxmax()].center.coords[:][0]
    
    # For participant 17, change index to 13
    homeCoords = plcs[plcs['totalStayHrs']==plcs['totalStayHrs'].max()]['center'][9].coords[:][0]    
    
    api.apiCall(dataName, 1000 * int(dataName) + version, homeCoords, thresholds["DP_tolerance"], thresholds["fisheye_factor"],thresholds["curver_min"], thresholds["curver_max"], thresholds["curver_r"])
    tripsAgrSchematic = api.readApiCall(trpsAgr.copy(), 1000*int(dataName)+version )
    
    trpsAgrSchematic_shp = tripsAgrSchematic.copy()
    trpsAgrSchematic_shp['weight'] = trpsAgrSchematic_shp['weight'].astype(int)
    trpsAgrSchematic_shp.to_file('../data/shp/'+dataName +'/TripsAggregatedSchemtic.shp')
 
#%%
if EXPORT_FOR_DASHBOARD:
    # drops = []
    # for i in plcs.index:
    #     if plcs.loc[i,'place_id'] not in set(trpsAgr['start_plc']) and plcs.loc[i,'place_id'] not in set(trpsAgr['end_plc']):
    #         drops.append(i)
    # plcs = plcs.drop(drops)  
    
    plcs['centerSchematic'] = None
    for i in range(len(tripsAgrSchematic)):
        plcs.loc[tripsAgrSchematic.loc[i,'start_plc']-1, 'centerSchematic'] = Point(tripsAgrSchematic.loc[i,'geom'].coords[0])
        plcs.loc[tripsAgrSchematic.loc[i,'end_plc']-1, 'centerSchematic'] = Point(tripsAgrSchematic.loc[i,'geom'].coords[-1])

    # Read the gpx response and convert to csv
    hlp.savecsv4js(dataName, plcs, trpsAgr, tripsAgrSchematic)    

    allthresholds[dataName] = thresholds
    outputFile = open("../data/stat/thresholds.txt", "w")
    outputFile.write(str(allthresholds))
    outputFile.flush()
    outputFile.close()







