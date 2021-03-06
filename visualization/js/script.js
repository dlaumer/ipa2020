/*
Location Diary - Interdisciplinary Project Thesis

This file containt all the code for the visualization. 

It is divided into first preparation fo all the elements,
then we load the data and fill it in 
and in the end there are several small help functions

Authors:    Daniel Laumer (laumerd@ethz.ch)
            Haojun Cai (caihao@ethz.ch)

*/

// Data files to import
// Options: 1 - Daniel's statistics, 2 - Haojun's statistics
var path = "./../../data/results/stat/"
var dataName = "1";
var urls = {
  places:
  path + dataName + "/places.csv",

  trips:
  path + dataName + "/tripsAgr.csv",

  tripsOriginal:
  path + dataName + "/trips.csv",

  timeline:
  path + dataName + "/PlcsStayHour.csv",

  semanticInfo:
  path + dataName + "/PlcsInfo.csv",

  homeworkbal:
  path + dataName + "/HomeWorkStay.csv",

  transportation:
  path + dataName + "/TransportationModeCo2Perc.csv",
  
  basicStatistics:
  path + dataName + "/BasicStatistics.csv",
};

// PERPARE MAP  ////////////////////////////////////////////////////////////////////////////////////

mapboxgl.accessToken = 'pk.eyJ1IjoiZGxhdW1lciIsImEiOiJjazlyN240NHowOG40M3FwaTBobmJtY282In0.J1FVlpwTp-p6SIihxJy0nw'

//Setup mapbox-gl map
var map = new mapboxgl.Map({
  container: 'mapboxx', // container id
  style: 'mapbox://styles/dlaumer/ck9viuh1c0ysh1irw0jadcwgc',
  center: [8.507412548555335, 47.40639137110055],
  zoom: 10
})

// Define the different map controls as classes
// First a map control which is a button
var legendControl = map.addControl(new mapboxgl.NavigationControl());
class MyCustomControl {

  constructor(id, textContent) {
    this.id = id;
    this.textContent = textContent
  }
  onAdd(map) {
    this.map = map;
    this.container = document.createElement('button');
    this.container.id = this.id;
    this.container.className = 'mapboxgl-ctrl my-custom-control hover-button';
    this.container.textContent = this.textContent;
    //this.container.innerHTML = document.createElement("IMG")
    this.container.type = "button";
    return this.container;
  }
  onRemove() {
    this.container.parentNode.removeChild(this.container);
    this.map = undefined;
  }
}
// Then a map element which is a text
class MyCustomText {
  constructor(id, textContent) {
    this.id = id;
    this.textContent = textContent
  }
  onAdd(map) {
    this.map = map;
    this.container = document.createElement('text');
    this.container.id = this.id;
    this.container.className = 'mapboxgl-ctrl';
    this.container.textContent = this.textContent;
    //this.container.innerHTML = document.createElement("IMG")
    this.container.type = "text";
    return this.container;
  }
  onRemove() {
    this.container.parentNode.removeChild(this.container);
    this.map = undefined;
  }
}

// Create the different map controls
const myCustomControl = new MyCustomControl("showGeometric", "Aggregated Map");
const myCustomControl5 = new MyCustomControl("showSchematic", "Schematic Map");
const myCustomControl2 = new MyCustomControl("zoomAll", "");
const myCustomControl3 = new MyCustomControl("removeLabelsButton", "");
const myCustomControl4 = new MyCustomControl("showOriginalTrips", "Original Map");
const myCustomText = new MyCustomText("hitouchText", "Schematic Map ©Hitouch AG");

// Add the different map controls
map.addControl(myCustomControl5, 'top-left');
map.addControl(myCustomControl, 'top-left');
map.addControl(myCustomControl2, 'top-right');
map.addControl(myCustomControl3, 'top-right');
map.addControl(myCustomControl4, 'top-left');
map.addControl(myCustomText, 'bottom-right');

// Add functionality and content
var elem = document.createElement("img");
elem.setAttribute("src", "imgs/zoom_out_map-white-48dp.svg");
document.getElementById("zoomAll").appendChild(elem);

var elem = document.createElement("img");
elem.setAttribute("src", "imgs/local_offer-white-36dp.svg");
document.getElementById("removeLabelsButton").appendChild(elem);

d3.select('#showGeometric').classed('selectMap', true)
d3.select('#showSchematic').classed('selectMap', true)
d3.select('#showOriginalTrips').classed('selectMap', true)
d3.select('#showSchematic')
      .style('background-color', "#A8322D")

// Functionality for the three buttons 
document.getElementById("showGeometric").addEventListener('click', event => {
  
  if (mapBlank) {
    d3.selectAll('.selectMap')
      .style('background-color', "#1F407A")
    d3.select('#showGeometric')
      .style('background-color', "#A8322D")

    changeData("geometric")
  }
  else if (geomMap) {
    d3.selectAll('.selectMap')
    .style('background-color', "#1F407A")
    d3.select('#showGeometric')
    .style('background-color', "#A8322D")
    geomMap = false;
    drawTrips(places, trips, geomMap)
  }

  d3.select("#hitouchText")
  .style("visibility", "hidden")
});
document.getElementById("showSchematic").addEventListener('click', event => {
  if (!mapBlank) {

    d3.selectAll('.selectMap')
    .style('background-color', "#1F407A")
    d3.select('#showSchematic')
    .style('background-color', "#A8322D")

    geomMap = false

    changeData("schematic")
  }
  d3.select("#hitouchText")
  .style("visibility", "visible")
});
document.getElementById("showOriginalTrips").addEventListener('click', event => {
  d3.selectAll('.selectMap')
  .style('background-color', "#1F407A")
  d3.select('#showOriginalTrips')
  .style('background-color', "#A8322D")

  if (!geomMap) {

    geomMap = true;
    drawTrips(places, trips, geomMap)
  }

  if (mapBlank) {
    geomMap = true;
    changeData("geometric")
  }
  d3.select("#hitouchText")
  .style("visibility", "hidden")
});
document.getElementById("removeLabelsButton").addEventListener('click', event => { removeLabels() });
document.getElementById("zoomAll").addEventListener('click', event => { zoomToAll() });

