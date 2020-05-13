// Data files to import
var urls = {
  map: "swiss.json",

  places:
    "places.csv",

  trips:
    "tripsAgr.csv",

  timeline:
    "AverStayTimebyHour.csv",

  semanticInfo:
    "AverStayTimebyHourwithLocinfo.csv"
};

// PERPARE MAP  ////////////////////////////////////////////////////////////////////////////////////

mapboxgl.accessToken = 'pk.eyJ1IjoiZGxhdW1lciIsImEiOiJjazhwdWc1aG8wazZnM2xubG5uaGwxN2RmIn0.cgSC6SK8DdnCPwO4NmjxAQ'

//Setup mapbox-gl map
var map = new mapboxgl.Map({
  container: 'mapboxx', // container id
  style: 'mapbox://styles/dlaumer/ck9vivxcy14761inolbg58hqu',
  center: [8.507412548555335, 47.40639137110055],
  zoom: 10
})

map.addControl(new mapboxgl.NavigationControl());

// re-render our visualization whenever the view changes
map.on("viewreset", function () {
  render()
})
map.on("move", function () {
  render()
})

// svg要素をアペンドする
var container = map.getCanvasContainer()
var removed = d3.select("svg#map").remove()
var svg = d3.select(container).append(function () {
  return removed.node();
});

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
//var projection = d3.geoMercator().scale(300000).center([8.507412548555335, 47.40639137110055]);
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


//svg.call(zoom);

// PREPARE TIMELINE  ////////////////////////////////////////////////////////////////////////////////////


// set the dimensions and margins of the graph
var margin = { top: 30, right: 30, bottom: 20, left: 60 };
var widthTimeline = d3
  .select('#chart-container')
  .node()
  .getBoundingClientRect().width  - margin.left - margin.right;
// Set dimensions
var heightTimeline = d3
  .select('#chart-container')
  .node()
  .getBoundingClientRect().height - margin.top - margin.bottom;


var svgTimeline = d3.select("#timeline")
  .append("svg")
  .attr("width", widthTimeline + margin.left + margin.right)
  .attr("height", heightTimeline + margin.top + margin.bottom)
  .append("g")
  .attr("transform",
    "translate(" + margin.left + "," + margin.top + ")")



// Initialize the X axis
var xScale = d3.scaleBand()
  .range([0, widthTimeline])
  .padding(0.2);

xScale.invert = function (x) {
  var domain = this.domain();
  var range = this.range()
  var scale = d3.scaleQuantize().domain(range).range(domain)
  return scale(x)
};
var xAxis = svgTimeline.append("g")
  .attr("transform", "translate(0," + heightTimeline + ")")

// Initialize the Y axis
var yScale = d3.scaleLinear()
  .range([heightTimeline, 0]);
var yAxis = svgTimeline.append("g")
  .attr("class", "myYaxis")


// LOAD DATA  ////////////////////////////////////////////////////////////////////////////////////

// load and draw base map
//d3.json(urls.map).then(drawMap);

var timelineData;
var places;
var trips;
var tripsAgr;
var semanticInfo;
var bubbles;
var pathBaseMap;
var pathTrips;
var links
var geojsons;
var placeIdOfBox;
var maxCount;
var mapBlank = true;
var geomMap = true;

// load the place and trip data together
let promises = [
  d3.dsv(';', urls.places, typePlace),
  d3.dsv(';', urls.trips, typeTrip),
  d3.csv(urls.timeline),
  d3.csv(urls.semanticInfo)
];

Promise.all(promises).then(processData);

// process place and trip data
function processData(values) {

  places = values[0];
  trips = values[1];
  timelineData = values[2];
  semanticInfo = values[3][0];

  fillPlacesBoxes();
  colorPlacesBoxes(0,23);
  drawTimeline();

  for (let i = 1; i < 11; i++) {
    document.getElementById("box-" + i).addEventListener('click', event => { updateTimeline(placeIdOfBox[i])});
  }

  console.log("places: " + places.length);
  console.log(" trips: " + trips.length);

  // convert places array (pre filter) into map for fast lookup
  // Basically make a dictionary (like in python) with placeId as key
  let placeId = new Map(places.map(node => [node.placeId, node]));

  // calculate incoming and outgoing degree based on trips
  // trips are given by place placeId code (not index)
  trips.forEach(function (link) {
    link.source = placeId.get(link.origin);
    link.target = placeId.get(link.destination);

    link.source.outgoing += link.count;
    link.target.incoming += link.count;
  });

  // remove places without any trips
  old = places.length;
  places = places.filter(place => place.outgoing > 0 || place.incoming > 0);
  console.log(" removed: " + (old - places.length) + " places without trips");

  // sort places by outgoing degree
  places.sort((a, b) => d3.descending(a.outgoing, b.outgoing));

  // done filtering places can draw
  drawPlaces(places);
  //drawPolygons(places);

  // reset map to only include places post-filter
  placeId = new Map(places.map(node => [node.placeId, node]));

  // filter out trips that are not between places we have leftover
  old = trips.length;
  trips = trips.filter(link => placeId.has(link.source.placeId) && placeId.has(link.target.placeId));
  console.log(" removed: " + (old - trips.length) + " trips");

  // done filtering trips can draw
  drawTrips(places, trips);
}

