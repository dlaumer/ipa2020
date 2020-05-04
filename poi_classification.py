# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 14:33:23 2020

Authors:    Daniel Laumer (laumerd@ethz.ch)
            Haojun Cai (caihao@ethz.ch)
            
Reference: https://statslab.eighty20.co.za/posts/finding_geographical_points_of_interest_using_python/
"""
#%% IMPORT PACKAGES AND READ SHP DATA
import geopandas
import help_functions as hlp
from geopy.geocoders import Nominatim # Nominatim geocoder for OpenStreetMap data
# from OSMPythonTools.nominatim import Nominatim

dataName = '1'
plcs = geopandas.read_file('E:/1_IPA/3_project/data/shp/'+dataName+'/Places.shp')

#%% REVERSE GEO-CODING
plcs['location'] = ""
geolocator = Nominatim(user_agent="ipalocationdiary1")

for i in range(0,len(plcs)):
    lon = plcs.iloc[i].geometry.y
    lat = plcs.iloc[i].geometry.x
    plcs['location'].iloc[i] = geolocator.reverse((lon,lat))

#%% POI CLASSIFICATION
import overpy
api = overpy.Overpass()

plcs['tag'] = ""

for i in range(0,len(plcs)):
    print(i)
    
    lon = plcs.iloc[i].geometry.x
    lat = plcs.iloc[i].geometry.y
    
    # for i = 1: 130 m
    # lat1 = 47.377
    # lon1 = 8.547
    # lat2 = 47.378
    # lon2 = 8.548
    # hlp.haversine_built(lat1,lon1,lat2,lon2)

    # Select around 100m to search for nearby nodes
    roundlon = round(lon,3)
    if roundlon>lon:
        nodelon2 = roundlon
        nodelon1 = round(roundlon-0.001,3)
    else:
        nodelon1 = roundlon
        nodelon2 = round(roundlon+0.001,3)

    roundlat = round(lat,3)
    if roundlat>lat:
        nodelat2 = roundlat
        nodelat1 = round(roundlat-0.001,3)
    else:
        nodelat1 = roundlat
        nodelat2 = round(roundlat+0.001,3)
    
    string = ('node('+str(nodelat1)+','+str(nodelon1)+','+str(nodelat2)+','+str(nodelon2)+');out;')
    result = api.query(string)
    nodes = result.nodes
    
    k = 0
    tagidx = []
    # Print tags
    print("number of nodes:",len(nodes))
    for j in range(0,len(nodes)):
        tag = nodes[j].tags;
        print(j,"Tag",tag)
        if (len(tag)!=0): 
            k=k+1; # count how many tags are returned
            tagidx.append(j)
    
    if (k!=0):
        # Return the tag with smallest distance between node and the queried point
        dist = []
        for j in tagidx:
            disti = hlp.haversine_built(lon,lat,nodes[j].lon,nodes[j].lat)
            dist.append(disti)
        
        mindistidx = tagidx[dist.index(min(dist))]
        tag = nodes[mindistidx].tags
        # print(min(dist))
        plcs["tag"].iloc[i] = list(tag.keys())[0] 
        
        # coords += [(float(node.lon), float(node.lat)) 
        #            for node in r.nodes]
            
        # print(sorted(set(dist))[1])
        # dist.index(sorted(set(dist))[1])
        # tag = nodes[4].tags

