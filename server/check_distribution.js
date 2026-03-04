const db = require('./database');

async function checkSourceDistribution() {
    const rows = await new Promise((resolve, reject) => {
        db.db.all('SELECT source, COUNT(*) as count FROM news GROUP BY source', (err, rows) => {
            if (err) reject(err);
            else resolve(rows);
        });
    });
    console.log('Source distribution:', rows);
}

checkSourceDistribution();
