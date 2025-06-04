document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded');
    var map = L.map('map').setView([54.372158, 18.638306], 14);
    L.tileLayer('tiles/{z}/{x}/{y}.png', {
        maxNativeZoom:18,
        maxZoom:25,
        attribution: 'UMP-pcPL'
    }).addTo(map);


    var droneIcon = L.icon({
    iconUrl: 'static/drone.png',
    shadowUrl: 'static/drone.png',

    iconSize:     [32,32], // size of the icon
    shadowSize:   [0,0], // size of the shadow
    iconAnchor:   [16,16], // point of the icon which will correspond to marker's location
    shadowAnchor: [0,0],  // the same for the shadow
    popupAnchor:  [0,0] // point from which the popup should open relative to the iconAnchor
});


    var dronesLayer = L.layerGroup().addTo(map);
    var nextPositionLayer = L.layerGroup().addTo(map);

    function updateDrones() {
        fetch('/get-drones')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Błąd odpowiedzi z serwera przy pobieraniu pozycji');
                }
                return response.json();
            })
            .then(data => {
                dronesLayer.clearLayers();

                var devices_list = document.getElementById("devices_list");
                devices_list.innerHTML = '';

                data.forEach(function (marker) {
                    var li = document.createElement('li');
                    li.innerHTML = `${marker.machine_id}<br>${marker.latitude},${marker.longitude}`;
                    li.onclick = (e) => console.log(e) ;
                    devices_list.appendChild(li);

                });

                data.forEach(function(marker) {
                    var m = L.marker([marker.latitude, marker.longitude], {icon: droneIcon}).
                    addTo(map).bindPopup(`${marker.machine_id}`);
                    dronesLayer.addLayer(m);
                });

                fetch('/get-next_position')
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Błąd odpowiedzi z serwera przy pobieraniu pozycji');
                    }
                    return response.json();
                })
                .then(data => {
                    nextPositionLayer.clearLayers();

                    data.forEach(function(item) {
                        var lat = item.lat;
                        var lon = item.lon;
                        var id = item.id;
                        var marker = L.marker([lat, lon])
                            .bindPopup(`${id}`);
                        nextPositionLayer.addLayer(marker);


                        var drone = dronesLayer.getLayers().find((el) => el._popup._content === id);
                        var linepos = [];
                        linepos.push(drone._latlng);
                        linepos.push([lat, lon]);
                        var line = L.polyline(linepos);
                        nextPositionLayer.addLayer(line);
                    });
            })
            .catch(err => {
                console.error('Błąd podczas aktualizacji pozycji:', err);
            });

            })
            .catch(err => {
                console.error('Błąd podczas aktualizacji pozycji:', err);
            });
    }
    updateDrones();
    setInterval(updateDrones, 1000);

    let goalMarker = null;
    
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

    fetch('/get-goal')
    .then(response => {
        if (!response.ok) throw new Error("Brak zapisanego celu");
        return response.json();
    })
    .then(data => {
        const latlng = [data.latitude, data.longitude];
        goalMarker = L.marker(latlng, { draggable: true }).addTo(map)
            .bindPopup("Cel").openPopup();

        goalMarker.on('dragend', function (e) {
            const newLatLng = e.target.getLatLng();
            fetch('/update-goal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lat: newLatLng.lat, lon: newLatLng.lng })
            })
            .then(res => res.ok ? console.log("Cel zaktualizowany") : console.error("Błąd zapisu"))
            .catch(err => console.error("Błąd sieci:", err));
        });

        goalMarker.on('contextmenu', function () {
            if (confirm("Czy chcesz usunąć cel?")) {
                map.removeLayer(goalMarker);
                goalMarker = null;
                fetch('/delete-goal', { method: 'POST' })
                    .then(res => res.ok ? console.log("Cel usunięty") : console.error("Błąd usuwania celu"))
                    .catch(err => console.error("Błąd sieci przy usuwaniu:", err));
            }
        });
    })
    .catch(err => {
        console.log("Cel nie istnieje:", err);
    });

    // Handle edits
    map.on('draw:edited', function (e) {
        var layers = e.layers;
        layers.eachLayer(function (layer) {
            // Ensure the GeoJSON includes the original ID
            var geojsonData = layer.toGeoJSON();
            geojsonData.properties = geojsonData.properties || {};
            geojsonData.properties.id = layer.feature.properties.id; // Retain the original polygon ID

            // Send the updated GeoJSON data back to the server
            fetch('/update-polygon', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(geojsonData) // Send the complete GeoJSON
            }).then(response => {
                if (response.ok) {
                    alert('Polygon updated successfully!');
                } else {
                    alert('Error updating polygon.');
                }
            });
        });
    });

   map.on('click', function (e) {
    const lat = e.latlng.lat;
    const lon = e.latlng.lng;
    if (!confirm("Czy ustanowić nowy cel w tym miejscu?")) {
        return;
    }
    if (goalMarker) {
        map.removeLayer(goalMarker);
    }
    goalMarker = L.marker([lat, lon], { draggable: true }).addTo(map).bindPopup("Cel").openPopup();

    goalMarker.on('dragend', function (e) {
        const newLatLng = e.target.getLatLng();
        fetch('/update-goal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lat: newLatLng.lat, lon: newLatLng.lng })
        })
        .then(res => {
            if (!res.ok) {
                console.error("Błąd zapisu celu po przesunięciu");
            } else {
                console.log("Cel zaktualizowany po przesunięciu");
            }
        })
        .catch(err => {
            console.error("Błąd sieci podczas zapisu celu po przesunięciu:", err);
        });
    });
    fetch('/update-goal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat: lat, lon: lon })
    })
    .then(response => {
        if (!response.ok) throw new Error("Błąd zapisu celu");
        return response.json();
    })
    .then(data => {
        console.log("Cel zapisany:", data);
    })
    .catch(err => {
        console.error("Błąd zapisu celu:", err);
    });
});


    // Handle deletions
    map.on('draw:deleted', function (e) {
        var layers = e.layers;
        layers.eachLayer(function (layer) {
            // Ensure the GeoJSON includes the ID for deletion
            var geojsonData = layer.toGeoJSON();
            geojsonData.properties = geojsonData.properties || {};
            geojsonData.properties.id = layer.feature.properties.id; // Retain the original polygon ID

            // Send delete request to the server
            fetch('/delete-polygon', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(geojsonData) // Use the GeoJSON with ID for deletion
            }).then(response => {
                if (response.ok) {
                    alert('Polygon deleted successfully!');
                } else {
                    alert('Error deleting polygon.');
                }
            });
        });
    });
});
