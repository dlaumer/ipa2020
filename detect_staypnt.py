# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 11:44:35 2020

Authors:    Haojun Cai (caihao@ethz.ch)
            Daniel Laumer (laumerd@ethz.ch)
"""

#%% IMPORT PACKAGES
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
from haversine import haversine
from sklearn.cluster import KMeans, DBSCAN
import seaborn as sns; sns.set()
import csv


# Local files
import help_functions as hlp

# Read data
dataName = 'Daniel'

#%% IMPORT DATA

if dataName == 'Daniel':
    dataPathLocs = '../Takeout_Daniel_Feb/Location History/Location History.json'
    dataPathTrips = '../Takeout_Daniel_Feb/Location History/Semantic Location History/'
elif dataName == 'Haojun':
    dataPathLocs = '../Takeout_Haojun_Feb/Location History/Location History.json'
    dataPathTrips = '../Takeout_Haojun_Feb/Location History/Semantic Location History/'
elif dataName == 'Lauro':
    dataPathLocs = '../Takeout_Lauro_Mar/Standortverlauf/Standortverlauf.json'
    dataPathTrips = '../Takeout_Lauro_Mar/Standortverlauf/Semantic Location History/'

locsdf, locsgdf = hlp.parseLocs(dataPathLocs)
trips, tripdf, tripgdf = hlp.parseTrips(dataPathTrips)

#%% TIME AND DISTANCE DIFF
# Calculate time and distance difference
locsdf['t_diff'] = 0
locsdf['t_diff'] = locsdf.index.to_series().diff().dt.seconds.shift(-1)

# Convert decimal degrees to radians 
lat1 = locsdf['latitudeE7'].iloc[:-1]
lon1 = locsdf['longitudeE7'].iloc[:-1]
lat2 = locsdf['latitudeE7'].iloc[1:]
lon2 = locsdf['longitudeE7'].iloc[1:]

# haver_vec = np.vectorize(hlp.haversine_built, otypes=[np.int16])
# locsdf['d_diff'] = 0
# locsdf['d_diff'].iloc[:-1] = (haver_vec(lat1,lon1,lat2,lon2))

locsdf['d_diff'] = 0
for i in range(0,len(locsdf)-1):
    lat1 = locsdf['latitudeE7'].iloc[i]
    lon1 = locsdf['longitudeE7'].iloc[i]
    lat2 = locsdf['latitudeE7'].iloc[i+1]
    lon2 = locsdf['longitudeE7'].iloc[i+1]
    
    locsdf['d_diff'].iloc[i] = haversine((lat1,lon1), (lat2,lon2))*1000

# drop last row
# locsdf.drop(locsdf.tail(1).index,inplace=True) 

# FOR VISUALIZATION
# hist and set t_diff and d_diff thresholds
# fig1 = px.histogram(locsdf, x="d_diff")
# fig1.show()

# fig2 = px.histogram(locsdf, x="t_diff")
# fig2.show()

# stat = locsdf.describe()

# filter_tdiff = locsdf.loc[locsdf['t_diff']>30]
# stayPnt = filter_tdiff.loc[filter_tdiff['d_diff']<30]

#%% STAY POINT DETECTION

# fliter out inaccurate data
locsdf = locsdf[locsdf['accuracy']<locsdf['d_diff']]

# find the stay point
v0 = locsdf[locsdf['velocity']==0] 
vnan = locsdf[locsdf['velocity'].isnull()]
staypoint = v0.append(vnan)
staypoint = staypoint[staypoint['accuracy']<50]

stat_staypnt = staypoint.describe()

# reformat the dataframe
staypoint = staypoint.drop(columns=['verticalAccuracy','datetimeUTC','date','heading'])
staypoint = staypoint.rename(columns={'timestampMs': 'started_at_ms'})
staypoint['finished_at_ms'] = pd.to_numeric(staypoint['started_at_ms'],errors='coerce') + staypoint['t_diff']*1000
staypoint['finished_at_ms'] = staypoint['finished_at_ms'].astype(str)  
staypoint = staypoint[['geometry','latitudeE7','longitudeE7','accuracy','altitude','started_at_ms','finished_at_ms','t_diff','d_diff','velocity']]    

# calculate velocity
# locsdf['vel'] = 0
# locsdf['vel'].iloc[1:-2] = (locsdf['d_diff'].iloc[:-3]+locsdf['d_diff'].iloc[1:-2])/(locsdf['t_diff'].iloc[:-3]+locsdf['t_diff'].iloc[1:-2])
# locsdf['vel_diff'] = locsdf['velocity'] - locsdf['vel']

#%% CLUSTERING1 - KMEANS - find the clusters

# calculate the wcss
staypoint_cluster = staypoint[['latitudeE7','longitudeE7']].values                            

k_clusters = range(1,11)
wcss = []

for i in k_clusters:
    kmeans = KMeans(n_clusters=i, init='k-means++', max_iter=300, n_init=10, random_state=0)
    kmeans.fit(staypoint_cluster)
    wcss.append(kmeans.inertia_)

# plot the curve
plt.plot(range(1, 11), wcss)
plt.title('Elbow Method')
plt.xlabel('Number of clusters')
plt.ylabel('WCSS')
plt.show()

#%% CLUSTERING1 - KMEANS - do clustering

# choose the cluters' number, do the clutering
kmeans = KMeans(n_clusters=4, init='k-means++', max_iter=300, n_init=10, random_state=0)
staypoint['cluster_label'] = kmeans.fit_predict(staypoint_cluster)

plt.scatter(staypoint_cluster[:,0],staypoint_cluster[:,1])
plt.scatter(kmeans.cluster_centers_[:, 0], kmeans.cluster_centers_[:, 1], s=300, c='red')
plt.show()

#%% CLUSTERING2 - DBSCAN - find the clusters

# find the optimal cluster
staypoint_cluster = staypoint[['latitudeE7','longitudeE7']].values                            

k_clusters = range(1,11)
wcss = []

for i in k_clusters:
    kmeans = KMeans(n_clusters=i, init='k-means++', max_iter=300, n_init=10, random_state=0)
    kmeans.fit(staypoint_cluster)
    wcss.append(kmeans.inertia_)
    
plt.plot(range(1, 11), wcss)
plt.title('Elbow Method')
plt.xlabel('Number of clusters')
plt.ylabel('WCSS')
plt.show()

# choose the cluters' number, do the clutering
kmeans = KMeans(n_clusters=2, init='k-means++', max_iter=300, n_init=10, random_state=0)
staypoint['cluster_label'] = kmeans.fit_predict(staypoint_cluster)

plt.scatter(staypoint_cluster[:,0],staypoint_cluster[:,1])
plt.scatter(kmeans.cluster_centers_[:, 0], kmeans.cluster_centers_[:, 1], s=300, c='red')
plt.show()

