#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" API call
    This script holds function to execute the call to the Hitouch API called ReRAPI
    and also parse the response
    
    Created on Thu Mar 28 2020
    Authors:    Daniel Laumer (laumerd@ethz.ch)
                Haojun Cai (caihao@ethz.ch)
    
"""

import requests # To open URL adresses
import json
import webbrowser
import io
import zipfile
import os
import numpy as np
import shutil

import gpxpy
import gpxpy.gpx
from lxml import etree
from shapely.geometry import LineString

import help_functions as hlp


def getResponse(url, data=None):
    """
    Make a "get" call

    Parameters
    ----------
    url : str - url to call, meaning to download sth

    Returns
    -------
    response.text: str - Response from the "get" call

    """
    if data is None: 
        response = requests.get(url)  # Get the response without input
    else:
        response = requests.get(url, data = data)  # Get the response with input data
    return response.text

def putResponse(url, data=None):
    """
    Make a "put" call, meaning to upload sth

    Parameters
    ----------
    url : str - url to call

    Returns
    -------
    response.text: str - Response from the "put" call

    """
    if data is None: 
        response = requests.put(url)  # Get the response without input
    else:
        response = requests.put(url, data = data)  # Get the response with input data
    return response.text

def readFile(path):
    """
    Make a "put" call, meaning to upload sth

    Parameters
    ----------
    path : str - path to the file

    Returns
    -------
    data: str - File as str

    """
    with open(path, 'r') as file:
        data = file.read()
    return data


def apiCall(dataname, scenarioNumber, homeCoords, DP_tolerance, fisheye_factor,curver_min, curver_max, curver_r):
    """
    Prepare all files for the API call, load them and then finally call the api

    Parameters
    ----------
    dataname : str - ID of the participant
    scenarioNumber: int - To differentiate between calls
    homeCoords: array - coordinates of the home place
    DP_tolerance, fisheye_factor,curver_min, curver_max, curver_r: float - all the parameters for the API settings

    Returns
    -------
    None

    """
    #%% Set variables: 
    urlCore = 'https://renderingapi.azurewebsites.net/api/'
    userId = "3cfb3bd4-add1-4460-8955-88e7eec7cb3b"

    # Read all the files in the directory (hardcoded path)
    for root,dirs,files in os.walk("../data/results/gpx/" + dataname + "/"):
       gpxFiles = files
       break
    
    #%% 1. Intialise and get importID
    urlInit = urlCore + 'initimport'
    importID = getResponse(urlInit)
    
    #%% 2. Upload GPX files
    urlImport = urlCore + 'import/' + importID
    gpsFileIds = []
    for gpxFile in gpxFiles:
        fileContent = readFile('../data/results/gpx/' + dataname + '/' + gpxFile)
        gpsFileIds.append(putResponse(urlImport, fileContent))
    
    # Read the settings file
    aeFile = readFile('../data/input/ETH1.json')
    aeFileJson = json.loads(aeFile)

    # Change some parameters according to the participant
    aeFileJson["douglasPeucker1"]["tolerance"]["from"] = DP_tolerance
    aeFileJson["douglasPeucker1"]["tolerance"]["to"] = DP_tolerance
    
    aeFileJson["fishEye"]["factor"]["from"] = fisheye_factor
    aeFileJson["fishEye"]["factor"]["to"] = fisheye_factor

    aeFileJson["fishEye"]["centerLat"] = homeCoords[1]
    aeFileJson["fishEye"]["centerLon"] = homeCoords[0]
    
    aeFileJson["curver"]["maxAngle"] = curver_max
    aeFileJson["curver"]["minAngle"] = curver_min
    aeFileJson["curver"]["radius"] = curver_r
    aeFileJson["curver"]["radius2"] = curver_r
    
    # Save the json file for further use
    if not os.path.exists('../data/results/APISettings/'):
        os.mkdir('../data/results/APISettings/')
    with open('../data/results/APISettings/' + dataname + '.json','w') as f:
        json.dump(aeFileJson, f)

    # Also upload the settings file
    aeFile = json.dumps(aeFileJson)
    aeFileId = putResponse(urlImport, aeFile)
    
    
    #%% 3. Prepare service call file (sc.json)
    scParam = {}
    scParam['UserId'] = userId
    scParam['RefGpx'] = gpsFileIds
    scParam['RefAutomationSettings'] = aeFileId
    scParam['NetworkName'] = "Import Network Example"
    scParam['CompilationName'] = "IPA_Compilation"
    scParam['ScenarioName']  = "IPA_Scenario_" + str(scenarioNumber)
    
    scFile = json.dumps(scParam)
    
    #%% 4. Execute the call
    urlExecute = urlCore + 'import/' + importID + '/execute'
    networkId = putResponse(urlExecute, scFile)
    
    # Open the result in a webbrowser
    webbrowser.open("https://network.zpheres.com/" + networkId)
    
    # Get the id of the scenario and then download the zip
    urlDownloadGPX = urlCore + 'network/' + networkId + '/gpx'
    gpxData = requests.get(urlDownloadGPX)  # Get the response 
    z = zipfile.ZipFile(io.BytesIO(gpxData.content))
    
    # Unzip the file and save it for further use
    if not os.path.exists("../data/results/gpxAPI/"):
        os.mkdir("../data/results/gpxAPI/")
    dataPath = "../data/results/gpxAPI/"+str(scenarioNumber) + '/'
    if os.path.exists(dataPath):
        shutil.rmtree(dataPath)
    os.makedirs(dataPath)
    z.extractall(dataPath)


def readApiCall(trips, scenarioNumber):
    """
    Read the files from the API call (zip file) and save them to an existing pandas dataframe

    Parameters
    ----------
    trips: df - Dataframe with all attributes from the aggregated trips
    scenarioNumber: int - To differentiate between calls

    Returns
    -------
    trips: df = Dataframe from the input, but geometry was changed to the schematic one

    """
    # Find all returned gps files
    pathRoot = "../data/results/gpxAPI/" + str(scenarioNumber) + "/IPA_Compilation/IPA_Scenario_" + str(scenarioNumber) + "/"
    for root,dirs,files in os.walk(pathRoot):
       gpxFiles = files
       break
    
    # Read each file
    for gpxFile in gpxFiles:
        # First find the ID of the trip to find out the end and start point
        path = pathRoot + gpxFile
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(path, parser)  
        root = tree.getroot()
        for neighbor in root.iter('PathRefID'):
            pathId = neighbor.text
        
        # Then extract the geometry
        gpx_file = open(path, 'r')
        gpx = gpxpy.parse(gpx_file)
        coords = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    coords.append((point.longitude, point.latitude))
        geom = LineString(coords)
        #print(gpxFile)
        idx = trips.index[np.where(trips['id']==pathId)[0][0]]
        
        #Replace the geometry
        trips.loc[int(idx),'geom'] = geom
    return trips

