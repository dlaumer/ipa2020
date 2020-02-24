import json
import pandas as pd
from pandas.io.json import json_normalize  
import datetime
import numpy as np
import matplotlib.pyplot as plt; plt.rcdefaults()
import matplotlib.pyplot as plt

dataPath = '../Takeout/Location History/Location History.json'
a = 10

chj = 64
dl = 664

ddd = 11

with open(dataPath) as f:
    data = json.load(f)
f.close()
df = json_normalize(data, 'locations')
df['datetime'] = pd.to_datetime(df['timestampMs'],  unit='ms')
df = df.set_index('datetime')
df.drop(['timestampMs'], axis=1, inplace=True)

ax = df.plot.hist(bins=10)

# This is a test blablabla
