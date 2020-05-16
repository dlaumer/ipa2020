#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Statstics function
    This script collects statistics about the data of each participant
    
    Created on Thu Mar 28 2020
    Authors:    Daniel Laumer (laumerd@ethz.ch)
                Haojun Cai (caihao@ethz.ch)
    
"""
import pandas as pd
import numpy as np
import math
import json
import os

import datetime  
from datetime import datetime
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
import poi_classification as poi
#import noiserm_functions as nrm


def stats(locs, trips):
    """
    Get some statistics of the files 
    TODO: Add more statistics

    Parameters
    ----------
    locs : gdf - individual location data
    trips : dict - Semantic information (nested)

    Returns
    -------
    None.

    """
    countPlace = 0
    countAct = 0
    countPoints = 0
    for year in trips:
        for month in trips[year]:        
            for event in trips[year][month]:
                if list(event)[0] == 'placeVisit':
                    countPlace = countPlace + 1
                    countPoints = countPoints + 1
                elif list(event)[0] == 'activitySegment':
                    countAct = countAct + 1
                    countPoints = countPoints + 2
                    try:
                        countPoints = countPoints + len(event['activitySegment']['waypointPath']['waypoints'])
                    except:
                        pass
                    try:
                        countPoints = countPoints + len(event['activitySegment']['transitPath']['transitStops'])
                    except:
                        pass
    print('Number of points: '+str(len(locs)))
    print('Number of stays (placeVisit): '+ str(countPlace))
    print('Number of trips (activitySegment): ' + str(countAct))
    print('Number of points in the trip file: ' + str(countPoints))
    

def pieChartInfoPlus(trips):
    """
    Calculates the total distance per activity mode

    Parameters
    ----------
    trips : dict - Semantic information (nested)

    Returns
    -------
    list(data): list - labels of the activity modes
    list(data.values()): list - distance per activity mode

    """
    labels = ["IN_PASSENGER_VEHICLE","STILL","WALKING","IN_BUS","CYCLING","FLYING","RUNNING","IN_FERRY","IN_TRAIN","SKIING","SAILING","IN_SUBWAY","IN_TRAM","IN_VEHICLE"]
    data = {}
    for year in trips:
        for month in trips[year]:        
            for event in trips[year][month]:
                if list(event)[0] == 'activitySegment':
                    try:
                        dist = event['activitySegment']['distance']
                    except:
                        print('There is no distance!')
                    for label in labels:
                        if label == event['activitySegment']['activityType']:
                            data[label] = data.get(label,0) + dist
    
    
    return list(data), list(data.values())


def transModeCsv(transtat, dataname):
    """
    Generate csv including percentage for transportation modes

    Parameters
    ----------
    transtat : tuple - returned results of pieChartInfoPlus() function
    dataname: str
    
    Returns
    -------
    None
    """
    
    transtatdf = pd.DataFrame(list(transtat))
    transtatdf = transtatdf.T
    transtatdf['percentage'] = ""
    transtatdf.columns = ['mode','value','percentage']
    
    for i in range(0,len(transtatdf)):
        valsum = transtatdf['value'].sum(axis=0)
        transtatdf.iloc[i,2] = round(transtatdf.iloc[i,1]/valsum,4)
    
    transtatdf.sort_values("percentage", axis = 0, ascending = False, 
                     inplace = True, na_position ='last') 
        
    if not(os.path.exists('../data/stat/'+ dataname + '/')):
        os.makedirs('../data/stat/'+ dataname + '/')
    transtatdf.to_csv('../data/stat/'+dataname+'/TransportationMode.csv', index = True)
    
    
def plcsStayWorkday(stps, plcs, dataname):
    """
    Calculate stay time statistics of each place for each working day

    Parameters
    ----------
    stps : dataframe - stay points
    plcs: dataframe - clustered places

    Returns
    -------
    None
    """

    # Calculate stay time for each stay point
    stps['stay_time'] = 0
    for i in range(0,len(stps)):
        stps['stay_time'].iloc[i] = (stps['finished_at'].iloc[i]-stps['started_at'].iloc[i]).total_seconds()
    
    # Calcualte stay time for each place for each working day
    stps['started_at_weekday'] = 0
    for i in range(0,len(stps)): stps['started_at_weekday'].iloc[i] = stps['started_at'].iloc[i].weekday() # 0 for Monday, 6 for Sunday
    
    # Summarize stay time by weekday for each clustered place
    cols = ['Mon_totalstay','Tues_totalstay','Wed_totalstay','Thur_totalstay','Fri_totalstay','Sat_totalstay','Sun_totalstay']
    for col in cols: plcs[col] = 0
    for i in range(0,len(plcs)):
        place_id = i+1
        stps_placeid = stps[stps['place_id']==place_id]
        stps_placeid_weekday1 = stps_placeid[stps_placeid['started_at_weekday']==0]
        plcs.loc[plcs['place_id']==place_id,'Mon_totalstay']=stps_placeid_weekday1['stay_time'].sum()
        stps_placeid_weekday2 = stps_placeid[stps_placeid['started_at_weekday']==1]
        plcs.loc[plcs['place_id']==place_id,'Tues_totalstay']=stps_placeid_weekday2['stay_time'].sum()
        stps_placeid_weekday3 = stps_placeid[stps_placeid['started_at_weekday']==2]
        plcs.loc[plcs['place_id']==place_id,'Wed_totalstay']=stps_placeid_weekday3['stay_time'].sum()
        stps_placeid_weekday4 = stps_placeid[stps_placeid['started_at_weekday']==3]
        plcs.loc[plcs['place_id']==place_id,'Thur_totalstay']=stps_placeid_weekday4['stay_time'].sum()
        stps_placeid_weekday5 = stps_placeid[stps_placeid['started_at_weekday']==4]
        plcs.loc[plcs['place_id']==place_id,'Fri_totalstay']=stps_placeid_weekday5['stay_time'].sum()
        stps_placeid_weekday6 = stps_placeid[stps_placeid['started_at_weekday']==5]
        plcs.loc[plcs['place_id']==place_id,'Sat_totalstay']=stps_placeid_weekday6['stay_time'].sum()
        stps_placeid_weekday7 = stps_placeid[stps_placeid['started_at_weekday']==6]
        plcs.loc[plcs['place_id']==place_id,'Sun_totalstay']=stps_placeid_weekday7['stay_time'].sum()
    for col in cols: plcs[col] =  plcs[col]/60 # in min

    # V1: simple matrix with hour x place_id
    plcstocsv = plcs[cols]
    plcstocsv_transpose = plcstocsv.T
    plcstocsv_transpose.columns = plcs['place_id']
    if not(os.path.exists('../data/stat/'+ dataname + '/')):
        os.makedirs('../data/stat/'+ dataname + '/')
    plcstocsv_transpose.to_csv('../data/stat/'+ dataname + '/' + '/StaybyWorkday.csv', index = True)
    
    # V2: with more information
    plcs = poi.reverseGeoCoding(plcs)
    plcstocsv_transpose.columns = plcs['location']
    plcstocsv_transpose.to_csv('../data/stat/'+ dataname + '/' + '/StaybyWorkdayLocinfo.csv', index = True)


def plcsStayHour(stps, plcs, dataname):
    """
    Calculate stay time statistics of each place for each hour

    Parameters
    ----------
    stps : dataframe - stay points
    plcs: dataframe - clustered places

    Returns
    -------
    None
    """
        
    # Calculate stay time
    stps['stay_time'] = 0
    for i in range(0,len(stps)):
        stps['stay_time'].iloc[i] = (stps['finished_at'].iloc[i]-stps['started_at'].iloc[i]).total_seconds()
        
    # Calcualte stay time for each place for each hour
    stps['started_at_hour'] = 0
    for i in range(0,len(stps)): stps['started_at_hour'].iloc[i] = stps['started_at'].iloc[i].hour
    
    # Summarize stay time by hour for each clustered place
    cols = [str(i) for i in range(0,24)]
    for col in cols: plcs[col] = 0
    
    for i in range(0,len(plcs)):
        place_id = i+1
        stps_placeid = stps[stps['place_id']==place_id]
        for j in range(0,len(cols)):
            stps_placeid_hour = stps_placeid[stps_placeid['started_at_hour']==j]
            plcs.loc[plcs['place_id']==place_id,cols[j]]=stps_placeid_hour['stay_time'].sum()
    
    for col in cols: plcs[col] =  plcs[col]/60

    # V1: simple matrix with hour x place_id
    plcstocsv = plcs[cols]
    plcstocsv_transpose = plcstocsv.T
    plcstocsv_transpose.columns = plcs['place_id']
    if not(os.path.exists('../data/stat/'+ dataname + '/')):
        os.makedirs('../data/stat/'+ dataname + '/')
    plcstocsv_transpose.to_csv('../data/stat/'+ dataname + '/' + '/StaybyHour.csv', index = True)
    
    # V2: with more information
    plcs = poi.reverseGeoCoding(plcs)
    plcstocsv_transpose.columns = plcs['placeName']
    plcstocsv_transpose.to_csv('../data/stat/'+ dataname + '/' + '/StaybyHourLocinfo.csv', index = True)
    
    
def homeworkStay(pfs, dataname, dist_threshold, time_threshold, minDist, minPoints):
    """
    Calculate stay time statistics of home and work places for all past data

    Parameters
    ----------
    pfs : dataframe - location points
    dataname: str
    dist_threshold, time_threshold - parameters for stay point detection
    minDist, minPoints - parameters for DBSCAN Clustering

    Returns
    -------
    None
    """
    
    pfs['tracked_at_hour'] = 0
    for i in range(0,len(pfs)): pfs['tracked_at_hour'].iloc[i] = pfs['tracked_at'].iloc[i].hour
    pfs['tracked_at_weekday'] = 0
    for i in range(0,len(pfs)): pfs['tracked_at_weekday'].iloc[i] = pfs['tracked_at'].iloc[i].weekday() # 0 for Monday, 6 for Sunday
    
    ## HOME ADDRESS
    homepfs = pfs[(pfs['tracked_at_hour']<=7) | (pfs['tracked_at_hour']>=22)]
    homestps = tim.extract_staypoints_ipa(homepfs, method='sliding',dist_threshold=dist_threshold, time_threshold=time_threshold)
    homeplcs = homestps.as_staypoints.extract_places(method='dbscan',epsilon=meters_to_decimal_degrees(minDist, 47.5), num_samples=minPoints)
 
    # HOME ADDRESS STATISTICS
    ## calcualte stay time for each place for each working day
    homestps['started_at_hour'] = 0
    for i in range(0,len(homestps)): homestps['started_at_hour'].iloc[i] = homestps['started_at'].iloc[i].hour
    homestps['started_at_weekday'] = 0
    for i in range(0,len(homestps)): homestps['started_at_weekday'].iloc[i] = homestps['started_at'].iloc[i].weekday() # 0 for Monday, 6 for Sunday
    
    # calculate stay time
    homestps['stay_time'] = 0
    for i in range(0,len(homestps)):
        homestps['stay_time'].iloc[i] = (homestps['finished_at'].iloc[i]-homestps['started_at'].iloc[i]).total_seconds()
    
    # summarize stay time by weekday for each clustered place
    cols = ['Sun','Sat','Fri','Thur','Wed','Tues','Mon']
    for col in cols: homeplcs[col] = 0
    for i in range(0,len(homeplcs)):
        place_id = i+1
        homestps_placeid = homestps[homestps['place_id']==place_id]
        homestps_placeid_weekday1 = homestps_placeid[homestps_placeid['started_at_weekday']==0]
        homeplcs.loc[homeplcs['place_id']==place_id,'Mon']=homestps_placeid_weekday1['stay_time'].sum()
        homestps_placeid_weekday2 = homestps_placeid[homestps_placeid['started_at_weekday']==1]
        homeplcs.loc[homeplcs['place_id']==place_id,'Tues']=homestps_placeid_weekday2['stay_time'].sum()
        homestps_placeid_weekday3 = homestps_placeid[homestps_placeid['started_at_weekday']==2]
        homeplcs.loc[homeplcs['place_id']==place_id,'Wed']=homestps_placeid_weekday3['stay_time'].sum()
        homestps_placeid_weekday4 = homestps_placeid[homestps_placeid['started_at_weekday']==3]
        homeplcs.loc[homeplcs['place_id']==place_id,'Thur']=homestps_placeid_weekday4['stay_time'].sum()
        homestps_placeid_weekday5 = homestps_placeid[homestps_placeid['started_at_weekday']==4]
        homeplcs.loc[homeplcs['place_id']==place_id,'Fri']=homestps_placeid_weekday5['stay_time'].sum()
        homestps_placeid_weekday6 = homestps_placeid[homestps_placeid['started_at_weekday']==5]
        homeplcs.loc[homeplcs['place_id']==place_id,'Sat']=homestps_placeid_weekday6['stay_time'].sum()
        homestps_placeid_weekday7 = homestps_placeid[homestps_placeid['started_at_weekday']==6]
        homeplcs.loc[homeplcs['place_id']==place_id,'Sun']=homestps_placeid_weekday7['stay_time'].sum()
           
    for col in cols: homeplcs[col] =  round(homeplcs[col]/3600,1)
    
    # WORKING ADDRESS
    # choose only working days and hours
    workpfs = pfs[pfs['tracked_at_weekday']<=4] 
    workpfs = workpfs[((workpfs['tracked_at_hour']>=9) & (workpfs['tracked_at_hour']<=12)) | ((workpfs['tracked_at_hour']>=14) & (workpfs['tracked_at_hour']<=17))]
    
    workstps = tim.extract_staypoints_ipa(workpfs, method='sliding',dist_threshold=100, time_threshold=15*60)
    workplcs = workstps.as_staypoints.extract_places(method='dbscan',epsilon=meters_to_decimal_degrees(80, 47.5), num_samples=6)
    # workstps = tim.extract_staypoints_ipa(workpfs, method='sliding',dist_threshold=100, time_threshold=15*60)
    # workplcs = workstps.as_staypoints.extract_places(method='dbscan',epsilon=meters_to_decimal_degrees(30,10), num_samples=6)
    
    ## WORKING ADDRESS STATISTICS
    # calcualte stay time for each place for each working day
    workstps['started_at_hour'] = 0
    for i in range(0,len(workstps)): workstps['started_at_hour'].iloc[i] = workstps['started_at'].iloc[i].hour
    workstps['started_at_weekday'] = 0
    for i in range(0,len(workstps)): workstps['started_at_weekday'].iloc[i] = workstps['started_at'].iloc[i].weekday() # 0 for Monday, 6 for Sunday
    
    # calculate stay time
    workstps['stay_time'] = 0
    for i in range(0,len(workstps)):
        workstps['stay_time'].iloc[i] = (workstps['finished_at'].iloc[i]-workstps['started_at'].iloc[i]).total_seconds()
    
    # summarize stay time by weekday for each clustered place
    cols = ['Sun','Sat','Fri','Thur','Wed','Tues','Mon']
    for col in cols: workplcs[col] = 0
    for i in range(0,len(workplcs)):
        place_id = i+1
        workstps_placeid = workstps[workstps['place_id']==place_id]
        workstps_placeid_weekday1 = workstps_placeid[workstps_placeid['started_at_weekday']==0]
        workplcs.loc[workplcs['place_id']==place_id,'Mon']=workstps_placeid_weekday1['stay_time'].sum()
        workstps_placeid_weekday2 = workstps_placeid[workstps_placeid['started_at_weekday']==1]
        workplcs.loc[workplcs['place_id']==place_id,'Tues']=workstps_placeid_weekday2['stay_time'].sum()
        workstps_placeid_weekday3 = workstps_placeid[workstps_placeid['started_at_weekday']==2]
        workplcs.loc[workplcs['place_id']==place_id,'Wed']=workstps_placeid_weekday3['stay_time'].sum()
        workstps_placeid_weekday4 = workstps_placeid[workstps_placeid['started_at_weekday']==3]
        workplcs.loc[workplcs['place_id']==place_id,'Thur']=workstps_placeid_weekday4['stay_time'].sum()
        workstps_placeid_weekday5 = workstps_placeid[workstps_placeid['started_at_weekday']==4]
        workplcs.loc[workplcs['place_id']==place_id,'Fri']=workstps_placeid_weekday5['stay_time'].sum()
        workstps_placeid_weekday6 = workstps_placeid[workstps_placeid['started_at_weekday']==5]
        workplcs.loc[workplcs['place_id']==place_id,'Sat']=workstps_placeid_weekday6['stay_time'].sum()
        workstps_placeid_weekday7 = workstps_placeid[workstps_placeid['started_at_weekday']==6]
        workplcs.loc[workplcs['place_id']==place_id,'Sun']=workstps_placeid_weekday7['stay_time'].sum()
        
    for col in cols: workplcs[col] =  round(workplcs[col]/3600,1)
    
    homeplcs = poi.reverseGeoCoding(homeplcs)
    homeplcs['id'] = 'home'
    workplcs = poi.reverseGeoCoding(workplcs)
    workplcs['id'] = 'work'
    homeworkplcs = pd.concat([homeplcs, workplcs], axis=0)
    
    if not(os.path.exists('../data/stat/'+ dataname + '/')):
        os.makedirs('../data/stat/'+ dataname + '/')
    homeworkplcs.to_csv('../data/stat/'+ dataname + '/' + 'HomeWorkStay.csv', index = True)


def homeworkStayMonth(pfs, dataname, dist_threshold, time_threshold, minDist, minPoints):
    """
    Calculate stay time statistics of home and work places for all past data by Month

    Parameters
    ----------
    pfs : dataframe - location points
    dataname: str
    dist_threshold, time_threshold - parameters for stay point detection
    minDist, minPoints - parameters for DBSCAN Clustering
    
    Returns
    -------
    None
    """
    
    pfs['tracked_at_hour'] = 0
    for i in range(0,len(pfs)): pfs['tracked_at_hour'].iloc[i] = pfs['tracked_at'].iloc[i].hour
    
    ### For home address ###
    # homepfs = pfs[(pfs['tracked_at_hour']<=6)]
    homepfs = pfs[(pfs['tracked_at_hour']<=7) | (pfs['tracked_at_hour']>=22)]
    homestps = tim.extract_staypoints_ipa(homepfs, method='sliding',dist_threshold=dist_threshold, time_threshold=time_threshold)
    # homestps = tim.extract_staypoints_ipa(homepfs, method='sliding',dist_threshold=5, time_threshold=1*60)
    # homeplcs = homestps.as_staypoints.extract_places(method='dbscan',epsilon=meters_to_decimal_degrees(10,2), num_samples=6)
    
    homestps['started_at_hour'] = 0
    for i in range(0,len(homestps)): homestps['started_at_hour'].iloc[i] = homestps['started_at'].iloc[i].hour
    homestps['started_at_month'] = 0
    for i in range(0,len(homestps)): homestps['started_at_month'].iloc[i] = homestps['started_at'].iloc[i].month
    homestps['started_at_weekday'] = 0
    for i in range(0,len(homestps)): homestps['started_at_weekday'].iloc[i] = homestps['started_at'].iloc[i].weekday() # 0 for Monday, 6 for Sunday
    
    homestps['stay_time'] = 0 
    for i in range(0,len(homestps)): # calculate stay time
        homestps['stay_time'].iloc[i] = (homestps['finished_at'].iloc[i]-homestps['started_at'].iloc[i]).total_seconds()
    
    ### For working address ###
    pfs['tracked_at_weekday'] = 0
    for i in range(0,len(pfs)): pfs['tracked_at_weekday'].iloc[i] = pfs['tracked_at'].iloc[i].weekday() # 0 for Monday, 6 for Sunday
    
    workpfs = pfs[pfs['tracked_at_weekday']<=4] 
    workpfs = workpfs[((workpfs['tracked_at_hour']>=9) & (workpfs['tracked_at_hour']<=12)) | ((workpfs['tracked_at_hour']>=14) & (workpfs['tracked_at_hour']<=17))]
    workstps = tim.extract_staypoints_ipa(workpfs, method='sliding',dist_threshold=dist_threshold, time_threshold=time_threshold)
    
    workstps['started_at_hour'] = 0
    for i in range(0,len(workstps)): workstps['started_at_hour'].iloc[i] = workstps['started_at'].iloc[i].hour
    workstps['started_at_month'] = 0
    for i in range(0,len(workstps)): workstps['started_at_month'].iloc[i] = workstps['started_at'].iloc[i].month
    workstps['started_at_weekday'] = 0
    for i in range(0,len(workstps)): workstps['started_at_weekday'].iloc[i] = workstps['started_at'].iloc[i].weekday() # 0 for Monday, 6 for Sunday
    
    workstps['stay_time'] = 0
    for i in range(0,len(workstps)):
        workstps['stay_time'].iloc[i] = (workstps['finished_at'].iloc[i]-workstps['started_at'].iloc[i]).total_seconds()
    
    months = np.unique(homestps['started_at_month'])
    
    for month in months:
        # month = 2
        # Select data by month
        homestps_month = homestps[homestps['started_at_month']==month]
        homeplcs = homestps_month.as_staypoints.extract_places(method='dbscan',epsilon=meters_to_decimal_degrees(minDist, 47.5), num_samples=minPoints)
        workstps_month = workstps[workstps['started_at_month']==month]
        workplcs = workstps.as_staypoints.extract_places(method='dbscan',epsilon=meters_to_decimal_degrees(minDist, 47.5), num_samples=minPoints)
    
        # summarize stay time by weekday for each clustered place
        cols = ['Mon','Tues','Wed','Thur','Fri','Sat','Sun']
        for col in cols: homeplcs[col] = 0
        for i in range(0,len(homeplcs)):
            place_id = i+1
            homestps_placeid = homestps_month[homestps_month['place_id']==place_id]
            homestps_placeid_weekday1 = homestps_placeid[homestps_placeid['started_at_weekday']==0]
            homeplcs.loc[homeplcs['place_id']==place_id,'Mon']=homestps_placeid_weekday1['stay_time'].sum()
            homestps_placeid_weekday2 = homestps_placeid[homestps_placeid['started_at_weekday']==1]
            homeplcs.loc[homeplcs['place_id']==place_id,'Tues']=homestps_placeid_weekday2['stay_time'].sum()
            homestps_placeid_weekday3 = homestps_placeid[homestps_placeid['started_at_weekday']==2]
            homeplcs.loc[homeplcs['place_id']==place_id,'Wed']=homestps_placeid_weekday3['stay_time'].sum()
            homestps_placeid_weekday4 = homestps_placeid[homestps_placeid['started_at_weekday']==3]
            homeplcs.loc[homeplcs['place_id']==place_id,'Thur']=homestps_placeid_weekday4['stay_time'].sum()
            homestps_placeid_weekday5 = homestps_placeid[homestps_placeid['started_at_weekday']==4]
            homeplcs.loc[homeplcs['place_id']==place_id,'Fri']=homestps_placeid_weekday5['stay_time'].sum()
            homestps_placeid_weekday6 = homestps_placeid[homestps_placeid['started_at_weekday']==5]
            homeplcs.loc[homeplcs['place_id']==place_id,'Sat']=homestps_placeid_weekday6['stay_time'].sum()
            homestps_placeid_weekday7 = homestps_placeid[homestps_placeid['started_at_weekday']==6]
            homeplcs.loc[homeplcs['place_id']==place_id,'Sun']=homestps_placeid_weekday7['stay_time'].sum()
        
        for col in cols: workplcs[col] = 0
        for i in range(0,len(workplcs)):
            place_id = i+1
            workstps_placeid = workstps[workstps['place_id']==place_id]
            workstps_placeid_weekday1 = workstps_placeid[workstps_placeid['started_at_weekday']==0]
            workplcs.loc[workplcs['place_id']==place_id,'Mon']=workstps_placeid_weekday1['stay_time'].sum()
            workstps_placeid_weekday2 = workstps_placeid[workstps_placeid['started_at_weekday']==1]
            workplcs.loc[workplcs['place_id']==place_id,'Tues']=workstps_placeid_weekday2['stay_time'].sum()
            workstps_placeid_weekday3 = workstps_placeid[workstps_placeid['started_at_weekday']==2]
            workplcs.loc[workplcs['place_id']==place_id,'Wed']=workstps_placeid_weekday3['stay_time'].sum()
            workstps_placeid_weekday4 = workstps_placeid[workstps_placeid['started_at_weekday']==3]
            workplcs.loc[workplcs['place_id']==place_id,'Thur']=workstps_placeid_weekday4['stay_time'].sum()
            workstps_placeid_weekday5 = workstps_placeid[workstps_placeid['started_at_weekday']==4]
            workplcs.loc[workplcs['place_id']==place_id,'Fri']=workstps_placeid_weekday5['stay_time'].sum()
            workstps_placeid_weekday6 = workstps_placeid[workstps_placeid['started_at_weekday']==5]
            workplcs.loc[workplcs['place_id']==place_id,'Sat']=workstps_placeid_weekday6['stay_time'].sum()
            workstps_placeid_weekday7 = workstps_placeid[workstps_placeid['started_at_weekday']==6]
            workplcs.loc[workplcs['place_id']==place_id,'Sun']=workstps_placeid_weekday7['stay_time'].sum()
        
        for col in cols: 
            homeplcs[col] =  homeplcs[col]/60
            workplcs[col] =  workplcs[col]/60
    
        homeplcs = poi.reverseGeoCoding(homeplcs)
        homeplcs['id'] = 'home'
        workplcs = poi.reverseGeoCoding(workplcs)
        workplcs['id'] = 'work'
        homeworkplcs = pd.concat([homeplcs, workplcs], axis=0)

        if not(os.path.exists('../data/stat/'+ dataname + '/')):
            os.makedirs('../data/stat/'+ dataname + '/')
        homeworkplcs.to_csv('../data/stat/'+ dataname + '/' + str(month) + 'HomeWorkStaybyMonth.csv', index = True)
    
    
def accuracyStat(dataName, dataNames, timestart, timeend):
    # Trip files
    if len(dataNames) == 0:
        for root,dirs,files in os.walk("../../4-Collection/DataParticipants/"):
            dataNames = dirs
            break
    
    dfQuestionnaire = pd.read_csv("../data/Pre-Questionnaire - Location Diary.csv")
    dfPhoneModel = dfQuestionnaire[["Enter your participant ID:","What is your mobile phone's brand used to collect data?"]]
    dfPhoneModel = dfPhoneModel.rename(columns = {"id":"Enter your participant ID:", "phoneModel":"What is your mobile phone's brand used to collect data?"})
    
    generated_dfStatistics = []
    
    for dataName in dataNames:
        print('Processing '+ dataName)
        dfStatistics = pd.DataFrame(columns =['id','30','40','50','60','70', 'NumDays', 'NumPoints', 'AvgNumPoints', 'phoneModel','dateStart','dateEnd'])

        tempStat = {}

        #dfStatistics = dfStatistics.append(pd.Series(name=dataName))
        tempStat['id'] = dataName
        
        dataPathLocs,dataPathTrips = hlp.getDataPaths(dataName)
        dataPathLocs,dataPathTrips,labelStart,labelEnd = hlp.selectRange(dataPathLocs, dataPathTrips, dateStart = timestart, dateEnd = timeend)
        
        locs, locsgdf = hlp.parseLocs(dataPathLocs)
        #trips, tripdf, tripsgdf = hlp.parseTrips(dataPathTrips)
    
        tempStat['dateStart'] = labelStart
        tempStat['dateEnd'] = lebelEnd
        
        # Number of points per day
        idx = pd.date_range(locs.index[0].date(), locs.index[-1].date())
        perDay = (locs.groupby(locs.index.date).count()['timestampMs'])
        #perDay = perDay.reindex(idx, fill_value=0)
        tempStat['NumDays'] = len(perDay)
        tempStat['NumPoints'] = perDay.sum()
        tempStat['AvgNumPoints'] = perDay.mean()
        
        #hlp.checkTrips(trips)
        tempStat['phoneModel'] = dfPhoneModel.loc[np.where(dfPhoneModel["Enter your participant ID:"] == int(dataName))[0][0],"What is your mobile phone's brand used to collect data?"]
        
        #Accuracy
        for i in [30,40,50,60,70]:
            tempStat[str(i)] =  round(100*len(locs[locs['accuracy'].lt(i)])/len(locs),2)
            
        generated_dfStatistics.append(tempStat)
        dfStatistics = dfStatistics.append(generated_dfStatistics)
        
        dfStatistics.to_csv('../data/statistics.csv', index=False, sep=';')
    return dfStatistics