// Re-render our visualization whenever the view changes
map.on("viewreset", function () {
  render()
})
map.on("move", function () {
  render()
})

// Move the SVG elements on top of the map
var container = map.getCanvasContainer()
var removed = d3.select("svg#map").remove()
var svg = d3.select(container).append(function () {
  return removed.node();
});


// Define the width and height of the map
var widthMap = d3
  .select('#map-container')
  .node()
  .getBoundingClientRect().width
// Set dimensions
var heightMap = d3
  .select('#map-container')
  .node()
  .getBoundingClientRect().height
var hypotenuse = Math.sqrt(widthMap * widthMap + heightMap * heightMap);

svg
  .style('position', 'relative')
  .attr('width', widthMap)
  .attr('height', heightMap)

var k = 1;
var projection = d3.geoTransform({ point: projectPoint });
var scales = {
  // used to scale places bubbles
  places: d3.scaleSqrt()
    .range([4, 18]),
};

// have these already created for easier drawing
var g = {
  basemap: svg.select("g#basemap"),
  trips: svg.select("g#trips"),
  places: svg.select("g#places"),
  voronoi: svg.select("g#voronoi")
};
var tooltip = d3.select("text#tooltip");

// PRE-ALLOCATE GLOBAL VARIABLES  ////////////////////////////////////////////////////////////////////////////////////
var timelineData;
var places;
var placeId;
var trips;
var tripsAgr;
var semanticInfo;
var homeworkbal;
var HomeWorkData;
var HomeWorkSeries;
var yAxisMax;
var transportationmode;
var transportationData;
var transportationSeries;
var totalCo2;
var bubbles;
var labels;
var pathBaseMap;
var pathTrips;
var links
var geojsons;
var placeIdOfBox;
var maxCount;
var mapBlank = true;
var geomMap = false;
var extents;
var startTime = 0;
var endTime = 23;

var margin
var widthTimeline
var heightTimeline
var svgTimeline
var xScale
var xAxis
var yScale
var yAxis
var marginTime
var widthTime
var heightTime
var svgTime
var xScaleTime
var xAxisTime
var numOfBoxes
var topkPlaces


// LOAD DATA  //////////////////////////////////////////////////////////////////////////////////////////////////////

// Load all the data together
let promises = [
  d3.dsv(';', urls.places, typePlace),
  d3.dsv(';', urls.trips, typeTrip),
  d3.dsv(';', urls.tripsOriginal, typeTripOriginal),
  d3.csv(urls.timeline),
  d3.csv(urls.semanticInfo),
  d3.csv(urls.homeworkbal),
  d3.csv(urls.transportation),
  d3.csv(urls.basicStatistics)
];

Promise.all(promises).then(processData);

