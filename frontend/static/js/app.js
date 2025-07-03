class GeospatialAnalyzer {
    constructor() {
        this.currentJobId = null;
        this.map = null;
        this.init();
    }

    init() {
        this.initEventListeners();
        this.initMap();
        this.loadData();
        this.loadJobs();
    }

    initEventListeners() {
        // Query submission
        document.getElementById('submit-query').addEventListener('click', () => {
            this.submitQuery();
        });

        // Enter key in textarea
        document.getElementById('query-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                this.submitQuery();
            }
        });

        // File upload
        document.getElementById('upload-btn').addEventListener('click', () => {
            this.uploadFiles();
        });

        // Auto-refresh job status
        setInterval(() => {
            if (this.currentJobId) {
                this.checkJobStatus(this.currentJobId);
            }
        }, 2000);
    }

    initMap() {
        this.map = L.map('map').setView([40.7128, -74.0060], 10);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.map);
    }

    async submitQuery() {
        const query = document.getElementById('query-input').value.trim();
        if (!query) {
            alert('Please enter a query');
            return;
        }

        this.showLoading('Submitting query...');

        try {
            const response = await fetch('/api/jobs/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query })
            });

            const result = await response.json();
            
            if (response.ok) {
                this.currentJobId = result.job_id;
                this.updateLoadingStatus('Processing query...');
                this.startJobStatusMonitoring(result.job_id);
            } else {
                this.hideLoading();
                alert('Error: ' + result.detail);
            }
        } catch (error) {
            this.hideLoading();
            console.error('Error:', error);
            alert('Failed to submit query');
        }
    }

    async startJobStatusMonitoring(jobId) {
        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/jobs/${jobId}`);
                const job = await response.json();

                if (response.ok) {
                    this.updateJobDisplay(job);
                    
                    if (job.status === 'completed') {
                        this.hideLoading();
                        this.displayResults(job);
                        this.loadJobs(); // Refresh jobs list
                    } else if (job.status === 'failed') {
                        this.hideLoading();
                        this.displayError(job.error_message);
                        this.loadJobs(); // Refresh jobs list
                    } else {
                        // Continue monitoring
                        setTimeout(checkStatus, 2000);
                    }
                } else {
                    this.hideLoading();
                    alert('Error checking job status');
                }
            } catch (error) {
                this.hideLoading();
                console.error('Error checking job status:', error);
            }
        };

        checkStatus();
    }

    updateJobDisplay(job) {
        // Update loading status
        const statusMap = {
            'pending': 'Job queued...',
            'processing': 'Processing...',
            'completed': 'Analysis complete!',
            'failed': 'Analysis failed'
        };

        this.updateLoadingStatus(statusMap[job.status] || 'Processing...');

        // Update plan display
        if (job.plan) {
            this.displayPlan(job.plan);
        }

        // Update code display
        if (job.code) {
            this.displayCode(job.code);
        }
    }

    displayResults(job) {
        const container = document.getElementById('results-container');
        
        if (job.result) {
            let resultHtml = '<div class="results-content">';
            
            if (job.result.type === 'GeoDataFrame') {
                resultHtml += `
                    <h4><i class="fas fa-table"></i> Analysis Results</h4>
                    <div class="result-summary">
                        <p><strong>Type:</strong> ${job.result.type}</p>
                        <p><strong>Shape:</strong> ${job.result.shape[0]} rows, ${job.result.shape[1]} columns</p>
                        <p><strong>CRS:</strong> ${job.result.crs || 'Not specified'}</p>
                        <p><strong>Columns:</strong> ${job.result.columns.join(', ')}</p>
                    </div>
                `;

                // Display data on map if available
                if (job.result.data) {
                    this.displayOnMap(job.result.data);
                }
            } else {
                resultHtml += `
                    <h4><i class="fas fa-check-circle"></i> Analysis Complete</h4>
                    <pre class="result-data">${JSON.stringify(job.result, null, 2)}</pre>
                `;
            }

            resultHtml += '</div>';
            container.innerHTML = resultHtml;
        }

        // Switch to results tab
        this.showTab('results');
    }

    displayPlan(plan) {
        const container = document.getElementById('plan-container');
        
        let planHtml = '<div class="plan-content">';
        planHtml += `<h4><i class="fas fa-lightbulb"></i> Analysis Plan</h4>`;
        planHtml += `<p><strong>Type:</strong> ${plan.analysis_type}</p>`;
        planHtml += `<p><strong>Expected Output:</strong> ${plan.expected_output}</p>`;
        
        if (plan.steps && plan.steps.length > 0) {
            planHtml += '<h5>Steps:</h5>';
            plan.steps.forEach(step => {
                planHtml += `
                    <div class="plan-step">
                        <h4>Step ${step.step_number}: ${step.operation}</h4>
                        <p>${step.description}</p>
                        <p><strong>Parameters:</strong> ${JSON.stringify(step.parameters)}</p>
                    </div>
                `;
            });
        }
        
        planHtml += '</div>';
        container.innerHTML = planHtml;
    }

    displayCode(code) {
        const container = document.getElementById('code-container');
        container.innerHTML = `
            <div class="code-content">
                <h4><i class="fas fa-code"></i> Generated Code</h4>
                <div class="code-display">
                    <pre>${this.escapeHtml(code)}</pre>
                </div>
            </div>
        `;
    }

    displayOnMap(geoJsonData) {
        try {
            const geoData = typeof geoJsonData === 'string' ? JSON.parse(geoJsonData) : geoJsonData;
            
            // Clear existing layers
            this.map.eachLayer(layer => {
                if (layer instanceof L.GeoJSON) {
                    this.map.removeLayer(layer);
                }
            });

            // Add new data
            const geoJsonLayer = L.geoJSON(geoData, {
                style: {
                    color: '#667eea',
                    weight: 2,
                    fillColor: '#667eea',
                    fillOpacity: 0.3
                },
                onEachFeature: (feature, layer) => {
                    if (feature.properties) {
                        let popupContent = '<div class="popup-content">';
                        Object.entries(feature.properties).forEach(([key, value]) => {
                            popupContent += `<p><strong>${key}:</strong> ${value}</p>`;
                        });
                        popupContent += '</div>';
                        layer.bindPopup(popupContent);
                    }
                }
            }).addTo(this.map);

            // Fit map to bounds
            this.map.fitBounds(geoJsonLayer.getBounds());
        } catch (error) {
            console.error('Error displaying on map:', error);
        }
    }

    displayError(errorMessage) {
        const container = document.getElementById('results-container');
        container.innerHTML = `
            <div class="error-content">
                <h4><i class="fas fa-exclamation-triangle"></i> Analysis Failed</h4>
                <p class="error-message">${errorMessage}</p>
            </div>
        `;
        this.showTab('results');
    }

    async uploadFiles() {
        const fileInput = document.getElementById('file-input');
        const files = fileInput.files;
        
        if (files.length === 0) {
            alert('Please select files to upload');
            return;
        }

        const statusDiv = document.getElementById('upload-status');
        statusDiv.innerHTML = '<p>Uploading files...</p>';

        for (let file of files) {
            try {
                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch('/api/data/upload', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (response.ok) {
                    statusDiv.innerHTML += `<p style="color: green;">✓ ${file.name} uploaded successfully</p>`;
                } else {
                    statusDiv.innerHTML += `<p style="color: red;">✗ ${file.name} failed: ${result.detail}</p>`;
                }
            } catch (error) {
                statusDiv.innerHTML += `<p style="color: red;">✗ ${file.name} failed: ${error.message}</p>`;
            }
        }

        // Refresh data list
        this.loadData();
        
        // Clear file input
        fileInput.value = '';
    }

    async loadData() {
        try {
            const response = await fetch('/api/data/');
            const data = await response.json();
            
            const container = document.getElementById('data-list');
            
            if (data.length === 0) {
                container.innerHTML = '<p>No data uploaded yet</p>';
                return;
            }

            let html = '';
            data.forEach(item => {
                html += `
                    <div class="data-item">
                        <h4>${item.name}</h4>
                        <p><strong>Type:</strong> ${item.data_type}</p>
                        <small>Uploaded: ${new Date(item.created_at).toLocaleString()}</small>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        } catch (error) {
            console.error('Error loading data:', error);
        }
    }

    async loadJobs() {
        try {
            const response = await fetch('/api/jobs/');
            const jobs = await response.json();
            
            const container = document.getElementById('jobs-list');
            
            if (jobs.length === 0) {
                container.innerHTML = '<p>No jobs yet</p>';
                return;
            }

            let html = '';
            jobs.slice(0, 10).forEach(job => {
                html += `
                    <div class="job-item">
                        <h4>${job.query.substring(0, 50)}${job.query.length > 50 ? '...' : ''}</h4>
                        <p><span class="status-indicator status-${job.status}">${job.status}</span></p>
                        <small>Created: ${new Date(job.created_at).toLocaleString()}</small>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        } catch (error) {
            console.error('Error loading jobs:', error);
        }
    }

    async checkJobStatus(jobId) {
        try {
            const response = await fetch(`/api/jobs/${jobId}`);
            const job = await response.json();
            
            if (response.ok && job.status === 'completed') {
                this.displayResults(job);
                this.currentJobId = null;
            }
        } catch (error) {
            console.error('Error checking job status:', error);
        }
    }

    showTab(tabName) {
        // Hide all tabs
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Remove active class from all tab buttons
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active');
        });
        
        // Show selected tab
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        // Add active class to corresponding button
        document.querySelector(`button[onclick="showTab('${tabName}')"]`).classList.add('active');
        
        // Refresh map if showing map tab
        if (tabName === 'map' && this.map) {
            setTimeout(() => {
                this.map.invalidateSize();
            }, 100);
        }
    }

    showLoading(message) {
        const overlay = document.getElementById('loading-overlay');
        const status = document.getElementById('loading-status');
        status.textContent = message;
        overlay.classList.remove('hidden');
    }

    updateLoadingStatus(message) {
        const status = document.getElementById('loading-status');
        status.textContent = message;
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        overlay.classList.add('hidden');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global function for tab switching
function showTab(tabName) {
    if (window.analyzer) {
        window.analyzer.showTab(tabName);
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    window.analyzer = new GeospatialAnalyzer();
});