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
import gpxpy
import gpxpy.gpx
from lxml import etree
import bisect # To find an index in a sorted list
import calendar
from pathlib import Path
from shutil import copyfile
import shapely
from functools import partial
import pyproj
import math

from trackintel.geogr.distances import haversine_dist


from scipy.spatial.distance import euclidean
from fastdtw import fastdtw


def getDataPaths(participantId):
    rootPath = "../../4-Collection/DataParticipants/"
    path = rootPath + participantId + "/Takeout/"
    if os.path.exists(path + "Location History/"):        
        dataPathLocs = path + '/Location History/Location History.json'
        dataPathTrips = path + '/Location History/Semantic Location History/'
    elif os.path.exists(path + "Standortverlauf/"): 
        dataPathLocs =  path + '/Standortverlauf/Standortverlauf.json'
        dataPathTrips =  path + '/Standortverlauf/Semantic Location History/'
    elif os.path.exists(path + "Historique des positions/"): 
        dataPathLocs =  path + '/Historique des positions/Historique des positions.json'
        dataPathTrips =  path + '/Historique des positions/Semantic Location History/'
    elif os.path.exists(path + "位置记录/"): 
        dataPathLocs =  path + '/位置记录/位置记录.json'
        dataPathTrips =  path + '/位置记录/Semantic Location History/'

    else:
        raise TypeError('The files are not in the needed format!')
    return dataPathLocs,dataPathTrips


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
    gdf = gpd.GeoDataFrame(crs={'init':'epsg:4326'})
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
                                    gdf.loc[i,"placeId"] = entry['location'].get('placeId', None)
                                    gdf.loc[i, "placeName"] = entry['location'].get('name', None)

                                gdf.loc[i, 'geometry'] = shape
                                i = i + 1
                        f.close()                       
    df = pd.DataFrame(d)
    return allData, df, gdf

def parseTripsWithLocs(dataPath, locs):
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
    timestamps = locs["timestampMs"].astype(np.int64)
    
    df = pd.DataFrame(columns=['Year', 'Month', 'Type', 'startTime', 'endTime', 'geom', 'distance', 'actType', 'confidence', 'correspondingLocs'])

    dirs = os.listdir(dataPath)
    generated_trips = []
    for year in dirs:
        if year.isdigit():
            dataPathYear = os.path.join(dataPath, year)
            for root, dirs, files in os.walk(dataPathYear):
                for fil in files:
                    if fil.endswith('.json'):
                        dataPathFile = os.path.join(dataPathYear, fil)
                        with open(dataPathFile) as f:
                            month = fil[5:-5]
                            data = json.load(f)
                            for obj in data['timelineObjects']:
                                typ = list(obj)[0]
                                entry = obj[typ]   
                                if typ == 'activitySegment':
                                    
                                    dateStart = int(entry['duration']['startTimestampMs'])
                                    dateEnd = int(entry['duration']['endTimestampMs'])
                                    indexStart = bisect.bisect_left(timestamps,dateStart)
                                    indexEnd = bisect.bisect_right(timestamps,dateEnd)
                                    try:
                                        shape = LineString(locs['geometry'][indexStart:indexEnd+1])
                                    except: 
                                        print("Upsi")
                                        shape = LineString()
                                    correspondingLocs = range(indexStart,indexEnd+1)
                                    
                                    distance = entry.get('distance',None)
                                    actType = entry['activityType']
                                    confidence = entry.get('confidence',None)
                                else:
                                    distance = None
                                    actType = None
                                    confidence = entry.get('placeConfidence',None)
                                    correspondingLocs = None
                                    try:
                                        coordinates = (entry['centerLngE7']/10000000,entry['centerLatE7']/10000000)
                                        shape = Point(coordinates)
                                    except:
                                        try:
                                            coordinates = (entry['location']['longitudeE7']/10000000,entry['location']['latitudeE7']/10000000)
                                            shape = Point(coordinates)
                                        except:
                                            shape = Point()

                                generated_trips.append({
                                    'Year': year,
                                    'Month': month,
                                    'Type': typ,  # pfs_tripleg['tracked_at'].iloc[0],
                                    'startTime': pd.to_datetime(entry['duration']['startTimestampMs'],  unit='ms') + pd.DateOffset(hours=1),  # pfs_tripleg['tracked_at'].iloc[-1],
                                    'endTime': pd.to_datetime(entry['duration']['endTimestampMs'],  unit='ms') + pd.DateOffset(hours=1),
                                    'geom': shape,
                                    'distance': distance,
                                    'actType': actType,
                                    'confidence' : confidence,
                                    'correspondingLocs': correspondingLocs
                                })
                        f.close()
    df = df.append(generated_trips)
    gdf = gpd.GeoDataFrame(df, geometry='geom', crs={'init':'epsg:4326'})
    return gdf
    
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
    haver_vec = np.vectorize(haversine_built, otypes=[np.int16])
    locs['d_diff'] = 0
    # Calculate distance
    locs['d_diff'].iloc[1:] = (haver_vec(lat1,lon1,lat2,lon2))
    # Calculate velocity
    locs['velocity_calc'] = locs['d_diff']/locs['t_diff']
    return locs

