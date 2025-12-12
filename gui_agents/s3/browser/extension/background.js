/**
 * Agent-S3 Browser Extension - Background Service Worker
 * 
 * Handles WebSocket communication with Agent-S3 and routes commands
 * to content scripts for DOM manipulation.
 */

// WebSocket connection to Agent-S3
let ws = null;
let wsConnected = false;
const WS_URL = 'ws://127.0.0.1:9333';
const RECONNECT_INTERVAL = 3000;

// Connection state
let connectionAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;

/**
 * Connect to Agent-S3 WebSocket server
 */
function connectWebSocket() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        return;
    }

    console.log('[Agent-S3] Connecting to WebSocket:', WS_URL);

    try {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            console.log('[Agent-S3] WebSocket connected');
            wsConnected = true;
            connectionAttempts = 0;

            // Notify popup of connection status
            chrome.runtime.sendMessage({ type: 'connection_status', connected: true }).catch(() => { });

            // Send handshake
            ws.send(JSON.stringify({
                type: 'handshake',
                client: 'agent-s3-extension',
                version: '1.0.0'
            }));
        };

        ws.onmessage = async (event) => {
            try {
                const message = JSON.parse(event.data);
                console.log('[Agent-S3] Received command:', message);

                const response = await handleCommand(message);
                ws.send(JSON.stringify(response));
            } catch (error) {
                console.error('[Agent-S3] Error handling message:', error);
                ws.send(JSON.stringify({
                    id: 'unknown',
                    success: false,
                    error: error.message
                }));
            }
        };

        ws.onclose = () => {
            console.log('[Agent-S3] WebSocket disconnected');
            wsConnected = false;
            ws = null;

            // Notify popup of connection status
            chrome.runtime.sendMessage({ type: 'connection_status', connected: false }).catch(() => { });

            // Attempt reconnection
            if (connectionAttempts < MAX_RECONNECT_ATTEMPTS) {
                connectionAttempts++;
                setTimeout(connectWebSocket, RECONNECT_INTERVAL);
            }
        };

        ws.onerror = (error) => {
            console.error('[Agent-S3] WebSocket error:', error);
        };

    } catch (error) {
        console.error('[Agent-S3] Failed to create WebSocket:', error);
        setTimeout(connectWebSocket, RECONNECT_INTERVAL);
    }
}

/**
 * Handle incoming commands from Agent-S3
 */
async function handleCommand(message) {
    const { id, action, params } = message;

    try {
        let result;

        switch (action) {
            case 'navigate':
                result = await handleNavigate(params);
                break;
            case 'click':
                result = await handleClick(params);
                break;
            case 'type':
                result = await handleType(params);
                break;
            case 'scroll':
                result = await handleScroll(params);
                break;
            case 'screenshot':
                result = await handleScreenshot(params);
                break;
            case 'get_dom':
                result = await handleGetDom(params);
                break;
            case 'find_element':
                result = await handleFindElement(params);
                break;
            case 'get_url':
                result = await handleGetUrl(params);
                break;
            case 'ping':
                result = { pong: true };
                break;
            default:
                throw new Error(`Unknown action: ${action}`);
        }

        return { id, success: true, result };

    } catch (error) {
        console.error('[Agent-S3] Command error:', error);
        return { id, success: false, error: error.message };
    }
}

/**
 * Get active tab
 */
async function getActiveTab() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
        throw new Error('No active tab found');
    }
    return tab;
}

/**
 * Send message to content script
 */
async function sendToContentScript(tabId, message) {
    try {
        const response = await chrome.tabs.sendMessage(tabId, message);
        return response;
    } catch (error) {
        // Content script might not be loaded, try injecting it
        await chrome.scripting.executeScript({
            target: { tabId },
            files: ['content.js']
        });
        // Retry
        return await chrome.tabs.sendMessage(tabId, message);
    }
}

/**
 * Navigate to URL
 */
async function handleNavigate(params) {
    const { url } = params;
    const tab = await getActiveTab();
    await chrome.tabs.update(tab.id, { url });

    // Wait for navigation to complete
    return new Promise((resolve) => {
        const listener = (tabId, changeInfo) => {
            if (tabId === tab.id && changeInfo.status === 'complete') {
                chrome.tabs.onUpdated.removeListener(listener);
                resolve({ navigated: true, url });
            }
        };
        chrome.tabs.onUpdated.addListener(listener);

        // Timeout after 30 seconds
        setTimeout(() => {
            chrome.tabs.onUpdated.removeListener(listener);
            resolve({ navigated: true, url, timeout: true });
        }, 30000);
    });
}

/**
 * Click element
 */
async function handleClick(params) {
    const tab = await getActiveTab();
    return await sendToContentScript(tab.id, {
        action: 'click',
        params
    });
}

/**
 * Type text
 */
async function handleType(params) {
    const tab = await getActiveTab();
    return await sendToContentScript(tab.id, {
        action: 'type',
        params
    });
}

/**
 * Scroll
 */
async function handleScroll(params) {
    const tab = await getActiveTab();
    return await sendToContentScript(tab.id, {
        action: 'scroll',
        params
    });
}

/**
 * Take screenshot
 */
async function handleScreenshot(params) {
    const tab = await getActiveTab();
    const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });
    return { screenshot: dataUrl };
}

/**
 * Get DOM
 */
async function handleGetDom(params) {
    const tab = await getActiveTab();
    return await sendToContentScript(tab.id, {
        action: 'get_dom',
        params
    });
}

/**
 * Find element
 */
async function handleFindElement(params) {
    const tab = await getActiveTab();
    return await sendToContentScript(tab.id, {
        action: 'find_element',
        params
    });
}

/**
 * Get current URL
 */
async function handleGetUrl(params) {
    const tab = await getActiveTab();
    return { url: tab.url, title: tab.title };
}

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'get_status') {
        sendResponse({ connected: wsConnected });
    } else if (message.type === 'reconnect') {
        connectionAttempts = 0;
        connectWebSocket();
        sendResponse({ reconnecting: true });
    }
    return true;
});

// Start connection on extension load
connectWebSocket();

console.log('[Agent-S3] Background service worker loaded');
