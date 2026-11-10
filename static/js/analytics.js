/**
 * RoadWatch - Analytics & Heatmap Dashboard Logic
 */
document.addEventListener('DOMContentLoaded', function () {
    // Default coordinates: Mysuru, Karnataka, India
    const DEFAULT_LAT = 12.3051;
    const DEFAULT_LNG = 76.6551;
    const DEFAULT_ZOOM = 13;

    // Brand Palette
    const COLORS = {
        navy: '#101D2E',
        green: '#16A078',
        greenLight: '#48D6A4',
        amber: '#F59E0B',
        blue: '#3B82F6',
        red: '#EF4444',
        purple: '#8B5CF6',
        pink: '#EC4899',
        border: '#E5ECE9'
    };

    let chartStatusInstance = null;
    let chartCategoryInstance = null;
    let chartTrendsInstance = null;
    let chartComparisonInstance = null;

    let analyticsMap = null;
    let analyticsHeatmapLayer = null;
    let analyticsMarkersLayer = L.layerGroup();
    let currentMapMode = 'heatmap'; // 'heatmap' or 'markers'

    // DOM Elements
    const form = document.getElementById('analyticsFilterForm');
    const filterStartDate = document.getElementById('filterStartDate');
    const filterEndDate = document.getElementById('filterEndDate');
    const filterStatus = document.getElementById('filterStatus');
    const filterCategory = document.getElementById('filterCategory');
    const btnReset = document.getElementById('btnResetAnalyticsFilters');
    const btnHeatmap = document.getElementById('btnAnalyticsHeatmap');
    const btnMarkers = document.getElementById('btnAnalyticsMarkers');

    // Summary Metric Elements
    const valTotal = document.getElementById('valTotalComplaints');
    const valPending = document.getElementById('valPendingComplaints');
    const valInProgress = document.getElementById('valInProgressComplaints');
    const valResolved = document.getElementById('valResolvedComplaints');
    const valHighPriority = document.getElementById('valHighPriorityComplaints');
    const subPendingPct = document.getElementById('subPendingPct');
    const subInProgressPct = document.getElementById('subInProgressPct');
    const subResolvedPct = document.getElementById('subResolvedPct');

    // Initialize Map
    function initAnalyticsMap() {
        if (!document.getElementById('analyticsHeatmapMap')) return;

        analyticsMap = L.map('analyticsHeatmapMap', {
            zoomControl: true,
            scrollWheelZoom: false
        }).setView([DEFAULT_LAT, DEFAULT_LNG], DEFAULT_ZOOM);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(analyticsMap);

        analyticsMarkersLayer.addTo(analyticsMap);
    }

    // Helper: Map Pin SVG
    function createPin(status) {
        let color = COLORS.amber;
        if (status === 'In Progress') color = COLORS.blue;
        if (status === 'Resolved') color = COLORS.green;

        const svg = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="26" height="36">
                <path d="M12 0C5.373 0 0 5.373 0 12c0 9 12 24 12 24s12-15 12-24c0-6.627-5.373-12-12-12z" fill="${color}"/>
                <circle cx="12" cy="12" r="4.5" fill="#FFFFFF"/>
            </svg>`;
        return L.divIcon({
            html: svg,
            className: 'analytics-pin',
            iconSize: [26, 36],
            iconAnchor: [13, 36]
        });
    }

    // Initialize Charts
    function initCharts() {
        // Chart 1: Status (Doughnut)
        const ctxStatus = document.getElementById('chartStatus');
        if (ctxStatus) {
            chartStatusInstance = new Chart(ctxStatus, {
                type: 'doughnut',
                data: {
                    labels: ['Pending', 'In Progress', 'Resolved'],
                    datasets: [{
                        data: [0, 0, 0],
                        backgroundColor: [COLORS.amber, COLORS.blue, COLORS.green],
                        borderWidth: 2,
                        borderColor: '#FFFFFF',
                        hoverOffset: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { boxWidth: 12, padding: 16 } }
                    },
                    cutout: '68%'
                }
            });
        }

        // Chart 2: Category (Bar)
        const ctxCategory = document.getElementById('chartCategory');
        if (ctxCategory) {
            chartCategoryInstance = new Chart(ctxCategory, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Complaints',
                        data: [],
                        backgroundColor: [
                            COLORS.green,
                            COLORS.navy,
                            COLORS.blue,
                            COLORS.amber,
                            COLORS.purple,
                            COLORS.pink,
                            '#0D9488'
                        ],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { precision: 0 },
                            grid: { color: 'rgba(0,0,0,0.05)' }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { maxRotation: 30, minRotation: 0 }
                        }
                    }
                }
            });
        }

        // Chart 3: Monthly Trends (Line)
        const ctxTrends = document.getElementById('chartMonthlyTrends');
        if (ctxTrends) {
            chartTrendsInstance = new Chart(ctxTrends, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Reported Incidents',
                        data: [],
                        borderColor: COLORS.green,
                        backgroundColor: 'rgba(22, 160, 120, 0.12)',
                        fill: true,
                        tension: 0.35,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        pointBackgroundColor: COLORS.green
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { precision: 0 },
                            grid: { color: 'rgba(0,0,0,0.05)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }

        // Chart 4: Resolved vs Pending (Bar)
        const ctxComparison = document.getElementById('chartResolvedPending');
        if (ctxComparison) {
            chartComparisonInstance = new Chart(ctxComparison, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Resolved',
                            data: [],
                            backgroundColor: COLORS.green,
                            borderRadius: 6
                        },
                        {
                            label: 'Pending / Backlog',
                            data: [],
                            backgroundColor: COLORS.amber,
                            borderRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { boxWidth: 12, padding: 14 } }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { precision: 0 },
                            grid: { color: 'rgba(0,0,0,0.05)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }
    }

    // Fetch and apply analytics data
    window.applyFilters = function () {
        const params = new URLSearchParams();
        if (filterStartDate && filterStartDate.value) params.append('start_date', filterStartDate.value);
        if (filterEndDate && filterEndDate.value) params.append('end_date', filterEndDate.value);
        if (filterStatus && filterStatus.value !== 'ALL') params.append('status', filterStatus.value);
        if (filterCategory && filterCategory.value !== 'ALL') params.append('category', filterCategory.value);

        const queryString = params.toString();

        // 1. Fetch Analytics Aggregations
        fetch('/api/admin/analytics?' + queryString)
            .then(res => res.json())
            .then(data => {
                updateSummaryCards(data.summary);
                updateCharts(data);
            })
            .catch(err => console.error('Error fetching analytics:', err));

        // 2. Fetch Filtered Complaints for Heatmap
        fetch('/api/complaints?' + queryString)
            .then(res => res.json())
            .then(complaints => {
                updateHeatmapLayer(complaints);
            })
            .catch(err => console.error('Error fetching complaints for heatmap:', err));
    };

    function updateSummaryCards(summary) {
        if (!summary) return;
        const total = summary.total || 0;
        const pending = summary.pending || 0;
        const inProgress = summary.in_progress || 0;
        const resolved = summary.resolved || 0;
        const highPriority = summary.high_priority || 0;

        if (valTotal) valTotal.textContent = total;
        if (valPending) valPending.textContent = pending;
        if (valInProgress) valInProgress.textContent = inProgress;
        if (valResolved) valResolved.textContent = resolved;
        if (valHighPriority) valHighPriority.textContent = highPriority;

        const pendingPct = total > 0 ? Math.round((pending / total) * 100) : 0;
        const inProgPct = total > 0 ? Math.round((inProgress / total) * 100) : 0;
        const resolvedPct = total > 0 ? Math.round((resolved / total) * 100) : 0;

        if (subPendingPct) subPendingPct.textContent = `${pendingPct}% of filtered`;
        if (subInProgressPct) subInProgressPct.textContent = `${inProgPct}% of filtered`;
        if (subResolvedPct) subResolvedPct.textContent = `${resolvedPct}% resolution rate`;
    }

    function updateCharts(data) {
        // Update Chart 1: Status
        if (chartStatusInstance && data.by_status) {
            chartStatusInstance.data.labels = data.by_status.labels;
            chartStatusInstance.data.datasets[0].data = data.by_status.data;
            chartStatusInstance.update();
        }

        // Update Chart 2: Category
        if (chartCategoryInstance && data.by_category) {
            chartCategoryInstance.data.labels = data.by_category.labels;
            chartCategoryInstance.data.datasets[0].data = data.by_category.data;
            chartCategoryInstance.update();
        }

        // Update Chart 3: Monthly Trends
        if (chartTrendsInstance && data.monthly_trends) {
            chartTrendsInstance.data.labels = data.monthly_trends.labels;
            chartTrendsInstance.data.datasets[0].data = data.monthly_trends.data;
            chartTrendsInstance.update();
        }

        // Update Chart 4: Resolved vs Pending
        if (chartComparisonInstance && data.resolved_vs_pending) {
            chartComparisonInstance.data.labels = data.resolved_vs_pending.labels;
            chartComparisonInstance.data.datasets[0].data = data.resolved_vs_pending.resolved;
            chartComparisonInstance.data.datasets[1].data = data.resolved_vs_pending.pending;
            chartComparisonInstance.update();
        }
    }

    function updateHeatmapLayer(complaints) {
        if (!analyticsMap) return;

        // Clear existing
        analyticsMarkersLayer.clearLayers();
        if (analyticsHeatmapLayer && analyticsMap.hasLayer(analyticsHeatmapLayer)) {
            analyticsMap.removeLayer(analyticsHeatmapLayer);
            analyticsHeatmapLayer = null;
        }

        const validCoords = complaints.filter(c => c.latitude !== null && c.longitude !== null);
        if (validCoords.length === 0) return;

        const bounds = [];

        if (currentMapMode === 'heatmap') {
            const heatData = validCoords.map(c => {
                bounds.push([c.latitude, c.longitude]);
                const intensity = c.priority === 'High' ? 1.0 : (c.priority === 'Medium' ? 0.7 : 0.4);
                return [c.latitude, c.longitude, intensity];
            });

            if (typeof L.heatLayer === 'function') {
                analyticsHeatmapLayer = L.heatLayer(heatData, {
                    radius: 30,
                    blur: 20,
                    maxZoom: 16,
                    max: 1.0,
                    gradient: {
                        0.2: '#10B981',
                        0.5: '#F59E0B',
                        0.8: '#EF4444',
                        1.0: '#991B1B'
                    }
                }).addTo(analyticsMap);
            }
        } else {
            validCoords.forEach(c => {
                bounds.push([c.latitude, c.longitude]);
                const marker = L.marker([c.latitude, c.longitude], {
                    icon: createPin(c.status)
                });
                marker.bindPopup(`<b>#RW-${c.id}: ${c.damage_type}</b><br>${c.location}<br>Status: ${c.status}`);
                analyticsMarkersLayer.addLayer(marker);
            });
        }

        if (bounds.length > 0) {
            try {
                analyticsMap.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });
            } catch (e) {}
        }
    }

    function setMapMode(mode) {
        currentMapMode = mode;
        if (mode === 'heatmap') {
            btnHeatmap.classList.add('active');
            btnMarkers.classList.remove('active');
        } else {
            btnMarkers.classList.add('active');
            btnHeatmap.classList.remove('active');
        }
        applyFilters();
    }

    if (btnHeatmap) btnHeatmap.addEventListener('click', () => setMapMode('heatmap'));
    if (btnMarkers) btnMarkers.addEventListener('click', () => setMapMode('markers'));

    if (btnReset) {
        btnReset.addEventListener('click', function () {
            if (filterStartDate) filterStartDate.value = '';
            if (filterEndDate) filterEndDate.value = '';
            if (filterStatus) filterStatus.value = 'ALL';
            if (filterCategory) filterCategory.value = 'ALL';
            applyFilters();
        });
    }

    // Start everything
    initAnalyticsMap();
    initCharts();
    applyFilters();
});

