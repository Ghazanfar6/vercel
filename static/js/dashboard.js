document.addEventListener('DOMContentLoaded', function() {
    const reelForm = document.getElementById('reelForm');
    const logContainer = document.getElementById('logContainer');
    const tasksList = document.getElementById('tasksList');

    // Set minimum datetime-local to current time
    const scheduledForInput = document.getElementById('scheduledFor');
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    scheduledForInput.min = now.toISOString().slice(0, 16);

    // Handle form submission
    reelForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const urlInput = document.getElementById('url');
        const scheduledForInput = document.getElementById('scheduledFor');
        const repeatIntervalInput = document.getElementById('repeatInterval');

        const formData = new FormData();
        formData.append('url', urlInput.value);
        if (scheduledForInput.value) {
            formData.append('scheduled_for', scheduledForInput.value);
        }
        if (repeatIntervalInput.value) {
            formData.append('repeat_interval', repeatIntervalInput.value);
        }

        try {
            const response = await fetch('/add_reel', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                // Clear form
                urlInput.value = '';
                scheduledForInput.value = '';
                repeatIntervalInput.value = '';

                // Add new task to the list
                const scheduledTime = data.scheduled_for ? new Date(data.scheduled_for).toLocaleString() : 'ASAP';
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${data.url}</td>
                    <td><span class="badge bg-warning">pending</span></td>
                    <td>${scheduledTime}</td>
                    <td>${data.repeat_interval || 'No'}</td>
                    <td>${new Date().toLocaleString()}</td>
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