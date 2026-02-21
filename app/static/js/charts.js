// Chart colors for blood groups
const BLOOD_COLORS = [
    '#dc3545', '#fd7e14', '#0d6efd', '#20c997',
    '#198754', '#6610f2', '#ffc107', '#e83e8c'
];

// Initialize blood inventory charts
function initializeBloodCharts(bloodGroups, bloodUnits) {
    // Pie Chart Configuration
    const pieConfig = {
        type: 'pie',
        data: {
            labels: bloodGroups,
            datasets: [{
                data: bloodUnits,
                backgroundColor: BLOOD_COLORS
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${context.label}: ${value} units (${percentage}%)`;
                        }
                    }
                }
            }
        }
    };

    // Bar Chart Configuration
    const barConfig = {
        type: 'bar',
        data: {
            labels: bloodGroups,
            datasets: [{
                label: 'Units Available',
                data: bloodUnits,
                backgroundColor: BLOOD_COLORS
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.raw} units`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Units Available'
                    }
                }
            }
        }
    };

    // Initialize Charts
    const pieCtx = document.getElementById('inventory-pie-chart');
    const barCtx = document.getElementById('inventory-bar-chart');

    if (pieCtx) {
        new Chart(pieCtx, pieConfig);
    }

    if (barCtx) {
        new Chart(barCtx, barConfig);
    }
} 