// Process place and trip data
function processData(values) {
  // Read the values out
  places = values[0];
  trips = values[1];
  tripsOriginal = values[2]
  timelineData = values[3];
  semanticInfo = values[4][0];
  homeworkbal = values[5];
  transportationmode = values[6];
  basicStatistics = values[7];

  // Write the basic statistics to the dashboard
  setBasicStatistics(basicStatistics);

  // Find extents to 
  extents = getExtentofPlaces(places)
  // Convert places array (pre filter) into map for fast lookup
  // Basically make a dictionary (like in python) with placeId as key
  placeId = new Map(places.map(node => [node.placeId, node]));
  console.log("places: " + places.length);
  console.log(" trips: " + trips.length);

  // Here we define the maximum number of boxes on the panel
  numOfBoxes = places.length + 1;
  if (numOfBoxes >= 10) {
    numOfBoxes = 10;
  }

  // Get the first box and copy it according to the number of places
  var myDiv = document.getElementById("box-1").parentNode;
  for (let i = 2; i < numOfBoxes; i++) {
    var divClone = myDiv.cloneNode(true); // the true is for deep cloning
    divClone.childNodes[1].id = "box-" + i
    divClone.childNodes[3].id = "zoom-" + i
    document.getElementById("places-boxes").appendChild(divClone);
  }

  // PREPARE BAR CHART  ////////////////////////////////////////////////////////////////////////////////////
  margin = { top: 10, right: 30, bottom: 40, left: 60 };
  widthTimeline = d3
    .select('#chart-container')
    .node()
    .getBoundingClientRect().width - margin.left - margin.right;
  // Set dimensions
  heightTimeline = d3
    .select('#chart-container')
    .node()
    .getBoundingClientRect().height - margin.top - margin.bottom;


  svgTimeline = d3.select("#timeline")
    .append("svg")
    .attr("width", widthTimeline + margin.left + margin.right)
    .attr("height", heightTimeline + margin.top + margin.bottom)
    .append("g")
    .attr("transform",
      "translate(" + margin.left + "," + margin.top + ")")

  // Text label for the y axis
  svgTimeline.append("text")
    .attr("font-size", "10px")
    .attr("transform", "rotate(-90)")
    .attr("y", 0 - margin.left / 2)
    .attr("x", 0 - (heightTimeline / 2))
    .style("text-anchor", "middle")
    .text("Staytime [hrs]");

  // Initialize the X axis
  xScale = d3.scaleBand()
    .range([0, widthTimeline])
    .padding(0.2);

  xScale.invert = function (x) {
    var domain = this.domain();
    var range = this.range()
    var scale = d3.scaleQuantize().domain(range).range(domain)
    return scale(x)
  };
  xAxis = svgTimeline.append("g")
    .attr("transform", "translate(0," + heightTimeline + ")")

  // Initialize the Y axis
  yScale = d3.scaleLinear()
    .range([heightTimeline, 0]);
  yAxis = svgTimeline.append("g")
    .attr("class", "myYaxis")


  // PREPARE TIME AXIS ////////////////////////////////////////////////////////////////////////////////////

  // Set the dimensions and margins of the graph
  marginTime = { top: 10, right: 20, bottom: 0, left: 50 };

  widthTime = d3
    .select('#time-container')
    .node()
    .getBoundingClientRect().width - marginTime.left - marginTime.right;
  heightTime = d3
    .select('#time-container')
    .node()
    .getBoundingClientRect().height - marginTime.top - marginTime.bottom;

  svgTime = d3.select("#time")
    .append("svg")
    .attr("width", widthTime + marginTime.left + marginTime.right)
    .attr("height", heightTime + marginTime.top + marginTime.bottom)
    .append("g")
    .attr("transform",
      "translate(" + marginTime.left + "," + marginTime.top + ")")

  // Initialize the X axis
  xScaleTime = d3.scaleBand()
    .range([0, widthTime])
    .padding(0.2);

  xScaleTime.invert = function (x) {
    var domain = this.domain();
    var range = this.range()
    var scale = d3.scaleQuantize().domain(range).range(domain)
    return scale(x)
  };
  xAxisTime = svgTime.append("g")


  // PREPARE MAP  ////////////////////////////////////////////////////////////////////////////////////

  // Calculate incoming and outgoing degree based on trips
  // Trips are given by place placeId code (not index)
  trips.forEach(function (link) {
    link.source = placeId.get(link.origin);
    link.target = placeId.get(link.destination);

    link.source.outgoing += link.count;
    link.target.incoming += link.count;
  });

  // Calculate incoming and outgoing degree based on trips
  // Trips are given by place placeId code (not index)
  tripsOriginal.forEach(function (link) {
    link.source = placeId.get(link.origin);
    link.target = placeId.get(link.destination);

  });

  // Sort places by outgoing degree
  places.sort((a, b) => d3.descending(a.outgoing, b.outgoing));

  // Done filtering places can draw
  drawPlaces(places);
  // Done filtering trips can draw
  geojsons = addWaypoints(trips);
  geojsonOriginal = addWaypointsOriginal(tripsOriginal);
  drawTrips(places, trips, false);

  const capitalize = (s) => {
    if (typeof s !== 'string') return ''
    return s.charAt(0).toUpperCase() + s.slice(1)
  }

  // Prepare variables for diagrams
  HomeWorkData = [];
  HomeWorkSeries = [];
  transportationData = [];
  transportationSeries = [];
  yAxisMax = [];
  totalCo2 = 0;
  var tempabs = [];

  // Fill the diagrams
  fillPlacesBoxes();
  colorPlacesBoxes(startTime, endTime);
  drawTimeline();

  // Add functionality to the boxes
  for (let i = 1; i < numOfBoxes; i++) {
    document.getElementById("box-" + i).addEventListener('click', event => { updateTimeline(placeIdOfBox[i]) });
    document.getElementById("zoom-" + i).addEventListener('click', event => { updateZoom(placeIdOfBox[i]) });
    document.getElementById("box-" + i).parentNode.addEventListener("mouseover", event => { mousoverFunction(placeIdOfBox[i]) });
    document.getElementById("box-" + i).parentNode.addEventListener("mouseout", event => { mouseoutFunction(placeIdOfBox[i]) });
  }

  // PREPARE HOMEWORKBALANCE DATA  ////////////////////////////////////////////////////////////////////////////////////

  // Reformat homeworkbalance data
  // Make monochrome colors
  var barColors = (function () {
    var colors = [],
      base = Highcharts.getOptions().colors[0],
      i;

    for (i = 0; i < homeworkbal.length; i += 1) {
      // Start out with a darkened base color (negative brighten), and end
      // up with a much brighter color
      colors.push(Highcharts.color(base).brighten((i - 2) / 6).get());
    }
    return colors;
  }());
  for (let i = 0; i < homeworkbal.length; i++) {
    var homework = homeworkbal[i];
    var homeworkid = homework['id']
    if (homeworkid == 'home') {
      var homeworkdata = [-homework['Sun'], -homework['Sat'], -homework['Fri'], -homework['Thur'], -homework['Wed'], -homework['Tues'], -homework['Mon']]
      var data = homeworkdata.map(Number);
    }
    else {
      var homeworkdata = [homework['Sun'], homework['Sat'], homework['Fri'], homework['Thur'], homework['Wed'], homework['Tues'], homework['Mon']]
      var data = homeworkdata.map(Number);
    }
    for (let k = 0; k < data.length; k++) {
      var datai = Math.abs(data[k]);
      tempabs.push(datai);
    }
    var homeworkname = capitalize(homeworkid).concat(': ', homework['placeName'])
    var homeworkarray = [homeworkname, data, barColors[i]]
    HomeWorkData.push(homeworkarray);
  }
  yAxisMax = Math.max(...tempabs)
  yAxisMax = Math.ceil(yAxisMax / 10) * 10;
  for (i = 0; i < HomeWorkData.length; i++) {
    HomeWorkSeries.push({
      name: HomeWorkData[i][0],
      data: HomeWorkData[i][1],
      color: HomeWorkData[i][2],
    })
  }
  drawNegativeBar(HomeWorkSeries, yAxisMax);

  // PREPARE TRANSORTION DATA  ////////////////////////////////////////////////////////////////////////////////////

  // Reformat transportation data
  for (let i = 0; i < transportationmode.length; i++) {
    var transportationi = transportationmode[i];
    var mode = transportationi['name']
    var co2Perc = transportationi['co2Perc'] * 100
    var dist = transportationi['dist']
    var co2km = transportationi['co2km']
    var co2Emission = dist*co2km
    var distPerc = transportationi['distPerc']
    // co2Emission = co2Emission.toFixed(2)
    var transarray = [mode, co2Perc, dist, co2km, co2Emission, distPerc]

    totalCo2 = totalCo2 + co2Emission
    transportationData.push(transarray);
  }

  for (i = 0; i < transportationData.length; i++) {
    transportationSeries.push({
      name: transportationData[i][0],
      y: transportationData[i][1],
      distVal: transportationData[i][2],
      co2kmVal: transportationData[i][3],
      co2EmissionVal: transportationData[i][4],
      distPercVal: transportationData[i][5],
    })
  }

  zoomToAll();
}

// FUNCTIONS ////////////////////////////////////////////////////////////////////////////////////

