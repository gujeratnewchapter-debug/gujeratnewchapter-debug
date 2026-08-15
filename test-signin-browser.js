// Test script to diagnose sign-in issues
// Run this in the browser console at http://localhost:3001 after clicking Sign In

async function testSignInFlow() {
  console.log('🧪 Testing sign-in flow...\n');
  
  // Test 1: Check localStorage
  console.log('1️⃣ Checking localStorage...');
  const djangoToken = localStorage.getItem('django_access');
  console.log(`   Django token in storage: ${djangoToken ? 'YES' : 'NO'}`);
  if (djangoToken) {
    console.log(`   Token: ${djangoToken.substring(0, 40)}...`);
  }
  
  // Test 2: Test backend login directly
  console.log('\n2️⃣ Testing backend login directly...');
  try {
    const loginRes = await fetch('http://localhost:8000/api/auth/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: 'testuser@example.com',
        password: 'TestPassword123'
      })
    });
    
    if (loginRes.status === 200) {
      const data = await loginRes.json();
      console.log('✅ Backend login works');
      console.log(`   Access token: ${data.access.substring(0, 40)}...`);
      
      // Test 3: Use the token to call /auth/me/
      console.log('\n3️⃣ Testing /auth/me/ with token...');
      const meRes = await fetch('http://localhost:8000/api/auth/me/', {
        headers: { 'Authorization': `Bearer ${data.access}` }
      });
      
      if (meRes.status === 200) {
        const user = await meRes.json();
        console.log('✅ Protected endpoint works');
        console.log(`   User: ${user.email} (${user.role})`);
      } else {
        console.log('❌ Protected endpoint failed:', meRes.status);
      }
    } else {
      console.log('❌ Backend login failed:', loginRes.status);
      const err = await loginRes.json();
      console.log('   Error:', err);
    }
  } catch (err) {
    console.log('❌ Error:', err);
  }
  
  // Test 4: Check auth context
  console.log('\n4️⃣ Checking auth context in page...');
  if (window.__auth_context) {
    console.log('   Auth context found:', window.__auth_context);
  } else {
    console.log('   Auth context not exposed globally');
  }
  
  console.log('\n📝 To test sign-in manually:');
  console.log('   1. Open the browser Network tab');
  console.log('   2. Click Sign In button');
  console.log('   3. Enter: testuser@example.com / TestPassword123');
  console.log('   4. Watch for POST to /api/auth/login/');
  console.log('   5. Check if localStorage gets django_access token');
  console.log('   6. Check if modal closes or shows error');
}

testSignInFlow();
