#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
This is the main file. 
From here all the functions are called the the whole workflow is described. 

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
dataNameList = ["3","4","5","6","7","17","20","25","28"]
dataNameListPreQ = ["3","4","5","6","7","10","11","15","17","18","20","25","28"]
dataName = '2'

# Some datapaths are different for the mac, so this boolean
mac = True

# Here you can turn the different processing steps on and off and define what parts should be run
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
EXPORT_FOR_DASHBOARD = True

exportShp =         True

TimelineStat =      True
TransmodeStat =     True
HomeWorkStat =      True


#%% LOAD ALL SAVED THRESHOLDS
if IMPORT_THRES:
    import ast
    
    inputFile = open("../data/stat/thresholds2405.txt", "r")
    lines = inputFile.readlines()
    
    objects = []
    for line in lines:
        objects.append( ast.literal_eval(line) )
    
    allthresholds = objects[0]
    
    thresholds = allthresholds[dataName]

# thresholds['accuracy_threshold'] = 200

#%% Pre-Questionnaire analysis to rank the interested questions

threshdf = pd.DataFrame.from_dict(allthresholds).T
# threshdf.to_csv('../data/allthreshods2405.csv', index=False)
dfStatistics = pd.read_csv('../data/statistics.csv',sep=",")
threshdf['id'] = threshdf.index.astype(int)
finalstat = pd.merge(threshdf,dfStatistics,left_on='id',right_on='id')
finalstat.to_csv('../data/allthreshods2405.csv', index=False)

pre = pd.read_csv('../data/pre.csv')
labels2score = {"Very interested":5,"Somewhat interested":4,"Neither interested or uninterested":3,"Somewhat uninterested":2,"Very uninterested":1}
cols = [str(i) for i in range(1,10)]    
for col in cols:
    pre=pre.replace({col: labels2score})
qmean = pre.mean()
highest = []
secHigh = []
for col in cols:
    # col="2"
    highest.append(len(pre[pre[col] == 5]))
    secHigh.append(len(pre[pre[col] == 4]))

#%% Merge the basic statistics of formal participants and Haojun & Daniel's

dfStatisticsAll = pd.read_csv('../data/statisticsAll.csv',sep=",")
dfStatistics = pd.read_csv('../data/statistics.csv',sep=",")
updatedStat = dfStatisticsAll.append(dfStatistics.iloc[0], ignore_index=True)
updatedStat = updatedStat.append(dfStatistics.iloc[1], ignore_index=True)
columns =['id','phoneModel','NumDays', 'NumPoints', 'AvgNumPoints','TotalDist', 'AvgDist', 'OneQuatile','Median','ThreeQuatile','Avg','30','40','50','60','70']
updatedStat = updatedStat[columns]
updatedStat2 = updatedStat.drop(['TotalDist', 'AvgDist', 'OneQuatile','Median','ThreeQuatile'],axis=1)
# labelsChange = {'Avg':'AvgAccuracy'}
updatedStat2 = updatedStat2.rename(columns={'Avg': 'AvgAccuracy'})