function drawTimeline() {
  // Draws the Bar Chart 

  // X axis
  xScaleTime.domain(timelineData.map(function (d) { return d.group; }))
  xAxisTime.call(d3.axisBottom(xScale).tickFormat(function (d) {
    var parseDate = d3.timeParse("%H");
    return d3.timeFormat("%H:%M")(parseDate(d))
  }
  ))
    .selectAll("text")
    .style("text-anchor", "end")
    .attr("dx", "-.8em")
    .attr("dy", ".15em")
    .attr("transform", "rotate(-65)")

  // Add brush
  var brush = d3.brushX()
    .extent([[0, 1], [widthTime, heightTime]]) //(x0,y0)  (x1,y1)
    .on("brush", brushend) //when mouse up, move the selection to the exact tick //start(mouse down), brush(mouse move), end(mouse up)

  svgTime.append("g")
    .attr("class", "brush")
    .call(brush)
    .call(brush.move, xScale.range());;

  svgTime.select(".brush")
    .on("click", function (d) {
      svgTime.select(".brush")
        .call(brush.move, xScale.range());
    });
}

function fillPlacesBoxes() {
  // Fill the places with the names and the staytime

  var timeData = getPlaceTime(startTime, endTime);
  delete timeData.group;
  var values = Object.values(timeData);
  var keys = Object.keys(timeData);
  count = 1;
  placeIdOfBox = {};
  while (count < numOfBoxes) {
    var maxIdx = values.indexOf(Math.max.apply(Math, values))
    var placeId = keys[maxIdx];

    placeIdOfBox[count] = placeId;
    document.getElementById("box-" + count).innerHTML = semanticInfo[placeId] + ", Time: " + Math.round(Math.max.apply(Math, values));
    if (count == 1) {
      maxCount = Math.max.apply(Math, values);
      updateTimeline(placeIdOfBox[count])
    }
    values.splice(maxIdx, 1);
    keys.splice(maxIdx, 1);
    count++;
  }
  topkPlaces = Object.values(placeIdOfBox);
}

function getPlaceTime(startTime, endTime) {
  // Filter the staytime by the chosen timerange

  var timeData = {};
  for (var idx = 0; idx < Object.keys(timelineData[0]).length; idx++) {
    timeData[Object.keys(timelineData[0])[idx]] = 0;
  }

  for (let i = startTime; i <= endTime; i++) {
    for (var idx = 0; idx < Object.keys(timelineData[i]).length; idx++) {
      timeData[Object.keys(timelineData[i])[idx]] += parseFloat(timelineData[i][Object.keys(timelineData[i])[idx]]);
    }
  }
  return timeData
}

function colorPlacesBoxes(startTime, endTime) {
  // Update the color of the places and also the staytime

  var timeData = getPlaceTime(startTime, endTime);
  delete timeData.group;
  var maxValue = Math.log(Math.max.apply(Math, Object.values(timeData)));
  var color = d3.scaleLinear()
    .domain([0, maxValue])
    .range(["#ffffff ", "#1F407A"]);
  for (let i = 1; i < numOfBoxes; i++) {
    document.getElementById("box-" + i).parentNode.style.backgroundColor = color(Math.log(timeData[placeIdOfBox[i]]));
    document.getElementById("box-" + i).innerHTML = "<span style='font-size:15px;'>" + semanticInfo[placeIdOfBox[i]] + "</span>" + "<span style='font-size:10px;'>" + ", Staytime: " + Math.round(timeData[placeIdOfBox[i]]) + " hrs" + "</span>";
    if (Math.log(timeData[placeIdOfBox[i]]) > 0.6 * maxValue) {
      document.getElementById("box-" + i).style.color = "white";
    }
    else {
      document.getElementById("box-" + i).style.color = "black";
    }
    try {
      placeId.get(placeIdOfBox[i]).bubble.style.fill = color(Math.log(timeData[placeIdOfBox[i]]))

    }
    catch {

    }
  }
}

function drawMap(map) {
  // Draws the underlying map (not in use right now, we used Mapbox instead)

  // Use projection; data is not already projected
  pathBaseMap = d3.geoPath(projection);

  // Draw base map
  g.basemap.append("path")
    .datum(map)
    .attr("class", "land")
    .attr("d", pathBaseMap);

  // Draw interior borders
  g.basemap.append("path")
    .datum(map)
    .attr("class", "border")
    .attr("d", pathBaseMap);
}

function drawPlaces(places) {
  // Draw the places on the map and color and scale them accordingly

  // Adjust scale
  let extent = d3.extent(places, d => d.outgoing);
  scales.places.domain(extent);

  // Draw place bubbles

  bubbles = g.places.selectAll("circle.place")
    .remove()

  bubbles = g.places.selectAll("circle.place")
    .data(places, d => d.placeId)
    .enter()
    .append("circle")
    .attr("r", d => scales.places(d.outgoing))
    .attr("cx", d => project(d).x)
    .attr("cy", d => project(d).y)
    .attr("class", "place")
    .each(function (d) {
      // Add the circle object to our place
      // Make it fast to select places on hover
      d.bubble = this;
    })
    .on("mouseover", function (d, i) {
      mousoverFunction(d.placeId);
    })
    .on("mouseout", function (d, i) {
      mouseoutFunction(d.placeId)
    })
    .on("click", function (d) {
      if (topkPlaces.includes(d.placeId)) {
        updateTimeline(d.placeId);
      }
    });

  // Add labels to the map, but hide them
  labels = g.places.selectAll(".label")
    .data(places, d => d.placeId)
    .enter()
    .append("text")
    .attr("class", "label")
    .text(function (d) { return semanticInfo[d.placeId]; })
    .attr("text-anchor", "end")
    .attr("dx", "-20px")
    .attr("dy", "10px")
    .attr("x", d => project(d).x)
    .attr("y", d => project(d).y)
    .attr("opacity", 0);

}

