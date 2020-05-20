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
import main_functions as main
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
                        for label in labels:
                            if label == event['activitySegment']['activityType']:
                                data[label] = data.get(label,0) + dist

                    except:
                        print('There is no distance!')
    
    
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

    # labels = ["IN_PASSENGER_VEHICLE","STILL","WALKING","IN_BUS","CYCLING","FLYING","RUNNING","IN_FERRY","IN_TRAIN","SKIING","SAILING","IN_SUBWAY","IN_TRAM","IN_VEHICLE"]
    # modes = ['by Car','by Train','by Plane','Walking','by Bus','by Bike','by Ferry','by Tram','Running']
    labels2modes = {"IN_PASSENGER_VEHICLE":'by Car',"STILL":'Still',"WALKING": 'Walking',"IN_BUS": 'by Bus',"CYCLING":'by Bike',"FLYING":'by Plane',"RUNNING":'Running',"IN_FERRY":'by Ferry',"IN_TRAIN": 'by Train',"SKIING": 'Skiing',"SAILING": 'Sailing',"IN_SUBWAY": 'by Subway',"IN_TRAM": 'by Tram',"IN_VEHICLE":'in Vehicle'} 

    transtatdf['name'] = transtatdf['mode']
    transtatdf=transtatdf.replace({"name": labels2modes})
    
    if not(os.path.exists('../data/stat/'+ dataname + '/')):
        os.makedirs('../data/stat/'+ dataname + '/')
    transtatdf.to_csv('../../5-Final Product/stat'+dataname+'/TransportationMode.csv', index = True)
    
    
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
    
    cols = [str(i) for i in range(0,24)]
    for col in cols: plcs[col] = 0

    cols = [str(i) for i in range(0,24)]
    for col in cols: stps[col] = 0
      
    # Calculate stay time
    stps['daydiff'] = 0
    stps['hourdiff'] = 0
    stps['monthdiff'] = 0
    
    for i in range(0,len(stps)):
        timedelta = stps['finished_at'].iloc[i] - stps['started_at'].iloc[i]
        stps['daydiff'].iloc[i] = stps['finished_at'].iloc[i].day - stps['started_at'].iloc[i].day
        stps['hourdiff'].iloc[i] = stps['finished_at'].iloc[i].hour - stps['started_at'].iloc[i].hour
        stps['monthdiff'].iloc[i] = stps['finished_at'].iloc[i].month - stps['started_at'].iloc[i].month

        list31 = [1,3,5,7,8,10,12]
        list30 = [4,6,9,11]
        listFeb = [2] 
        if (stps['monthdiff'].iloc[i] >= 1):
            startMonth = stps['started_at'].iloc[i].month
            if (startMonth in list31):
                stps['daydiff'].iloc[i] += 31
            elif (startMonth in list30):
                stps['daydiff'].iloc[i] += 30
            elif (startMonth in listFeb):
                stps['daydiff'].iloc[i] += 29; # change based on current year
            else:
                print("invalid start month")
        if (stps['monthdiff'].iloc[i] >= 2):
            secMonth = stps['started_at'].iloc[i].month+1
            if (secMonth in list31):
                stps['daydiff'].iloc[i] += 31
            elif (secMonth in list30):
                stps['daydiff'].iloc[i] += 30
            elif (secMonth in listFeb):
                stps['daydiff'].iloc[i] += 29; # change based on current year
            else:
                print("invalid start month")
                
        if (stps['daydiff'].iloc[i] == 0):
            startHour = stps['started_at'].iloc[i].hour
            endHour = stps['finished_at'].iloc[i].hour
            if (stps['hourdiff'].iloc[i] == 0):
                stps[str(startHour)].iloc[i] = 3600 - stps['started_at'].iloc[i].minute*60 - stps['started_at'].iloc[i].second
            elif (stps['hourdiff'].iloc[i] == 1):
                stps[str(startHour)].iloc[i] = 3600 - stps['started_at'].iloc[i].minute*60 - stps['started_at'].iloc[i].second
                stps[str(endHour)].iloc[i] = stps['finished_at'].iloc[i].minute*60 + stps['finished_at'].iloc[i].second
            elif (stps['hourdiff'].iloc[i] >= 2):
                stps[str(startHour)].iloc[i] = 3600 - stps['started_at'].iloc[i].minute*60 - stps['started_at'].iloc[i].second
                stps[str(endHour)].iloc[i] = stps['finished_at'].iloc[i].minute*60 + stps['finished_at'].iloc[i].second
                for midHour in range(startHour+1, endHour):
                    stps[str(midHour)].iloc[i] = 3600  
            else:
                print('Wrong hour difference! Please check your data.')
        elif (stps['daydiff'].iloc[i] == 1):
            startHour = stps['started_at'].iloc[i].hour
            endHour = stps['finished_at'].iloc[i].hour
            stps[str(startHour)].iloc[i] = 3600 - stps['started_at'].iloc[i].minute*60 - stps['started_at'].iloc[i].second
            stps[str(endHour)].iloc[i] = stps['finished_at'].iloc[i].minute*60 + stps['finished_at'].iloc[i].second
            for midHourSday in range(startHour+1, 24):
                stps[str(midHourSday)].iloc[i] += 3600  
            for midHourEday in range(0, endHour):
                stps[str(midHourEday)].iloc[i] += 3600              
        elif (stps['daydiff'].iloc[i] >= 2):
            wholeDays = stps['daydiff'].iloc[i] - 1;
            for wholeHour in range(0, 24):
                stps[str(wholeHour)].iloc[i] = 3600*wholeDays
            # repetitive as for daydiff==1
            startHour = stps['started_at'].iloc[i].hour
            endHour = stps['finished_at'].iloc[i].hour
            stps[str(startHour)].iloc[i] += (3600 - stps['started_at'].iloc[i].minute*60 - stps['started_at'].iloc[i].second)
            stps[str(endHour)].iloc[i] += (stps['finished_at'].iloc[i].minute*60 + stps['finished_at'].iloc[i].second)
            for midHourSday in range(startHour+1, 24):
                stps[str(midHourSday)].iloc[i] += 3600  
            for midHourEday in range(0, endHour):
                stps[str(midHourEday)].iloc[i] += 3600             
        else:
            print("Wrong day difference! Please check your codes.")
                
    for i in range(0,len(plcs)):
        plcid = i+1
        stps_plcid = stps[stps['place_id']==plcid]
        
        for col in cols:
            stps_placeid_hour = stps_plcid[col]
            plcs.loc[plcs['place_id']==plcid,col]=stps_placeid_hour.sum()
    
    for col in cols: plcs[col] = plcs[col]/3600 # convert unit from second to hour
    
    tempcols = plcs[cols]
    plcs['totalStayHrs'] = tempcols.sum(axis=1)
    
    # V1: simple matrix with hour x place_id
    plcstocsv = plcs[cols]
    plcstocsv_transpose = plcstocsv.T
    plcstocsv_transpose.columns = plcs['place_id']
    if not(os.path.exists('../data/stat/'+ dataname + '/')):
        os.makedirs('../data/stat/'+ dataname + '/')
    #plcstocsv_transpose.to_csv('../data/stat/'+ dataname + '/PlcsStayHour.csv', index = True)
    plcstocsv_transpose.to_csv('../../5-Final Product/stat'+ dataname + '/PlcsStayHour.csv', index = True)

    # V2: with more information
    plcs = poi.reverseGeoCoding(plcs)
    plcsInfo = plcs[['place_id','location','placeName']]
    plcsInfoT = plcsInfo.T
    plcsInfoT.columns = plcs['place_id']
    plcsInfoT.to_csv('../../5-Final Product/stat'+ dataname + '/PlcsInfo.csv', index = True)


    # column_names = ["user_id","place_id","center","extent","location","placeName","nameId",'totalStayHrs',"0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","23"]
    column_names = ["user_id","place_id","center","extent","location","placeName","nameId","totalStayHrs","id","0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","23"]
    
    plcs = plcs.reindex(columns=column_names)
    
    return plcs    
    
