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
    """
    Finds the staypoints from the raw locations, following Li's algorithm with the help of trackintel   

    Parameters
    ----------
    locs : gdf - raw points as a geopandas df
    dataName : str - ID of participant
    accuracy_threshold, dist_threshold, time_threshold, timemax_threshold : float - Different thresholds needed in the analysis

    Returns
    -------
    pds : gdf - positionfixes, also the raw locations but in the format of trackintel
    stps : gdf - staypoints, found by the algorithm of trackintel

    """
    # Calculate time and distance difference
    if True:    
        locs['d_diff'] = np.append(haversine_dist(locs.longitudeE7[1:], locs.latitudeE7[1:], locs.longitudeE7[:-1], locs.latitudeE7[:-1]),0)
        
        locs = locs[locs['accuracy']<accuracy_threshold]
        #locs = locs[locs['accuracy']<locs['d_diff']]
    
        if not(os.path.exists('../data/results/shp/'+ dataName + '/')):
            os.makedirs('../data/results/shp/'+ dataName + '/')
                    
        hlp.loc2csv4ti(locs, dataName)
    pfs = ti.read_positionfixes_csv('../data/results/csv/'+dataName +'/' + dataName + '.csv', sep=';')
    
    # Find staypoints using a slightly modified version of the trackintel script
    stps = tim.extract_staypoints_ipa(pfs, method='sliding',dist_threshold=dist_threshold,time_threshold=time_threshold,timemax_threshold=timemax_threshold)
    return pfs, stps

def findPlaces(stps, dataName, minDist, minPoints):
    """
    Used the result from findStayPoints() to cluster places with DBSCAN   

    Parameters
    ----------
    stps : gdf - staypoints, found by the algorithm of trackintel
    dataName: str - ID of participant
    minDist, minPoints: float - Thresholds for the DBSCAN

    Returns
    -------
    plcs : gdf - The clustered places defined by the DBSCAN

    """
    # Find places
    plcs = stm.cluster_staypoints(stps,method='dbscan', epsilon=meters_to_decimal_degrees(minDist, 47.5), num_samples=minPoints)
    return plcs

def findTrips(pfs, stps, plcs, dataName):
    """
    Extract the trajectories between the found places   

    Parameters
    ----------
    pds : gdf - positionfixes, also the raw locations but in the format of trackintel
    stps : gdf - staypoints, found by the algorithm of trackintel
    plcs : gdf - The clustered places defined by the DBSCAN
    dataName: str - ID of participant

    Returns
    -------
    tpls: gdf - triplegs, all trajectories between staypoints
    trps: gdf - Trips, all trahectories between places
    trpsCount: gdf - Only one trip per place pair, and geometry is a straight line

    """
    # First find the trips between the staypoints
    tpls = tim.extract_triplegs_ipa(pfs, stps)
    
    # Prepare the gdf
    trps = pd.DataFrame(columns=['id', 'started_at', 'finished_at','start_plc', 'end_plc', 'geom'])
    trpsCount = pd.DataFrame(columns=['id','count', 'start_plc', 'end_plc', 'geom'])

    generated_trips = []        
    generated_trips_count = {}

    count = 0;
    
    coordsCombined = []
    tplTemp = {}
    # Go through each tripleg and combine them until a new place comes
    for i in range(len(tpls)):
        startPlace = stps.loc[tpls.loc[i,'start_stp'],'place_id']
        endPlace = stps.loc[tpls.loc[i,'end_stp'],'place_id']
        coords = tpls.loc[i,'geom'].coords[:]
        # Case 1: tripleg is not between places, just add it
        if (startPlace == -1) and (endPlace == -1):
            coordsCombined = coordsCombined[:-1] + coords
        # Case 2: tripleg starts at a place: start a new trip
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
        # Case 3: tripleg ends at a place: finish the entry
        if (endPlace != -1) and tplTemp:
            endCoord = plcs.loc[endPlace-1,'center'].coords[:]
            if (startPlace != -1):
                coordsCombined =  coordsCombined[:-1] + endCoord
            else:
                coordsCombined =  coordsCombined[:-1] + coords[:-1] + endCoord
            
            tplTemp["finished_at"] = tpls.loc[i,'finished_at']
            tplTemp["geom"] = LineString(coordsCombined)
            tplTemp["end_plc"] = endPlace

            # Here also prepare the entry for the counted trajectories
            ide = str(min(tplTemp["start_plc"], tplTemp["end_plc"])) + '_' + str(max(tplTemp["start_plc"], tplTemp["end_plc"]))
            #ide = str(startPlace) + '_' + str(endPlace)
            coords = [(coordsCombined[0]), (coordsCombined[-1])]

            generated_trips.append(tplTemp)
            
            if ide not in list(generated_trips_count):
                generated_trips_count[ide] = {
                        'id': ide,
                        'count' : 1,
                        'trpIds' : [count],
                        'start_plc': tplTemp["start_plc"],
                        'end_plc': tplTemp["end_plc"],
                        'geom': LineString(coords),
                    }
            else:
                generated_trips_count[ide]['count'] = generated_trips_count[ide]['count']+ 1
                generated_trips_count[ide]['trpIds'].append(count)
            count = count + 1
            coordsCombined = []
            tplTemp = {}

            
    trps = trps.append(generated_trips)
    trps = gpd.GeoDataFrame(trps, geometry='geom')
    
    trpsCount = trpsCount.append(list(generated_trips_count.values()))
    trpsCount = gpd.GeoDataFrame(trpsCount, geometry='geom')
    
    return tpls, trps, trpsCount