// NOT IN USE RIGHT NOW
function drawPolygons(places) {
  // From the template, used to have polygons n the background

  // Convert array of places into geojson format
  let geojsonPoly = places.map(function (place) {
    return {
      type: "Feature",
      properties: place,
      geometry: {
        type: "Point",
        coordinates: [place.longitude, place.latitude]
      }
    };
  });

  // Calculate voronoi polygons
  let polygons = d3.geoVoronoi().polygons(geojsonPoly);

  g.voronoi.selectAll("path")
    .data(polygons.features)
    .enter()
    .append("path")
    .attr("d", d3.geoPath(projection))
    .attr("class", "voronoi")
    .on("mouseover", function (d) {
      let place = d.properties.site.properties;

      d3.select(place.bubble)
        .call(highlight);

      d3.selectAll(place.trips)
        .call(highlight)
        .raise();

      // Make tooltip take up space but keep it invisible
      tooltip.style("display", null);
      tooltip.style("visibility", "hidden");

      var pos = place.bubble.getBoundingClientRect();
      var x = pos.left + pos.width / 2, y = pos.top + pos.height / 2;


      // Set default tooltip positioning
      tooltip.attr("text-anchor", "middle");
      //tooltip.attr("dy", -scales.places(place.outgoing));
      tooltip.attr("x", x);
      tooltip.attr("y", y - scales.places(place.outgoing));

      // Set the tooltip text
      tooltip.text(semanticInfo[place.placeId]);

      // Double check if the anchor needs to be changed
      let bbox = tooltip.node().getBBox();

      if (bbox.x <= 0) {
        tooltip.attr("text-anchor", "start");
      }
      else if (bbox.x + bbox.width >= widthMap) {
        tooltip.attr("text-anchor", "end");
      }

      tooltip.style("visibility", "visible");
    })
    .on("mouseout", function (d) {
      let place = d.properties.site.properties;

      d3.select(place.bubble)
        .call(notHighlight, 'aiport');

      d3.selectAll(place.trips)
        .call(notHighlight, 'trip');

      d3.select("text#tooltip").style("visibility", "hidden");
    })
    .on("dblclick", function (d) {
      // Toggle voronoi outline
      let toggle = d3.select(this).classed("highlight");
      d3.select(this).classed("highlight", !toggle);
    });
}

function drawTrips(places, trips, orig) {
  // Draw the trips between the places

  if (!mapBlank) {
    geojson = geojsons[0];
  }
  else {
    geojson = geojsons[1];
  }
  if (orig) {
    geojson = geojsonOriginal;
  }

  pathTrips = d3.geoPath(projection);

  links = g.trips.selectAll("path.trip")
    .remove()

  links = g.trips.selectAll("path.trip")
    .data(geojson.features)
    .enter()
    .append("path")
    .attr("d", pathTrips)
    .attr("class", "trip")
    .attr("id", function (d) { return "id_" + d.properties.id })
    .style("stroke-width", d => d.properties.count)
    .each(function (d) {
      // Add the path object to our source place
      // Make it fast to select outgoing paths
      tripTemp = this;
      ind = 0;
      places.forEach(function (dd, ii) {
        if (dd.placeId == d.properties.placeId) {
          ind = ii;
          places[ind].trips.push(tripTemp)
        }
      })
    });

}

// Turns a single edge into several segments that can
// be used for simple edge bundling.
function addWaypoints(links) {
  // Called before the drawing of the trips
  // Create the geojson of the trips based onthe csv data

  var geojsonSchematic = {
    "name": "NewFeatureType",
    "type": "FeatureCollection",
    "features": []
  };

  var geojson = {
    "name": "NewFeatureType",
    "type": "FeatureCollection",
    "features": []
  };

  var count = 0;
  links.forEach(function (d, i) {
    var featureSchematic = {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": []
      },
      "properties": {
        "placeId": null,
        "id": null,
        "count": null
      }
    }

    var feature = {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": []
      },
      "properties": {
        "placeId": null,
        "id": null,
        "count": null
      }
    }

    for (let j = 0; j < d.waypointsLongSchematic.length; j++) {
      featureSchematic.geometry.coordinates.push([d.waypointsLongSchematic[j], d.waypointsLatSchematic[j]]);
      featureSchematic.properties.placeId = d.source.placeId;
      featureSchematic.properties.id = count;
      featureSchematic.properties.count = d.count;

    }

    for (let j = 0; j < d.waypointsLong.length; j++) {
      feature.geometry.coordinates.push([d.waypointsLong[j], d.waypointsLat[j]]);
      feature.properties.placeId = d.source.placeId;
      feature.properties.id = count;
      feature.properties.count = d.count;

    }

    geojsonSchematic.features.push(featureSchematic);
    geojson.features.push(feature);
    count += 1;

  });

  return [geojson, geojsonSchematic];
}

// Turns a single edge into several segments that can
// be used for simple edge bundling.
function addWaypointsOriginal(links) {
  // Do the same as the function addWaypoints() but for the original trips

  var geojson = {
    "name": "NewFeatureType",
    "type": "FeatureCollection",
    "features": []
  };

  var count = 0;
  links.forEach(function (d, i) {

    var feature = {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": []
      },
      "properties": {
        "placeId": null,
        "id": null,
        "count": null
      }
    }

    for (let j = 0; j < d.waypointsLong.length; j++) {
      feature.geometry.coordinates.push([d.waypointsLong[j], d.waypointsLat[j]]);
      feature.properties.placeId = d.source.placeId;
      feature.properties.id = count;
      feature.properties.count = d.count;

    }

    geojson.features.push(feature);
    count += 1;

  });

  return geojson;
}


function typePlace(place) {
  // Called while loading the places. Parses some of the data and changes the type and the projection

  place.longitude = parseFloat(place.longitude);
  place.latitude = parseFloat(place.latitude);
  place.longitudeSchematic = parseFloat(place.longitudeSchematic);
  place.latitudeSchematic = parseFloat(place.latitudeSchematic);

  var point = map.project(new mapboxgl.LngLat(place.longitude, place.latitude));
  place.x = point.x;
  place.y = point.y;

  var point = map.project(new mapboxgl.LngLat(place.longitudeSchematic, place.latitudeSchematic));
  place.xSchematic = point.x;
  place.ySchematic = point.y;

  place.outgoing = 0;  // eventually tracks number of outgoing trips
  place.incoming = 0;  // eventually tracks number of incoming trips

  place.trips = [];  // eventually tracks outgoing trips

  return place;
}


