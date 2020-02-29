#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 10:09:23 2020

@author: dlaumer
"""
import pandas as pd
import numpy as np
import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
pio.renderers.default = "browser"


# Local files
import help_functions as hlp
#import noiserm_functions as nrm

dataPathLocs = '../Takeout_Haojun_Feb/Takeout/Location History/Location History.json'
#dataPathLocs = '../Takeout_Lauro_Mar/Standortverlauf/Standortverlauf.json'
locs = hlp.parseLocs(dataPathLocs)

dataPathTrips = '../Takeout_Haojun_Feb/Takeout/Location History/Semantic Location History/'
#dataPathTrips = '../Takeout_Haojun_Feb/Standortverlauf/Semantic Location History/'
trips, tripdf = hlp.parseTrips(dataPathTrips)

locs['t_diff'] = locs.index.to_series().diff().dt.seconds

lat1 = locs['latitudeE7'].iloc[:-1]
lon1 = locs['longitudeE7'].iloc[:-1]
lat2 = locs['latitudeE7'].iloc[1:]
lon2 = locs['longitudeE7'].iloc[1:]
haver_vec = np.vectorize(hlp.haversine, otypes=[np.int16])
locs['d_diff'] = 0
locs['d_diff'].iloc[1:] = (haver_vec(lat1,lon1,lat2,lon2))
locs['velocity_calc'] = locs['d_diff']/locs['t_diff']

labels, values = hlp.pieChartInfoPlus(trips)

hlp.checkTrips(trips)

idx = pd.date_range(locs.index[0].date(), locs.index[-1].date())
perDay = (locs.groupby(locs.index.date).count()['timestampMs'])
perDay = perDay.reindex(idx, fill_value=0)

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
    #go.Histogram(x=locs['d_diff'].tolist()),
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