// FUNCTIONS ////////////////////////////////////////////////////////////////////////////////////

function drawTimeline() {

  // TIMELINE PLOT
  updateTimeline('1')

  //add brush
  var brush = d3.brushX()
    .extent([[0, 0], [widthTimeline, heightTimeline]])//(x0,y0)  (x1,y1)
    .on("end", brushend);//when mouse up, move the selection to the exact tick //start(mouse down), brush(mouse move), end(mouse up)

  svgTimeline.append("g")
    .attr("class", "brush")
    .call(brush);

}

function fillPlacesBoxes() {
  var timeData = getPlaceTime(0,23);
  delete timeData.group;
  var values = Object.values(timeData);
  var keys = Object.keys(timeData);
  count = 1;
  placeIdOfBox = {};
  while (count < 11) {
    var maxIdx = values.indexOf(Math.max.apply(Math,values))
    var placeId = keys[maxIdx];
    values.splice(maxIdx, 1);
    keys.splice(maxIdx, 1);
    placeIdOfBox[count] = placeId;
    document.getElementById("box-" + count).innerHTML = "Place ID: " + placeId + ", Time: " +  Math.round(Math.max.apply(Math,values)) ;
    if (count == 1){
      maxCount = Math.max.apply(Math,values);
    }
    count++;
  }

}

function getPlaceTime(startTime, endTime){

    var timeData = {};
    for (var idx = 0; idx < Object.keys(timelineData[0]).length; idx++ ){
      timeData[Object.keys(timelineData[0])[idx]] = 0;
    }

    for (let i = startTime; i <= endTime; i++) {
      for (var idx = 0; idx < Object.keys(timelineData[i]).length; idx++ ){
        timeData[Object.keys(timelineData[i])[idx]] += parseFloat(timelineData[i][Object.keys(timelineData[i])[idx]]);
      }
    }
    return timeData
}

function colorPlacesBoxes(startTime, endTime) {
  var timeData = getPlaceTime(startTime,endTime);
  delete timeData.group;
  var color = d3.scaleLinear()
  .domain([0,Math.max.apply(Math,Object.values(timeData))])
  .range(["#ffffff ", "#a83290"]);
  for (let i = 1; i < 11; i++) {
    document.getElementById("box-" + i).style.backgroundColor = color(timeData[placeIdOfBox[i]]);
    document.getElementById("box-" + i).innerHTML = "Place ID: " + placeIdOfBox[i] + ", Time: " +  Math.round(timeData[placeIdOfBox[i]]) ;

  }

}
// draws the underlying map
function drawMap(map) {

  // run topojson on remaining states and adjust projection
  //let land = topojson.merge(map, map.geometries);

  // use projection; data is not already projected
  pathBaseMap = d3.geoPath(projection);

  // draw base map
  g.basemap.append("path")
    .datum(map)
    .attr("class", "land")
    .attr("d", pathBaseMap);

  // draw interior borders
  g.basemap.append("path")
    .datum(map)
    .attr("class", "border")
    .attr("d", pathBaseMap);

}

function drawPlaces(places) {
  // adjust scale
  let extent = d3.extent(places, d => d.outgoing);
  scales.places.domain(extent);

  // draw place bubbles

  bubbles = g.places.selectAll("circle.place")
    .remove()

  bubbles = g.places.selectAll("circle.place")
    .data(places, d => d.placeId)
    .enter()
    .append("circle")
    .attr("r", d => scales.places(d.outgoing))
    .attr("cx", d => project(d).x)
    .attr("cy", d => project(d).y)
    //.attr("cx", function(d) {if (!mapBlank) {return d.x} else {return d.xSchematic}}) // calculated on load
    //.attr("cx", function(d) {if (!mapBlank) {return d.y} else {return d.ySchematic}}) // calculated on load
    .attr("class", "place")
    .each(function (d) {
      // adds the circle object to our place
      // makes it fast to select places on hover
      d.bubble = this;
    })
    .on("mouseover", function (d, i) {
      mousoverFunction(i);
    })
    .on("mouseout", function (d, i) {
      mouseoutFunction(i)
    })
    .on("click", function (d) {
      updateTimeline(d.placeId);
    });
}