function typeTrip(trip) {
  // Called while loading the trips. Read and change type of values

  trip.count = parseInt(trip.count);
  trip.waypointsLong = trip.waypointsLong.split(" ").map(parseFloat);
  trip.waypointsLongSchematic = trip.waypointsLongSchematic.split(" ").map(parseFloat);

  trip.waypointsLat = trip.waypointsLat.split(" ").map(parseFloat);
  trip.waypointsLatSchematic = trip.waypointsLatSchematic.split(" ").map(parseFloat);

  return trip;
}



function typeTripOriginal(trip) {
// Called while loading the trips original. Read and change type of values
  trip.waypointsLong = trip.waypointsLong.split(" ").map(parseFloat);

  trip.waypointsLat = trip.waypointsLat.split(" ").map(parseFloat);

  return trip;
}


function distance(source, target) {
  // Calculates the distance between two nodes
  // sqrt( (x2 - x1)^2 + (y2 - y1)^2 )
  var dx2 = Math.pow(target.x - source.x, 2);
  var dy2 = Math.pow(target.y - source.y, 2);

  return Math.sqrt(dx2 + dy2);
}

function highlight(selection) {
  // Change the color on the map
  selection
    .style("opacity", 0.8)
    .style("stroke", "#A8322D")
    .style("stroke-opacity", 0.8);
}

function notHighlight(selection, type) {
  // Change back to original colors on the map
  selection
    .style("stroke", "#252525")
  if (type == 'trip') {
    selection
      .style("stroke-opacity", 1);
  }
  else {
    selection
      .style("opacity", 1)
  }
}


function updateTimeline(selectedVar) {
  // Update the barcharts according to what is clicked

  // First change the order
  order = 0;
  for (let i = 1; i < numOfBoxes; i++) {
    if (placeIdOfBox[i] == selectedVar) {
      document.getElementById("box-" + i).parentNode.style.order = order;
      order += 2;
    }
    else {
      document.getElementById("box-" + i).parentNode.style.order = order;
    }
  }

  // Parse the Data
  // X axis
  xScale.domain(timelineData.map(function (d) { return d.group; }))
  xAxis.transition().duration(1000).call(d3.axisBottom(xScale).tickFormat(function (d) {
    var parseDate = d3.timeParse("%H");
    return d3.timeFormat("%H:%M")(parseDate(d))
  }
  ))
    .selectAll("text")
    .style("text-anchor", "end")
    .attr("dx", "-.8em")
    .attr("dy", ".15em")
    .attr("transform", "rotate(-65)")

  // Add Y axis
  yScale.domain([0, d3.max(timelineData, function (d) { return +d[selectedVar] })]);
  yAxis.transition().duration(1000).call(d3.axisLeft(yScale).ticks(3));

  // variable u: map data to existing bars
  var u = svgTimeline.selectAll("rect")
    .data(timelineData)

  // Update bars
  u
    .enter()
    .append("rect")
    .merge(u)
    .transition()
    .duration(1000)
    .attr("x", function (d) { return xScale(d.group); })
    .attr("y", function (d) { return yScale(d[selectedVar]); })
    .attr("width", xScale.bandwidth())
    .attr("height", function (d) { return heightTimeline - yScale(d[selectedVar]); })
    .attr("fill", "#A8322D")
    .attr("class", "bars")



}

function updateZoom(selectedVar) {
  // Fly to a specfic place

  let place = placeId.get(selectedVar);
  if (!mapBlank) {
    map.flyTo({ center: [place.longitude, place.latitude], zoom: 16 })
  }
  else {
    map.flyTo({ center: [place.longitudeSchematic, place.latitudeSchematic], zoom: 16 })
  }
}

function brushend() {
  // Change the colors of the places boxes and map elements after the brush was moved

  if (!d3.event.sourceEvent) return; // Only transition after input.
  if (!d3.event.selection) return; // Ignore empty selections.
  var areaArray = d3.event.selection;//[x0,x1]
  startTime = xScaleTime.invert(areaArray[0])
  endTime = xScaleTime.invert(areaArray[1])
  colorPlacesBoxes(parseInt(startTime), parseInt(endTime));
}



function arcTween(a) {
  // Store the displayed angles in _current.
  // Then, interpolate from _current to the new angles.
  // During the transition, _current is updated in-place by d3.interpolate.
  var i = d3.interpolate(this._current, a);
  this._current = i(0);
  return function (t) {
    return arc(i(t));
  }
}

function mousoverFunction(i) {
  // What to do when hovering over a place or box

  if (parseInt(i) < places.length + 1) {
    let place = placeId.get(i);

    svg.selectAll('path')
      .call(notHighlight, 'trip');
    svg.selectAll('circle')
      .call(notHighlight, 'aiport');
    d3.select(place.bubble)
      .call(highlight);

    d3.selectAll(place.trips)
      .call(highlight)
      .raise();

    // Make tooltip take up space but keep it invisible
    tooltip.style("display", null);
    tooltip.style("visibility", "hidden");

    var pos = place.bubble.getBBox();
    var x = pos.x + pos.width / 2, y = pos.y + pos.height / 2;


    // Set default tooltip positioning
    tooltip.attr("text-anchor", "middle");
    tooltip.attr("dy", -scales.places(place.outgoing));
    tooltip.attr("x", x);
    tooltip.attr("y", y - scales.places(place.outgoing));

    // Set the tooltip text
    tooltip.text(semanticInfo[place.placeId]);

    // Double check if the anchor needs to be changed
    let bbox = tooltip.node().getBBox();

    if (bbox.x <= 0) {
      tooltip.attr("text-anchor", "start");
    }
    else if (bbox.x + bbox.width >= widthMap) {
      tooltip.attr("text-anchor", "end");
    }

    tooltip.style("visibility", "visible");

  }
}

