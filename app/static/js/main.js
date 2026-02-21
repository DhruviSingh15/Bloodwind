// Main JavaScript for Blood Donation System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);

    // Donation request form validation
    const donationForm = document.getElementById('donation-request-form');
    if (donationForm) {
        donationForm.addEventListener('submit', function(event) {
            const isEligible = donationForm.getAttribute('data-eligible') === 'true';
            if (!isEligible) {
                event.preventDefault();
                alert('You are not eligible to donate blood at this time.');
            }
        });
    }

    // Blood inventory adjustment
    const adjustmentForms = document.querySelectorAll('.inventory-adjustment-form');
    adjustmentForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const inventoryId = this.getAttribute('data-inventory-id');
            const units = this.querySelector('input[name="units"]').value;
            
            fetch(`/hospital/inventory/update/${inventoryId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: `units=${units}`
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById(`inventory-units-${inventoryId}`).textContent = data.units;
                    alert('Inventory updated successfully!');
                } else {
                    alert('Error updating inventory: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while updating inventory.');
            });
        });
    });

    // Fetch notification count for donors
    const notificationBadge = document.querySelector('.notification-badge');
    if (notificationBadge) {
        fetch('/donor/notifications/count')
            .then(response => response.json())
            .then(data => {
                if (data.count > 0) {
                    notificationBadge.textContent = data.count;
                }
            })
            .catch(error => console.error('Error fetching notifications:', error));
    }

    // Fetch pending donation count for hospitals
    const pendingBadge = document.querySelector('.pending-badge');
    if (pendingBadge) {
        fetch('/hospital/donations/pending/count')
            .then(response => response.json())
            .then(data => {
                if (data.count > 0) {
                    pendingBadge.textContent = data.count;
                }
            })
            .catch(error => console.error('Error fetching pending donations:', error));
    }

    // Eligibility checker on donor dashboard
    const eligibilityChecker = document.getElementById('eligibility-checker');
    if (eligibilityChecker) {
        const ageInput = document.getElementById('age');
        const weightInput = document.getElementById('weight');
        const lastDonationInput = document.getElementById('last-donation');
        const checkButton = document.getElementById('check-eligibility');
        const resultDiv = document.getElementById('eligibility-result');
        
        checkButton.addEventListener('click', function() {
            const age = parseInt(ageInput.value);
            const weight = parseFloat(weightInput.value);
            const lastDonation = lastDonationInput.value ? new Date(lastDonationInput.value) : null;
            
            let isEligible = true;
            let message = '';
            
            // Check age
            if (age < 18) {
                isEligible = false;
                message += 'You must be at least 18 years old to donate blood.<br>';
            }
            
            // Check weight
            if (weight < 50) {
                isEligible = false;
                message += 'You must weigh at least 50 kg to donate blood.<br>';
            }
            
            // Check last donation date
            if (lastDonation) {
                const today = new Date();
                const daysSinceLastDonation = Math.floor((today - lastDonation) / (1000 * 60 * 60 * 24));
                
                if (daysSinceLastDonation < 180) {
                    isEligible = false;
                    message += `You must wait ${180 - daysSinceLastDonation} more days before donating again.<br>`;
                }
            }
            
            // Display result
            resultDiv.innerHTML = '';
            resultDiv.classList.remove('eligible', 'not-eligible');
            
            if (isEligible) {
                resultDiv.classList.add('eligible');
                resultDiv.innerHTML = '<i class="fas fa-check-circle"></i> You are eligible to donate blood!';
            } else {
                resultDiv.classList.add('not-eligible');
                resultDiv.innerHTML = `<i class="fas fa-times-circle"></i> You are not eligible to donate blood:<br>${message}`;
            }
        });
    }

    // Blood inventory charts for hospital dashboard
    const inventoryChart = document.getElementById('inventory-chart');
    if (inventoryChart) {
        const ctx = inventoryChart.getContext('2d');
        
        // Get data from the page
        const bloodGroups = JSON.parse(inventoryChart.getAttribute('data-blood-groups'));
        const units = JSON.parse(inventoryChart.getAttribute('data-units'));
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: bloodGroups,
                datasets: [{
                    label: 'Units Available',
                    data: units,
                    backgroundColor: [
                        '#28a745', // A+
                        '#20c997', // A-
                        '#fd7e14', // B+
                        '#ffc107', // B-
                        '#6f42c1', // AB+
                        '#6610f2', // AB-
                        '#dc3545', // O+
                        '#e83e8c'  // O-
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Units'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Blood Group'
                        }
                    }
                }
            }
        });
    }

    // Donation trend chart for admin dashboard
    const trendChart = document.getElementById('donation-trend-chart');
    if (trendChart) {
        const ctx = trendChart.getContext('2d');
        
        // Get data from the page
        const dates = JSON.parse(trendChart.getAttribute('data-dates'));
        const counts = JSON.parse(trendChart.getAttribute('data-counts'));
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Donations',
                    data: counts,
                    backgroundColor: 'rgba(220, 53, 69, 0.2)',
                    borderColor: '#dc3545',
                    borderWidth: 2,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Donations'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    }
                }
            }
        });
    }
});