// NOT IN USE RIGHT NOW
function drawPolygons(places) {
  // convert array of places into geojson format
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

  // calculate voronoi polygons
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

      // make tooltip take up space but keep it invisible
      tooltip.style("display", null);
      tooltip.style("visibility", "hidden");

      var pos = place.bubble.getBoundingClientRect();
      var x = pos.left + pos.width / 2, y = pos.top + pos.height / 2;


      // set default tooltip positioning
      tooltip.attr("text-anchor", "middle");
      //tooltip.attr("dy", -scales.places(place.outgoing));
      tooltip.attr("x", x);
      tooltip.attr("y", y - scales.places(place.outgoing));

      // set the tooltip text
      tooltip.text("Place ID: " + place.placeId);

      // double check if the anchor needs to be changed
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
      // toggle voronoi outline
      let toggle = d3.select(this).classed("highlight");
      d3.select(this).classed("highlight", !toggle);
    });
}

function drawTrips(places, trips) {
  // break each trip between places into multiple segments
  geojsons = addWaypoints(trips);
  if (!mapBlank) {
    geojson = geojsons[0];
  }
  else {
    geojson = geojsons[1];
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
    .attr("id", function (d) {return "id_" + d.properties.id})
    //.style("stroke-width", d => d.properties.count*2)
    .each(function (d) {
      // adds the path object to our source place
      // makes it fast to select outgoing paths
      tripTemp = this;
      ind = 0;
      places.forEach(function (dd, ii) {
        if (dd.placeId == d.properties.placeId) {
          ind = ii;
          places[ind].trips.push(tripTemp)
        }
      })
      //d[0].trips.push(this);
    });

}

// Turns a single edge into several segments that can
// be used for simple edge bundling.
function addWaypoints(links) {

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


// see places.csv
// convert gps coordinates to number and init degree
function typePlace(place) {
  place.longitude = parseFloat(place.longitude);
  place.latitude = parseFloat(place.latitude);
  place.longitudeSchematic = parseFloat(place.longitudeSchematic);
  place.latitudeSchematic = parseFloat(place.latitudeSchematic);
  // use projection hard-coded to match topojson data
  //let coords = projection(place.longitude, place.latitude);
  //place.x = coords[0];
  //place.y = coords[1];
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

// see trips.csv
// convert count to number
function typeTrip(trip) {
  trip.count = parseInt(trip.count);
  trip.waypointsLong = trip.waypointsLong.split(" ").map(parseFloat);
  trip.waypointsLongSchematic = trip.waypointsLongSchematic.split(" ").map(parseFloat);

  trip.waypointsLat = trip.waypointsLat.split(" ").map(parseFloat);
  trip.waypointsLatSchematic = trip.waypointsLatSchematic.split(" ").map(parseFloat);

  return trip;
}

// calculates the distance between two nodes
// sqrt( (x2 - x1)^2 + (y2 - y1)^2 )
function distance(source, target) {
  var dx2 = Math.pow(target.x - source.x, 2);
  var dy2 = Math.pow(target.y - source.y, 2);

  return Math.sqrt(dx2 + dy2);
}

function highlight(selection) {
  selection
    .style("opacity", 1)
    .style("stroke", "a83290")
    .style("stroke-opacity", 0.8);
}

function notHighlight(selection, type) {
  selection
    .style("opacity", 0.5)
    .style("stroke", "#252525")
  if (type == 'trip') {
    selection
      .style("stroke-opacity", 0.5);
  }
}


// A function that create / update the plot for a given variable:
function updateTimeline(selectedVar) {

  order = 0;
  for (let i = 1; i < 11; i++) {
    if (placeIdOfBox[i] == selectedVar){
      document.getElementById("box-" + i).style.order = order;
      order +=2;
    }
    else {
      document.getElementById("box-" + i).style.order = order;

    }

  }

  // Parse the Data
  // X axis
  xScale.domain(timelineData.map(function (d) { return d.group; }))
  xAxis.transition().duration(1000).call(d3.axisBottom(xScale))

  // Add Y axis
  yScale.domain([0, d3.max(timelineData, function (d) { return +d[selectedVar] })]);
  yAxis.transition().duration(1000).call(d3.axisLeft(yScale));

  // variable u: map data to existing bars
  var u = svgTimeline.selectAll("rect")
    .data(timelineData)

  // update bars
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
    .attr("fill", "#a83290")
    .attr("class", "bars")
}

function brushend() {
  if (!d3.event.sourceEvent) return; // Only transition after input.
  if (!d3.event.selection) return; // Ignore empty selections.
  var areaArray = d3.event.selection;//[x0,x1]
  startTime = xScale.invert(areaArray[0])
  endTime = xScale.invert(areaArray[1])
  colorPlacesBoxes(parseInt(startTime), parseInt(endTime));
}

function updatePieChart(startTime, endTime) {
  //clearTimeout(timeout);
  pie.value(function (d) { return getPieValues(d, startTime, endTime); }); // change the value function
  path = pathPie.data(pie); // compute the new angles
  path.transition().duration(750).attrTween("d", arcTween); // redraw the arcs
}

// Store the displayed angles in _current.
// Then, interpolate from _current to the new angles.
// During the transition, _current is updated in-place by d3.interpolate.
function arcTween(a) {
  var i = d3.interpolate(this._current, a);
  this._current = i(0);
  return function (t) {
    return arc(i(t));
  }
}

function getPieValues(d, startTime, endTime) {
  sum = 0;
  for (i = parseInt(startTime); i <= parseInt(endTime); i++) {
    sum += parseFloat(timelineData[i][d.group]);
  }
  return sum
}

function mousoverFunction(i) {
  let place = places[i];

  d3.select(place.bubble)
    .call(highlight);

  d3.selectAll(place.trips)
    .call(highlight)
    .raise();

  // make tooltip take up space but keep it invisible
  tooltip.style("display", null);
  tooltip.style("visibility", "hidden");

  var pos = place.bubble.getBoundingClientRect();
  var x = pos.left + pos.width / 2, y = pos.top + pos.height / 2;


  // set default tooltip positioning
  tooltip.attr("text-anchor", "middle");
  tooltip.attr("dy", -scales.places(place.outgoing) - 10);
  tooltip.attr("x", x);
  tooltip.attr("y", y - scales.places(place.outgoing));

  // set the tooltip text
  tooltip.text("Place ID: " + place.placeId);

  // double check if the anchor needs to be changed
  let bbox = tooltip.node().getBBox();

  if (bbox.x <= 0) {
    tooltip.attr("text-anchor", "start");
  }
  else if (bbox.x + bbox.width >= widthMap) {
    tooltip.attr("text-anchor", "end");
  }

  tooltip.style("visibility", "visible");

  d3.select("#SemanticInfo").text(semanticInfo[place.placeId]);


}

function mouseoutFunction(i) {
  let place = places[i];

  d3.select(place.bubble)
    .call(notHighlight, 'aiport');

  d3.selectAll(place.trips)
    .call(notHighlight, 'trip');

  d3.select("text#tooltip").style("visibility", "hidden");
  d3.select("#SemanticInfo").text("");

}

function projectPoint(lon, lat) {
  var point = map.project(new mapboxgl.LngLat(lon, lat));
  this.stream.point(point.x, point.y);
  return point;
}

function project(d) {
  return map.project(getLL(d));
}
function getLL(d) {
  if (!mapBlank) {
    return new mapboxgl.LngLat(+d.longitude, +d.latitude)
  }
  else {
    return new mapboxgl.LngLat(+d.longitudeSchematic, +d.latitudeSchematic)
  }
}

function render() {
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

}


function changeData() {
  mapBlank = !mapBlank;
  if (!mapBlank) {
    map.setStyle('mapbox://styles/mapbox/streets-v8');
  }
  else {
    map.setStyle('mapbox://styles/dlaumer/ck9vivxcy14761inolbg58hqu');
  }

  bubbles.remove();

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
      //var endPath = d3.select("path.tripGeometric#geometric_" + d.properties.id).attr('d'),
      //startPath = d3.select("path.trip#schematic_" + d.properties.id).attr('d');
    return d3.morphPath(startPath, endPath);
  })
  .on("end", function() { // use to be .each('end', function(){})
    n--;
    if (!n) {
      endall();
  }
})
function endall() {
  drawTrips(places, trips);
  drawPlaces(places)
}
}


// Negative stacked bar graph: Home and Work Balance
// Weekday categories
var categories = [
  'Sunday', 'Saturday', 'Friday', 'Thursday', 'Wednesday','Tuesday', 'Monday'
];

Highcharts.chart('container', {
  chart: {
    type: 'bar'
  },
  title: {
    text: 'Home and Work Balance'
  },
  // subtitle: {
  //   text: ''
  // },
  accessibility: {
    point: {
      valueDescriptionFormat: '{index}. StayTime {xDescription}, {value}hrs.'
    }
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
    title: {
      text: null
    },
    labels: {
      formatter: function () {
        return Math.abs(this.value);
      }
    },
    // accessibility: {
    //   description: 'Stay Time in Minutes',
    //   rangeDescription: 'above 0'
    // }
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

  series: [
  {
    name: 'Home at Affoltern',
    data: [-113.1,-31.6,-55.8,-94.6,-0.9,-8.2,-77],
  }, 
  // {
  //   name: 'Home at Schlieren',
  //   data: [0,0,0,0,-0.9,0,-0.5],
  // }, 
  {
    name: 'ETH Zurich',
    data: [0,0,28.5,73.9,3.6,39.4,15.3],
  }, 
  {
    name: 'Acht Grad Ost AG, 4, Wagistrasse, Schlieren',
    data: [0,0,5,0,12.5,5.9,27.3]
  }]
});