function mouseoutFunction(i) {
  // What to do when not hovering anymore over a place or box

  if (parseInt(i) < places.length) {

    let place = placeId.get(i);

    d3.select(place.bubble)
      .call(notHighlight, 'aiport');

    d3.selectAll(place.trips)
      .call(notHighlight, 'trip');

    d3.select("text#tooltip").style("visibility", "hidden");
    d3.select("#SemanticInfo").text("");
  }
}

function projectPoint(lon, lat) {
  // Project coordinates

  var point = map.project(new mapboxgl.LngLat(lon, lat));
  this.stream.point(point.x, point.y);
  return point;
}

function project(d) {
  // Project coordinates
  return map.project(getLL(d));
}

function getLL(d) {
  // Project coordinates
  if (!mapBlank) {
    return new mapboxgl.LngLat(+d.longitude, +d.latitude)
  }
  else {
    return new mapboxgl.LngLat(+d.longitudeSchematic, +d.latitudeSchematic)
  }
}

function render() {
  // Change according to zoom level

  g.basemap.select("path.land")
    .attr("d", pathBaseMap);

  g.basemap.select("path.border")
    .attr("d", pathBaseMap);

  g.trips.selectAll("path.trip")
    .attr("d", pathTrips);

  bubbles
    .attr("cx", function (d) {
      return project(d).x
    })
    .attr("cy", d => project(d).y)

  labels
    .attr("x", function (d) {
      return project(d).x
    })
    .attr("y", d => project(d).y)

}


function changeData(mapMode) {
  // Change between schematic and aggregated data --> Morphing effect

  drawTrips(places, trips, false);

  if (mapMode == 'schematic') {
    mapBlank = true;
  }
  if (mapMode == 'geometric') {
    mapBlank = false;
  }

  // Set background map
  if (!mapBlank) {
    map.setStyle('mapbox://styles/mapbox/light-v10');
    extent = extents[0];
  }
  else {
    map.setStyle('mapbox://styles/dlaumer/ck9viuh1c0ysh1irw0jadcwgc');
    extent = extents[1];
  }

  // Remove layers
  bubbles.remove();
  labels.remove();

  // Add layers again, with transition
  var n = 0;
  g.trips.selectAll("path.trip")
    .transition()
    .duration(3000)
    .attrTween('d', function (d) {
      n++;
      if (!mapBlank) {
        var startPath = pathTrips(geojsons[1].features[d.properties.id]),
          endPath = pathTrips(geojsons[0].features[d.properties.id]);
      }
      else {
        var startPath = pathTrips(geojsons[0].features[d.properties.id]),
          endPath = pathTrips(geojsons[1].features[d.properties.id]);
      }
      return d3.morphPath(startPath, endPath);
    })
    // Wait until the transition is done
    .on("end", function () { // use to be .each('end', function(){})
      n--;
      if (!n) {
        endall();
      }
    })


  function endall() {
    // as soon as the transition is done, draw the layers again and color boxes and zoom out

    drawTrips(places, trips, geomMap);
    drawPlaces(places);
    colorPlacesBoxes(startTime, endTime);
    zoomToAll();
  }
}

function zoomToAll() {
  // Zoom to the full extent

  if (!mapBlank) {
    extent = extents[0];
  }
  else {
    extent = extents[1];
  }
  map.fitBounds(extent, {
    padding: {
      top: 50,
      bottom: 50,
      left: 50,
      right: 50
    }
  });
}

// Negative stacked bar graph: Home and Work Balance
function drawNegativeBar(HomeWorkSeries, yAxisMax) {
  // Weekday categories
  var categories = [
    'Sunday', 'Saturday', 'Friday', 'Thursday', 'Wednesday', 'Tuesday', 'Monday'
  ];

  Highcharts.chart('container', {
    chart: {
      type: 'bar'
    },
    title: {
      text: 'Home and Work Balance',
      style: {
        fontSize: '18px',
        fontWeight: 'bold',
        fontFamily: 'Arial'
      }
    },
    accessibility: {
      point: {
        valueDescriptionFormat: '{index}. StayTime {xDescription}, {value}hrs.'
      }
    },
    exporting: {
      enabled: false, 
    },
    xAxis: [{
      categories: categories,
      reversed: false,
      labels: {
        step: 1
      },
      accessibility: {
        description: 'StayTime (Home)'
      }
    }, { // mirror axis on right side
      opposite: true,
      reversed: false,
      categories: categories,
      linkedTo: 0,
      labels: {
        step: 1
      },
      accessibility: {
        description: 'StayTime (Work)'
      }
    }],
    yAxis: {
      max: yAxisMax,
      min: -yAxisMax,
      title: {
        text: null
      },
      labels: {
        formatter: function () {
          return Math.abs(this.value);
        }
      },
    },

    plotOptions: {
      series: {
        stacking: 'normal'
      }
    },

    tooltip: {
      formatter: function () {
        return '<b>' + this.series.name + ', ' + this.point.category + '</b><br/>' +
          Highcharts.numberFormat(Math.abs(this.point.y), 1) + ' hrs';
      }
    },

    series: HomeWorkSeries
  });
}

function drawTransPieChart(transportationSeries, totalCo2) {
  // Make monochrome colors
  var pieColors = (function () {
    var colors = [],
      base = Highcharts.getOptions().colors[0],
      i;

    for (i = 0; i < 10; i += 1) {
      // Start out with a darkened base color (negative brighten), and end
      // up with a much brighter color
      colors.push(Highcharts.color(base).brighten((i - 3) / 7).get());
    }
    return colors;
  }());

  Highcharts.chart('container', {
    chart: {
      plotBackgroundColor: null,
      plotBorderWidth: null,
      plotShadow: false,
      type: 'pie'
    },
    title: {
      text: 'Commuting Habits',
      style: {
        fontSize: '18px',
        fontWeight: 'bold',
        fontFamily: 'Arial'
      }
    },
    subtitle: {
      text: 'Your total CO2 emission is: ' + totalCo2.toFixed(2) + ' kg',
    },
    tooltip: {
      headerFormat: '<span style="font-size:11px">{series.name}</span><br>',
      pointFormat: '<b>{point.name}</b></span>: <b>{point.y:.1f}%</b> of total CO2 emission<br/> {point.distVal:.1f} km x {point.co2kmVal} kg/km = <b>{point.co2EmissionVal:.2f}</b> kg'
    },
    accessibility: {
      point: {
        valueSuffix: '%'
      }
    },
    exporting: {
      enabled: false,
    },
    plotOptions: {
      pie: {
        allowPointSelect: true,
        cursor: 'pointer',
        colors: pieColors,
        center: ["50%", "48%"],
        size: "75%",
        dataLabels: {
          enabled: true,
          format: '<b>{point.name}</b><br>{point.y:.1f} %',
          distance: -30,
          filter: {
            property: 'percentage',
            operator: '>',
            value: 4
          },
          style: {
            fontSize: '10px',
            fontFamily: 'Arial',
            textOutline: '0px contrast'
          }
        }
      }
    },
    series: [{
      name: 'Transportation mode',
      colorByPoint: true,
      data: transportationSeries,
    }]
  });
}

