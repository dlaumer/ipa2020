# Interdisciplinary Project Work 2020

Title: Location Diary
Authors: Haojun Cai and Daniel Laumer

## Introduction
This research project came up with a product idea: Location Diary, to present individual traveling behavior patterns through a personalized interactive dashboard based on collected Google Maps Timeline data. A complete GPS data processing and analysis pipeline was developed from detecting stay points, clustering places, and adding semantic information to clustering and aggregating trajectories. 

If you are interested, more details can be found in the [Poster](https://ethz.ch/content/dam/ethz/special-interest/baug/ikg/geoinformation-engineering-dam/Lehre/Studienarbeiten/IPA/20_FS_IPA_Laumer_Cai.pdf).

## Getting Started

Analysis:
In order to use the analysis part of our code you need to run the file dashboard.py
It requires the python 3 (we used 3.6)

Visualisation:
In order to see the visualisation, you need to open a local host in the outmost folder and open the code/visualization/index.html.

### Prerequisites

What things you need to install the software and how to install them

The following python packages are required:
```
* pandas
* plotly
* shapefile
* numpy
* scipy
* pandas
* geopandas
* fastdtw
* fiona
* geopy
* gpxpy
* haversine
* lxml
* matplotlib
* overpy
* pyproj
* requests
* scikit-learn
* shapely
* trackintel
```

## Built With
* python
* HTML
* JavaScript
* CSS
* D3
* Highcharts


## Authors

* **Haojun Cai*** *Initial work** caihao@student.ethz.ch

* **Daniel Laumer*** *Initial work** laumerd@student.ethz.ch

## License

This project is licensed under the MIT License* see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Thanks to trackintel for the code on staypoint detection and clustering
* Thanks for Hitouch for their API on schematic maps

