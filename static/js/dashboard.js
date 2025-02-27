document.addEventListener('DOMContentLoaded', function() {
    const reelForm = document.getElementById('reelForm');
    const logContainer = document.getElementById('logContainer');
    const tasksList = document.getElementById('tasksList');

    // Handle form submission
    reelForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const urlInput = document.getElementById('url');
        
        try {
            const response = await fetch('/add_reel', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `url=${encodeURIComponent(urlInput.value)}`
            });
            
            const data = await response.json();
            
            if (response.ok) {
                urlInput.value = '';
                // Add new task to the list
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${urlInput.value}</td>
                    <td><span class="badge bg-warning">pending</span></td>
                    <td>${new Date().toISOString().slice(0, 19).replace('T', ' ')}</td>
                `;
                tasksList.insertBefore(row, tasksList.firstChild);
            } else {
                alert(data.error || 'Failed to add reel');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to add reel');
        }
    });

    // Setup SSE for live logs
    const evtSource = new EventSource('/stream_logs');
    evtSource.onmessage = function(event) {
        const logs = JSON.parse(event.data);
        logs.forEach(log => {
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry';
            logEntry.innerHTML = `
                <span class="log-timestamp">${log.timestamp}</span>
                <span class="log-level log-level-${log.level.toLowerCase()}">${log.level}</span>
                <span class="log-message">${log.message}</span>
            `;
            logContainer.insertBefore(logEntry, logContainer.firstChild);
            
            // Keep only the last 50 logs
            if (logContainer.children.length > 50) {
                logContainer.removeChild(logContainer.lastChild);
            }
        });
    };
});
