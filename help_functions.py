#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Help Functions
    This file holds all the small helper functions or inventory functions.
    
    Created on Thu Feb 27 09:20:41 2020
    Authors:    Daniel Laumer (laumerd@ethz.ch)
                Haojun Cai (caihao@ethz.ch)
    
"""

from math import radians, cos, sin, asin, sqrt
import os
import json
import pandas as pd


def parseLocs(dataPath):
    with open(dataPath) as f:
        data = json.load(f)
    f.close()
    df = pd.json_normalize(data, 'locations')
    df['datetimeUTC'] = pd.to_datetime(df['timestampMs'],  unit='ms')
    df['datetimeCH'] = df['datetimeUTC'] + pd.DateOffset(hours=1)
    df = df.set_index('datetimeCH')
    df['latitudeE7'] = df['latitudeE7'].astype(float)/10000000
    df['longitudeE7'] = df['longitudeE7'].astype(float)/10000000
    return df

def parseTrips(dataPath):
    
    allData = {}
    d = []
    dirs = os.listdir(dataPath)
    for year in dirs:
        if year.isdigit():
            dataPathYear = os.path.join(dataPath, year)
            allData[year] = {}
            for root, dirs, files in os.walk(dataPathYear):
                for fil in files:
                    if fil.endswith('.json'):
                        dataPathFile = os.path.join(dataPathYear, fil)
                        with open(dataPathFile) as f:
                            month = fil[5:-5]
                            data = json.load(f)
                            allData[year][month] = data['timelineObjects']
                            for obj in data['timelineObjects']:
                                tempData = {'Year':year, 'Month': month, 'Type':list(obj)[0]}
                                tempData.update(obj[list(obj)[0]])
                                d.append(tempData)
                        f.close()                       
    df = pd.DataFrame(d)
    return allData, df

def stats(locs, trips):
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
    
def pieChartInfo(trips):
    countPublic = 0
    countCar = 0
    countCycle = 0 
    countRest = 0
    for year in trips:
        for month in trips[year]:        
            for event in trips[year][month]:
                if list(event)[0] == 'activitySegment':
                    try:
                        dist = event['activitySegment']['distance']
                    except:
                        print(1)
                    if event['activitySegment']['activityType'] in ('CYCLING'): countCycle = countCycle + dist
                    elif event['activitySegment']['activityType'] in ('IN_BUS','IN_FERRY','IN_TRAIN','IN_SUBWAY','IN_TRAM'): countPublic = countPublic + dist
                    elif event['activitySegment']['activityType'] in ('IN_PASSENGER_VEHICLE'): countCar = countCar + dist
                    else: countRest = countRest + dist
    return [countPublic, countCar, countCycle, countRest]


def pieChartInfoPlus(trips):
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

def checkTrips(trips):
    previousTimeStamp = None
    for year in trips:
        for month in trips[year]:   
            for event in trips[year][month]:
                timeStamp = event[list(event)[0]]['duration']['startTimestampMs'] 
                if previousTimeStamp:
                    if previousTimeStamp != timeStamp:
                        if (int(timeStamp)-int(previousTimeStamp)) > 0:
                            print('There is a gap between ' + str(pd.to_datetime(previousTimeStamp,  unit='ms')) + ' and ' + str(pd.to_datetime(timeStamp,  unit='ms'))) 
                        else:
                            print('There is an overlap between ' + str(pd.to_datetime(previousTimeStamp,  unit='ms')) + ' and ' + str(pd.to_datetime(timeStamp,  unit='ms'))) 
                previousTimeStamp = event[list(event)[0]]['duration']['endTimestampMs'] 


def haversine(lat1,lon1,lat2,lon2):
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    km = 6367 * c
    return km