def clusterTrips(trps, trpsCount, minDistTh, factorTh, dataName, saveDendogramms = False):
    """
    Takes the trips from the previous steps and clusters and aggregates them. So in the end there are just a few trips per place pair   

    Parameters
    ----------
    trps: gdf - Trips, all trahectories between places
    trpsCount: gdf - Only one trip per place pair, and geometry is a straight line
    minDistTh, factorTh: float - two thresholds needed for the clustering
    dataName: str - ID of participant
    saveDendogramms: boolean - Save all dendrograms to a folder

    Returns
    -------
    trps: gdf - Trips, all trahectories between places, but added a column for the cluster ID
    trpsAgr: gdf - Aggregated Trips 

    """
    trps['length'] = trps['geom'].length
    trps['cluster'] = None
    
    trpsAgr = pd.DataFrame(columns=['weight', 'start_plc', 'end_plc', 'geom'])
    generated_trips_aggr = []

    # Go through each place pair, that has connecting trips
    for i in trpsCount.index:
        # Find the places which it connects
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
        
        # Add all trajectories into another format (array of coordinates)
        trpsTemp = []
        for j in trpsCount.loc[i,'trpIds']:
            if trps.loc[j,'start_plc'] == endPlace:
                temp = [a for a in reversed(trps.loc[j,'geom'].coords[:])]
                trpsTemp.append(temp)
            else:
                trpsTemp.append(trps.loc[j,'geom'].coords[:])

        # Make the distance matrix using DTW
        distMatrix = hlp.makeDistMatrix(trpsTemp)
        
        # Do the hierarchical clustering
        linkMatrix = linkage(distMatrix, method='complete')

        # Find the tree of the clustering result
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
        
        # Remove outliers
        for idx in sorted(outlierIdx, reverse=True):
            del trpsTemp[idx]
        
        print(str(len(outlierIdx)) + " outliers were detected and removed")
        
        # Do the clustering again, now without outliers
        distMatrix = hlp.makeDistMatrix(trpsTemp)   
        linkMatrix = linkage(distMatrix, method='complete')
        
        # Find the threshold on how to cut the tree
        th = max(minDistTh, max(linkMatrix[:,2])/factorTh)
        clusteringResult = fcluster(linkMatrix,th, 'distance')

        # Maybe save the images of the trees
        if saveDendogramms:
            if not os.path.exists('../data/results/clustering/'):
                os.mkdir('../data/results/clustering/')
            if not os.path.exists('../data/results/clustering/' + dataName + '/'):
                os.mkdir('../data/results/clustering/' + dataName + '/')
            fig = plt.figure(figsize=(25, 10))
            dn = dendrogram(linkMatrix, leaf_font_size=12.)
            #plt.show()
            fig.savefig('../data/results/clustering/' + dataName + '/' + str(startPlace) + '_' + str(endPlace) + '_' +  str(max(clusteringResult)) + '.png')
        

        # Aggregate the trips per cluster
        n = linkMatrix.shape[0] + 1
        numOfClusters = max(clusteringResult)
        clusters = defaultdict(dict)
        # First add all original trajectories into one dict
        for idx, geom in zip(range(n), trpsTemp):
            clusters[idx]['geom'] = geom
            clusters[idx]['weight'] = 1
            
        # Then go through them and combine them based on the info from the clustering step
        # But only upto where the tree is cut (n-numOfClusters)
        for i in range(n-numOfClusters):
            cluster1 = linkMatrix[i,0]
            cluster2 = linkMatrix[i,1]
            # Combine with weighted average
            newGeom = hlp.combineTrajectory(clusters[cluster1],clusters[cluster2])
            clusters[n + i] = {}
            # Add new geometry
            clusters[n + i]['geom'] = newGeom
            clusters[n + i]['weight'] = clusters[cluster1]['weight'] + clusters[cluster2]['weight']
            # Remove original trips
            clusters.pop(cluster1)
            clusters.pop(cluster2)
        
        # Then in the end add the remaining aggregated trips (often just 1-3) to the gdf
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