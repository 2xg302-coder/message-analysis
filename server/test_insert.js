const db = require('./database');

async function test() {
    console.log('Testing Sina insertion...');
    const sinaNews = {
        id: 'sina-test-' + Date.now(),
        timestamp: '20240304',
        time: '12:00:00',
        content: 'Sina Finance Test Content',
        link: 'http://finance.sina.com.cn/7x24/test',
        scrapedAt: new Date().toISOString(),
        source: 'sina'
    };
    const sinaResult = await db.addNews(sinaNews);
    console.log('Sina result:', sinaResult);

    console.log('Testing ITHome insertion...');
    const ithomeNews = {
        id: 'ithome-test-' + Date.now(),
        title: 'ITHome Test Title',
        link: 'https://www.ithome.com/0/123/456.htm',
        time: '12:00',
        scrapedAt: new Date().toISOString(),
        source: 'ithome'
    };
    const ithomeResult = await db.addNews(ithomeNews);
    console.log('ITHome result:', ithomeResult);
    
    // Verify
    const latest = await db.getLatestNews(10);
    console.log('Latest news:', latest.map(n => ({id: n.id, source: n.source, title: n.title, content: n.content})));
}

test();
