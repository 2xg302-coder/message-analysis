// background.js

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'sendNews') {
        const API_URL = 'http://localhost:3001/api/news';
        
        fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(request.data)
        })
        .then(response => response.json())
        .then(data => {
            console.log('✅ Background: Sent to backend', data);
            sendResponse({ success: true, data });
        })
        .catch(error => {
            console.error('❌ Background: Error sending to backend', error);
            sendResponse({ success: false, error: error.message });
        });

        return true; // Keep the message channel open for asynchronous response
    }
});
