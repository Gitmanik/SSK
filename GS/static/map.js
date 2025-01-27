// Initialize the map
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded');
    var map = L.map('map').setView([54.372158, 18.638306], 4); // Center the map

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Fetch markers from a global variable or API (provided by Flask)
    var markers = window.markers || [];
    markers.forEach(function(marker) {
        L.marker([marker.latitude, marker.longitude]).addTo(map).bindPopup(`Drone ID: ${marker.machine_id}`);;
    });
});