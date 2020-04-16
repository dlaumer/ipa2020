#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 10:09:23 2020

Authors:    Daniel Laumer (laumerd@ethz.ch)
            Haojun Cai (caihao@ethz.ch)
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import math
import json
import os
import time

from shapely.geometry import LineString, MultiPoint
from statistics import median 
import bisect # To find an index in a sorted list
import numpy as np
from scipy.spatial.distance import euclidean
from scipy.cluster.hierarchy import linkage, cut_tree, fcluster, dendrogram
from fastdtw import fastdtw

from matplotlib import pyplot as plt


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
#import noiserm_functions as nrm

dataName = '1'
SELECT_RANGE =      False
SAVE_SHP =          True
CHECK_VELO =        False
FIND_STAY_POINTS =  True
FIND_TRIPS =        True
SELECT_REPRESENTATIVE_TRP = False
EXPORT_GPX =        False
CLUSTER_TRPS =      True
CLUSTER_TRPS2 =     False
CHECK_NB_POINTS =   False
CHECK_ACCURACY =    False
PLOT =              False



#%% IMPORT DATA %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

dataPathLocs,dataPathTrips = hlp.getDataPaths(dataName)

if SELECT_RANGE:    
    dateStart = '2020-01-01'
    dateEnd = '2020-02-01'
    dataPathLocs,dataPathTrips = hlp.selectRange(dataPathLocs, dataPathTrips, dateStart = dateStart, dateEnd = dateEnd)
    
locs, locsgdf = hlp.parseLocs(dataPathLocs)
trips, tripdf, tripsgdf = hlp.parseTrips(dataPathTrips)
tripsgdf = hlp.parseTripsWithLocs(dataPathTrips, locsgdf)


#%% EXPORT SHP %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if SAVE_SHP:
    hlp.loc2shp(locsgdf, dataName)
    hlp.trip2shp(tripsgdf, dataName)

#%% ANALYSIS  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Velovity
if CHECK_VELO:
    locs = hlp.calculateVelocity(locs)

#%% TIME AND DISTANCE DIFF

if FIND_STAY_POINTS:
    # Calculate time and distance difference

    locs['d_diff'] = np.append(haversine_dist(locs.longitudeE7[1:], locs.latitudeE7[1:], locs.longitudeE7[:-1], locs.latitudeE7[:-1]),0)
    
    locs = locs[locs['accuracy']<70]
    #locs = locs[locs['accuracy']<locs['d_diff']]

    if not(os.path.exists('../data/shp/'+ dataName + '/')):
        os.makedirs('../data/shp/'+ dataName + '/')
                
    hlp.loc2csv4ti(locs, dataName)
    pfs = ti.read_positionfixes_csv('../data/csv/'+dataName +'/' + dataName + '.csv', sep=';')
    
    # Find staypoints
    #stps = pfs.as_positionfixes.extract_staypoints(method='sliding',dist_threshold=100, time_threshold=5*60)
    stps = tim.extract_staypoints_ipa(pfs, method='sliding',dist_threshold=100, time_threshold=15*60)

    stps_shp = stps.copy()
    stps_shp['started_at'] = stps_shp['started_at'].astype(str)
    stps_shp['finished_at'] = stps_shp['finished_at'].astype(str)
    stps_shp.to_file('../data/shp/'+dataName +'/Staypoints.shp')
    
    # Find places
    plcs = stps.as_staypoints.extract_places(method='dbscan',
        epsilon=meters_to_decimal_degrees(150, 47.5), num_samples=4)
    
    plcs_shp = plcs.copy()
    plcs_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places.shp')
    #plcs_shp.geometry = plcs_shp['extent']
    #plcs_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places_extent.shp')

