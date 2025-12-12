/**
 * Agent-S3 Browser Extension - Popup Script
 */

const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const reconnectBtn = document.getElementById('reconnectBtn');

function updateStatus(connected) {
    if (connected) {
        statusDot.classList.add('connected');
        statusText.classList.add('connected');
        statusText.textContent = 'Connected to Agent-S3';
        reconnectBtn.disabled = true;
    } else {
        statusDot.classList.remove('connected');
        statusText.classList.remove('connected');
        statusText.textContent = 'Disconnected';
        reconnectBtn.disabled = false;
    }
}

// Get initial status
chrome.runtime.sendMessage({ type: 'get_status' }, (response) => {
    if (response) {
        updateStatus(response.connected);
    }
});

// Listen for status updates
chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'connection_status') {
        updateStatus(message.connected);
    }
});

// Reconnect button
reconnectBtn.addEventListener('click', () => {
    reconnectBtn.disabled = true;
    reconnectBtn.textContent = 'Connecting...';

    chrome.runtime.sendMessage({ type: 'reconnect' }, () => {
        setTimeout(() => {
            reconnectBtn.textContent = 'Reconnect';
            chrome.runtime.sendMessage({ type: 'get_status' }, (response) => {
                if (response) {
                    updateStatus(response.connected);
                }
            });
        }, 2000);
    });
});
