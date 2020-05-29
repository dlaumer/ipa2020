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
    locs : gdf - Individual location data
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
    Generate csv with CO2 emission informatioin

    Parameters
    ----------
    transtat : tuple - returned results of pieChartInfoPlus() function
    dataname: str - participant ID
    
    Returns
    -------
    None
    """  
    transtatdf = pd.DataFrame(list(transtat))
    transtatdf = transtatdf.T
    transtatdf['percentage'] = ""
    transtatdf.columns = ['mode','value','percentage']
    
    # Calculate the percenatge of total distance for each transportation mode
    for i in range(0,len(transtatdf)):
        valsum = transtatdf['value'].sum(axis=0)
        transtatdf.iloc[i,2] = round(transtatdf.iloc[i,1]/valsum,4)
    
    # Sort the mode based on the percentage of total distance
    transtatdf.sort_values("percentage", axis = 0, ascending = False, 
                     inplace = True, na_position ='last') 

    # Interpret the Google's transportation mode into a nicer name
    labels2modes = {"IN_PASSENGER_VEHICLE":'by Car',"STILL":'Still',"WALKING": 'Walking',"IN_BUS": 'by Bus',"CYCLING":'by Bike',"FLYING":'by Plane',"RUNNING":'Running',"IN_FERRY":'by Ferry',"IN_TRAIN": 'by Train',"SKIING": 'Skiing',"SAILING": 'Sailing',"IN_SUBWAY": 'by Subway',"IN_TRAM": 'by Tram',"IN_VEHICLE":'in Vehicle'} 
    transtatdf['name'] = transtatdf['mode']
    transtatdf=transtatdf.replace({"name": labels2modes})
    
    # Read the file of CO2 emission per km for each transportation mode    
    co2 = pd.read_csv('../data/input/Co2Emission.csv')
    allModes = list(co2['name'])
    
    trans = transtatdf
    trans['value'] = trans['value']/1000 # transfer the unit from m to km
    trans['co2km'] = ""
    
    # Find the CO2 statistics for each transportation mode
    for i in range(0,len(trans)):
        modei = trans['name'].iloc[i]
        idx = allModes.index(modei)
        trans['co2km'].iloc[i] = co2['co2'].iloc[idx]
    
    transdf = trans[['name','value','percentage','co2km']
    transdf = transdf.rename(columns={'value':'dist','percentage':"distPerc"})  
    transdf['co2Total'] = ""
    transdf['co2Perc'] = ""
    
    # Calculate total CO2 emission of each transportation mode
    for i in range(0,len(transdf)):
        transdf['co2Total'].iloc[i] = transdf['dist'].iloc[i] * transdf['co2km'].iloc[i]
 
    # Calculate the percentage of CO2 emission of each transportation mode        
    for i in range(0,len(transdf)):
        valsum = transdf['co2Total'].sum(axis=0)
        transdf['co2Perc'].iloc[i] = round(transdf['co2Total'].iloc[i]/valsum,4)
    
    # Sort transportation mode according to the percentage of CO2 emission
    transdf.sort_values("co2Perc", axis = 0, ascending = False, 
                     inplace = True, na_position ='last')  

    transdf.to_csv('../data/results/stat/'+dataname+'/TransportationModeCo2Perc.csv', index = True)
    

def plcsStayHour(stps, plcs, dataname):
    """
    Calculate stay time statistics of each place by 24-hour

    Parameters
    ----------
    stps : gdf - detected stay points
    plcs: gdf - clustered places
    dataname: str - participant ID
        
    Returns
    -------
    plcs: gdf - clustered places with 24-hour stay time to further detect home and work address
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

        if (stps['hourdiff'].iloc[i]<0):
            stps['hourdiff'].iloc[i] += 24
 
        # Examine if the day difference across the month, if so, corresponding days need to be added
        list31 = [1,3,5,7,8,10,12] # for each month of this list, 31 days should be added
        list30 = [4,6,9,11] # 30 days for each month of this list
        listFeb = [2] # 29 days for each month of this list
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
        
        # Calculate stay time of each stay point by each hour based on the day difference
        # When the start time and end time of the stay point is one the same day
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
        # When the start time and end time of the stay point has one day difference
        elif (stps['daydiff'].iloc[i] == 1):
            startHour = stps['started_at'].iloc[i].hour
            endHour = stps['finished_at'].iloc[i].hour
            stps[str(startHour)].iloc[i] = 3600 - stps['started_at'].iloc[i].minute*60 - stps['started_at'].iloc[i].second
            stps[str(endHour)].iloc[i] = stps['finished_at'].iloc[i].minute*60 + stps['finished_at'].iloc[i].second
            for midHourSday in range(startHour+1, 24):
                stps[str(midHourSday)].iloc[i] += 3600  
            for midHourEday in range(0, endHour):
                stps[str(midHourEday)].iloc[i] += 3600              
        # When the start time and end time of the stay point has two day difference
        elif (stps['daydiff'].iloc[i] >= 2):
            wholeDays = stps['daydiff'].iloc[i] - 1;
            for wholeHour in range(0, 24):
                stps[str(wholeHour)].iloc[i] = 3600*wholeDays
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
    
    # Calculate stay time for each place by summing up all stay points
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

    # if not(os.path.exists('../data/stat/'+ dataname + '/')):
        # os.makedirs('../data/stat/'+ dataname + '/')
    # plcstocsv_transpose.to_csv('../data/stat/'+ dataname + '/PlcsStayHour.csv', index = True)
    # plcstocsv_transpose.to_csv('../../5-Final Product/stat/'+ dataname + '/PlcsStayHour.csv', index = True)
    plcstocsv_transpose.index.name='group'

    if not(os.path.exists('../data/results/stat/'+ dataname + '/')):
        os.makedirs('../data/results/stat/'+ dataname + '/stat/')
    plcstocsv_transpose.to_csv('../data/results/stat/'+ dataname + '/PlcsStayHour.csv', index = True)

    # V2: with place name added
    plcs = poi.reverseGeoCoding(plcs)
    plcsInfo = plcs[['placeName']]
    plcsInfoT = plcsInfo.T
    plcsInfoT.columns = plcs['place_id']
    plcsInfoT.to_csv('../data/results/stat/'+ dataname + '/PlcsInfo.csv', index = False)

    column_names = ["user_id","place_id","center","extent","location","placeName","nameId","totalStayHrs","0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","23"]
    plcs = plcs.reindex(columns=column_names)
    
    return plcs    
    