#%% Find trips from staypoints
if FIND_TRIPS:
    # Find the trips between the PLACES!!
    tpls = tim.extract_triplegs_ipa(pfs, stps)
    
    tpls_shp = tpls.copy()
    tpls_shp['started_at'] = tpls_shp['started_at'].astype(str)
    tpls_shp['finished_at'] = tpls_shp['finished_at'].astype(str)
    tpls_shp.to_file('../data/shp/'+dataName +'/Triplegs.shp')
    
    trps = pd.DataFrame(columns=['id', 'started_at', 'finished_at','start_plc', 'end_plc', 'geom'])
    trpsAgr = pd.DataFrame(columns=['id','count', 'start_plc', 'end_plc', 'geom'])

    generated_trips = []        
    generated_trips_aggr = {}

    count = 0;
    #countMatrix = np.zeros([len(plcs),len(plcs)])
    for i in range(len(tpls)):
        startPlace = stps.loc[tpls.loc[i,'start_stp'],'place_id']
        endPlace = stps.loc[tpls.loc[i,'end_stp'],'place_id']

        if (startPlace != -1) and (endPlace!= -1):
            coords = tpls.loc[i,'geom'].coords[1:-1]
            startCoord = plcs.loc[startPlace-1,'center'].coords[:]
            endCoord = plcs.loc[endPlace-1,'center'].coords[:]
            coords = startCoord + coords + endCoord
            
            generated_trips.append({
                        'id': count,
                        'started_at': tpls.loc[i,'started_at'],  # pfs_tripleg['tracked_at'].iloc[0],
                        'finished_at': tpls.loc[i,'finished_at'],  # pfs_tripleg['tracked_at'].iloc[-1],
                        'geom': LineString(coords),
                        'start_plc': startPlace,
                        'end_plc': endPlace
                    })
            ide = str(min(startPlace,endPlace)) + '_' + str(max(startPlace,endPlace))
            coords = startCoord + endCoord
            if ide not in list(generated_trips_aggr):
                generated_trips_aggr[ide] = {
                        'id': ide,
                        'count' : 1,
                        'trpIds' : [count],
                        'start_plc': startPlace,
                        'end_plc': endPlace,
                        'geom': LineString(coords),
                    }
            else:
                generated_trips_aggr[ide]['count'] = generated_trips_aggr[ide]['count']+ 1
                generated_trips_aggr[ide]['trpIds'].append(count)
            #countMatrix[startPlace-1,endPlace-1] = countMatrix[startPlace-1,endPlace-1] + 1
            #countMatrix[endPlace-1,startPlace-1] = countMatrix[endPlace-1,startPlace-1] + 1
            
            
            count = count + 1
            
    trps = trps.append(generated_trips)
    trps = gpd.GeoDataFrame(trps, geometry='geom')
        
    trps_shp = trps.copy()
    trps_shp['started_at'] = stps_shp['started_at'].astype(str)
    trps_shp['finished_at'] = stps_shp['finished_at'].astype(str)
    trps_shp.to_file('../data/shp/'+dataName +'/Trips.shp')
    
    
    trpsAgr = trpsAgr.append(list(generated_trips_aggr.values()))
    trpsAgr = gpd.GeoDataFrame(trpsAgr, geometry='geom')
    
    trpsAgr_shp = trpsAgr.copy()
    trpsAgr_shp['count'] = trpsAgr_shp['count'].astype(int)
    trpsAgr_shp = trpsAgr_shp.drop(["trpIds"], axis = 1)
    trpsAgr_shp.to_file('../data/shp/'+dataName +'/TripsAggregated.shp')
    
    """
    trpsAgr = pd.DataFrame(columns=['id', 'count', 'start_plc', 'end_plc', 'geom'])
    generated_trips_aggr = []

    # Aggregated and simplified trips
    for i in range(len(plcs)):
        for j in range(i,len(plcs)):
            if countMatrix[i,j] != 0:
                startCoord = plcs.loc[i,'center'].coords[:]
                endCoord = plcs.loc[j,'center'].coords[:]
                coords = startCoord + endCoord
                generated_trips_aggr.append({
                        'id': str(i+1) + '_' + str(j+1),
                        'count' : countMatrix[i,j],
                        'start_plc': str(i+1),
                        'end_plc': str(j+1),
                        'geom': LineString(coords),
                    })
    trpsAgr = trpsAgr.append(generated_trips_aggr)
    trpsAgr = gpd.GeoDataFrame(trpsAgr, geometry='geom')
        
    trpsAgr_shp = trpsAgr.copy()
    trpsAgr_shp.to_file('../data/shp/'+dataName +'/TripsAggregated.shp')
    """
    #%%
