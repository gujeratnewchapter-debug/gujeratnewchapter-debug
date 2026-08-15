import json
import requests

print('🧪 Testing frontend sign-in flow...\n')

# Step 1: Login via backend
print('1️⃣ Testing backend login endpoint...')
login_res = requests.post('http://localhost:8000/api/auth/login/', json={
    'username': 'testuser@example.com',
    'password': 'TestPassword123'
})

if login_res.status_code != 200:
    print('❌ Backend login failed:', login_res.json())
    exit(1)

login_data = login_res.json()
access = login_data['access']
print('✅ Backend login successful')
print(f'   Access token: {access[:40]}...')

# Step 2: Test protected endpoint
print('\n2️⃣ Testing /auth/me/ with access token...')
me_res = requests.get('http://localhost:8000/api/auth/me/', headers={
    'Authorization': f'Bearer {access}'
})

if me_res.status_code != 200:
    print('❌ Protected endpoint failed:', me_res.json())
    exit(1)

user = me_res.json()
print('✅ Protected endpoint access successful')
print(f'   User: {user["email"]} ({user["role"]})')
print(f'   Verified: {user["is_email_verified"]}')

# Step 3: Check frontend homepage
print('\n3️⃣ Testing frontend homepage...')
home_res = requests.get('http://localhost:3001/', allow_redirects=False)
print(f'   Status: {home_res.status_code}')

# Step 4: Check dashboard page
print('\n4️⃣ Testing /dashboard page...')
dash_res = requests.get('http://localhost:3001/dashboard', allow_redirects=False)
print(f'   Status: {dash_res.status_code}')

print('\n✨ Backend sign-in flow test complete!')
print('\n📝 Next manual steps:')
print('   1. Open http://localhost:3001 in your browser')
print('   2. Click "Sign In" button')
print('   3. Enter: testuser@example.com / TestPassword123')
print('   4. Verify the app signs in successfully')
print('   5. Check the Network tab in browser DevTools for API calls')