def homeworkStay(stps, dataname, places, threeQua, minDist, minPoints):
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
    
    stps['tracked_at_hour'] = 0
    for i in range(0,len(stps)): stps['tracked_at_hour'].iloc[i] = stps['started_at'].iloc[i].hour
    stps['t_diff'] = 0
    for i in range(0,len(stps)): stps['t_diff'].iloc[i] = (stps['finished_at'].iloc[i] - stps['started_at'].iloc[i]).total_seconds()/3600
    
    ## HOME ADDRESS   
    homestps = stps[(stps['tracked_at_hour']<=5) | (stps['tracked_at_hour']>=22) | (stps['t_diff']>=18)]
    homeplcs = main.findPlaces(homestps, dataname, minDist, minPoints) 
    homeplcs = poi.reverseGeoCoding(homeplcs)
    
    cols = [str(i) for i in range(0,7)]
    for col in cols: homeplcs[col] = 0

    cols = [str(i) for i in range(0,7)]
    for col in cols: homestps[col] = 0
      
    # Calculate stay time
    homestps['daydiff'] = 0
    homestps['wdaydiff'] = 0 # weekday difference
    homestps['weekdiff'] = 0
    homestps['monthdiff'] = 0
    
    for i in range(0,len(homestps)):
        homestps['daydiff'].iloc[i] = homestps['finished_at'].iloc[i].day - homestps['started_at'].iloc[i].day
        homestps['monthdiff'].iloc[i] = homestps['finished_at'].iloc[i].month - homestps['started_at'].iloc[i].month

        list31 = [1,3,5,7,8,10,12]
        list30 = [4,6,9,11]
        listFeb = [2] 
        if (homestps['monthdiff'].iloc[i] >= 1):
            startMonth = homestps['started_at'].iloc[i].month
            if (startMonth in list31):
                homestps['daydiff'].iloc[i] += 31
            elif (startMonth in list30):
                homestps['daydiff'].iloc[i] += 30
            elif (startMonth in listFeb):
                homestps['daydiff'].iloc[i] += 29; # change based on current year
            else:
                print("invalid start month")
        if (homestps['monthdiff'].iloc[i] >= 2):
            secMonth = homestps['started_at'].iloc[i].month+1
            if (secMonth in list31):
                homestps['daydiff'].iloc[i] += 31
            elif (secMonth in list30):
                homestps['daydiff'].iloc[i] += 30
            elif (secMonth in listFeb):
                homestps['daydiff'].iloc[i] += 29; # change based on current year
            else:
                print("invalid start month")
        homestps['weekdiff'].iloc[i] =  homestps['daydiff'].iloc[i] // 7
        homestps['wdaydiff'].iloc[i] = homestps['daydiff'].iloc[i] % 7
        
        if (homestps['wdaydiff'].iloc[i] == 0):  
            startWday = homestps['started_at'].iloc[i].weekday()
            startHour = homestps['started_at'].iloc[i].hour
            startMin = homestps['started_at'].iloc[i].minute
            startSec = homestps['started_at'].iloc[i].second
            homestps[str(startWday)].iloc[i] = 24*3600 - startHour*3600 - startMin*60 - startSec
        elif (homestps['wdaydiff'].iloc[i] == 1):
            startWday = homestps['started_at'].iloc[i].weekday()
            startHour = homestps['started_at'].iloc[i].hour
            startMin = homestps['started_at'].iloc[i].minute
            startSec = homestps['started_at'].iloc[i].second           
            homestps[str(startWday)].iloc[i] = 24*3600 - startHour*3600 - startMin*60 - startSec
            endWday = homestps['finished_at'].iloc[i].weekday()
            endHour = homestps['finished_at'].iloc[i].hour
            endMin = homestps['finished_at'].iloc[i].minute
            endSec = homestps['finished_at'].iloc[i].second           
            homestps[str(endWday)].iloc[i] = endHour*3600 + endMin*60 + endSec  
        elif (homestps['wdaydiff'].iloc[i] >= 2):
            startWday = homestps['started_at'].iloc[i].weekday()
            startHour = homestps['started_at'].iloc[i].hour
            startMin = homestps['started_at'].iloc[i].minute
            startSec = homestps['started_at'].iloc[i].second           
            homestps[str(startWday)].iloc[i] = 24*3600 - startHour*3600 - startMin*60 - startSec
            endWday = homestps['finished_at'].iloc[i].weekday()
            endHour = homestps['finished_at'].iloc[i].hour
            endMin = homestps['finished_at'].iloc[i].minute
            endSec = homestps['finished_at'].iloc[i].second           
            homestps[str(endWday)].iloc[i] = endHour*3600 + endMin*60 + endSec             
            for midWDay in range(1,homestps['wdaydiff'].iloc[i]):
                # print(str((startWday+midWDay)%7))
                homestps[str((startWday+midWDay)%7)].iloc[i] = 24*3600 
        else: print('Wrong weekday difference info')
            
        if (homestps['weekdiff'].iloc[i] >= 1):
            for wDay in range(0,7): homestps[str(wDay)].iloc[i] += (24*3600) * homestps['weekdiff'].iloc[i]
        if (homestps['weekdiff'].iloc[i] < 0): 
            print('Wrong week difference')
            
    for i in range(0,len(homeplcs)):
        plcid = i+1
        stps_plcid = homestps[homestps['place_id']==plcid]
        
        for col in cols:
            stps_placeid_wday = stps_plcid[col]
            homeplcs.loc[homeplcs['place_id']==plcid,col]=stps_placeid_wday.sum()
    
    for col in cols: homeplcs[col] = homeplcs[col]/3600 # convert unit from second to hour
    
    tempcols = homeplcs[cols]
    homeplcs['totalStayDays'] = tempcols.sum(axis=1)/24 # convert unit from hour to day only for this column
    homeplcs = homeplcs[homeplcs['totalStayDays']>2]
    

    ## WORKING ADDRESS   
    stps['tracked_at_Wday'] = 0
    for i in range(0,len(stps)): stps['tracked_at_Wday'].iloc[i] = stps['started_at'].iloc[i].weekday()
    
    workstps = stps[stps['tracked_at_Wday']<=4]
    workstps = workstps[((workstps['tracked_at_hour']>=8) & (workstps['tracked_at_hour']<=12)) | ((workstps['tracked_at_hour']>=14) & (workstps['tracked_at_hour']<=18))]
    workplcs = main.findPlaces(workstps, dataname, minDist, minPoints*2) 
    workplcs = poi.reverseGeoCoding(workplcs)
    
    cols = [str(i) for i in range(0,7)]
    for col in cols: workplcs[col] = 0

    cols = [str(i) for i in range(0,7)]
    for col in cols: workstps[col] = 0
      
    # Calculate stay time
    workstps['daydiff'] = 0
    workstps['wdaydiff'] = 0 # weekday difference
    workstps['weekdiff'] = 0
    workstps['monthdiff'] = 0
    
    for i in range(0,len(workstps)):
        workstps['daydiff'].iloc[i] = workstps['finished_at'].iloc[i].day - workstps['started_at'].iloc[i].day
        workstps['monthdiff'].iloc[i] = workstps['finished_at'].iloc[i].month - workstps['started_at'].iloc[i].month

        list31 = [1,3,5,7,8,10,12]
        list30 = [4,6,9,11]
        listFeb = [2] 
        if (workstps['monthdiff'].iloc[i] >= 1):
            startMonth = workstps['started_at'].iloc[i].month
            if (startMonth in list31):
                workstps['daydiff'].iloc[i] += 31
            elif (startMonth in list30):
                workstps['daydiff'].iloc[i] += 30
            elif (startMonth in listFeb):
                workstps['daydiff'].iloc[i] += 29; # change based on current year
            else:
                print("invalid start month")
        if (workstps['monthdiff'].iloc[i] >= 2):
            secMonth = workstps['started_at'].iloc[i].month+1
            if (secMonth in list31):
                workstps['daydiff'].iloc[i] += 31
            elif (secMonth in list30):
                workstps['daydiff'].iloc[i] += 30
            elif (secMonth in listFeb):
                workstps['daydiff'].iloc[i] += 29; # change based on current year
            else:
                print("invalid start month")
        workstps['weekdiff'].iloc[i] =  workstps['daydiff'].iloc[i] // 7
        workstps['wdaydiff'].iloc[i] = workstps['daydiff'].iloc[i] % 7
        
        if (workstps['wdaydiff'].iloc[i] == 0):  
            startWday = workstps['started_at'].iloc[i].weekday()
            startHour = workstps['started_at'].iloc[i].hour
            startMin = workstps['started_at'].iloc[i].minute
            startSec = workstps['started_at'].iloc[i].second
            workstps[str(startWday)].iloc[i] = 24*3600 - startHour*3600 - startMin*60 - startSec
        elif (workstps['wdaydiff'].iloc[i] == 1):
            startWday = workstps['started_at'].iloc[i].weekday()
            startHour = workstps['started_at'].iloc[i].hour
            startMin = workstps['started_at'].iloc[i].minute
            startSec = workstps['started_at'].iloc[i].second           
            workstps[str(startWday)].iloc[i] = 24*3600 - startHour*3600 - startMin*60 - startSec
            endWday = workstps['finished_at'].iloc[i].weekday()
            endHour = workstps['finished_at'].iloc[i].hour
            endMin = workstps['finished_at'].iloc[i].minute
            endSec = workstps['finished_at'].iloc[i].second           
            workstps[str(endWday)].iloc[i] = endHour*3600 + endMin*60 + endSec  
        elif (workstps['wdaydiff'].iloc[i] >= 2):
            startWday = workstps['started_at'].iloc[i].weekday()
            startHour = workstps['started_at'].iloc[i].hour
            startMin = workstps['started_at'].iloc[i].minute
            startSec = workstps['started_at'].iloc[i].second           
            workstps[str(startWday)].iloc[i] = 24*3600 - startHour*3600 - startMin*60 - startSec
            endWday = workstps['finished_at'].iloc[i].weekday()
            endHour = workstps['finished_at'].iloc[i].hour
            endMin = workstps['finished_at'].iloc[i].minute
            endSec = workstps['finished_at'].iloc[i].second           
            workstps[str(endWday)].iloc[i] = endHour*3600 + endMin*60 + endSec             
            for midWDay in range(1,workstps['wdaydiff'].iloc[i]):
                # print(str((startWday+midWDay)%7))
                workstps[str((startWday+midWDay)%7)].iloc[i] = 24*3600 
        else: print('Wrong weekday difference info')
            
        if (workstps['weekdiff'].iloc[i] >= 1):
            for wDay in range(0,7): workstps[str(wDay)].iloc[i] += (24*3600) * workstps['weekdiff'].iloc[i]
        if (workstps['weekdiff'].iloc[i] < 0): 
            print('Wrong week difference')
            
    for i in range(0,len(workplcs)):
        plcid = i+1
        stps_plcid = workstps[workstps['place_id']==plcid]
        
        for col in cols:
            stps_placeid_wday = stps_plcid[col]
            workplcs.loc[workplcs['place_id']==plcid,col]=stps_placeid_wday.sum()
    
    for col in cols: workplcs[col] = workplcs[col]/3600 # convert unit from second to hour
    
    tempcols = workplcs[cols]
    workplcs['totalStayDays'] = tempcols.sum(axis=1)/8 # convert unit from hour to workday (8hrs) only for this column
    workplcs = workplcs[workplcs['totalStayDays']>7]
    workplcs['totalStayDays'] = workplcs['totalStayDays']/3 # further convert to natural day

    workplcs['totalStayHrs'] = workplcs['totalStayDays']*24 # convert to hrs
    homeplcs['totalStayDays'] = homeplcs['totalStayDays']
    homeplcs['totalStayHrs'] = homeplcs['totalStayDays']*24 # convert to hrs
    
    homeplcs = poi.reverseGeoCoding(homeplcs)
    homeplcs['id'] = 'home'
    workplcs = poi.reverseGeoCoding(workplcs)
    workplcs['id'] = 'work'
    
    # homeworkplcs = pd.concat([homeplcs, workplcs], axis=0)
    # homeworkplcs = homeworkplcs.reset_index(drop=True)
    # homeworkplcs['place_id'] = homeworkplcs.index

    # homeworkplcs = hlp.findSemanticInfo(places, homeworkplcs, threeQua)

    # column_names = ["user_id","place_id","center","extent","location","placeName","id","totalStayDays","totalStayHrs","0","1","2","3","4","5","6"]
    # homeworkplcs = homeworkplcs.reindex(columns=column_names)
    # homeworkplcs = homeworkplcs.rename(columns={'0':'Mon','1':"Tues","2":"Wed","3":"Thur","4":"Fri","5":"Sat","6":"Sun"})  
    
    # if not(os.path.exists('../data/stat/'+ dataname + '/')):
    #     os.makedirs('../data/stat/'+ dataname + '/')
    # homeworkplcs.to_csv('../data/stat/'+ dataname + '/' + 'HomeWorkStay.csv', index = True)

    # return homeworkplcs

    return homeplcs, homestps, workplcs, workstps

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
    
    
def accuracyStat(dataName, dataNames, mac, timestart, timeend):
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
        dfStatistics = pd.DataFrame(columns =['id','OneQuatile','Median','ThreeQuatile','Avg','30','40','50','60','70', 'NumDays', 'NumPoints', 'AvgNumPoints', 'phoneModel'])

        tempStat = {}

        #dfStatistics = dfStatistics.append(pd.Series(name=dataName))
        tempStat['id'] = dataName
        
        dataPathLocs,dataPathTrips = hlp.getDataPaths(dataName)
        dataPathLocs,dataPathTrips = hlp.selectRange(dataPathLocs, dataPathTrips, mac, dateStart = timestart, dateEnd = timeend)
        
        locs, locsgdf = hlp.parseLocs(dataPathLocs)
        #trips, tripdf, tripsgdf = hlp.parseTrips(dataPathTrips)
    
        # tempStat['dateStart'] = labelStart
        # tempStat['dateEnd'] = lebelEnd
        
        # Number of points per day
        idx = pd.date_range(locs.index[0].date(), locs.index[-1].date())
        perDay = (locs.groupby(locs.index.date).count()['timestampMs'])
        #perDay = perDay.reindex(idx, fill_value=0)
        tempStat['Median'] = locs['accuracy'].median(axis=0)
        tempStat['Avg'] = locs['accuracy'].mean(axis=0)
        tempStat['OneQuatile'] = np.quantile(locs['accuracy'], .25)
        tempStat['ThreeQuatile'] = np.quantile(locs['accuracy'], .75)
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
        
        dfStatistics.to_csv('../data/statistics.csv', index=False)
    return dfStatistics