if SELECT_REPRESENTATIVE_TRP:
    trpsSelected = trpsAgr.copy()
    for i in range(len(trpsSelected)):
        if len(trpsSelected.loc[i,'trpIds']) > 0:
            selectedTrip = trpsSelected.loc[i,'trpIds'][0]
            for j in trpsSelected.loc[i,'trpIds']:
                #print(trps.loc[j,'geom'])
                if len(trps.loc[j,'geom'].coords[:]) > 6 and len(trps.loc[j,'geom'].coords[:]) < 10:
                    selectedTrip = j
                    
                    break
        print(len(trps.loc[j,'geom'].coords[:]))        
        trpsSelected.loc[i,'geom'] = trps.loc[selectedTrip,'geom']
    
    trpsSelected_shp = trpsSelected.copy()
    trpsSelected_shp['count'] = trpsSelected_shp['count'].astype(int)
    trpsSelected_shp = trpsSelected_shp.drop(["trpIds"], axis = 1)
    trpsSelected_shp.to_file('../data/shp/'+dataName +'/TripsSelected.shp')
 
#%% EXPORT GPX %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if EXPORT_GPX:
    for idx in trpsSelected.index:
        if trpsSelected.loc[idx,'start_plc'] == trpsSelected.loc[idx,'end_plc']:
            trpsSelected = trpsSelected.drop([idx])
        elif trpsSelected.loc[idx,'count'] < 5:
            trpsSelected = trpsSelected.drop([idx])
    hlp.trip2gpx(trpsSelected,dataName)
    
    
#%%
if CLUSTER_TRPS:
    trps['length'] = trps['geom'].length
    trps['cluster'] = None
    
    clusteredTrps = []
    #for i in range(len(trpsAgr)):
    i = 3
    
    distMatrix = hlp.makeDistMatrix([trps.loc[j,'geom'].coords[:] for j in trpsAgr.loc[i,'trpIds']])
    #minIndices = np.where(distMatrix == np.nanmin(distMatrix))
    #minIndices = list(zip(minIndices[0], minIndices[1]))
    #minIndex = minIndices[0]
    
    linkMatrix = linkage(distMatrix, method='complete')
    fig = plt.figure(figsize=(25, 10))
    dn = dendrogram(linkMatrix)
    plt.show()
    
    tree = cut_tree(linkMatrix)

    
    for idx, j in enumerate(trpsAgr.loc[i,'trpIds']):
        trps.loc[j,'cluster'] = int(tree[idx,68])
    
    trps_shp = trps.copy()
    trps_shp['started_at'] = stps_shp['started_at'].astype(str)
    trps_shp['finished_at'] = stps_shp['finished_at'].astype(str)
    trps_shp.to_file('../data/shp/'+dataName +'/Trips.shp')

    #%%

#NOT WORKING...
if CLUSTER_TRPS2:
    trps['length'] = trps['geom'].length
    trps['segments'] =  trps.apply(hlp.addDistancesToTrps,axis=1)
    
    clusteredTrps = []
    for i in range(len(trpsAgr)):
        waypoints = []
        for q in range(1,10):
            listpoints = []
            for j in range(len(trpsAgr.loc[i,'trpIds'])):
                segments = list(trps.loc[trpsAgr.loc[i,'trpIds'][j],'segments'])
                if len(segments) > 0:
                    idx = bisect.bisect_left(segments,q/10)
                    
                    if trps.loc[trpsAgr.loc[i,'trpIds'][j],'segments'][idx] > (q-1)/10:
                        listpoints.append(trps.loc[trpsAgr.loc[i,'trpIds'][j],'geom'].coords[idx])
            multi = MultiPoint(listpoints)
            if len(multi) > 0:
                waypoints.append(multi.centroid)
        if len(waypoints)>0:
            clusteredTrps.append(LineString([x.coords[:][0] for x in waypoints]))
        else:
            clusteredTrps.append(None)
    #trpsAgr = trpsAgr.drop(['geom'], axis = 1)
    #trpsAgr['geometry'] = clusteredTrps
    #trpsAgr.geometry = trpsAgr['geometry']
    
    #trpsAgr_shp = trpsAgr.copy()
    #trpsAgr_shp = trpsAgr_shp.drop(['geom', 'trpIds'], axis = 1)
    #trpsAgr_shp = trpsAgr_shp.dropna()
    #trpsAgr_shp.set_geometry('geometry')
    #trpsAgr_shp.to_file('../data/shp/'+dataName +'/TripsAggregatedNew.shp')

    