def haversine_built(lat1,lon1,lat2,lon2):
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
def loc2shp(locs, dataname):
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
    if not(os.path.exists('../data/shp/'+ dataname + '/')):
        os.makedirs('../data/shp/'+ dataname + '/')
    locs.to_file('../data/shp/'+ dataname + '/Loc.shp')
    
def trip2shp(trips, dataname):
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
    try:
        trips = trips.drop('correspondingLocs', axis=1)
    except:
        pass
    trips['startTime'] = trips['startTime'].astype(str)
    trips['endTime'] = trips['endTime'].astype(str)
    
    if not(os.path.exists('../data/shp/'+ dataname + '/')):
        os.makedirs('../data/shp/'+ dataname + '/')
    trips[trips['Type']=='activitySegment'].to_file('../data/shp/'+ dataname + '/Trip.shp')  
    #trips[trips['Type']=='placeVisit'].to_file('../data/shp/'+ dataname + '/Place.shp')

def haversine_np(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)

    All args must be of equal length.    

    """
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2

    c = 2 * np.arcsin(np.sqrt(a))
    km = 6367 * c
    return km

def distance(x):
    y = x.shift()
    return haversine_np(x['latitudeE7'], x['longitudeE7'], y['latitudeE7'], y['longitudeE7']).fillna(0)

def loc2csv4ti(locs, dataname):
    fields = set(['latitudeE7', 'longitudeE7', 'altitude', 'accuracy', 'velocity']).intersection(set(locs.keys()))
    locs = locs[list(fields)]
    locs.loc[:,'user_id'] = '1'
    locs.rename(columns = {'latitudeE7':'latitude', 'longitudeE7': 'longitude', 'altitude':'elevation'}, inplace = True)
    locs.loc[:,'tracked_at'] = locs.index.astype(str)
    if not(os.path.exists('../data/csv/'+ dataname + '/')):
        os.makedirs('../data/csv/'+ dataname + '/')
    locs.to_csv('../data/csv/' + dataname + '/' + dataname + '.csv', index=False, sep=';')
    
def trip2gpx(trips, dataname):
    if not(os.path.exists('../data/gpx/'+ dataname + '/')):
        os.makedirs('../data/gpx/'+ dataname + '/')
    for idx in trips.index:
        gpx = gpxpy.gpx.GPX()
    
        # Create first track in our GPX:
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)
        
        # Create first segment in our GPX track:
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)
        
        # Create points:
        for coord in trips.loc[idx,'geom'].coords:
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(coord[1], coord[0]))
        
        #print(gpx.to_xml())
        with open('../data/gpx/' + dataname + '/' + trips.loc[idx,'id'] + '.gpx', 'w') as f:
            f.write(gpx.to_xml())
        prepareGPXforAPI('../data/gpx/' + dataname + '/' + trips.loc[idx,'id'] + '.gpx', str(idx), trips.loc[idx,'id'])
            
def prepareGPXforAPI(path, routeId, pathId):
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(path, parser)  
    #etree.register_namespace('gpx',"http://www.topografix.com/GPX/1/1")
    root = tree.getroot()
    
    meta = etree.Element('metadata')
    
    name = etree.SubElement(meta, 'name')
    name.text = 'ETH.GEO.ZPHERES.001'
    
    extensions = etree.SubElement(meta, 'extensions')
    ZpheresMetadata = etree.SubElement(extensions, 'ZpheresMetadata')
    
    etree.SubElement(ZpheresMetadata, 'ZPathName').text = '1-A'
    etree.SubElement(ZpheresMetadata, 'PathRefID').text = pathId
    etree.SubElement(ZpheresMetadata, 'routeid').text = '1'
    etree.SubElement(ZpheresMetadata, 'color').text = '#e67e22'
    etree.SubElement(ZpheresMetadata, 'directionA').text = 'true'
    etree.SubElement(ZpheresMetadata, 'sourceID').text = 'src123'
    etree.SubElement(ZpheresMetadata, 'WayPointSnappingRadius').text = '25'
    etree.SubElement(ZpheresMetadata, 'MaintainPathShape').text = 'true'
    etree.SubElement(ZpheresMetadata, 'ReducePathPoints').text = 'false'
    
    link = etree.SubElement(meta, 'link', href="http://geo.zpheres.com")
    link.text = "GEO Zpheres"
    
    root.insert(0, meta)
    etree.dump(root)
    tree.write(path,encoding="utf-8", xml_declaration=True, pretty_print=True)

def selectLastMonth(dataPathLoc,dataPathTrip):
    oneMonth = 2592000000 # in ms
    dataPathLocs,dataPathTrips = selectRange(dataPathLoc,dataPathTrip, mac, timerange = oneMonth)
    return dataPathLocs,dataPathTrips

def selectRange(dataPathLoc,dataPathTrip, mac, dateStart = 'beginning', dateEnd = 'end', timerange = None):

    if mac:
        slash = "/"
    else:
        slash = "\\"
    newPath = str(Path(dataPathLoc).parents[2]) + slash + dateStart + "_" + dateEnd + slash

    if os.path.exists(newPath):
        return newPath + "Location History.json", newPath + "Semantic Location History" + slash
    
    # Location File
    if (type(dataPathLoc) is str):
        with open(dataPathLoc) as f:
            jsonData = json.load(f)
    else:
        jsonData = dataPathLoc
    
    collectDate = pd.to_datetime(int(jsonData["locations"][0]["timestampMs"]),  unit='ms')
    setDate = pd.to_datetime([dateStart])

    if (collectDate < setDate):
        # print("Start date: " + str(dateStart))
        labelStart = str(dateStart)
        print("Start date: " + labelStart)
    else:
        # print("Start date: " + str(pd.to_datetime(int(jsonData["locations"][0]["timestampMs"]),  unit='ms').date()))
        labelStart = str(pd.to_datetime(int(jsonData["locations"][0]["timestampMs"]),  unit='ms').date())
        print("Start date: " + labelStart)
        
    # print("Collected Start date: " + str(pd.to_datetime(int(jsonData["locations"][0]["timestampMs"]),  unit='ms').date()))
    # print("Setted Start date: " + str(dateStart))

    if (dateEnd == "end"):
        labelEnd = str(pd.to_datetime(int(jsonData["locations"][-1]["timestampMs"]),  unit='ms').date())
        print("End date: " + labelEnd)
        # print("End date: " + str(pd.to_datetime(int(jsonData["locations"][-1]["timestampMs"]),  unit='ms').date()))
        # labelEnd = str(pd.to_datetime(int(jsonData["locations"][-1]["timestampMs"]),  unit='ms').date())
    else:
        # print("End date: " + str(dateEnd))
        lebelEnd = str(dateEnd)
        print("End date: " + labelEnd)
    #dateStart = input("Choose a start date: ")
    #dateEnd = input("Choose a end date: ")

    if timerange:
        dateEnd = int(jsonData["locations"][-1]["timestampMs"])
        dateStart = dateEnd - timerange
    else:
        if dateStart == 'beginning':
            dateStart = int(jsonData["locations"][0]["timestampMs"])
        else:
            dateTemp = pd.to_datetime([dateStart])
            dateStart = ((dateTemp - pd.Timestamp("1970-01-01")) // pd.Timedelta('1ms'))[0]  
            
        if dateEnd == 'end':
            dateEnd = int(jsonData["locations"][-1]["timestampMs"])
        else:
            dateTemp = pd.to_datetime([dateEnd])
            dateEnd = ((dateTemp - pd.Timestamp("1970-01-01")) // pd.Timedelta('1ms'))[0]  

    newPath = str(Path(dataPathLoc).parents[2]) + slash + str(pd.to_datetime(dateStart,  unit='ms').date()) + "_" + str(pd.to_datetime(dateEnd,  unit='ms').date()) + slash

    
    if os.path.exists(newPath):
        return newPath + "Location History.json", newPath + "Semantic Location History" + slash
    else:
        os.makedirs(newPath)
    
    #timestamps = pd.json_normalize(jsonData, 'locations')['timestampMs'].astype(np.int64)
    timestamps = pd.Series([x['timestampMs'] for x in jsonData['locations']]).astype(np.int64)
    
    indexStart = bisect.bisect_right(timestamps,dateStart)
    indexEnd = bisect.bisect_left(timestamps,dateEnd)
    
    jsonData["locations"] = jsonData["locations"][indexStart:indexEnd]
    if (type(dataPathLoc) is str):
        newDataPathLoc = newPath + "Location History.json"
        with open(newPath + "Location History.json", 'w') as outfile:
            json.dump(jsonData, outfile)
    
    # Trip files
    for root,dirs,files in os.walk(dataPathTrip):
       years = dirs
       break
    
    startYear = pd.to_datetime(dateStart,  unit='ms').year
    endYear = pd.to_datetime(dateEnd,  unit='ms').year
    startMonth = pd.to_datetime(dateStart,  unit='ms').month
    endMonth = pd.to_datetime(dateEnd,  unit='ms').month
    
    newDataPathTrip = newPath + "Semantic Location History" + slash

    if not(os.path.exists(newDataPathTrip)):
        os.makedirs(newDataPathTrip)
    
    for year in years:
        if int(year) >= startYear and int(year) <=endYear:
            if not(os.path.exists(newDataPathTrip + year + slash)):
                os.makedirs(newDataPathTrip + year + slash)

            for month in range(1,13):
                dateTemp = pd.to_datetime([year + '-' + str(month)])
                if dateTemp >= pd.to_datetime([str(startYear) + '-' + str(startMonth)]) and dateTemp <= pd.to_datetime([str(endYear) + '-' + str(endMonth)]):
                    filePath = dataPathTrip + year + slash + year + "_" + calendar.month_name[month].upper() + ".json"
                    newFilePath = newDataPathTrip + year + slash + year + "_" + calendar.month_name[month].upper() + ".json"
                    if os.path.exists(filePath):
                        if (int(year) == startYear) and month == startMonth:
                            _splitTripFile(filePath, newFilePath, dateStart, dateEnd)
                        elif (int(year) == endYear) and month == endMonth:
                            _splitTripFile(filePath, newFilePath, dateStart, dateEnd)
                        else:
                            copyfile(filePath , newFilePath)
                
    return newDataPathLoc,newDataPathTrip,labelStart,labelEnd

def _splitTripFile(filePath, newFilePath, dateStart, dateEnd):
    with open(filePath) as f:
        jsonData = json.load(f)
            
    timestamps = pd.Series([x[list(x)[0]]['duration']['startTimestampMs'] for x in jsonData['timelineObjects']]).astype(np.int64)
    
    indexStart = bisect.bisect_right(timestamps,dateStart)
    indexEnd = bisect.bisect_left(timestamps,dateEnd)
    
    jsonData["timelineObjects"] = jsonData["timelineObjects"][indexStart:indexEnd]
    with open(newFilePath, 'w') as outfile:
        json.dump(jsonData, outfile)

def addDistancesToTrps(row):
    coords = row['geom'].coords
    length = row['length']
    segments = []
    cumsum = 0
    if (length > 0):
        for i in range(1,len(coords)):
            proportion = LineString((coords[i-1],coords[i])).length / length
            cumsum = cumsum + proportion
            segments.append(cumsum)
    return segments

def calc_length(row, epsg_code):        
    project = partial(pyproj.transform,
                      pyproj.Proj(init='EPSG:4326'),
                      pyproj.Proj(init='EPSG:{}'.format(epsg_code)))

    shapely_geom = shapely.geometry.shape(row['geom'])
    proj_line = shapely.ops.transform(project, shapely_geom) 
    return round(proj_line.length,2)

def makeDistMatrix(traj):
    #distMatrix = np.empty([len(traj),len(traj)])
    #distMatrix[:] = np.NaN
    condensedDistMatrix = []
    for i in range(len(traj)):
        for j in range(i+1, len(traj)):
            distance, path = fastdtw(traj[i], traj[j], dist=euclidean)
            #distMatrix[i,j] = distance
            condensedDistMatrix.append(distance)
    #i_lower = np.tril_indices(len(traj), -1)
    #distMatrix[i_lower] = distMatrix.T[i_lower]
    condensedDistMatrix = np.array(condensedDistMatrix)
    return condensedDistMatrix

def combineTrajectory(cluster1, cluster2):
    distance, path = fastdtw(cluster1['geom'], cluster2['geom'], dist=euclidean)
    #TODO: Vectorize?
    newGeom = []
    for i,j in path:
        newGeom.append(np.average(np.asarray([cluster1['geom'][i], cluster2['geom'][j]]), axis= 0, weights=[cluster1['weight'],cluster2['weight']]).tolist())
    return newGeom

def findSemanticInfo(places, plcs, threeQua):
    count = 0
    plcs['nameId'] = ""

    for idx in plcs.index:
        minDist = math.inf
        minIdx = None
        for jdx in places.index:
            dist = haversine_dist(plcs.loc[idx,'center'].x, plcs.loc[idx,'center'].y, places.loc[jdx,'geometry'].x, places.loc[jdx,'geometry'].y)
            if dist<minDist:
                minDist = dist
                minIdx = jdx
                
        #a = plcs.loc[idx,'extent'].bounds
        #extent = haversine_dist(a[0],a[1],a[2],a[3])
        if minDist < threeQua:
            plcs.loc[idx,'nameId'] = "Google"
            plcs.loc[idx,'placeName'] = places.loc[minIdx,'placeName']
            count += 1
        else:
            plcs.loc[idx,'nameId'] = "OSMAPI"
            a = plcs.loc[idx,'location'][0].split(",")[0].strip()
            b = plcs.loc[idx,'location'][0].split(",")[1].strip()
            if (a.isdigit()):
                plcs.loc[idx,'placeName'] = b + ' ' + a
            elif(b.isdigit()):
                plcs.loc[idx,'placeName'] = a + ' ' + b
            else:
                plcs.loc[idx,'placeName'] = a + ' ' + b
        
    print(str(count)+" plcs out of "+str(len(plcs))+" are macthed!")

    return plcs

def removeLongTrips(trps, trpsCount):
    for idx in trpsCount.index:
        trpIds = []
        for jdx in trpsCount.loc[idx,'trpIds']:
            # Check if the trip is too long:
            if trps.loc[jdx,"geom"].length < 3*trpsCount.loc[idx,'geom'].length:
                trpIds.append(jdx)
            else:
                trps = trps.drop(jdx)   
        if len(trpIds) == 0:
            trpsCount = trpsCount.drop(idx)
        else:
            trpsCount.at[idx,'trpIds'] = trpIds
            trpsCount.at[idx,'count'] = len(trpIds)
    return trps, trpsCount
    
    
def savecsv4js(dataName, places, trips, tripsSchematic):
    places['city'] = 'Zurich'
    places['state'] = 'Zurich'
    places['country'] = 'Switzerland'
    places = places.rename(columns = {'place_id':'placeId'})
    places['placeId'] = places['placeId'].astype(str)
    places['latitude'] = places['center'].y
    places['longitude'] = places['center'].x
    places.geometry = places['centerSchematic']
    places['latitudeSchematic'] = places.geometry.y
    places['longitudeSchematic'] = places.geometry.x
    places = places.drop(columns = ['user_id', 'extent', 'center', 'centerSchematic'])
    places.to_csv('../../5-Final Product/stat' + dataName+'/places.csv',  index = False, sep = ";")
 
    
    trips = trips.rename(columns = {'start_plc':'origin', 'end_plc':'destination', 'weight':'count'})
    trips["waypointsLat"] = ""
    trips["waypointsLong"] = ""
    for i in trips.index:
        trips.loc[i, "waypointsLong"] = ' '.join([str(j[0]) for j in trips.loc[i,'geom'].coords])
        trips.loc[i, "waypointsLat"] = ' '.join([str(j[1]) for j in trips.loc[i,'geom'].coords])
        trips.loc[i, "waypointsLongSchematic"] = ' '.join([str(j[0]) for j in tripsSchematic.loc[i,'geom'].coords])
        trips.loc[i, "waypointsLatSchematic"] = ' '.join([str(j[1]) for j in tripsSchematic.loc[i,'geom'].coords])

    trips = trips.rename(columns = {'weight':'count'})
    trips = trips[['origin', 'destination','count','waypointsLong','waypointsLat','waypointsLatSchematic','waypointsLongSchematic']]
    #trips.to_csv('../jsProject/stat/trips.csv',  index = False, sep = ";")
    trips.to_csv('../../5-Final Product/stat' + dataName+'/tripsAgr.csv',  index = False, sep = ";")

def savecsv4jsTrps(dataName, trips):    
    trips = trips.rename(columns = {'start_plc':'origin', 'end_plc':'destination'})
    trips["waypointsLat"] = ""
    trips["waypointsLong"] = ""
    for i in trips.index:
        trips.loc[i, "waypointsLong"] = ' '.join([str(j[0]) for j in trips.loc[i,'geom'].coords])
        trips.loc[i, "waypointsLat"] = ' '.join([str(j[1]) for j in trips.loc[i,'geom'].coords])

    trips = trips[['origin', 'destination','waypointsLong','waypointsLat']]
    #trips.to_csv('../jsProject/stat/trips.csv',  index = False, sep = ";")
    trips.to_csv('../../5-Final Product/FINALDATA/stat' + dataName+'/trips.csv',  index = False, sep = ";")

    

