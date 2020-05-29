# -*- coding: utf-8 -*-

""" POI Classificatioin Functions
    This file helps to classify POIs by attaching different tag information
    
    Created on Thu Apr 23 14:33:23 2020
    Authors:    Daniel Laumer (laumerd@ethz.ch)
                Haojun Cai (caihao@ethz.ch)
    
    Reference: https://statslab.eighty20.co.za/posts/finding_geographical_points_of_interest_using_python/
"""   
    
import geopandas
import help_functions as hlp
#import overpy
import pandas as pd
from geopy.geocoders import Nominatim

def reverseGeoCoding(plcs):
    """
    Return the place name of input places   

    Parameters
    ----------
    plcs : df - df for the different clustered places, including latitude and longitude

    Returns
    -------
    plcs: with one more column for the place name

    """    
    plcs['location'] = ""
    geolocator = Nominatim(user_agent="ipalocationdiary1")
    
    for i in range(0,len(plcs)):
        lon = plcs.iloc[i].center.x
        lat = plcs.iloc[i].center.y
        plcs['location'].iloc[i] = geolocator.reverse((lat,lon))

    return plcs


def poiClassify(plcs):
    """
    Return the place tag of input places by calling Overpass API  

    Parameters
    ----------
    plcs : df - df for the different clustered places, including latitude and longitude

    Returns
    -------
    plcs: with one more column for the place tag

    """          
    api = overpy.Overpass()
    
    plcs['tag_api'] = ""
    
    for i in range(0,len(plcs)):
        lon = plcs.iloc[i].center.x
        lat = plcs.iloc[i].center.y
            
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
        
        # Call the API to get all nodes within the above set bounding box
        string = ('node('+str(nodelat1)+','+str(nodelon1)+','+str(nodelat2)+','+str(nodelon2)+');out;')
        result = api.query(string)
        nodes = result.nodes
        
        nodeNum = []
        nodeNum.append(len(nodes))
        tagNum = []
        tagidx = []
        k = 0

        for j in range(0,len(nodes)):
            # j = 1
            tag = nodes[j].tags;
            if (len(tag)!=0): 
                k=k+1; # count how many tags are returned
                tagidx.append(j)
        tagNum.append(k)
        
        # Return the tag with smallest distance between node and the queried point
        if (k!=0):
            dist = []
            for j in tagidx:
                disti = hlp.haversine_built(lon,lat,nodes[j].lon,nodes[j].lat)
                dist.append(disti)
            
            mindistidx = tagidx[dist.index(min(dist))]
            tag = nodes[mindistidx].tags
            plcs["tag_api"].iloc[i] = list(tag.keys())[0] 

    return plcs
 

def poiClassify2(plcs):
    """
    Return the place tag of input places by matching tags in Swizterland provided by OpenStreeMap

    Parameters
    ----------
    plcs : df - df for the different clustered places, including latitude and longitude

    Returns
    -------
    plcs: with one more column for the place tag

    """ 
    pois = pd.read_csv("E:/1_IPA/3_project/data/poiZurich/poiZurich.csv")
    poisOut = pd.read_csv("E:/1_IPA/3_project/data/poiOutZurich/poiOutZurich.csv")
    
    plcs['tag'] = ""
    mindist = []
    
    for i in range(0,len(plcs)):
        lon = plcs.iloc[i].center.x
        lat = plcs.iloc[i].center.y
    
        dist = []
    
        # First match with the POIs inside Zurich since most of participants live in Zurich
        for j in range(0,len(pois)):
            disti = hlp.haversine_built(lon,lat,pois.iloc[j].lon,pois.iloc[j].lat)
            dist.append(disti)
            
        # If the closest tag is larger than 100 meters, then match with POIs outside Zurich
        if min(dist) > 100:
            distOut = []
        
            for k in range(0,len(poisOut)):
                disti = hlp.haversine_built(lon,lat,poisOut.iloc[k].lon,poisOut.iloc[k].lat)
                distOut.append(disti)
        
            if min(distOut) < min(dist):
                mindist.append(min(distOut)) 
                mindistidx = distOut.index(min(distOut))
                tag = poisOut.iloc[mindistidx].fclass
            else:
                mindist.append(min(dist)) 
                mindistidx = dist.index(min(dist))
                tag = pois.iloc[mindistidx].fclass
        
        else:
            mindist.append(min(dist)) 
            mindistidx = dist.index(min(dist))
            tag = pois.iloc[mindistidx].fclass
        
        plcs["tag"].iloc[i] = tag 
    
    return plcs




