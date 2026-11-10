/**
 * RoadWatch - Interactive Complaint Map & Geographic Heatmap
 */
document.addEventListener('DOMContentLoaded', function () {
    // Default coordinates: Mysuru, Karnataka, India
    const DEFAULT_LAT = 12.3051;
    const DEFAULT_LNG = 76.6551;
    const DEFAULT_ZOOM = 13;

    // Color definitions
    const STATUS_COLORS = {
        'Pending': '#F59E0B',    // Amber / Orange
        'In Progress': '#3B82F6', // Vibrant Blue
        'Resolved': '#10B981'    // Emerald Green
    };

    let map = null;
    let markersLayer = L.layerGroup();
    let heatmapLayer = null;
    let currentMode = 'markers'; // 'markers' or 'heatmap'
    let complaintsData = [];

    // DOM Elements
    const filterStatus = document.getElementById('filterStatus');
    const filterCategory = document.getElementById('filterCategory');
    const filterPriority = document.getElementById('filterPriority');
    const btnResetFilters = document.getElementById('btnResetFilters');
    const btnViewMarkers = document.getElementById('btnViewMarkers');
    const btnViewHeatmap = document.getElementById('btnViewHeatmap');
    const mapResultsCount = document.getElementById('mapResultsCount');
    const countPending = document.getElementById('countPending');
    const countInProgress = document.getElementById('countInProgress');
    const countResolved = document.getElementById('countResolved');
    const legendMarkers = document.getElementById('legendMarkers');
    const legendHeatmap = document.getElementById('legendHeatmap');
    const loadingOverlay = document.getElementById('mapLoadingOverlay');

    // Helper: Create colored SVG Map Pin
    function createMarkerIcon(status) {
        const color = STATUS_COLORS[status] || '#718096';
        const svg = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="30" height="42">
                <defs>
                    <filter id="shadow-${status.replace(/\s+/g, '')}" x="-20%" y="-10%" width="140%" height="140%">
                        <feDropShadow dx="0" dy="3" stdDeviation="2" flood-color="#101D2E" flood-opacity="0.3"/>
                    </filter>
                </defs>
                <path d="M12 0C5.373 0 0 5.373 0 12c0 9 12 24 12 24s12-15 12-24c0-6.627-5.373-12-12-12z" fill="${color}" filter="url(#shadow-${status.replace(/\s+/g, '')})"/>
                <circle cx="12" cy="12" r="5" fill="#FFFFFF"/>
            </svg>`;
        return L.divIcon({
            html: svg,
            className: 'custom-map-pin',
            iconSize: [30, 42],
            iconAnchor: [15, 42],
            popupAnchor: [0, -38]
        });
    }

    // Helper: Build rich popup content
    function createPopupContent(c) {
        const statusClass = (c.status || '').toLowerCase().replace(/\s+/g, '-');
        const priorityClass = (c.priority || 'Medium').toLowerCase();
        const dateStr = c.created_at ? c.created_at.substring(0, 16) : 'Recently reported';

        let imageHtml = '';
        if (c.image_url) {
            imageHtml = `
                <div class="popup-image-wrap">
                    <img src="${c.image_url}" alt="Report photo" class="popup-thumb" onclick="window.open('${c.image_url}', '_blank')"/>
                </div>`;
        }

        const originTag = c.is_demo 
            ? '<span class="origin-badge origin-demo">📌 Demo Data</span>' 
            : '<span class="origin-badge origin-citizen">👤 Citizen Report</span>';

        return `
            <div class="rw-map-popup">
                <div class="popup-header">
                    <span class="popup-id">#RW-${c.id}</span>
                    <div class="popup-badges">
                        ${originTag}
                        <span class="status-badge status-${statusClass}">${c.status}</span>
                    </div>
                </div>
                <h4 class="popup-type">${c.damage_type}</h4>
                <div class="popup-location">📍 ${c.location}</div>
                ${c.description ? `<p class="popup-desc">${escapeHtml(c.description)}</p>` : ''}
                ${imageHtml}
                <div class="popup-meta">
                    <span class="priority-pill priority-${priorityClass}">Priority: ${c.priority || 'Medium'}</span>
                    <span class="popup-date">${dateStr}</span>
                </div>
            </div>`;
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // Initialize Leaflet Map
    function initMap() {
        if (!document.getElementById('exploreMap')) return;

        // Check URL params for centered coordinates
        const urlParams = new URLSearchParams(window.location.search);
        const paramLat = parseFloat(urlParams.get('lat'));
        const paramLng = parseFloat(urlParams.get('lng'));
        const paramZoom = parseInt(urlParams.get('zoom')) || DEFAULT_ZOOM;

        const initialLat = !isNaN(paramLat) ? paramLat : DEFAULT_LAT;
        const initialLng = !isNaN(paramLng) ? paramLng : DEFAULT_LNG;

        map = L.map('exploreMap', {
            zoomControl: true,
            scrollWheelZoom: true
        }).setView([initialLat, initialLng], paramZoom);

        // Standard OpenStreetMap Tile Layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        markersLayer.addTo(map);

        // Fetch data
        fetchComplaints();
    }

    // Fetch complaints from backend API
    function fetchComplaints() {
        if (loadingOverlay) loadingOverlay.style.display = 'flex';

        fetch('/api/complaints')
            .then(res => {
                if (!res.ok) throw new Error('Network error loading complaints');
                return res.json();
            })
            .then(data => {
                complaintsData = data;
                renderMapLayers();
                if (loadingOverlay) loadingOverlay.style.display = 'none';
            })
            .catch(err => {
                console.error('Error fetching complaints:', err);
                if (mapResultsCount) mapResultsCount.textContent = 'Error loading complaint data.';
                if (loadingOverlay) loadingOverlay.style.display = 'none';
            });
    }

    // Filter complaints based on UI selections
    function getFilteredComplaints() {
        const selectedStatus = filterStatus ? filterStatus.value : 'ALL';
        const selectedCategory = filterCategory ? filterCategory.value : 'ALL';
        const selectedPriority = filterPriority ? filterPriority.value : 'ALL';

        return complaintsData.filter(c => {
            // Must have valid coordinates
            if (c.latitude === null || c.longitude === null) return false;

            // Status filter
            if (selectedStatus !== 'ALL' && c.status !== selectedStatus) return false;

            // Category filter
            if (selectedCategory !== 'ALL' && c.damage_type !== selectedCategory) return false;

            // Priority filter
            if (selectedPriority !== 'ALL' && c.priority !== selectedPriority) return false;

            return true;
        });
    }

    // Render Markers or Heatmap based on mode
    function renderMapLayers() {
        const filtered = getFilteredComplaints();

        // Update counts
        let pending = 0, inProg = 0, resolved = 0;
        filtered.forEach(c => {
            if (c.status === 'Pending') pending++;
            else if (c.status === 'In Progress') inProg++;
            else if (c.status === 'Resolved') resolved++;
        });

        if (countPending) countPending.textContent = pending;
        if (countInProgress) countInProgress.textContent = inProg;
        if (countResolved) countResolved.textContent = resolved;
        if (mapResultsCount) {
            mapResultsCount.innerHTML = `Displaying <b>${filtered.length}</b> verified damage locations`;
        }

        // Clear existing layers
        markersLayer.clearLayers();
        if (heatmapLayer && map.hasLayer(heatmapLayer)) {
            map.removeLayer(heatmapLayer);
            heatmapLayer = null;
        }

        if (filtered.length === 0) {
            return;
        }

        const latLngBounds = [];

        if (currentMode === 'markers') {
            // Render individual markers
            filtered.forEach(c => {
                const marker = L.marker([c.latitude, c.longitude], {
                    icon: createMarkerIcon(c.status)
                });
                marker.bindPopup(createPopupContent(c), { maxWidth: 320 });
                markersLayer.addLayer(marker);
                latLngBounds.push([c.latitude, c.longitude]);
            });
        } else if (currentMode === 'heatmap') {
            // Render heatmap using L.heatLayer
            const heatPoints = filtered.map(c => {
                latLngBounds.push([c.latitude, c.longitude]);
                // Weight intensity by severity
                let intensity = 0.6;
                if (c.priority === 'High') intensity = 1.0;
                else if (c.priority === 'Medium') intensity = 0.7;
                return [c.latitude, c.longitude, intensity];
            });

            if (typeof L.heatLayer === 'function') {
                heatmapLayer = L.heatLayer(heatPoints, {
                    radius: 28,
                    blur: 18,
                    maxZoom: 16,
                    max: 1.0,
                    gradient: {
                        0.2: '#10B981', // green
                        0.5: '#F59E0B', // amber
                        0.8: '#EF4444', // red
                        1.0: '#991B1B'  // dark red (extreme density)
                    }
                }).addTo(map);
            } else {
                console.warn('Leaflet.heat plugin is not loaded. Falling back to markers.');
                currentMode = 'markers';
                renderMapLayers();
                return;
            }
        }

        // If not centered by explicit URL params, fit map to points
        const urlParams = new URLSearchParams(window.location.search);
        if (!urlParams.get('lat') && latLngBounds.length > 0) {
            try {
                map.fitBounds(latLngBounds, { padding: [40, 40], maxZoom: 15 });
            } catch (e) {
                // Ignore bounds error if points are single location
            }
        }
    }

    // Switch view mode
    function setViewMode(mode) {
        currentMode = mode;
        if (mode === 'markers') {
            btnViewMarkers.classList.add('active');
            btnViewHeatmap.classList.remove('active');
            if (legendMarkers) legendMarkers.style.display = 'block';
            if (legendHeatmap) legendHeatmap.style.display = 'none';
        } else {
            btnViewHeatmap.classList.add('active');
            btnViewMarkers.classList.remove('active');
            if (legendMarkers) legendMarkers.style.display = 'none';
            if (legendHeatmap) legendHeatmap.style.display = 'block';
        }
        renderMapLayers();
    }

    // Event Listeners
    if (btnViewMarkers) {
        btnViewMarkers.addEventListener('click', () => setViewMode('markers'));
    }
    if (btnViewHeatmap) {
        btnViewHeatmap.addEventListener('click', () => setViewMode('heatmap'));
    }

    if (filterStatus) filterStatus.addEventListener('change', renderMapLayers);
    if (filterCategory) filterCategory.addEventListener('change', renderMapLayers);
    if (filterPriority) filterPriority.addEventListener('change', renderMapLayers);

    if (btnResetFilters) {
        btnResetFilters.addEventListener('click', () => {
            if (filterStatus) filterStatus.value = 'ALL';
            if (filterCategory) filterCategory.value = 'ALL';
            if (filterPriority) filterPriority.value = 'ALL';
            renderMapLayers();
        });
    }

    // Initialize
    initMap();
});

