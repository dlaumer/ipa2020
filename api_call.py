#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" API call
    This script executes the call to the Hitouch API called ReRAPI
    
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
    if data is None: 
        response = requests.get(url)  # Get the response 
    else:
        response = requests.get(url, data = data)  # Get the response 
    return response.text

def putResponse(url, data=None):
    if data is None: 
        response = requests.put(url)  # Get the response 
    else:
        response = requests.put(url, data = data)  # Get the response 
    return response.text

def readFile(path):
    with open(path, 'r') as file:
        data = file.read()
    return data

def apiCall(dataname, scenarioNumber, homeCoords):
    #%% Set variables: 
    urlCore = 'https://renderingapi.azurewebsites.net/api/'
    userId = "3cfb3bd4-add1-4460-8955-88e7eec7cb3b"
    for root,dirs,files in os.walk("../data/gpx/" + dataname + "/"):
       gpxFiles = files
       break
    #gpxFiles = ['1_11','1_13','1_242','1_350']
    
    #%% 1. Intialise and get importID
    urlInit = urlCore + 'initimport'
    importID = getResponse(urlInit)
    
    #%% 2. Upload GPX files
    
    urlImport = urlCore + 'import/' + importID
    gpsFileIds = []
    for gpxFile in gpxFiles:
        fileContent = readFile('../data/gpx/' + dataname + '/' + gpxFile)
        gpsFileIds.append(putResponse(urlImport, fileContent))
    
    aeFile = readFile('../data/ETH1.json')
    aeFileJson = json.loads(aeFile)
    aeFileJson["fishEye"]["centerLat"] = homeCoords[1]
    aeFileJson["fishEye"]["centerLon"] = homeCoords[0]
    
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
    
    #%% 4. Import
    urlExecute = urlCore + 'import/' + importID + '/execute'
    networkId = putResponse(urlExecute, scFile)
    
    webbrowser.open("https://network.zpheres.com/" + networkId)
    
    urlDownloadGPX = urlCore + 'network/' + networkId + '/gpx'
    gpxData = requests.get(urlDownloadGPX)  # Get the response 
    z = zipfile.ZipFile(io.BytesIO(gpxData.content))
    
    dataPath = "../data/gpxAPI/"+str(scenarioNumber) + '/'
    if os.path.exists(dataPath):
        shutil.rmtree(dataPath)
    os.makedirs(dataPath)
    z.extractall(dataPath)


def readApiCall(trips, scenarioNumber):
    
    pathRoot = "../data/gpxAPI/" + str(scenarioNumber) + "/IPA_Compilation/IPA_Scenario_" + str(scenarioNumber) + "/"
    for root,dirs,files in os.walk(pathRoot):
       gpxFiles = files
       break
    
    for gpxFile in gpxFiles:
        path = pathRoot + gpxFile
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(path, parser)  
        #etree.register_namespace('gpx',"http://www.topografix.com/GPX/1/1")
        root = tree.getroot()
        
        for neighbor in root.iter('PathRefID'):
            pathId = neighbor.text
        
        gpx_file = open(path, 'r')
        gpx = gpxpy.parse(gpx_file)
        
        
        coords = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    coords.append((point.longitude, point.latitude))
        geom = LineString(coords)
        idx = trips.index[np.where(trips['id']==pathId)[0][0]]
        
        trips.loc[int(idx),'geom'] = geom
    return trips

