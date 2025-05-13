document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded');
    var map = L.map('map').setView([54.372158, 18.638306], 14);
    L.tileLayer('tiles/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: 'UMP-pcPL'
    }).addTo(map);

    var markers = window.markers || [];
    markers.forEach(function(marker) {
        L.marker([marker.latitude, marker.longitude]).addTo(map).bindPopup(`Drone ID: ${marker.machine_id}\nGPS: ${marker.latitude},${marker.longitude}`);
    });


    // Initialize Leaflet.Draw
    var drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);

    var drawControl = new L.Control.Draw({
    edit: {
        featureGroup: drawnItems
    },
    draw: {
        polygon: true,
        polyline: false,
        circle: false,
        rectangle: false,
        marker: false
    }
    });
    map.addControl(drawControl);

    // Listen for creation events
    map.on(L.Draw.Event.CREATED, function (e) {
        var layer = e.layer;
        drawnItems.addLayer(layer);

        // Send GeoJSON data to the server
        var geojsonData = JSON.stringify(layer.toGeoJSON());
        fetch('/save-polygon', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: geojsonData
        }).then(response => {
            if (response.ok) {
                alert('Polygon saved successfully!');
            } else {
                alert('Error saving polygon.');
            }
        });
    });

    // Load polygons from the database on page load
    fetch('/get-polygons')
    .then(response => response.json())
    .then(data => {
        data.forEach(function (polygon) {
            // Create a GeoJSON layer from the database data
            var layer = L.geoJSON(polygon, {
                onEachFeature: function (feature, layer) {
                    // Ensure the layer retains the feature properties (e.g., id for editing/deleting).
                    layer.feature = feature;
                }
            });

            // Add each layer from the GeoJSON to the `drawnItems` layer group
            layer.eachLayer(function (l) {
                drawnItems.addLayer(l); // Add to the editable FeatureGroup
            });
        });
    })
    .catch(error => {
        console.error('Error loading polygons:', error);
    });


});