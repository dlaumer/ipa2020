#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Statstics function
    This script collects statistics about the data of each participant
    
    Created on Thu Mar 28 2020
    Authors:    Daniel Laumer (laumerd@ethz.ch)
                Haojun Cai (caihao@ethz.ch)
    
"""
import pandas as pd
import numpy as np
import math





# Local files
import help_functions as hlp
#import noiserm_functions as nrm

dataNames = ['1','2','4','10','11','15','17','20','21','28']
EXPORT_GPX =        False
SAVE_SHP =          False
CHECK_VELO =        False
FIND_STAY_POINTS =  False
CHECK_NB_POINTS =   True
CHECK_ACCURACY =    True
PLOT =              False

#%% IMPORT DATA %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

dfAccuracy = pd.DataFrame(columns =['Id','30','40','50','60','70', 'NumDays', 'AvgNumPoints'])

for dataName in dataNames:
    print('Processing '+ dataName)
    dfAccuracy = dfAccuracy.append(pd.Series(name=dataName))
    dfAccuracy['Id'][dataName] = dataName
    
    dataPathLocs,dataPathTrips = hlp.getDataPaths(dataName)
    
    locs, locsgdf = hlp.parseLocs(dataPathLocs)
    #trips, tripdf, tripsgdf = hlp.parseTrips(dataPathTrips)
    
    #Accuracy
    if CHECK_ACCURACY:
        for i in [30,40,50,60,70]:
            dfAccuracy[str(i)][dataName] = round(100*len(locs[locs['accuracy'].lt(i)])/len(locs),2)
    
    # Number of points per day
    if CHECK_NB_POINTS:
        idx = pd.date_range(locs.index[0].date(), locs.index[-1].date())
        perDay = (locs.groupby(locs.index.date).count()['timestampMs'])
        #perDay = perDay.reindex(idx, fill_value=0)
        dfAccuracy['NumDays'][dataName] = len(perDay)
        dfAccuracy['AvgNumPoints'][dataName] = perDay.mean()
    
    #hlp.checkTrips(trips)

dfQuestionnaire = pd.read_csv("../data/Pre-Questionnaire - Location Diary.csv")
dfPhoneModel = dfQuestionnaire[["Enter your participant ID:","What is your mobile phone's brand used to collect data?"]]
dfAccuracy['Id'] = dfAccuracy['Id'].astype(int)
dfAccuracy = pd.merge(dfAccuracy, dfPhoneModel, left_on='Id',right_on="Enter your participant ID:")
#dfAccuracy = dfAccuracy.drop("Enter your participant ID:")

dfAccuracy.to_csv('../data/statistics.csv', index=False, sep=';')