#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Main Functions
    This file holds all the bigger functions of the main steps.
    
    Created on Sat May  9 12:07:38 2020
    Authors:    Daniel Laumer (laumerd@ethz.ch)
                Haojun Cai (caihao@ethz.ch)
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import os
from collections import defaultdict

from shapely.geometry import LineString
from scipy.cluster.hierarchy import linkage, cut_tree, fcluster, dendrogram, cophenet, inconsistent, maxinconsts, maxdists, maxRstat
from scipy.spatial.distance import squareform
from matplotlib import pyplot as plt


import trackintel as ti
from trackintel.geogr.distances import meters_to_decimal_degrees
from trackintel.geogr.distances import haversine_dist

# Local files
import help_functions as hlp
import trackintel_modified as tim
import staypoints_modified as stm

def findStayPoints(locs, dataName, accuracy_threshold, dist_threshold, time_threshold, timemax_threshold):
    # Calculate time and distance difference
    #if not(os.path.exists('../data/csv/'+dataName +'/' + dataName + '.csv')):
    if True:    
        locs['d_diff'] = np.append(haversine_dist(locs.longitudeE7[1:], locs.latitudeE7[1:], locs.longitudeE7[:-1], locs.latitudeE7[:-1]),0)
        
        locs = locs[locs['accuracy']<accuracy_threshold]
        #locs = locs[locs['accuracy']<locs['d_diff']]
    
        if not(os.path.exists('../data/shp/'+ dataName + '/')):
            os.makedirs('../data/shp/'+ dataName + '/')
                    
        hlp.loc2csv4ti(locs, dataName)
    pfs = ti.read_positionfixes_csv('../data/csv/'+dataName +'/' + dataName + '.csv', sep=';')
    
    # Find staypoints
    #stps = pfs.as_positionfixes.extract_staypoints(method='sliding',dist_threshold=100, time_threshold=5*60)
    stps = tim.extract_staypoints_ipa(pfs, method='sliding',dist_threshold=dist_threshold,time_threshold=time_threshold,timemax_threshold=timemax_threshold)
    return pfs, stps

def findPlaces(stps, dataName, minDist, minPoints):
    
    # Find places
    plcs = stm.cluster_staypoints(stps,method='dbscan', epsilon=meters_to_decimal_degrees(minDist, 47.5), num_samples=minPoints)
    return plcs

