/**
 * RoadWatch - GPS Location Capture & Report Form Handler
 */
document.addEventListener('DOMContentLoaded', function () {
    // Default coordinates: Mysuru, Karnataka, India (zoom 13)
    const DEFAULT_LAT = 12.3051;
    const DEFAULT_LNG = 76.6551;
    const DEFAULT_ZOOM = 13;

    const latInput = document.getElementById('latitude');
    const lngInput = document.getElementById('longitude');
    const feedbackBox = document.getElementById('gpsFeedback');
    const btnGeolocate = document.getElementById('btnGeolocate');
    const btnManualSelect = document.getElementById('btnManualSelect');
    const btnClearCoords = document.getElementById('btnClearCoords');
    const imageInput = document.getElementById('imageInput');
    const imagePreviewContainer = document.getElementById('imagePreviewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const uploadPrompt = document.getElementById('uploadPrompt');
    const removeImageBtn = document.getElementById('removeImageBtn');

    let map = null;
    let marker = null;

    // Helper: Show status message
    function showFeedback(message, type) {
        feedbackBox.style.display = 'flex';
        feedbackBox.className = 'gps-feedback-msg feedback-' + type;
        const icon = type === 'success' ? '✓' : type === 'error' ? '⚠️' : 'ℹ️';
        feedbackBox.innerHTML = `<span class="feedback-icon">${icon}</span><span class="feedback-text">${message}</span>`;
    }

    function clearFeedback() {
        feedbackBox.style.display = 'none';
        feedbackBox.innerHTML = '';
    }

    // Helper: Custom Pin Icon
    function createCustomPin(color = '#16A078') {
        const svgIcon = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="30" height="42">
                <defs>
                    <filter id="shadow" x="-20%" y="-10%" width="140%" height="140%">
                        <feDropShadow dx="0" dy="3" stdDeviation="2" flood-color="#101D2E" flood-opacity="0.35"/>
                    </filter>
                </defs>
                <path d="M12 0C5.373 0 0 5.373 0 12c0 9 12 24 12 24s12-15 12-24c0-6.627-5.373-12-12-12z" fill="${color}" filter="url(#shadow)"/>
                <circle cx="12" cy="12" r="5" fill="#FFFFFF"/>
            </svg>`;
        return L.divIcon({
            html: svgIcon,
            className: 'custom-leaflet-marker',
            iconSize: [30, 42],
            iconAnchor: [15, 42],
            popupAnchor: [0, -38]
        });
    }

    // Initialize Leaflet Map
    function initMap() {
        if (!document.getElementById('reportMap')) return;

        // Check if Leaflet loaded
        if (typeof L === 'undefined') {
            console.error('Leaflet library is not available.');
            showFeedback('Map engine could not be loaded. You may enter coordinates manually or submit without GPS.', 'error');
            return;
        }

        map = L.map('reportMap', {
            zoomControl: true,
            scrollWheelZoom: true
        }).setView([DEFAULT_LAT, DEFAULT_LNG], DEFAULT_ZOOM);

        // Standard OpenStreetMap Tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        // Click on map to place or move marker (Option 2: Select on Map)
        map.on('click', function (e) {
            updateMarkerPosition(e.latlng.lat, e.latlng.lng, true);
            showFeedback('Pin placed at ' + e.latlng.lat.toFixed(5) + ', ' + e.latlng.lng.toFixed(5) + '. You can drag the pin to refine.', 'success');
        });

        // Trigger map invalidateSize to prevent rendering glitches
        setTimeout(function () {
            map.invalidateSize();
        }, 250);
    }

    // Update marker and coordinate fields
    function updateMarkerPosition(lat, lng, panTo = false) {
        lat = parseFloat(lat);
        lng = parseFloat(lng);

        latInput.value = lat.toFixed(6);
        lngInput.value = lng.toFixed(6);

        if (!marker) {
            marker = L.marker([lat, lng], {
                draggable: true,
                icon: createCustomPin('#16A078')
            }).addTo(map);

            marker.bindPopup('<b>Reported Damage Location</b><br>Drag to fine-tune').openPopup();

            // Dragend event listener
            marker.on('dragend', function (event) {
                const position = marker.getLatLng();
                latInput.value = position.lat.toFixed(6);
                lngInput.value = position.lng.toFixed(6);
                showFeedback('Position adjusted to: ' + position.lat.toFixed(5) + ', ' + position.lng.toFixed(5), 'info');
                marker.getPopup().setContent('<b>Adjusted Location</b><br>' + position.lat.toFixed(5) + ', ' + position.lng.toFixed(5)).openPopup();
            });
        } else {
            marker.setLatLng([lat, lng]);
            marker.getPopup().setContent('<b>Reported Damage Location</b><br>' + lat.toFixed(5) + ', ' + lng.toFixed(5));
        }

        if (panTo && map) {
            map.setView([lat, lng], Math.max(map.getZoom(), 15));
        }
    }

    // Option 1: Browser Geolocation
    if (btnGeolocate) {
        btnGeolocate.addEventListener('click', function () {
            if (!navigator.geolocation) {
                showFeedback('Geolocation is not supported by your browser. Please select location manually on the map.', 'error');
                return;
            }

            showFeedback('Detecting your GPS position... Please allow location access if prompted.', 'info');
            btnGeolocate.disabled = true;
            btnGeolocate.classList.add('loading');

            navigator.geolocation.getCurrentPosition(
                function (position) {
                    btnGeolocate.disabled = false;
                    btnGeolocate.classList.remove('loading');
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    const accuracy = Math.round(position.coords.accuracy || 0);

                    updateMarkerPosition(lat, lng, true);

                    let msg = `GPS location detected (accuracy within ~${accuracy}m).`;
                    if (accuracy > 30) {
                        msg += ' Feel free to drag the pin on the map to pinpoint the exact road spot.';
                    } else {
                        msg += ' Confirmed on map preview. Drag to adjust if necessary.';
                    }
                    showFeedback(msg, 'success');
                },
                function (error) {
                    btnGeolocate.disabled = false;
                    btnGeolocate.classList.remove('loading');
                    let errorMsg = '';
                    switch (error.code) {
                        case error.PERMISSION_DENIED:
                            errorMsg = 'GPS permission was denied. You can still select the exact road damage location by clicking on the map below.';
                            break;
                        case error.POSITION_UNAVAILABLE:
                            errorMsg = 'GPS location is currently unavailable. Please click on the map below to pinpoint the spot manually.';
                            break;
                        case error.TIMEOUT:
                            errorMsg = 'GPS request timed out. Please click anywhere on the map to set the location.';
                            break;
                        default:
                            errorMsg = 'Could not retrieve GPS location. Please manually click on the map to select the location.';
                    }
                    showFeedback(errorMsg, 'error');
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        });
    }

    // Option 2: Select on Map button
    if (btnManualSelect) {
        btnManualSelect.addEventListener('click', function () {
            if (map) {
                map.scrollWheelZoom.enable();
                const container = document.getElementById('reportMap');
                container.scrollIntoView({ behavior: 'smooth', block: 'center' });
                showFeedback('Click anywhere on the map below to drop the damage location pin.', 'info');
            }
        });
    }

    // Clear coordinates
    if (btnClearCoords) {
        btnClearCoords.addEventListener('click', function () {
            latInput.value = '';
            lngInput.value = '';
            if (marker && map) {
                map.removeLayer(marker);
                marker = null;
            }
            clearFeedback();
        });
    }

    // Image Upload Preview & Drag-Drop
    if (imageInput) {
        imageInput.addEventListener('change', function () {
            handleImageFile(this.files[0]);
        });

        const dropZone = document.getElementById('dropZone');
        if (dropZone) {
            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    dropZone.classList.add('drag-active');
                }, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    dropZone.classList.remove('drag-active');
                }, false);
            });

            dropZone.addEventListener('drop', (e) => {
                const dt = e.dataTransfer;
                const files = dt.files;
                if (files.length > 0) {
                    imageInput.files = files;
                    handleImageFile(files[0]);
                }
            }, false);
        }
    }

    function handleImageFile(file) {
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            alert('Please select a valid image file (PNG, JPG, JPEG, WEBP).');
            return;
        }

        const reader = new FileReader();
        reader.onload = function (e) {
            imagePreview.src = e.target.result;
            imagePreviewContainer.style.display = 'block';
            uploadPrompt.style.display = 'none';
        };
        reader.readAsDataURL(file);
    }

    if (removeImageBtn) {
        removeImageBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            imageInput.value = '';
            imagePreview.src = '#';
            imagePreviewContainer.style.display = 'none';
            uploadPrompt.style.display = 'flex';
        });
    }

    // Initialize Map
    initMap();
});

