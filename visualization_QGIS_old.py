###############################################################################
# Created on Wed Jun 21 17:01:42 2017
# Author: Daniel Laumer (laumerd)
# -----------------------------------------------------------------------------
# File which can be run in QGIS, to visualize the results
# Create a new QGIS file, open the console, load this script and run it. 
# Remark: The open layers plugin must be installed
###############################################################################

import os

# Define which participant should be visualized. If the list is empty, all available participants will be visualized
dataNames = ['15']
# Define which layers it should contain. You can only choose from the ones in 'allLayers'. If the list is empty, all available layers are taken.
layers = []
# Folder where the results are stored. They must be a folder per participant and the folder structure must be unchanged 
dataDirRoot = "/Users/dlaumer/Google Drive/2020 FRUEHLINGSSEMESTER/IPA 2020/3-Testing/data/shp/"
# Folder where the styled definitions for each layer are stored
qgisStylesFolder = "/Users/dlaumer/Google Drive/2020 FRUEHLINGSSEMESTER/IPA 2020/3-Testing/visualization/QGIS_Style_Files/"

# All available layers, the names correspond to the names of the shape files
allLayers = [	"Loc", 						
				"Trip",							
				"Staypoints",	 		
				#"Places_extent",
                "Triplegs",
                "Trips",
                #"TripsCount",
                "TripsAggregated",
                "Places"
                ]

# Name of the layers on QGIS
allLayerNames = ["Locations",
				"Semantic Trip Data",
				"Staypoints (trackintel)",
				#"Extent Places (trackintel)",
                "Triplegs (trackintel)",
                "Trips (trackintel)",
                #"Trips Count",
                "Trips Aggregated",
                "Places (trackintel)"]

hiddenLayers = ["Trip"]
layerNames = dict(zip(allLayers, allLayerNames))

if not dataNames:
   for root,dirs,files in os.walk(dataDirRoot):
       dataNames = dirs
       break
   
if not layers:	
	layers = allLayers

root = QgsProject.instance().layerTreeRoot()
	
# Delete all existing layers
oldLayers = QgsMapLayerRegistry.instance().mapLayers()
for oldLayer in iface.legendInterface().layers():
	QgsMapLayerRegistry.instance().removeMapLayer(oldLayer)

# Iterate over all participants
for dataName in dataNames:
    dataDir = dataDirRoot + "/" + dataName + "/"
    
    cityGroup = root.addGroup(dataName)
    
    for layer in layers:
        layerPath = dataDir + layer + ".shp"
        
        qgisLayer = QgsVectorLayer(layerPath,layerNames[layer],"ogr")
        QgsMapLayerRegistry.instance().addMapLayer(qgisLayer,False)
        cityGroup.insertChildNode(0,QgsLayerTreeLayer(qgisLayer))
        
        #qgisLayer = iface.addVectorLayer(layerPath , layerNames[layer], "ogr")
        #if not qgisLayer:
        #    print("Layer" + layer + " failed to load!")
        qgisLayer.loadNamedStyle(qgisStylesFolder + layer + ".qml")
        
        
        # Hide the layer
        if layer in hiddenLayers:
            legend = iface.legendInterface()  # access the legend
            legend.setLayerVisible(qgisLayer, False)  # hide the layer
 
# Load the google maps background (I just copied that from a forum)
mapProvider = 'OpenStreetMap' #also use e.g. 'OpenStreetMap', 'Bing Maps' etc. as given in the Web->OpenLayers plugin menu
openLayersMap = 'OpenStreetMap' #also use e.g. 'Google Streets', 'OpenStreetMap', 'Bing Road' etc. as given in the Web->OpenLayers plugin menu

webMenu = qgis.utils.iface.webMenu() #get object of the Web menu of QGIS

for webMenuItem in webMenu.actions(): #open the Web menu of QGIS and loop through the list of web plugins
    if 'OpenLayers plugin' in webMenuItem.text(): #look for OpenLayers plugin entry in the Web menu
        openLayersMenu = webMenuItem #and open it

        for openLayersMenuItem in openLayersMenu.menu().actions(): #open the OpenLayers plugin menu entry and loop through the list of map providers
            if mapProvider in openLayersMenuItem.text(): #if the desired mapProvider is found
                mapProviderMenu = openLayersMenuItem #open its menu entry

                for map in mapProviderMenu.menu().actions(): #loop through the list of maps for the opened provider
                    if openLayersMap in map.text(): #if the desired map entry is found
                        map.trigger() #click the entry to load the map as a layer
