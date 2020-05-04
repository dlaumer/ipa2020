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

def apiCall():
    #%% Set variables: 
    urlCore = 'https://renderingapi.azurewebsites.net/api/'
    userId = "3cfb3bd4-add1-4460-8955-88e7eec7cb3b"
    dataname = "1"
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
    
    aeFile = readFile('../data/Settings.json')
    aeFileId = putResponse(urlImport, aeFile)
    
    
    #%% 3. Prepare service call file (sc.json)
    scParam = {}
    scParam['UserId'] = userId
    scParam['RefGpx'] = gpsFileIds
    scParam['RefAutomationSettings'] = aeFileId
    scParam['NetworkName'] = "Import Network Example"
    scParam['CompilationName'] = "SelectedTrips 1"
    scParam['ScenarioName']  = "RerApi Scenario #4"
    
    scFile = json.dumps(scParam)
    
    #%% 4. Import
    urlExecute = urlCore + 'import/' + importID + '/execute'
    networkId = putResponse(urlExecute, scFile)
    
    webbrowser.open("https://network.zpheres.com/" + networkId)
    
    urlDownloadGPX = urlCore + 'network/' + networkId + '/gpx'
    gpxData = requests.get(urlDownloadGPX)  # Get the response 
    z = zipfile.ZipFile(io.BytesIO(gpxData.content))
    
    dataPath = "../data/gpxAPI/"
    if not(os.path.exists(dataPath)):
        os.makedirs(dataPath)
    z.extractall(dataPath)

