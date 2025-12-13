/**
 * Agent-S3 Browser Extension - Content Script
 * 
 * Runs in page context with full DOM access.
 * Handles element finding, clicking, typing, and DOM extraction.
 */

(function () {
    'use strict';

    // Prevent multiple injections
    if (window.__agentS3ContentScriptLoaded) {
        return;
    }
    window.__agentS3ContentScriptLoaded = true;

    console.log('[Agent-S3] Content script loaded');

    // Overlay for visual feedback during automation
    let overlay = null;

    /**
     * Show automation overlay
     */
    function showOverlay(message) {
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'agent-s3-overlay';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                border: 4px solid #4285f4;
                pointer-events: none;
                z-index: 2147483647;
                box-sizing: border-box;
            `;

            const badge = document.createElement('div');
            badge.style.cssText = `
                position: absolute;
                top: 8px;
                right: 8px;
                background: #4285f4;
                color: white;
                padding: 4px 12px;
                border-radius: 4px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 12px;
                font-weight: 500;
            `;
            badge.textContent = '🤖 Agent-S3';
            overlay.appendChild(badge);

            document.body.appendChild(overlay);
        }
    }

    /**
     * Hide automation overlay
     */
    function hideOverlay() {
        if (overlay) {
            overlay.remove();
            overlay = null;
        }
    }

    /**
     * Find element by various methods
     */
    function findElement(params) {
        const { selector, text, role, index } = params;

        // Try CSS selector first
        if (selector) {
            const elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                const idx = index || 0;
                return elements[idx] || elements[0];
            }
        }

        // Try finding by text content
        if (text) {
            const normalizedText = text.toLowerCase().trim();

            // Search in interactive elements first
            const interactiveElements = document.querySelectorAll(
                'button, a, input, select, textarea, [role="button"], [role="link"], [onclick], [tabindex]'
            );

            for (const el of interactiveElements) {
                const elText = (el.textContent || el.value || el.placeholder || el.getAttribute('aria-label') || '').toLowerCase().trim();
                if (elText.includes(normalizedText) || normalizedText.includes(elText)) {
                    return el;
                }
            }

            // Search all elements
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_ELEMENT,
                null,
                false
            );

            let node;
            while (node = walker.nextNode()) {
                const elText = (node.textContent || '').toLowerCase().trim();
                if (elText === normalizedText) {
                    return node;
                }
            }

            // Fuzzy match
            const allElements = document.body.querySelectorAll('*');
            for (const el of allElements) {
                const elText = (el.textContent || '').toLowerCase().trim();
                if (elText.includes(normalizedText)) {
                    // Prefer smaller/more specific elements
                    if (el.children.length === 0 || el.textContent.length < 200) {
                        return el;
                    }
                }
            }
        }

        // Try finding by role
        if (role) {
            const elements = document.querySelectorAll(`[role="${role}"]`);
            if (elements.length > 0) {
                return elements[index || 0];
            }
        }

        return null;
    }

    /**
     * Click an element
     */
    function clickElement(params) {
        const element = findElement(params);

        if (!element) {
            return { clicked: false, error: 'Element not found' };
        }

        // Scroll into view
        element.scrollIntoView({ behavior: 'instant', block: 'center' });

        // Focus the element
        if (element.focus) {
            element.focus();
        }

        // Create and dispatch click events
        const rect = element.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;

        const mouseEvents = ['mouseenter', 'mouseover', 'mousedown', 'mouseup', 'click'];

        for (const eventType of mouseEvents) {
            const event = new MouseEvent(eventType, {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: x,
                clientY: y
            });
            element.dispatchEvent(event);
        }

        return {
            clicked: true,
            element: describeElement(element),
            coordinates: { x: Math.round(x), y: Math.round(y) }
        };
    }

    /**
     * Type text into an element
     */
    function typeText(params) {
        const { text, clear, text_match, selector } = params;

        // Construct dedicated finder params
        // For finding, we strictly want selector OR text_match. 
        // We do NOT want 'text' (which is the keystrokes) to be used for finding.
        const findParams = {
            selector: selector,
            text: text_match, // Map bridge's text_match to findElement's text criterion
            role: params.role,
            index: params.index
        };

        let element = findElement(findParams);

        // If no specific element, try to find focused element or first input
        if (!element) {
            // Only fallback if NO specific target was requested
            if (!selector && !text_match) {
                element = document.activeElement;
                if (!element || element === document.body) {
                    element = document.querySelector('input:not([type="hidden"]), textarea');
                }
            }
        }

        if (!element) {
            return { typed: false, error: 'No input element found' };
        }

        // Focus the element
        element.focus();

        // Clear existing text if requested
        if (clear) {
            element.value = '';
            element.dispatchEvent(new Event('input', { bubbles: true }));
        }

        // Type the text
        if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
            // Robust value setting for React/Angular/Vue
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;

            const setter = element.tagName === 'INPUT' ? nativeInputValueSetter : nativeTextAreaValueSetter;

            if (setter && setter !== element.value) {
                setter.call(element, element.value + text);
            } else {
                element.value += text;
            }

            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
            element.dispatchEvent(new Event('keydown', { bubbles: true }));
            element.dispatchEvent(new Event('keyup', { bubbles: true }));
        } else if (element.isContentEditable) {
            document.execCommand('insertText', false, text);
        }

        return {
            typed: true,
            element: describeElement(element),
            text: text
        };
    }

    /**
     * Scroll the page or element
     */
    function scrollPage(params) {
        const { direction, amount, selector } = params;

        let target = document;
        if (selector) {
            target = document.querySelector(selector) || document;
        }

        const scrollAmount = amount || 300;

        switch (direction) {
            case 'up':
                target.scrollBy(0, -scrollAmount);
                break;
            case 'down':
                target.scrollBy(0, scrollAmount);
                break;
            case 'left':
                target.scrollBy(-scrollAmount, 0);
                break;
            case 'right':
                target.scrollBy(scrollAmount, 0);
                break;
            case 'top':
                target.scrollTo(0, 0);
                break;
            case 'bottom':
                target.scrollTo(0, target.scrollHeight || document.body.scrollHeight);
                break;
        }

        return { scrolled: true, direction, amount: scrollAmount };
    }

    /**
     * Get DOM content
     */
    function getDom(params) {
        const { simplified } = params || {};

        if (simplified) {
            // Return simplified DOM with just interactive elements
            const elements = [];
            const interactive = document.querySelectorAll(
                'a, button, input, select, textarea, [role="button"], [role="link"], [onclick]'
            );

            for (const el of interactive) {
                elements.push({
                    tag: el.tagName.toLowerCase(),
                    text: (el.textContent || '').trim().slice(0, 100),
                    type: el.type || null,
                    id: el.id || null,
                    className: el.className || null,
                    href: el.href || null
                });
            }

            return {
                url: window.location.href,
                title: document.title,
                elements: elements
            };
        }

        return {
            url: window.location.href,
            title: document.title,
            html: document.documentElement.outerHTML
        };
    }

    /**
     * Describe an element for logging
     */
    function describeElement(el) {
        if (!el) return null;

        let desc = el.tagName.toLowerCase();
        if (el.id) desc += `#${el.id}`;
        if (el.className && typeof el.className === 'string') {
            desc += '.' + el.className.split(' ').filter(c => c).slice(0, 2).join('.');
        }

        const text = (el.textContent || '').trim().slice(0, 50);
        if (text) desc += ` "${text}"`;

        return desc;
    }

    /**
     * Handle messages from background script
     */
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        const { action, params } = message;

        console.log('[Agent-S3] Content script received:', action, params);

        // Show overlay during action
        showOverlay(action);

        let result;

        try {
            switch (action) {
                case 'click':
                    result = clickElement(params);
                    break;
                case 'type':
                    result = typeText(params);
                    break;
                case 'scroll':
                    result = scrollPage(params);
                    break;
                case 'get_dom':
                    result = getDom(params);
                    break;
                case 'find_element':
                    const element = findElement(params);
                    result = {
                        found: !!element,
                        element: element ? describeElement(element) : null
                    };
                    break;
                default:
                    result = { error: `Unknown action: ${action}` };
            }
        } catch (error) {
            result = { error: error.message };
        }

        // Hide overlay after a short delay
        setTimeout(hideOverlay, 500);

        sendResponse(result);
        return true;
    });

})();
