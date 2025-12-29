const API_CONFIG = {
    endpoint: localStorage.getItem('apiEndpoint') || 'https://uuqounhnz2.execute-api.eu-west-2.amazonaws.com/Prod/wallboard',
    timeout: 10000
};
const DEBUG_MODE = false;
const updateInterval = 10;
const callAlertThreshold = 10;
const callWarnThreshold = 5;
const waitTimeAlertThreshold = 300000; // 5 minutes in milliseconds
const abandonmentAlertThreshold = 10;
const alertStyle = 'alert';
const warnStyle = 'warn';

let timeLeft = updateInterval;
let countdownTimer;

function updateWallboard() {
    console.log('Fetching data...');
    fetch(API_CONFIG.endpoint, {
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
            const wallboardData = data;

            safeUpdateElement('callsHandled', wallboardData.CallsHandled);
            safeUpdateElement('callsInQueue', wallboardData.CallsInQueue);
            safeUpdateElement('callsAbandoned', wallboardData.CallsAbandoned);
            safeUpdateElement('longestWaitTime', formatTime(wallboardData.LongestWaitTime));
            safeUpdateElement('agentAnswerRate', formatPercentage(wallboardData.AgentAnswerRate));
            safeUpdateElement('averageContactDuration', formatDuration(wallboardData.AverageContactDuration));

            if (DEBUG_MODE) {
                wallboardData.CallsInQueue = 11;
            }

            if (wallboardData.CallsInQueue >= callAlertThreshold) {
                document.getElementById('callsInQueueContainer').classList.add(alertStyle);
            }
            else {
                document.getElementById('callsInQueueContainer').classList.remove(alertStyle);

                if (wallboardData.CallsInQueue >= callWarnThreshold) {
                    document.getElementById('callsInQueueContainer').classList.add(warnStyle);
                }
                else {
                    document.getElementById('callsInQueueContainer').classList.remove(warnStyle);
                }
            }

            const customInfoElement = document.getElementById('customInformation');
            if (wallboardData.CustomInformation != 'No custom information available.') {
                customInfoElement.textContent = wallboardData.CustomInformation;
                customInfoElement.style.display = 'block';
            } else {
                customInfoElement.style.display = 'none';
            }
            
            const agentList = document.getElementById('agent-status-list');
            agentList.innerHTML = '';

            for (const agent of wallboardData.Users) {
                var agentName = agent.FirstName + ' ' + agent.LastName;
                var agentBadge  = '<span class="agent-status-badge ' + agent.Status + '">' + agent.Status +'</span>'
                var agentNameBadge  = '<span class="agent-name-badge">'  + agent.FirstName.charAt(0) + agent.LastName.charAt(0) +'</span>'
                var agentCallStatus = agent.OnContacts ? 'On-Call' : 'Free';
                var agentCallBadge = '<span class="agent-status-badge ' + agentCallStatus + '">' + agentCallStatus +'</span>'
                agentList.innerHTML = agentList.innerHTML + '<div class="agent-status"><div>'+ agentNameBadge + agentName +'</div><div>'+ agentBadge +'</div><div>'+ agentCallBadge +'</div></div>';
            }

            if (wallboardData.Users.length === 0) {
                document.getElementById('no-agent-message').style.display = 'block';
            }

            timeLeft = updateInterval;
            updateCountdown();
        })
        .catch(error => console.error('Error fetching data:', error));

        startCountdown();
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

function startCountdown() {
    if (countdownTimer) clearInterval(countdownTimer);
    countdownTimer = setInterval(updateCountdown, 1000);
}

function safeUpdateElement(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    } else {
        console.warn(`Element with ID '${elementId}' not found`);
    }
}

updateWallboard();