def findTrips(pfs, stps, plcs, dataName):
    # Find the trips between the PLACES!!
    tpls = tim.extract_triplegs_ipa(pfs, stps)
    
    trps = pd.DataFrame(columns=['id', 'started_at', 'finished_at','start_plc', 'end_plc', 'geom'])
    trpsAgr = pd.DataFrame(columns=['id','count', 'start_plc', 'end_plc', 'geom'])

    generated_trips = []        
    generated_trips_aggr = {}

    count = 0;
    #countMatrix = np.zeros([len(plcs),len(plcs)])
    
    coordsCombined = []
    tplTemp = {}
    for i in range(len(tpls)):
        startPlace = stps.loc[tpls.loc[i,'start_stp'],'place_id']
        endPlace = stps.loc[tpls.loc[i,'end_stp'],'place_id']
        coords = tpls.loc[i,'geom'].coords[:]

        if (startPlace == -1) and (endPlace == -1):
            coordsCombined = coordsCombined[:-1] + coords
        if (startPlace != -1):
            startCoord = plcs.loc[startPlace-1,'center'].coords[:]
            coordsCombined = startCoord + coords[1:]
            
            tplTemp = { 'id': count,
                        'started_at': tpls.loc[i,'started_at'],  # pfs_tripleg['tracked_at'].iloc[0],
                        'finished_at': None,  # pfs_tripleg['tracked_at'].iloc[-1],
                        'geom': None,
                        'start_plc': startPlace,
                        'end_plc': None
                    }
            
        if (endPlace != -1) and tplTemp:
            endCoord = plcs.loc[endPlace-1,'center'].coords[:]
            if (startPlace != -1):
                coordsCombined =  coordsCombined[:-1] + endCoord
            else:
                coordsCombined =  coordsCombined[:-1] + coords[:-1] + endCoord
            
            tplTemp["finished_at"] = tpls.loc[i,'finished_at']
            tplTemp["geom"] = LineString(coordsCombined)
            tplTemp["end_plc"] = endPlace

            
            ide = str(min(tplTemp["start_plc"], tplTemp["end_plc"])) + '_' + str(max(tplTemp["start_plc"], tplTemp["end_plc"]))
            #ide = str(startPlace) + '_' + str(endPlace)
            coords = [(coordsCombined[1]), (coordsCombined[-1])]

            generated_trips.append(tplTemp)
            
            if ide not in list(generated_trips_aggr):
                generated_trips_aggr[ide] = {
                        'id': ide,
                        'count' : 1,
                        'trpIds' : [count],
                        'start_plc': tplTemp["start_plc"],
                        'end_plc': tplTemp["end_plc"],
                        'geom': LineString(coords),
                    }
            else:
                generated_trips_aggr[ide]['count'] = generated_trips_aggr[ide]['count']+ 1
                generated_trips_aggr[ide]['trpIds'].append(count)
            #countMatrix[startPlace-1,endPlace-1] = countMatrix[startPlace-1,endPlace-1] + 1
            #countMatrix[endPlace-1,startPlace-1] = countMatrix[endPlace-1,startPlace-1] + 1
            count = count + 1
            coordsCombined = []
            tplTemp = {}

            
    trps = trps.append(generated_trips)
    trps = gpd.GeoDataFrame(trps, geometry='geom')
    
    trpsAgr = trpsAgr.append(list(generated_trips_aggr.values()))
    trpsAgr = gpd.GeoDataFrame(trpsAgr, geometry='geom')
    
    return tpls, trps, trpsAgr


def findDirectTrips(pfs, stps, plcs, dataName):
    # Find the trips between the PLACES!!
    tpls = tim.extract_triplegs_ipa(pfs, stps)
    
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
            #ide = str(startPlace) + '_' + str(endPlace)
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
    
    trpsAgr = trpsAgr.append(list(generated_trips_aggr.values()))
    trpsAgr = gpd.GeoDataFrame(trpsAgr, geometry='geom')
    
    return tpls, trps, trpsAgr


