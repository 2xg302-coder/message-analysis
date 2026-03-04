// background.js

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'sendNews') {
        const API_URL = 'http://127.0.0.1:3001/api/news';
        
        console.log('Background: Sending news to backend:', request.data.id);

        fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(request.data)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
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
