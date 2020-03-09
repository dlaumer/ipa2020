#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 10:09:23 2020

Authors:    Daniel Laumer (laumerd@ethz.ch)
            Haojun Cai (caihao@ethz.ch)
"""
import pandas as pd
import numpy as np
import math

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
pio.renderers.default = "browser"

# Local files
import help_functions as hlp
#import noiserm_functions as nrm

dataName = 'Haojun'
SAVE_SHP =          False
CHECK_VELO =        False
FIND_STAY_POINTS =  False
CHECK_NB_POINTS =   False
CHECK_ACCURACY =    False
PLOT =              False

#%% IMPORT DATA %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

if dataName == 'Daniel':
    dataPathLocs = '../Takeout_Daniel_Feb/Location History/Location History.json'
    dataPathTrips = '../Takeout_Daniel_Feb/Location History/Semantic Location History/'
elif dataName == 'Haojun':
    dataPathLocs = '../Takeout_Haojun_Feb/Location History/Location History.json'
    dataPathTrips = '../Takeout_Haojun_Feb/Location History/Semantic Location History/'
elif dataName == 'Lauro':
    dataPathLocs = '../Takeout_Lauro_Mar/Standortverlauf/Standortverlauf.json'
    dataPathTrips = '../Takeout_Lauro_Mar/Standortverlauf/Semantic Location History/'

locs = hlp.parseLocs(dataPathLocs)
trips, tripdf, tripsgdf = hlp.parseTrips(dataPathTrips)

#%% EXPORT SHP %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if SAVE_SHP:
    hlp.loc2shp(locs, dataName)
    hlp.trip2shp(tripsgdf, dataName)

#%% ANALYSIS  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Velovity
if CHECK_VELO:
    locs = hlp.calculateVelocity(locs)

if FIND_STAY_POINTS:
    th_dist = 300
    th_time = 30*60*1000
    stayPoints = hlp.findStayPoints(locs, th_dist, th_time)

#Accuracy
if CHECK_ACCURACY:
    for i in [30,40,50,60,70]:
        print('Lower then '+str(i)+'m: '+str(round(100*len(locs[locs['accuracy'].lt(i)])/len(locs),2)))

# Number of points per day
if CHECK_NB_POINTS:
    idx = pd.date_range(locs.index[0].date(), locs.index[-1].date())
    perDay = (locs.groupby(locs.index.date).count()['timestampMs'])
    perDay = perDay.reindex(idx, fill_value=0)

#hlp.checkTrips(trips)

#%% PLOT %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
if PLOT:
    labels, values = hlp.pieChartInfoPlus(trips)

    fig = make_subplots(
    rows=2, cols=2,
    column_widths=[0.6, 0.4],
    row_heights=[0.4, 0.6],
    specs=[[{"type": "Bar", "colspan": 2}, None],
           [ {"type": "scattergeo"}    , {"type": "Pie"}]])

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
        
    fig.add_trace(
        go.Scattergeo(
            lon = locs['longitudeE7'],
            lat = locs['latitudeE7'],
            text = locs['datetimeUTC'],
            mode = 'markers',
            name="Recorded Points"
            ),
        row=2, col=1
        )
    
    fig.update_geos(
            showland = True,
            landcolor = "rgb(212, 212, 212)",
            subunitcolor = "rgb(255, 255, 255)",
            countrycolor = "rgb(255, 255, 255)",
            showlakes = True,
            lakecolor = "rgb(255, 255, 255)",
            showsubunits = True,
            showcountries = True,         
            )
    fig.show()
    
    fig2 = px.histogram(locs, x="accuracy")
    fig2.show()