def homeworkStay(plcs, stps, dataname, places, threeQua):
    """
    Calculate stay time statistics of home and work places by weekday

    Parameters
    ----------
    stps : gdf - detected stay points
    plcs: gdf - clustered places
    dataname: str - participant ID
    places : gdf - places defined by google with place name provided
    threeQua: float- 3rd quantile of the distance difference, used as the threshold to match place name

    Returns
    -------
    homeworkplcs: gdf - home and workplace with weekday stay time
    """
    
    # Define a flag to see if the user has the workplace    
    flag = 0
    
    # HOME ADDRESS 
    cols = [str(i) for i in range(0,24)]
    stps = stps.drop(cols, axis=1)
    
    # Choose the daytime to detect homeplace
    homecols = [str(i) for i in range(0,7)] + [str(i) for i in range(22,24)]
    homeHrs = list(plcs[homecols].sum(axis=1)) 
    
    # Set the minimum stay time threshold for homeplace
    if(max(homeHrs)>40): 
        homeidx = homeHrs.index(max(homeHrs))
        homeid = plcs['place_id'].iloc[homeidx]
        
        homeplcs = plcs[plcs['place_id']==homeid]
        plcs = plcs.drop(homeplcs.index,axis=0)
        cols = [str(i) for i in range(0,24)]
        homeplcs = homeplcs.drop(cols, axis=1)
        homestps = stps[stps['place_id']==homeid]
                
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
    
            # Examine if the day difference across the month, if so, corresponding days need to be added
            list31 = [1,3,5,7,8,10,12] # for each month of this list, 31 days should be added
            list30 = [4,6,9,11] # 30 days for each month of this list
            listFeb = [2] # 29 days for each month of this list

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
            
            # Calculate stay time of each stay point of homeplace by each weekday
            homestps['weekdiff'].iloc[i] =  homestps['daydiff'].iloc[i] // 7
            homestps['wdaydiff'].iloc[i] = homestps['daydiff'].iloc[i] % 7
            
            if (homestps['wdaydiff'].iloc[i] == 0 and homestps['weekdiff'].iloc[i]==0):  
                startWday = homestps['started_at'].iloc[i].weekday()
                startHour = homestps['started_at'].iloc[i].hour
                startMin = homestps['started_at'].iloc[i].minute
                startSec = homestps['started_at'].iloc[i].second
                homestps[str(startWday)].iloc[i] = (homestps['finished_at'].iloc[i]-homestps['started_at'].iloc[i]).total_seconds()
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
            elif (homestps['wdaydiff'].iloc[i] >= 2 or (homestps['wdaydiff'].iloc[i] == 0 and homestps['weekdiff'].iloc[i]>=1)):
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
 
        # Sum up stay time of all stay points by weekday
        for col in cols:
            stps_placeid_wday = homestps[col]
            homeplcs[col]=stps_placeid_wday.sum()
        
        for col in cols: 
            homeplcs[col] = homeplcs[col]/3600 # convert unit from second to hour
        
        tempcols = homeplcs[cols]
        homeplcs['totalStayDays'] = tempcols.sum(axis=1)/24 # convert unit from hour to day only for this column
        # homeplcs = homeplcs[homeplcs['totalStayDays']>2]

    else: print('No home place found!')
    
    # WORKING ADDRESS  
    # Choose nighttime to detect workplace
    workcols = [str(i) for i in range(9,12)] + [str(i) for i in range(14,17)]
    workHrs = list(plcs[workcols].sum(axis=1))
    
    # Minimum stay time for workplace should be met
    if(max(workHrs)>15): 
        workidx = workHrs.index(max(workHrs))
        workid = plcs['place_id'].iloc[workidx]
        
        workplcs = plcs[plcs['place_id']==workid]
        cols = [str(i) for i in range(0,24)]
        workplcs = workplcs.drop(cols, axis=1)
        workstps = stps[stps['place_id']==workid]
        
        cols = [str(i) for i in range(0,7)]
        for col in cols: workplcs[col] = 0
    
        cols = [str(i) for i in range(0,7)]
        for col in cols: workstps[col] = 0
          
        # Calculate stay time of each stay point of workplace
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
            
            if (workstps['wdaydiff'].iloc[i] == 0 and workstps['weekdiff'].iloc[i]==0):  
                startWday = workstps['started_at'].iloc[i].weekday()
                startHour = workstps['started_at'].iloc[i].hour
                startMin = workstps['started_at'].iloc[i].minute
                startSec = workstps['started_at'].iloc[i].second
                workstps[str(startWday)].iloc[i] = (workstps['finished_at'].iloc[i]-workstps['started_at'].iloc[i]).total_seconds()
                # workstps[str(startWday)].iloc[i] = 24*3600 - startHour*3600 - startMin*60 - startSec
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
            elif (workstps['wdaydiff'].iloc[i] >= 2 or (workstps['wdaydiff'].iloc[i] == 0 and workstps['weekdiff'].iloc[i]>=1)):
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
              
        # Sum up stay time of all stay points by weekday
        for col in cols:
            stps_placeid_wday = workstps[col]
            workplcs[col]=stps_placeid_wday.sum()
        
        for col in cols: workplcs[col] = workplcs[col]/3600 # convert unit from second to hour
        
        tempcols = workplcs[cols]
        workplcs['totalStayDays'] = tempcols.sum(axis=1)/8 # convert unit from hour to workday (8hrs) only for this column
        workplcs['totalStayDays'] = workplcs['totalStayDays']/3 # further convert to natural day      
        flag = 1 # change the flag
        
    else:
        print('No work place found!')

    # Output csv file based on if there is any workplace found
    if (flag == 1):
        workplcs['totalStayHrs'] = workplcs['totalStayDays']*24 # convert to hrs
        homeplcs['totalStayDays'] = homeplcs['totalStayDays']
        homeplcs['totalStayHrs'] = homeplcs['totalStayDays']*24 # convert to hrs
        
        homeplcs = poi.reverseGeoCoding(homeplcs)
        homeplcs['id'] = 'home'
        workplcs = poi.reverseGeoCoding(workplcs)
        workplcs['id'] = 'work'
        
        homeworkplcs = pd.concat([homeplcs, workplcs], axis=0)
        homeworkplcs = homeworkplcs.reset_index(drop=True)
    
        homeworkplcs = hlp.findSemanticInfo(places, homeworkplcs, threeQua)
    
        column_names = ["user_id","place_id","center","extent","location","placeName","id","totalStayDays","totalStayHrs","0","1","2","3","4","5","6"]
        homeworkplcs = homeworkplcs.reindex(columns=column_names)
        homeworkplcs = homeworkplcs.rename(columns={'0':'Mon','1':"Tues","2":"Wed","3":"Thur","4":"Fri","5":"Sat","6":"Sun"})  
        
        if not(os.path.exists('../data/results/stat/'+ dataname+ '/')):
            os.makedirs('../data/results/stat/'+ dataname+ '/')
        homeworkplcs.to_csv('../data/results/stat/'+ dataname+ '/' + 'HomeWorkStay.csv', index = True)
        
    else:        
        homeplcs['totalStayDays'] = homeplcs['totalStayDays']
        homeplcs['totalStayHrs'] = homeplcs['totalStayDays']*24 # convert to hrs
        
        homeplcs = poi.reverseGeoCoding(homeplcs)
        homeplcs['id'] = 'home'
        homeplcs = homeplcs.reset_index(drop=True)
    
        homeplcs = hlp.findSemanticInfo(places, homeplcs, threeQua)
    
        column_names = ["user_id","place_id","center","extent","location","placeName","id","totalStayDays","totalStayHrs","0","1","2","3","4","5","6"]
        homeplcs = homeplcs.reindex(columns=column_names)
        homeplcs = homeplcs.rename(columns={'0':'Mon','1':"Tues","2":"Wed","3":"Thur","4":"Fri","5":"Sat","6":"Sun"})  
        homeworkplcs = homeplcs
        if not(os.path.exists('../data/results/stat/'+ dataname + '/')):
            os.makedirs('../data/results/stat/'+ dataname + '/')
        homeworkplcs.to_csv('../data/results/stat/'+ dataname + '/' + 'HomeWorkStay.csv', index = True)
        
    return homeworkplcs

    
