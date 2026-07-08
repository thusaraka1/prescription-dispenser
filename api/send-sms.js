// Vercel Serverless Function: SMS Proxy
// This runs server-side on Vercel, bypassing browser CORS restrictions

const https = require('https');

module.exports = (req, res) => {
    // Handle CORS preflight
    if (req.method === 'OPTIONS') {
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
        return res.status(204).end();
    }

    if (req.method !== 'POST') {
        return res.status(405).json({ status: 'error', message: 'Method not allowed' });
    }

    const payload = JSON.stringify(req.body);

    console.log('📱 SMS Proxy Request:', payload);

    const options = {
        hostname: 'app.text.lk',
        port: 443,
        path: '/api/v3/sms/send',
        method: 'POST',
        headers: {
            'Authorization': 'Bearer 1997|0cqO0COunscpPJBOiHHjJtpi5mODfElhyvIkOEcf5803240e',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Content-Length': Buffer.byteLength(payload),
        },
    };

    const apiReq = https.request(options, (apiRes) => {
        let responseData = '';
        apiRes.on('data', chunk => { responseData += chunk; });
        apiRes.on('end', () => {
            console.log('✅ Text.lk Response:', apiRes.statusCode, responseData);
            res.setHeader('Access-Control-Allow-Origin', '*');
            res.setHeader('Content-Type', 'application/json');
            res.status(apiRes.statusCode).send(responseData);
        });
    });

    apiReq.on('error', (err) => {
        console.error('❌ Text.lk Error:', err.message);
        res.status(500).json({ status: 'error', message: 'Proxy error: ' + err.message });
    });

    apiReq.write(payload);
    apiReq.end();
};
