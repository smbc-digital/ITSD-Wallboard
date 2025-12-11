const updateInterval = 10;
let timeLeft = updateInterval;
let countdownTimer;

function updateWallboard() {
    console.log('Fetching data...');
    fetch('https://xxxuuqounhnz2.execute-api.eu-west-2.amazonaws.com/Prod/wallboard', {
        method: 'GET',
        mode: 'cors',
        headers: {
            'Content-Type': 'application/json',
        },
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('HTTP error! status: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            console.log(data);
            const wallboardData = data;
            document.getElementById('callsHandled').textContent = wallboardData.CallsHandled;
            document.getElementById('callsInQueue').textContent = wallboardData.CallsInQueue;
            document.getElementById('callsAbandoned').textContent = wallboardData.CallsAbandoned;
            document.getElementById('longestWaitTime').textContent = formatTime(wallboardData.LongestWaitTime);
            document.getElementById('agentAnswerRate').textContent = formatPercentage(wallboardData.AgentAnswerRate);
            document.getElementById('averageContactDuration').textContent = formatDuration(wallboardData.AverageContactDuration);

            const customInfoElement = document.getElementById('customInformation');
            if (wallboardData.CustomInformation) {
                customInfoElement.textContent = wallboardData.CustomInformation;
                customInfoElement.style.display = 'block';
            } else {
                customInfoElement.style.display = 'none';
            }

            const agentStatusesList = document.getElementById('agentStatuses');
            agentStatusesList.innerHTML = '';

            const statusCounts = wallboardData.AgentStatuses.reduce((acc, status) => {
                acc[status] = (acc[status] || 0) + 1;
                return acc;
            }, {});

            for (const [status, count] of Object.entries(statusCounts)) {
                const li = document.createElement('li');
                li.innerHTML = '<span class="agent-count">' + count + '</span>' + status;
                agentStatusesList.appendChild(li);
            }

            timeLeft = updateInterval;
            updateCountdown();
        })
        .catch(error => console.error('Error fetching data:', error));
}

function formatTime(milliseconds) {
    if (milliseconds === undefined || milliseconds === null) return '-';

    const totalSeconds = Math.floor(milliseconds / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    return [hours, minutes, seconds]
        .map(v => v.toString().padStart(2, '0'))
        .join(':');
}

function formatDuration(seconds) {
    if (seconds === undefined || seconds === null) return '-';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = Math.floor(seconds % 60);

    return [hours, minutes, remainingSeconds]
        .map(v => v.toString().padStart(2, '0'))
        .join(':');
}

function formatPercentage(value) {
    if (value === undefined || value === null) return '-';
    return value.toFixed(2) + '%';
}

function updateCountdown() {
    const countdownElement = document.getElementById('countdown');
    countdownElement.textContent = 'Next update in ' + timeLeft + ' seconds';
    timeLeft--;

    if (timeLeft < 0) {
        updateWallboard();
    }
}

updateWallboard();
countdownTimer = setInterval(updateCountdown, 1000);