def accuracyStat(dataName, dataNames, mac, timestart, timeend):
    """
    Calculate basic statistics for each participant

    Parameters
    ----------
    dataName: str - participant ID
    dataNames: list - all participants' ID
    mac: bool - change the file route based on if it is mac or windows system
    timestart: str - start day of the data
    timeend : str - end day of the data

    Returns
    -------
    None
    """
    if len(dataNames) == 0:
        for root,dirs,files in os.walk("../data/results/questionnaires"):
            dataNames = dirs
            break
    
    dfQuestionnaire = pd.read_csv("../data/results/questionnaires/Pre-Questionnaire - Location Diary.csv")
    dfPhoneModel = dfQuestionnaire[["Enter your participant ID:","What is your mobile phone's brand used to collect data?"]]
    dfPhoneModel = dfPhoneModel.rename(columns = {"id":"Enter your participant ID:", "phoneModel":"What is your mobile phone's brand used to collect data?"})
    
    generated_dfStatistics = []
    
    for dataName in dataNames:
        print('Processing '+ dataName)
        dfStatistics = pd.DataFrame(columns =['id','OneQuatile','Median','ThreeQuatile','Avg','30','40','50','60','70', 'NumDays', 'NumPoints', 'AvgNumPoints', 'TotalDist', 'AvgDist', 'phoneModel'])

        tempStat = {}
        tempStat['id'] = dataName
        
        dataPathLocs,dataPathTrips = hlp.getDataPaths(dataName)
        dataPathLocs,dataPathTrips = hlp.selectRange(dataPathLocs, dataPathTrips, mac, dateStart = timestart, dateEnd = timeend)
        
        locs, locsgdf = hlp.parseLocs(dataPathLocs)
        locs['d_diff'] = np.append(haversine_dist(locs.longitudeE7[1:], locs.latitudeE7[1:], locs.longitudeE7[:-1], locs.latitudeE7[:-1]),0)
        
        # Number of points per day
        idx = pd.date_range(locs.index[0].date(), locs.index[-1].date())
        perDay = (locs.groupby(locs.index.date).count()['timestampMs'])
        tempStat['Median'] = locs['accuracy'].median(axis=0)
        tempStat['Avg'] = locs['accuracy'].mean(axis=0)
        tempStat['OneQuatile'] = np.quantile(locs['accuracy'], .25)
        tempStat['ThreeQuatile'] = np.quantile(locs['accuracy'], .75)
        tempStat['NumDays'] = len(perDay)
        tempStat['NumPoints'] = perDay.sum()
        tempStat['AvgNumPoints'] = perDay.mean()
        tempStat['TotalDist'] = locs['d_diff'].sum(axis=0)/1000 # unit: km
        tempStat['AvgDist'] = tempStat['TotalDist']/tempStat['NumDays']
    
        tempStat['phoneModel'] = dfPhoneModel.loc[np.where(dfPhoneModel["Enter your participant ID:"] == int(dataName))[0][0],"What is your mobile phone's brand used to collect data?"]
        
        # Calculate the percentage of GPS points within chosen accuracy threshold
        for i in [30,40,50,60,70]:
            tempStat[str(i)] =  round(100*len(locs[locs['accuracy'].lt(i)])/len(locs),2)
            
        generated_dfStatistics.append(tempStat)
        dfStatistics = dfStatistics.append(generated_dfStatistics)
        
    dfStatistics.to_csv('../data/results/statistics.csv', index=False)
    return dfStatistics


def analysePreQuest():
    """
    Calculate the mean score of the interesting tasks in pre-questionnaire
    
    Parameters
    ----------
    None

    Returns
    -------
    qmean: list - mean score of each questions
    highest: list - the number of participants rating 'Very interested' for each question
    secHigh: list - the number of participants rating 'Somewhat interested' for each question
    """   
    pre = pd.read_csv('../data/results/questionnaires/Pre-Questionnaire - Location Diary.csv')
    labels2score = {"Very interested":5,"Somewhat interested":4,"Neither interested or uninterested":3,"Somewhat uninterested":2,"Very uninterested":1}
    cols = [str(i) for i in range(1,10)]    
    for col in cols:
        pre=pre.replace({col: labels2score})
    qmean = pre.mean()
    highest = []
    secHigh = []
    for col in cols:
        highest.append(len(pre[pre[col] == 5]))
        secHigh.append(len(pre[pre[col] == 4]))
    return qmean, highest, secHigh