// Add functionalty to the info button
document.getElementById("info-button").addEventListener("click", function () {
  let toggle = d3.select("#info-container").classed("collapseHoriz");
  d3.select('#info-container')
    .classed("collapseHoriz", !toggle);
});

// Add functionality to the collapse button 2
document.getElementById("collapeButton2").addEventListener("click", function () {
  let toggle = d3.select("#homeWorkBalance-container").classed("collapse");
  d3.select('#homeWorkBalance-container')
    .style("visibility", toggle ? "visible" : "hidden");
  d3.select("#homeWorkBalance-container")
    .classed("collapse", !toggle);
  if (toggle) {
    this.getElementsByTagName("span")[0].innerHTML = "&gt;";
  }
  else {
    this.getElementsByTagName("span")[0].innerHTML = "&lt;";
  }

});

// Add functionality to the collapse button 1
document.getElementById("collapeButton1").addEventListener("click", function () {

  let toggle = d3.select("#places-container").classed("collapse");
  d3.select('#places-boxes')
    .style("visibility", toggle ? "visible" : "hidden");
  d3.select("#places-container")
    .classed("collapse", !toggle);
  if (toggle) {
    this.getElementsByTagName("span")[0].innerHTML = "&lt;";
  }
  else {
    this.getElementsByTagName("span")[0].innerHTML = "&gt;";
  }
});

// Add functionality to the change diagramm button
var toggleChart = true;
document.getElementById("buttonChangeHighcart").addEventListener("click", function () {
  if (toggleChart) {
    drawTransPieChart(transportationSeries, totalCo2);

  }
  else{
    drawNegativeBar(HomeWorkSeries, yAxisMax);

  }
  toggleChart = !toggleChart;

});


// Make the map resize when collapsing boxes
d3.selectAll(".flex-item")
  .on("transitionend", function () {
    map.resize();

    var widthMap = d3
      .select('#map-container')
      .node()
      .getBoundingClientRect().width
    // Set dimensions
    var heightMap = d3
      .select('#map-container')
      .node()
      .getBoundingClientRect().height

    svg
      .attr('width', widthMap)
      .attr('height', heightMap)

  });



function getExtentofPlaces(places) {
  // get full extent

  var lats = [],
    lons = [],
    latsSchem = []
  lonsSchem = []
  for (var i = 0; i < places.length; i++) {
    lats.push(places[i].latitude);
    lons.push(places[i].longitude);
    latsSchem.push(places[i].latitudeSchematic);
    lonsSchem.push(places[i].longitudeSchematic);
  }

  extentPlaces = [[Math.min.apply(null, lons), Math.min.apply(null, lats)],
  [Math.max.apply(null, lons), Math.max.apply(null, lats)]];
  extentPlacesSchematic = [[Math.min.apply(null, lonsSchem), Math.min.apply(null, latsSchem)],
  [Math.max.apply(null, lonsSchem), Math.max.apply(null, latsSchem)]];
  return [extentPlaces, extentPlacesSchematic]
}


d3.select("#homeWorkBalance-container")
  .style("max-width", document.getElementById('homeWorkBalance-container').getBoundingClientRect().width)

d3.select("#places-container")
  .style("max-width", document.getElementById('places-container').getBoundingClientRect().width)


function setBasicStatistics(basicStatistics) {
  // set the basic statistics automatically

  for (var i = 0; i < basicStatistics.length; i++) {
    if (basicStatistics[i].id == dataName) {
      basicStats = basicStatistics[i]
    }
  }


  mybody = document.getElementsByTagName("body")[0];
  mytable = mybody.getElementsByTagName("table")[0];
  mytablebody = mytable.getElementsByTagName("tbody")[0];

  var parseTime = d3.timeParse("%Y-%m-%d");
  var formatTime = d3.timeFormat("%d. %b %Y");

  rowTime = mytablebody.getElementsByTagName("tr")[0];
  mycel = rowTime.getElementsByTagName("td")[1].textContent = formatTime(parseTime(basicStats['startTime'])) + " - " + formatTime(parseTime(basicStats['endTime']));

  rowPhone = mytablebody.getElementsByTagName("tr")[1];
  mycel = rowPhone.getElementsByTagName("td")[1].textContent = basicStats['phoneModel'];

  rowPoints = mytablebody.getElementsByTagName("tr")[2];
  mycel = rowPoints.getElementsByTagName("td")[1].textContent = basicStats['NumPoints'] + " GPS Points";

  rowDistAvg = mytablebody.getElementsByTagName("tr")[3];
  mycel = rowDistAvg.getElementsByTagName("td")[1].textContent = parseFloat(basicStats['AvgDist']).toFixed(1) + " km/day";

  rowDist = mytablebody.getElementsByTagName("tr")[4];
  mycel = rowDist.getElementsByTagName("td")[1].textContent = parseFloat(basicStats['TotalDist']).toFixed(1) + " km total";
}

function removeLabels() {
  // Remove labels from the map

  newOpacity = d3.selectAll(".label").attr("opacity") == 0 ? 1 : 0;
  d3.selectAll(".label").attr("opacity", newOpacity);

  d3.select('#removeLabelsButton')
    .style('background-color',newOpacity==0 ? "#1F407A":"#A8322D")
  

}