#%%Accuracy
if CHECK_ACCURACY:
    #for i in [30,40,50,60,70]:
    #    print('Lower then '+str(i)+'m: '+str(round(100*len(locs[locs['accuracy'].lt(i)])/len(locs),2)))
    
    accuracyPerMode = {}
    for i in range(len(tripsgdf)):
        if (tripsgdf.loc[i,'Type'] == 'activitySegment'):
            if (tripsgdf.loc[i,'actType'] not in list(accuracyPerMode)):
                accuracyPerMode[tripsgdf.loc[i,'actType']] = []
            accuracies = list(locsgdf['accuracy'][tripsgdf.loc[i,'correspondingLocs'][0]:tripsgdf.loc[i,'correspondingLocs'][-1]])
            accuracyPerMode[tripsgdf.loc[i,'actType']] = accuracyPerMode[tripsgdf.loc[i,'actType']] + accuracies
    infoPerModeTemp = []
    infoPerMode = pd.DataFrame(columns=['mode', 'averageAccuracy', 'numberOfPoints'])
    for mode in list(accuracyPerMode):
        infoPerModeTemp.append({
            'mode': mode,
            'averageAccuracy': float(median(accuracyPerMode[mode])),
            'numberOfPoints': len(accuracyPerMode[mode])
            })
    infoPerMode = infoPerMode.append(infoPerModeTemp)

    
# Number of points per day
if CHECK_NB_POINTS:
    idx = pd.date_range(locs.index[0].date(), locs.index[-1].date())
    perDay = (locs.groupby(locs.index.date).count()['timestampMs'])
    perDay = perDay.reindex(idx, fill_value=0)

#hlp.checkTrips(trips)

#%% PLOT %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if PLOT:
    
    def getWidth(count):
        if count < 4:
            return 2
        elif count < 10:
            return 4
        elif count < 50:
            return 8
        else: 
            return 10
    
    labels, values = hlp.pieChartInfoPlus(trips)

    fig = make_subplots(
    rows=2, cols=2,
    column_widths=[0.6, 0.4],
    row_heights=[0.4, 0.6],
    specs=[[{"type": "Bar", "colspan": 2}, None],
           [ {"type": "Scattermapbox"}    , {"type": "Pie"}]])

    fig.add_trace( 
        go.Bar(x=list(perDay.index), 
               y=list(perDay),
               name="Number of points per day"
               ),
        row=1, col=1
        )
    
    fig.add_trace( 
        go.Pie(labels=labels, values=values),
        row=2, col=2
        )
        
    for idx in trpsAgr.index:
        if trpsAgr.loc[idx,'count'] > 2:
            trpsAgr.loc[idx,'geom'].coords[:]
            fig.add_trace(
                go.Scattermapbox(
                    lon = [trpsAgr.loc[idx,'geom'].coords[0][0], trpsAgr.loc[idx,'geom'].coords[1][0]],
                    lat = [trpsAgr.loc[idx,'geom'].coords[0][1], trpsAgr.loc[idx,'geom'].coords[1][1]],
                    text = "Number of trips taken: " +  str(trpsAgr.loc[idx,'count']),
                    mode = 'markers+lines',
                    name="Trips Aggregated",
                    showlegend=False,
                    marker = go.scattermapbox.Marker(
                        color = "red"
                    ),
                    line = go.scattermapbox.Line(
                        color = "red",
                        width=getWidth(trpsAgr.loc[idx,'count'])
                    ),
                    ),
                row=2, col=1
                )
    
    
    fig.update_layout(
        mapbox=dict(
            accesstoken = "pk.eyJ1IjoiZGxhdW1lciIsImEiOiJjazhwdWc1aG8wazZnM2xubG5uaGwxN2RmIn0.cgSC6SK8DdnCPwO4NmjxAQ",                    
            ))
    fig.update_layout(
    mapbox = {
        'center': {'lon': 8.49, 'lat': 47.41},
        'style': "mapbox://styles/dlaumer/ck91fkxzs08kw1is4sr31byc5",
        'zoom': 11})
    fig.show()
    fig.write_html("dashboard.html")

    #fig2 = px.histogram(locs, x="accuracy")
    #fig2.show()