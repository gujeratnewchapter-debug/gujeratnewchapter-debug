#!/usr/bin/env node

const http = require('http');

/**
 * Test the frontend sign-in flow by simulating what the browser auth-context.tsx does
 */

function makeRequest(method, url, headers = {}, body = null) {
  return new Promise((resolve, reject) => {
    const options = new URL(url);
    const client = url.startsWith('https') ? require('https') : http;
    
    const req = client.request(
      {
        method,
        hostname: options.hostname,
        port: options.port,
        path: options.pathname + options.search,
        headers: { 'Content-Type': 'application/json', ...headers },
      },
      (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          try {
            resolve({ status: res.statusCode, data: JSON.parse(data), headers: res.headers });
          } catch {
            resolve({ status: res.statusCode, data, headers: res.headers });
          }
        });
      }
    );
    
    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

async function testSignIn() {
  console.log('🧪 Testing frontend sign-in flow...\n');
  
  // Step 1: Login via backend
  console.log('1️⃣ Testing backend login endpoint...');
  const loginRes = await makeRequest('POST', 'http://localhost:8000/api/auth/login/', {}, {
    username: 'testuser@example.com',
    password: 'TestPassword123'
  });
  
  if (loginRes.status !== 200) {
    console.error('❌ Backend login failed:', loginRes);
    process.exit(1);
  }
  
  const { access, refresh } = loginRes.data;
  console.log('✅ Backend login successful');
  console.log(`   Access token: ${access.substring(0, 40)}...`);
  
  // Step 2: Test protected endpoint with token
  console.log('\n2️⃣ Testing /auth/me/ with access token...');
  const meRes = await makeRequest('GET', 'http://localhost:8000/api/auth/me/', {
    'Authorization': `Bearer ${access}`
  });
  
  if (meRes.status !== 200) {
    console.error('❌ Protected endpoint failed:', meRes);
    process.exit(1);
  }
  
  console.log('✅ Protected endpoint access successful');
  console.log(`   User: ${meRes.data.email} (${meRes.data.role})`);
  console.log(`   Verified: ${meRes.data.is_email_verified}`);
  
  // Step 3: Test dashboard access
  console.log('\n3️⃣ Testing frontend homepage...');
  const homeRes = await makeRequest('GET', 'http://localhost:3001/');
  if (homeRes.status === 200) {
    console.log('✅ Frontend homepage loaded');
  } else {
    console.log('⚠️  Homepage returned:', homeRes.status);
  }
  
  // Step 4: Test dashboard page
  console.log('\n4️⃣ Testing /dashboard page...');
  const dashboardRes = await makeRequest('GET', 'http://localhost:3001/dashboard');
  if (dashboardRes.status === 200) {
    console.log('✅ Dashboard page loaded');
  } else {
    console.log('⚠️  Dashboard returned:', dashboardRes.status);
  }
  
  console.log('\n✨ Sign-in flow test complete!\n');
  console.log('📝 Next steps:');
  console.log('   1. Open http://localhost:3001 in your browser');
  console.log('   2. Click "Sign In" button');
  console.log('   3. Enter: testuser@example.com / TestPassword123');
  console.log('   4. Verify the app navigates to dashboard or home');
  console.log('   5. Check browser console for any auth errors');
}

testSignIn().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
