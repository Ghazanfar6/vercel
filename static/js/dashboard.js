document.addEventListener('DOMContentLoaded', function() {
    const reelForm = document.getElementById('reelForm');
    const logContainer = document.getElementById('logContainer');
    const tasksList = document.getElementById('tasksList');
    const clearAllTasksBtn = document.getElementById('clearAllTasksBtn');

    // Convert all UTC timestamps to local time
    function convertTimestampsToLocalTime() {
        const timestampElements = document.querySelectorAll('.created-time');
        timestampElements.forEach(element => {
            const utcTimestamp = element.getAttribute('data-timestamp');
            if (utcTimestamp) {
                const localDate = new Date(utcTimestamp);
                element.textContent = localDate.toLocaleString();
            }
        });
    }

    // Delete task functionality
    function setupDeleteButtons() {
        const deleteButtons = document.querySelectorAll('.delete-task');
        deleteButtons.forEach(button => {
            button.addEventListener('click', async function() {
                const taskId = this.getAttribute('data-task-id');
                if (confirm('Are you sure you want to delete this task?')) {
                    try {
                        const response = await fetch(`/delete_task/${taskId}`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            }
                        });

                        const data = await response.json();
                        if (response.ok) {
                            // Remove the task row from the table
                            const row = document.querySelector(`tr[data-task-id="${taskId}"]`);
                            if (row) {
                                row.remove();
                            }
                        } else {
                            alert(`Error: ${data.error}`);
                        }
                    } catch (error) {
                        console.error('Error deleting task:', error);
                        alert('An error occurred while deleting the task.');
                    }
                }
            });
        });
    }

    // Initialize feather icons for the delete buttons
    function initFeatherIcons() {
        if (typeof feather !== 'undefined') {
            feather.replace();
        }peof feather !== 'undefined') {
            feather.replace();
        }
    }

    // Initial load of timestamps
    convertTimestampsToLocalTime();

    // Set up event listeners
    setupDeleteButtons();

    // Clear All Tasks functionality
    if (clearAllTasksBtn) {
        clearAllTasksBtn.addEventListener('click', async function() {
            if (confirm('Are you sure you want to delete ALL tasks? This cannot be undone.')) {
                try {
                    const response = await fetch('/clear_all_tasks', {
                        method: 'POST',
                    });

                    const data = await response.json();
                    if (response.ok) {
                        // Remove all task rows from the table
                        tasksList.innerHTML = '';
                        alert(`Successfully cleared ${data.count} tasks.`);
                    } else {
                        alert(`Error: ${data.error || 'Failed to clear tasks'}`);
                    }
                } catch (error) {
                    console.error('Error clearing tasks:', error);
                    alert('An error occurred while clearing tasks.');
                }
            }
        });
    } else {
        console.error('Clear All Tasks button not found in the DOM');
    }

    // Initialize feather icons
    initFeatherIcons();

    // Connect to task status updates stream with auto-reconnect
    let taskUpdateSource;

    function connectToTaskUpdates() {
        taskUpdateSource = new EventSource('/stream_task_updates');

        taskUpdateSource.onmessage = function(event) {
            const updates = JSON.parse(event.data);
            updates.forEach(update => {
                const taskRow = document.querySelector(`tr[data-task-id="${update.id}"]`);
                if (taskRow) {
                    const statusCell = taskRow.querySelector('td:nth-child(2)');
                    if (statusCell) {
                        const badgeClass = update.status === 'completed' ? 'success' : 
                                          update.status === 'failed' ? 'danger' : 'warning';
                        statusCell.innerHTML = `<span class="badge bg-${badgeClass}">${update.status}</span>`;
                    }
                }
            });
        };

        taskUpdateSource.onerror = function() {
            taskUpdateSource.close();
            setTimeout(connectToTaskUpdates, 5000); // Try to reconnect after 5 seconds
        };
    }

    // Connect to task updates
    connectToTaskUpdates();

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
                const currentTime = new Date();
                const row = document.createElement('tr');
                row.setAttribute('data-task-id', data.task_id);
                row.innerHTML = `
                    <td>${data.url}</td>
                    <td><span class="badge bg-warning">pending</span></td>
                    <td>${scheduledTime}</td>
                    <td>${data.repeat_interval || 'No'}</td>
                    <td class="created-time" data-timestamp="${currentTime.toISOString()}">${currentTime.toLocaleString()}</td>
                    <td>
                        <button class="btn btn-sm btn-danger delete-task" data-task-id="${data.task_id}">
                            <i data-feather="trash-2"></i> Delete
                        </button>
                    </td>
                `;
                tasksList.insertBefore(row, tasksList.firstChild);

                // Initialize feather icons for the new row
                if (typeof feather !== 'undefined') {
                    feather.replace();
                }

                // Setup delete button for the new row
                const newDeleteButton = row.querySelector('.delete-task');
                if (newDeleteButton) {
                    newDeleteButton.addEventListener('click', async function() {
                        const taskId = this.getAttribute('data-task-id');
                        if (confirm('Are you sure you want to delete this task?')) {
                            try {
                                const response = await fetch(`/delete_task/${taskId}`, {
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/json'
                                    }
                                });

                                const data = await response.json();
                                if (response.ok) {
                                    // Remove the task row from the table
                                    row.remove();
                                } else {
                                    alert(`Error: ${data.error}`);
                                }
                            } catch (error) {
                                console.error('Error deleting task:', error);
                                alert('An error occurred while deleting the task.');
                            }
                        }
                    });
                }
            } else {
                alert(data.error || 'Failed to add reel');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to add reel');
        }
    });

    // Setup SSE for live logs with auto-reconnect
    let evtSource;

    function connectToLogStream() {
        evtSource = new EventSource('/stream_logs');
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
        evtSource.onerror = function() {
            evtSource.close();
            setTimeout(connectToLogStream, 5000); // Try to reconnect after 5 seconds
        };
    }

    connectToLogStream();
});