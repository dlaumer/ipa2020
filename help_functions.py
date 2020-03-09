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
import numpy as np

import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
import fiona

def parseLocs(dataPath):
    """
    Parse the location file

    Parameters
    ----------
    dataPath : str - (relative) path to the location file

    Returns
    -------
    gdf : gpd - geopandas dataframe of the data

    """
    with open(dataPath) as f:
        data = json.load(f)
    f.close()
    df = pd.json_normalize(data, 'locations')
    df['datetimeUTC'] = pd.to_datetime(df['timestampMs'],  unit='ms')
    df['datetimeCH'] = df['datetimeUTC'] + pd.DateOffset(hours=1)
    df['date'] = df['datetimeUTC'].dt.date
    df = df.set_index('datetimeCH')
    df['latitudeE7'] = df['latitudeE7'].astype(float)/10000000
    df['longitudeE7'] = df['longitudeE7'].astype(float)/10000000
    gdf = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df['longitudeE7'], df['latitudeE7']))
    return df, gdf

def parseTrips(dataPath):
    """
    Parse the trips file

    Parameters
    ----------
    dataPath : str - (relative) path to the location file

    Returns
    -------
    allData: dict - nested dict of the trips file
    df : df - pandas dataframe of the data

    """
    gdf = gpd.GeoDataFrame()
    gdf['geometry'] = None

    allData = {}
    d = []
    dirs = os.listdir(dataPath)
    i = 0
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
                                typ = list(obj)[0]
                                tempData = {'Year':year, 'Month': month, 'Type':typ}
                                tempData.update(obj[list(obj)[0]])
                                d.append(tempData)
                                
                                gdf.loc[i,'Year'] = year
                                gdf.loc[i,'Month'] = month
                                gdf.loc[i,'Type'] = typ
                                entry = obj[typ]                                
                                gdf.loc[i,'startTime'] = pd.to_datetime(entry['duration']['startTimestampMs'],  unit='ms') + pd.DateOffset(hours=1)
                                gdf.loc[i,'endTime'] = pd.to_datetime(entry['duration']['endTimestampMs'],  unit='ms') + pd.DateOffset(hours=1)
                                if typ == 'activitySegment':
                                    coordinates = []
                                    try:
                                        coordinates.append((entry['startLocation']['longitudeE7']/10000000,entry['startLocation']['latitudeE7']/10000000))
                                        if 'waypointPath' in list(entry):
                                            for point in entry['waypointPath']['waypoints']:
                                                coordinates.append((point['lngE7']/10000000,point['latE7']/10000000))
                                        coordinates.append((entry['endLocation']['longitudeE7']/10000000,entry['endLocation']['latitudeE7']/10000000))
                                        shape = LineString(coordinates)
                                    except: 
                                        shape = LineString()
                                    gdf.loc[i,'distance'] = entry.get('distance',None)
                                    gdf.loc[i,'actType'] = entry['activityType']
                                    gdf.loc[i,'confidence'] = entry.get('confidence',None)
                                else:
                                    pass
                                    gdf.loc[i,'confidence'] = entry.get('placeConfidence',None)
                                    try:
                                        coordinates = (entry['centerLngE7']/10000000,entry['centerLatE7']/10000000)
                                        shape = Point(coordinates)
                                    except:
                                        try:
                                            coordinates = (entry['location']['longitudeE7']/10000000,entry['location']['latitudeE7']/10000000)
                                            shape = Point(coordinates)
                                        except:
                                            shape = Point()
                                gdf.loc[i, 'geometry'] = shape
                                i = i + 1
                        f.close()                       
    df = pd.DataFrame(d)
    return allData, df, gdf

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

def checkTrips(trips):
    """
    This function checks if the endtime of one activity is the same as the 
    starttimes in the nect activity. 
    If there is a gap or an overlap, it is printed to the prompt

    Parameters
    ----------
    trips : dict - Semantic information (nested)

    Returns
    -------
    None.

    """
    previousTimeStamp = None
    for year in trips: # Loop over years
        for month in trips[year]:  # Loop over months 
            for event in trips[year][month]: # Loop over entries
                timeStamp = event[list(event)[0]]['duration']['startTimestampMs'] 
                if previousTimeStamp:
                    if previousTimeStamp != timeStamp:
                        # Compare previous and current timestamp
                        if (int(timeStamp)-int(previousTimeStamp)) > 0:
                            print('There is a gap between ' + str(pd.to_datetime(previousTimeStamp,  unit='ms')) + ' and ' + str(pd.to_datetime(timeStamp,  unit='ms'))) 
                        else:
                            print('There is an overlap between ' + str(pd.to_datetime(previousTimeStamp,  unit='ms')) + ' and ' + str(pd.to_datetime(timeStamp,  unit='ms'))) 
                previousTimeStamp = event[list(event)[0]]['duration']['endTimestampMs'] 


def calculateVelocity(locs):
    """
    This function calculates the velocity of two consecutive points in 
    the location data. It calculates the quotient between the time 
    difference and the distance difference.

    Parameters
    ----------
    locs : gdf - individual location data

    Returns
    -------
    locs : dict - individual location data, added columns t_diff, d_diff and
    velocity

    """
    # Get time difference
    locs['t_diff'] = locs.index.to_series().diff().dt.seconds

    # Extract location
    lat1 = locs['latitudeE7'].iloc[:-1]
    lon1 = locs['longitudeE7'].iloc[:-1]
    lat2 = locs['latitudeE7'].iloc[1:]
    lon2 = locs['longitudeE7'].iloc[1:]
    # Get vectorized version of the haversine function
    haver_vec = np.vectorize(haversine, otypes=[np.int16])
    locs['d_diff'] = 0
    # Calculate distance
    locs['d_diff'].iloc[1:] = (haver_vec(lat1,lon1,lat2,lon2))
    # Calculate velocity
    locs['velocity_calc'] = locs['d_diff']/locs['t_diff']
    return locs

def haversine(lat1,lon1,lat2,lon2):
    """
    This function calculates the distance between two points on a sphere

    Parameters
    ----------
    lat1 : float - latitude of point 1
    lon1 : float - longitude of point 1
    lat2 : float - latitude of point 2
    lon2 : float - longitude of point 2

    Returns
    -------
    m : float - Distance between points in m

    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    m = 6367 * c * 1000
    return m

#%%
def loc2shp(locs, dataName):
    """
    This function saves the location data to a shapefile

    Parameters
    ----------
    locs : gdf - individual location data
    dataName : str - Name of the dataset

    Returns
    -------
    None.

    """
    try:
        locs = locs.drop('activity', axis=1)
    except:
        pass
    locs['date'] = locs['date'].astype(str)
    locs['datetimeUTC'] = locs['datetimeUTC'].astype(str)
    locs.to_file('../shp/Loc_'+dataName +'.shp')
    
def trip2shp(trips, dataName):
    """
    This function saves the location data to a shapefile

    Parameters
    ----------
    trips : gdf - Semantic information (points and lines)
    dataName : str - Name of the dataset

    Returns
    -------
    None.

    """
    trips['startTime'] = trips['startTime'].astype(str)
    trips['endTime'] = trips['endTime'].astype(str)

    trips[trips['Type']=='activitySegment'].to_file('..\shp\Trip_'+dataName +'.shp')  
    trips[trips['Type']=='placeVisit'].to_file('..\shp\Place_'+dataName +'.shp')