#%% CHOOSE THRESHOLDS - PART 1
if CHOOSE_THRES:
    # For the first time, run the following four lines to save the data
    dateStart = '2020-01-01'
    dateEnd = 'end'
    # stythred = thred.stydiffstat(dataNameList, SELECT_RANGE, dateStart, dateEnd)
    # stythred.to_csv('../data/csv'+'/StayDiffStatRange.csv', index=False)
    
    # Then read the data after the second time
    # staythred = pd.read_csv('../data/csv'+'/StayDiffStat.csv') 
    staythredrange = pd.read_csv('../data/csv'+'/StayDiffStatRange.csv') 
    
    # dfStatistics = calstat.accuracyStat(dataName, dataNameListPreQ, mac, dateStart, dateEnd)
    dfStatistics = pd.read_csv('../data/statisticsAll.csv',sep=",")
    
    # staythredrange[staythredrange['dataName']==int(dataName)]['dist_quarter'][dataNameList.index(dataName)],
    # staythredrange[staythredrange['dataName']==int(dataName)]['time_quarter'][dataNameList.index(dataName)],
    
    #allthresholds = {}
    
    # allthresholds.get('3')
    
    thresholds = {
        "accuracy_threshold" : 0,
        "dist_threshold" : 0,
        "time_threshold" : 15*60, #staythredrange[staythredrange['dataName']==int(dataName)]['dist_quarter'][dataNameList.index(dataName)],
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

    thresholds['dist_threshold'] = 150   

#%% IMPORT DATA %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
print("-> Loading the data")
dateStart = '2020-01-01'
dateEnd = 'end'
dataName = "21"
dataPathLocs,dataPathTrips = hlp.getDataPaths(dataName)

if SELECT_RANGE:    
    dataPathLocs,dataPathTrips = hlp.selectRange(dataPathLocs, dataPathTrips, mac, dateStart = thresholds["dateStart"], dateEnd = thresholds["dateEnd"],)
    
locs, locsgdf = hlp.parseLocs(dataPathLocs)
trips, tripdf, tripsgdf = hlp.parseTrips(dataPathTrips)

# add location data to the trips file (not used now because only for visualization of google results)
# tripsgdf = hlp.parseTripsWithLocs(dataPathTrips, locsgdf)

locs['d_diff'] = np.append(haversine_dist(locs.longitudeE7[1:], locs.latitudeE7[1:], locs.longitudeE7[:-1], locs.latitudeE7[:-1]),0)
if CHOOSE_THRES:
    thresholds['accuracy_threshold'] = np.quantile(locs['d_diff'], .95)

# export to shapefile
if exportShp:
    hlp.loc2shp(locsgdf, dataName)
    hlp.trip2shp(tripsgdf, dataName)

#%% FIND STAY POINTS
if FIND_STAY_POINTS:
    print("-> Finding stay points ")
    pfs,stps = main.findStayPoints(locs, dataName,thresholds["accuracy_threshold"],thresholds["dist_threshold"],thresholds["time_threshold"],thresholds["timemax_threshold"])
  
    if exportShp: 
        stps_shp = stps.copy()
        stps_shp['started_at'] = stps_shp['started_at'].astype(str)
        stps_shp['finished_at'] = stps_shp['finished_at'].astype(str)
        stps_shp.to_file('../data/shp/'+dataName +'/Staypoints.shp')
        
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

#%% FIND PLACES (CLUSTER OF STAY POINTS)

if FIND_PLACES:
    print("-> Finding the places ")

    plcs = main.findPlaces(stps, dataName, thresholds["minDist"], thresholds["minPoints"])
    
    if exportShp:
        plcs_shp = plcs.copy()
        plcs_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places.shp')
        
        # The following parts are to export the extent of the clustered places, not needed right now   
        # plcs_shp = plcs.copy()
        # plcs_shp.geometry = plcs_shp['extent']
        # plcs_shp_polygon = plcs_shp[plcs_shp['extent'].apply(lambda x: isinstance(x, Polygon))]
        # plcs_shp_polygon.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places_extent_polygon.shp')
        
        # plcs_shp = plcs.copy()
        # plcs_shp.geometry = plcs_shp['extent']               
        # plcs_shp_polyline = plcs_shp[plcs_shp['extent'].apply(lambda x: isinstance(x, LineString))]
        # plcs_shp_polyline.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places_extent_polyline.shp')

    plcs = poi.reverseGeoCoding(plcs)                  

#%% MATCH GOOGLE PLACES %%%%%%%
if FIND_SEMANTIC_INFO:
    dfStatistics = pd.read_csv('../data/statistics.csv', sep=',')
    dataStat = dfStatistics[dfStatistics['id']==int(dataName)]    
    threeQua = dataStat['ThreeQuatile'][dataNameList.index(dataName)]
    
    places = tripsgdf[tripsgdf['Type']=='placeVisit']
    places.drop_duplicates(subset ="placeId", keep = 'first', inplace = True) 
    places = places[~places.geometry.is_empty]
    
    dfStatistics = pd.read_csv('../data/statistics.csv',sep=",")
    dataStat = dfStatistics[dfStatistics['id']==int(dataName)]    
    threeQua = dataStat['ThreeQuatile'][dataNameList.index(dataName)]

    plcs = hlp.findSemanticInfo(places, plcs, threeQua)
            
    if exportShp:
        places['startTime'] = places['startTime'].astype(str)
        places['endTime'] = places['endTime'].astype(str)
        places.to_file('../data/shp/'+dataName +'/Places_google.shp')
 
#%% OUTPUT STATISTICS %%%%%%%%%%
if TimelineStat:
    plcs = calstat.plcsStayHour(stps, plcs, dataName)

if HomeWorkStat:
    homeworkplcs = calstat.homeworkStay(plcs, stps, dataName, places, threeQua)
    
    # homeplcs, homestps, workplcs, workstps = calstat.homeworkStay(stps, dataName, places, threeQua, thresholds["minDist"], thresholds["minPoints"])
        
    # homeplcs = hlp.findSemanticInfo(places, homeplcs, threeQua)
    # workplcs = hlp.findSemanticInfo(places, workplcs, threeQua) 

#%%
#% HOME WORK DETECTION
HOMEWORK = False
if HOMEWORK:

    homeworkplcs = pd.concat([homeplcs, workplcs], axis=0)
    homeworkplcs = homeworkplcs.reset_index(drop=True)
    homeworkplcs['place_id'] = homeworkplcs.index

    homeworkplcs = hlp.findSemanticInfo(places, homeworkplcs, threeQua=100)

    column_names = ["user_id","place_id","center","extent","location","placeName","id","totalStayDays","totalStayHrs","0","1","2","3","4","5","6"]
    homeworkplcs = homeworkplcs.reindex(columns=column_names)
    homeworkplcs = homeworkplcs.rename(columns={'0':'Mon','1':"Tues","2":"Wed","3":"Thur","4":"Fri","5":"Sat","6":"Sun"})  
    
    if not(os.path.exists('../data/stat/'+ dataName + '/')):
        os.makedirs('../data/stat/'+ dataName + '/')
    homeworkplcs.to_csv('../data/stat/'+ dataName + '/' + 'HomeWorkStay.csv', index = True)

    if exportShp: 
        HomeWork_shp = homeworkplcs.copy()
        # stps_shp['started_at'] = HomeWork_shp['started_at'].astype(str)
        HomeWork_shp['location'] = HomeWork_shp['location'].astype(str)
        HomeWork_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/HomeWork.shp')
        # HomeWork_shp.to_file('../data/shp/'+dataName +'/HomeWork.shp')

#%% CALCULATE HOME WORK HOURS
HOMEWORKHRS = False
if HOMEWORKHRS:
    
    # For dataName = '7'
    # homeHrs = pd.DataFrame(homestps[cols].sum(axis=0))/3600
    # workHrs = pd.DataFrame(workstps[cols].sum(axis=0))/3600
    # totalStay = homeHrs+workHrs
    
    # For dataName = '17'
    # homestps = homestps[homestps['place_id']==1]
    # homeHrs = pd.DataFrame(homestps[cols].sum(axis=0))/3600
    # workstps1 = workstps[workstps['place_id']==4]    
    # workHrs1 = pd.DataFrame(workstps1[cols].sum(axis=0))/3600
    # totalStay = homeHrs+workHrs
    # workstps2 = workstps[workstps['place_id']==1]   
    # workHrs2 = pd.DataFrame(workstps2[cols].sum(axis=0))/3600
    # workstps3 = workstps[workstps['place_id']==2]    
    # workHrs3 = pd.DataFrame(workstps3[cols].sum(axis=0))/3600   
    homeworkplcs2 = homeworkplcs.loc[[2,4,5],:]
    homeworkplcs2.to_csv('../data/stat/'+ dataName + '/' + 'HomeWorkStay.csv', index = True)
    
    #homeHrs = calstat.plcsStayHour(    , homeplcs, dataName)
    workHrs = calstat.plcsStayHour(workstps, workplcs, dataName)
    homeWorkHrs = pd.concat([homeHrs, workHrs], axis=0)

    homestps2 = homestps[homestps['place_id']==3]
    homeHrs2 = pd.DataFrame(homestps2[cols].sum(axis=0))/3600
    
    homeWorkHrsRep = homeWorkHrs.iloc[[0,1],]
    cols = [str(i) for i in range(0,24)]
    totalStay = pd.DataFrame(homeWorkHrsRep[cols].sum(axis=0))
    totalStay.to_csv('../data/stat/'+ dataName + '/' + 'totalStayrep.csv', index = True)
    
    homeWorkHrsNotrep = homeWorkHrs.iloc[[3,4],]
    totalStayNotrep = pd.DataFrame(homeWorkHrsNotrep[cols]).transpose()
    totalStayNotrep.to_csv('../data/stat/'+ dataName + '/' + 'totalStayNotrep.csv', index = True)
#%%
if TransmodeStat:
    transtat = calstat.pieChartInfoPlus(trips)
    calstat.transModeCsv(transtat, dataName)

#%% Find trips from staypoints
if FIND_TRIPS:
    print("-> Finding the trips ")

    tpls, trps, trpsCount = main.findTrips(pfs, stps, plcs, dataName)
    hlp.savecsv4jsTrps(dataName, trps)
    
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

if CLUSTER_TRPS:
    print("-> Cluster the trips")
    print("Number of trips before removing long trips " + str(len(trps)))
    trpsShort, trpsCount = hlp.removeLongTrips(trps.copy(), trpsCount.copy())
    print("Number of trips after removing long trips " + str(len(trpsShort)))

    trpsShort, trpsAgr = main.clusterTrips(trpsShort, trpsCount, thresholds["minDistTh"], thresholds["factorTh"], dataName, saveDendogramms=True)
    #trps, trpsAgr = main.clusterTrips(trps, trpsCount, 0.2, 2, dataName, saveDendogramms=True)

    if exportShp:
        
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
    version = 6

    if CHOOSE_THRES:
        thresholds["DP_tolerance"] = 0.00001
        thresholds["fisheye_factor"] = 0.5
        thresholds["curver_max"] = 360
        thresholds["curver_min"] = 0
        thresholds["curver_r"] = 20000
    
    # Find the coordinates of home (for the fisheye effect)
    temp = plcs[plcs['totalStayHrs']==plcs['totalStayHrs'].max()]['center']
    homeCoords = temp[temp.index[0]].coords[:][0]    
    
    # Call the API
    api.apiCall(dataName, 1000 * int(dataName) + version, homeCoords, thresholds["DP_tolerance"], thresholds["fisheye_factor"],thresholds["curver_min"], thresholds["curver_max"], thresholds["curver_r"])
    # Read the gpx response from the API 
    tripsAgrSchematic = api.readApiCall(trpsAgr.copy(), 1000*int(dataName)+version )
    
    trpsAgrSchematic_shp = tripsAgrSchematic.copy()
    trpsAgrSchematic_shp['weight'] = trpsAgrSchematic_shp['weight'].astype(int)
    trpsAgrSchematic_shp.to_file('../data/shp/'+dataName +'/TripsAggregatedSchemtic.shp')
 
#%%
if EXPORT_FOR_DASHBOARD:
    
    plcs['centerSchematic'] = None
    for i in range(len(tripsAgrSchematic)):
        plcs.loc[tripsAgrSchematic.loc[i,'start_plc']-1, 'centerSchematic'] = Point(tripsAgrSchematic.loc[i,'geom'].coords[0])
        plcs.loc[tripsAgrSchematic.loc[i,'end_plc']-1, 'centerSchematic'] = Point(tripsAgrSchematic.loc[i,'geom'].coords[-1])

    # Convert the final result to csv
    hlp.savecsv4js(dataName, plcs, trpsAgr, tripsAgrSchematic)    

    # Uncomment and run this part, to change the final thresholds!
    # allthresholds[dataName] = thresholds
    # outputFile = open("../data/stat/thresholds.txt", "w")
    # outputFile.write(str(allthresholds))
    # outputFile.flush()
    # outputFile.close()







