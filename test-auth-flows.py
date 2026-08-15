#!/usr/bin/env python3
import requests
import json

print('🧪 Testing auth flows...\n')

# Test 1: Sign up new user
print('1️⃣ Testing user registration...')
signup_data = {
    'username': 'newuser123',
    'email': 'newuser@example.com',
    'password': 'NewPassword123',
    'first_name': 'New',
    'last_name': 'User',
    'role': 'student'
}
signup_res = requests.post('http://localhost:8000/api/auth/register/', json=signup_data)
print(f'   Status: {signup_res.status_code}')
if signup_res.status_code != 201:
    print(f'   Error: {signup_res.json()}')
else:
    email = signup_res.json().get('email')
    print(f'   OK User registered: {email}')

# Test 2: Login with registered user
print('\n2️⃣ Testing login...')
login_res = requests.post('http://localhost:8000/api/auth/login/', json={
    'username': 'newuser@example.com',
    'password': 'NewPassword123'
})
print(f'   Status: {login_res.status_code}')
if login_res.status_code != 200:
    print(f'   Error: {login_res.json()}')
else:
    login_data = login_res.json()
    print(f'   OK Login successful')
    access = login_data['access']
    
    # Test 3: Use token to call protected endpoint
    print('\n3️⃣ Testing protected endpoint with token...')
    me_res = requests.get('http://localhost:8000/api/auth/me/', headers={
        'Authorization': f'Bearer {access}'
    })
    print(f'   Status: {me_res.status_code}')
    if me_res.status_code == 200:
        user = me_res.json()
        email = user['email']
        role = user['role']
        print(f'   OK Protected endpoint works: {email} ({role})')
    else:
        print(f'   Error: {me_res.json()}')

print('\n✨ Auth flow test complete!')
