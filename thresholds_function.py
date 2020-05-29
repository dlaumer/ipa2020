# -*- coding: utf-8 -*-

""" Thresholds Functions
    This file helps to calculate useful statistics to further choose thresholds
    
    Created on Fri May 15 12:47:14 2020
    Authors:    Daniel Laumer (laumerd@ethz.ch)
                Haojun Cai (caihao@ethz.ch)
"""

import numpy as np
import pandas as pd
from trackintel.geogr.distances import haversine_dist

# Local files
import help_functions as hlp

def stydiffstat(dataNameList, SELECT_RANGE, dateStart, dateEnd):
    """
    Return the place name of input places   

    Parameters
    ----------
    dataNameList : list - list of strings of all participant id with shared data
    SELECT_RANGE: var - flag to define if select certain period
    dateStart: str - the start date of the period if selecting certain period
    dateEnd: str - the end date of the period if selecting certain period
        
    Returns
    -------
    staythredstat: useful statistics to semi-automatically choose thresholds

    """ 
    ddiff_max = []
    ddiff_min = []
    ddiff_mean = []
    ddiff_median = []
    ddiff_quar = []
    
    tdiff_max = []
    tdiff_min = []
    tdiff_mean = []
    tdiff_median = []
    tdiff_quar = []
    
    for dataName in dataNameList:
        dataPathLocs,dataPathTrips = hlp.getDataPaths(dataName)
        
        if SELECT_RANGE:    
            dataPathLocs,dataPathTrips = hlp.selectRange(dataPathLocs, dataPathTrips, dateStart, dateEnd)
        
        locs, locsgdf = hlp.parseLocs(dataPathLocs)
        
        locs['d_diff'] = np.append(haversine_dist(locs.longitudeE7[1:], locs.latitudeE7[1:], locs.longitudeE7[:-1], locs.latitudeE7[:-1]),0)
        accuracy_threshold = np.quantile(locs['d_diff'], .95)
        
        locs['t_diff'] = np.append((locs.index[1:]-locs.index[:-1]).total_seconds(),0)
          
        maxi = max(locs['d_diff'])
        ddiff_max.append(maxi)  
        mini = min(locs['d_diff'])
        ddiff_min.append(mini)
        meani = np.mean(locs['d_diff'])
        ddiff_mean.append(meani)
        mediani = np.median(locs['d_diff'])
        ddiff_median.append(mediani)
        quari = np.quantile(locs['d_diff'], .25)
        ddiff_quar.append(quari)
      
        maxi = max(locs['t_diff'])
        tdiff_max.append(maxi)  
        mini = min(locs['t_diff'])
        tdiff_min.append(mini)
        meani = np.mean(locs['t_diff'])
        tdiff_mean.append(meani)
        mediani = np.median(locs['t_diff'])
        tdiff_median.append(mediani)
        quari = np.quantile(locs['t_diff'], .25)
        tdiff_quar.append(quari)
        
    ddiff_max = np.array(ddiff_max)
    ddiff_max = np.transpose(ddiff_max)
    ddiff_min = np.array(ddiff_min)
    ddiff_min = np.transpose(ddiff_min)
    ddiff_mean = np.array(ddiff_mean)
    ddiff_mean = np.transpose(ddiff_mean)
    ddiff_median = np.array(ddiff_median)
    ddiff_median = np.transpose(ddiff_median)
    ddiff_quar = np.array(ddiff_quar)
    ddiff_quar = np.transpose(ddiff_quar)
    
    tdiff_max = np.array(tdiff_max)
    tdiff_max = np.transpose(tdiff_max)
    tdiff_min = np.array(tdiff_min)
    tdiff_min = np.transpose(tdiff_min)
    tdiff_mean = np.array(tdiff_mean)
    tdiff_mean = np.transpose(tdiff_mean)
    tdiff_median = np.array(tdiff_median)
    tdiff_median = np.transpose(tdiff_median)
    tdiff_quar = np.array(tdiff_quar)
    tdiff_quar = np.transpose(tdiff_quar)
    
    thredstat = {'dataName': np.array(dataNameList),
                'dist_max': ddiff_max,
                'dist_min': ddiff_min,
                'dist_range': ddiff_max-ddiff_min,
                'dist_mean': ddiff_mean,
                'dist_median': ddiff_median,
                'dist_quarter': ddiff_quar,
                'time_max': tdiff_max,
                'time_min': tdiff_min,
                'time_range': tdiff_max-tdiff_min,
                'time_mean': tdiff_mean,
                'time_median': tdiff_median,
                'time_quarter': tdiff_quar}
            
    staythredstat = pd.DataFrame(thredstat)

    return staythredstat