def clusterTrips(trps, trpsCount, minDistTh, factorTh, dataName, saveDendogramms = False):
    trps['length'] = trps['geom'].length
    trps['cluster'] = None
    
    trpsAgr = pd.DataFrame(columns=['weight', 'start_plc', 'end_plc', 'geom'])
    generated_trips_aggr = []

    for i in trpsCount.index:
    #for i in range(3,4):
        startPlace = trpsCount.loc[i,'start_plc']
        endPlace = trpsCount.loc[i,'end_plc']
        if startPlace == endPlace:
            continue
        if trpsCount.loc[i,'count'] < 2:
            generated_trips_aggr.append({
                            'id' : str(min(startPlace,endPlace)) + '_' + str(max(startPlace,endPlace)) + '_0',
                            'weight' : 1,
                            'start_plc': startPlace,
                            'end_plc': endPlace,
                            'geom': trps.loc[trpsCount.loc[i,'trpIds'][0],'geom'],
                        })
            continue
        
        trpsTemp = []
        for j in trpsCount.loc[i,'trpIds']:
            if trps.loc[j,'start_plc'] == endPlace:
                temp = [a for a in reversed(trps.loc[j,'geom'].coords[:])]
                trpsTemp.append(temp)
            else:
                trpsTemp.append(trps.loc[j,'geom'].coords[:])
        #trpsTemp = [trps.loc[j,'geom'].coords[:] for j in trpsCount.loc[i,'trpIds']]
        distMatrix = hlp.makeDistMatrix(trpsTemp)
        #minIndices = np.where(distMatrix == np.nanmin(distMatrix))
        #minIndices = list(zip(minIndices[0], minIndices[1]))
        #minIndex = minIndices[0]
        
        linkMatrix = linkage(distMatrix, method='complete')
        
        #a_coph = squareform(cophenet(linkMatrix))
        #a_inco = inconsistent(linkMatrix)
        #a_maxinc = maxinconsts(linkMatrix,a_inco)
        #a_maxdist = maxdists(linkMatrix)
        #a_maxRstat = maxRstat(linkMatrix, a_inco,0)
        a_dn = dendrogram(linkMatrix)
        
        #Find outliers
        outlierIdx = []
        for i in range(len(a_dn["dcoord"])-1,0,-1):
            coo = a_dn["dcoord"][i]
            height1 = coo[1] - coo[0]
            height2 = coo[2] - coo[3]
            if len(trpsTemp) > 2:
                # Check if outlier (large merge height and not a cluster before)
                if height1 > max(linkMatrix[:,2])/2 and linkMatrix[i,0] < len(trpsTemp):
                    outlierIdx.append(int(linkMatrix[i,0]))
                if height2 > max(linkMatrix[:,2])/2 and linkMatrix[i,1] < len(trpsTemp):
                    outlierIdx.append(int(linkMatrix[i,1]))
        
        for idx in sorted(outlierIdx, reverse=True):
            del trpsTemp[idx]
        
        distMatrix = hlp.makeDistMatrix(trpsTemp)   
        linkMatrix = linkage(distMatrix, method='complete')
        
        
        #tree = cut_tree(linkMatrix)
        th = max(minDistTh, max(linkMatrix[:,2])/factorTh)
        clusteringResult = fcluster(linkMatrix,th, 'distance')
        #clusteringResult = tree[:,linkMatrix.shape[0] - 4]
        if saveDendogramms:
            if not os.path.exists('../data/clustering/' + dataName + '/'):
                os.mkdir('../data/clustering/' + dataName + '/')
            fig = plt.figure(figsize=(25, 10))
            dn = dendrogram(linkMatrix, leaf_font_size=12.)
            #plt.show()
            fig.savefig('../data/clustering/' + dataName + '/' + str(startPlace) + '_' + str(endPlace) + '_' +  str(max(clusteringResult)) + '.png')
        
        #for idx, j in enumerate(trpsCount.loc[i,'trpIds']):
        #    #for q in range(len(tree)):
        #    trps.loc[j,'cluster'] = int(clusteringResult[idx])
        
        
        
        #Combining clusters 
        n = linkMatrix.shape[0] + 1
        numOfClusters = max(clusteringResult)
        clusters = defaultdict(dict)
        for idx, geom in zip(range(n), trpsTemp):
            clusters[idx]['geom'] = geom
            clusters[idx]['weight'] = 1
            
        for i in range(n-numOfClusters):
            cluster1 = linkMatrix[i,0]
            cluster2 = linkMatrix[i,1]
            newGeom = hlp.combineTrajectory(clusters[cluster1],clusters[cluster2])
            clusters[n + i] = {}
            clusters[n + i]['geom'] = newGeom
            clusters[n + i]['weight'] = clusters[cluster1]['weight'] + clusters[cluster2]['weight']
            clusters.pop(cluster1)
            clusters.pop(cluster2)
        
        for idx, cluster in enumerate(clusters):
            ide = str(min(startPlace,endPlace)) + '_' + str(max(startPlace,endPlace)) + '_' + str(idx)
            generated_trips_aggr.append({
                            'id' :  ide,
                            'weight' : clusters[cluster]['weight'],
                            'start_plc': startPlace,
                            'end_plc': endPlace,
                            'geom': LineString(clusters[cluster]['geom']),
                        })
    
            
    trpsAgr = trpsAgr.append(generated_trips_aggr)
    trpsAgr = gpd.GeoDataFrame(trpsAgr, geometry='geom')
    return trps, trpsAgr 