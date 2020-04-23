# -*- coding: utf-8 -*-
"""
Created on Mon Apr  6 16:41:35 2020

Authors:    Daniel Laumer (laumerd@ethz.ch)
            Haojun Cai (caihao@ethz.ch)
"""
import pandas as pd
import numpy as np
import math
import json
import os

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
pio.renderers.default = "browser"
import trackintel as ti
from trackintel.geogr.distances import meters_to_decimal_degrees


# Local files
import help_functions as hlp
import trackintel_modified as tim

# Read data
dataName = '2'

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
    
    plcs.to_csv('../data/csv/'+dataName+'/Places.csv')
    
    plcs_shp = plcs.copy()
    plcs_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places.shp')
    #plcs_shp.geometry = plcs_shp['extent']
    #plcs_shp.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/Places_extent.shp')

#%% FIND HOME
import datetime

pfs['tracked_at_hour'] = 0
for i in range(0,len(pfs)): pfs['tracked_at_hour'].iloc[i] = pfs['tracked_at'].iloc[i].hour

homepfs = pfs[(pfs['tracked_at_hour']<=7) | (pfs['tracked_at_hour']>=22)]
#homepfs = pfs[(pfs['tracked_at_hour']<=6)]
homestps = tim.extract_staypoints_ipa(homepfs, method='sliding',dist_threshold=100, time_threshold=15*60)
homeplcs = homestps.as_staypoints.extract_places(method='dbscan',epsilon=meters_to_decimal_degrees(80, 47.5), num_samples=6)
homeplcs.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/HomePlaces.shp')
homeplcs.geometry = plcs['extent']
homeplcs.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/HomePlaces_extent.shp')

#%% HOME ADDRESS STATISTICS
## calcualte stay time for each place for each working day
homestps['started_at_hour'] = 0
for i in range(0,len(homestps)): homestps['started_at_hour'].iloc[i] = homestps['started_at'].iloc[i].hour
homestps['started_at_weekday'] = 0
for i in range(0,len(homestps)): homestps['started_at_weekday'].iloc[i] = homestps['started_at'].iloc[i].weekday() # 0 for Monday, 6 for Sunday

# calculate stay time
homestps['stay_time'] = 0
for i in range(0,len(homestps)):
    homestps['stay_time'].iloc[i] = (homestps['finished_at'].iloc[i]-homestps['started_at'].iloc[i]).total_seconds()

# summarize stay time by weekday for each clustered place
cols = ['Mon_totalstay','Tues_totalstay','Wed_totalstay','Thur_totalstay','Fri_totalstay']
for col in cols: homeplcs[col] = 0
for i in range(0,len(homeplcs)):
    place_id = i+1
    homestps_placeid = homestps[homestps['place_id']==place_id]
    homestps_placeid_weekday1 = homestps_placeid[homestps_placeid['started_at_weekday']==0]
    homeplcs.loc[homeplcs['place_id']==place_id,'Mon_totalstay']=homestps_placeid_weekday1['stay_time'].sum()
    homestps_placeid_weekday2 = homestps_placeid[homestps_placeid['started_at_weekday']==1]
    homeplcs.loc[homeplcs['place_id']==place_id,'Tues_totalstay']=homestps_placeid_weekday2['stay_time'].sum()
    homestps_placeid_weekday3 = homestps_placeid[homestps_placeid['started_at_weekday']==2]
    homeplcs.loc[homeplcs['place_id']==place_id,'Wed_totalstay']=homestps_placeid_weekday3['stay_time'].sum()
    homestps_placeid_weekday4 = homestps_placeid[homestps_placeid['started_at_weekday']==3]
    homeplcs.loc[homeplcs['place_id']==place_id,'Thur_totalstay']=homestps_placeid_weekday4['stay_time'].sum()
    homestps_placeid_weekday5 = homestps_placeid[homestps_placeid['started_at_weekday']==4]
    homeplcs.loc[homeplcs['place_id']==place_id,'Fri_totalstay']=homestps_placeid_weekday5['stay_time'].sum()
    
for col in cols: homeplcs[col] =  homeplcs[col]/60

#%% FIND WORKING ADDRESS
import datetime  
from datetime import datetime
  
pfs['tracked_at_weekday'] = 0
for i in range(0,len(pfs)): pfs['tracked_at_weekday'].iloc[i] = pfs['tracked_at'].iloc[i].weekday() # 0 for Monday, 6 for Sunday

# choose only working days and hours
workpfs = pfs[pfs['tracked_at_weekday']<=4] 
workpfs = workpfs[((workpfs['tracked_at_hour']>=9) & (workpfs['tracked_at_hour']<=12)) | ((workpfs['tracked_at_hour']>=14) & (workpfs['tracked_at_hour']<=17))]

workstps = tim.extract_staypoints_ipa(workpfs, method='sliding',dist_threshold=100, time_threshold=15*60)
workplcs = workstps.as_staypoints.extract_places(method='dbscan',epsilon=meters_to_decimal_degrees(80, 47.5), num_samples=6)
workplcs.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/WorkPlaces.shp')
workplcs.geometry = plcs['extent']
workplcs.drop(columns = ['extent']).to_file('../data/shp/'+dataName +'/WorkPlaces_extent.shp')

#%% WORKING ADDRESS STATISTICS
## calcualte stay time for each place for each working day
workstps['started_at_hour'] = 0
for i in range(0,len(workstps)): workstps['started_at_hour'].iloc[i] = workstps['started_at'].iloc[i].hour
workstps['started_at_weekday'] = 0
for i in range(0,len(workstps)): workstps['started_at_weekday'].iloc[i] = workstps['started_at'].iloc[i].weekday() # 0 for Monday, 6 for Sunday

# calculate stay time
workstps['stay_time'] = 0
for i in range(0,len(workstps)):
    workstps['stay_time'].iloc[i] = (workstps['finished_at'].iloc[i]-workstps['started_at'].iloc[i]).total_seconds()

# summarize stay time by weekday for each clustered place
cols = ['Mon_totalstay','Tues_totalstay','Wed_totalstay','Thur_totalstay','Fri_totalstay']
for col in cols: workplcs[col] = 0
for i in range(0,len(workplcs)):
    place_id = i+1
    workstps_placeid = workstps[workstps['place_id']==place_id]
    workstps_placeid_weekday1 = workstps_placeid[workstps_placeid['started_at_weekday']==0]
    workplcs.loc[workplcs['place_id']==place_id,'Mon_totalstay']=workstps_placeid_weekday1['stay_time'].sum()
    workstps_placeid_weekday2 = workstps_placeid[workstps_placeid['started_at_weekday']==1]
    workplcs.loc[workplcs['place_id']==place_id,'Tues_totalstay']=workstps_placeid_weekday2['stay_time'].sum()
    workstps_placeid_weekday3 = workstps_placeid[workstps_placeid['started_at_weekday']==2]
    workplcs.loc[workplcs['place_id']==place_id,'Wed_totalstay']=workstps_placeid_weekday3['stay_time'].sum()
    workstps_placeid_weekday4 = workstps_placeid[workstps_placeid['started_at_weekday']==3]
    workplcs.loc[workplcs['place_id']==place_id,'Thur_totalstay']=workstps_placeid_weekday4['stay_time'].sum()
    workstps_placeid_weekday5 = workstps_placeid[workstps_placeid['started_at_weekday']==4]
    workplcs.loc[workplcs['place_id']==place_id,'Fri_totalstay']=workstps_placeid_weekday5['stay_time'].sum()
    
for col in cols: workplcs[col] =  workplcs[col]/60
