// ==========================================
// Simple Local Server with SMS Proxy
// ==========================================
// This server does two things:
// 1. Serves your static files (index.html, app.js, styles.css)
// 2. Proxies SMS requests to Text.lk API (bypassing browser CORS restrictions)
//
// Usage: node server.js
// Then open: http://localhost:3000

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const PORT = 3000;

// MIME types for static file serving
const MIME_TYPES = {
    '.html': 'text/html',
    '.js':   'application/javascript',
    '.css':  'text/css',
    '.png':  'image/png',
    '.jpg':  'image/jpeg',
    '.svg':  'image/svg+xml',
    '.json': 'application/json',
};

const server = http.createServer((req, res) => {

    // ---- SMS Proxy Endpoint ----
    if (req.method === 'POST' && req.url === '/api/send-sms') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
            console.log('\n📱 SMS Proxy Request Received');
            console.log('   Body:', body);

            const postData = body;
            const options = {
                hostname: 'app.text.lk',
                port: 443,
                path: '/api/v3/sms/send',
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer 1997|0cqO0COunscpPJBOiHHjJtpi5mODfElhyvIkOEcf5803240e',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Content-Length': Buffer.byteLength(postData),
                },
            };

            const apiReq = https.request(options, (apiRes) => {
                let responseData = '';
                apiRes.on('data', chunk => { responseData += chunk; });
                apiRes.on('end', () => {
                    console.log('   ✅ Text.lk Response Status:', apiRes.statusCode);
                    console.log('   ✅ Text.lk Response Body:', responseData);

                    res.writeHead(apiRes.statusCode, {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                    });
                    res.end(responseData);
                });
            });

            apiReq.on('error', (err) => {
                console.error('   ❌ Error connecting to Text.lk:', err.message);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ status: 'error', message: 'Proxy error: ' + err.message }));
            });

            apiReq.write(postData);
            apiReq.end();
        });
        return;
    }

    // ---- Handle CORS preflight for the SMS proxy ----
    if (req.method === 'OPTIONS' && req.url === '/api/send-sms') {
        res.writeHead(204, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        });
        res.end();
        return;
    }

    // ---- Static File Server ----
    let filePath = req.url === '/' ? '/index.html' : req.url.split('?')[0];
    filePath = path.join(__dirname, filePath);

    const ext = path.extname(filePath);
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    fs.readFile(filePath, (err, data) => {
        if (err) {
            res.writeHead(404, { 'Content-Type': 'text/plain' });
            res.end('404 Not Found');
            return;
        }
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(data);
    });
});

server.listen(PORT, () => {
    console.log('');
    console.log('  ╔══════════════════════════════════════════════╗');
    console.log('  ║   🏥 DocCare Prescription Dispenser          ║');
    console.log('  ║   Server running on http://localhost:' + PORT + '     ║');
    console.log('  ║   SMS Proxy active on /api/send-sms          ║');
    console.log('  ╚══════════════════════════════════════════════╝');
    console.log('');
});
