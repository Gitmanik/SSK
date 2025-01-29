// Initialize the map
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded');
    var map = L.map('map').setView([54.372158, 18.638306], 4); // Center the map

    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; <a href="https://www.esri.com/en-us/home">Esri</a> & contributors',
        maxZoom: 19
    }).addTo(map);

    // Fetch markers from a global variable or API (provided by Flask)
    var markers = window.markers || [];
    markers.forEach(function(marker) {
        L.marker([marker.latitude, marker.longitude]).addTo(map).bindPopup(`Drone ID: ${marker.machine_id}`);;
    });
});