# GitHub OAuth Integration with Supabase

**Status:** Setup Guide  
**Date:** 2026-08-16  
**Supabase Project:** vpqglrzjfavqdiruxhqc

---

## 🔑 Step 1: Create GitHub OAuth Application

### 1.1 Register on GitHub Developer Settings

1. Go to GitHub Settings → Developer settings → OAuth Apps
   - URL: https://github.com/settings/developers

2. Click **"New OAuth App"**

3. Fill in the form:

   | Field | Value |
   |-------|-------|
   | **Application name** | Ethiopian Startup School Portal |
   | **Homepage URL** | `https://vpqglrzjfavqdiruxhqc.supabase.co` |
   | **Application description** | AI-powered education platform for startup founders |
   | **Authorization callback URL** | `https://vpqglrzjfavqdiruxhqc.supabase.co/auth/v1/callback` |

4. Click **"Create OAuth App"**

5. You'll get:
   - **Client ID** (copy this)
   - **Client Secret** (click "Generate a new client secret" and copy)
   - Keep these safe! You'll need them in the next step.

### 1.2 Add Redirect URLs for Development

Add these additional callback URLs in GitHub OAuth app settings:
```
http://localhost:3000/auth/callback
http://localhost:3000/
http://127.0.0.1:3000/auth/callback
```

---

## 🔐 Step 2: Configure GitHub OAuth in Supabase

### 2.1 Access Supabase Dashboard

1. Go to your Supabase project:
   - URL: https://app.supabase.com/

2. Select your project (if not already selected)

### 2.2 Enable GitHub Authentication

1. Navigate to **Authentication** → **Providers**

2. Find **GitHub** in the providers list

3. Toggle **GitHub** to **ON**

4. Paste your GitHub OAuth credentials:
   - **Client ID**: (from Step 1.5)
   - **Client Secret**: (from Step 1.5)

5. Click **Save**

### 2.3 Configure Redirect URLs

1. Go to **Authentication** → **Settings**

2. Scroll to **Redirect URLs**

3. Add these URLs:
   ```
   http://localhost:3000/auth/callback
   http://localhost:3000/
   http://127.0.0.1:3000/auth/callback
   https://yourdomain.com/auth/callback
   https://www.yourdomain.com/auth/callback
   ```

   (Replace `yourdomain.com` with your production domain)

4. Click **Save**

---

## 🌍 Step 3: Update Environment Variables

### 3.1 Frontend Environment (.env.local)

Your `.portal/.env.local` should already have Supabase configured:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id
NEXT_PUBLIC_SUPABASE_URL=https://vpqglrzjfavqdiruxhqc.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

**Note:** GitHub OAuth does NOT require additional environment variables on the frontend. Supabase handles it internally.

### 3.2 Production Environment Variables

For production deployment (Vercel, Railway, etc.):

In your deployment platform settings, set:
```
NEXT_PUBLIC_SUPABASE_URL=https://vpqglrzjfavqdiruxhqc.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-production-google-id
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
```

---

## 💻 Step 4: Update Frontend Code

### 4.1 Check Auth Context

Your auth-context.tsx already supports Supabase auth. GitHub OAuth will work automatically once enabled in Supabase.

The current sign-in flow supports:
- ✅ Email/Password (Supabase)
- ✅ Google OAuth (Supabase)
- ✅ GitHub OAuth (Supabase) — automatically enabled
- ✅ Backend fallback login (Django)

### 4.2 Add GitHub Sign-In Button (Optional)

If you want an explicit GitHub sign-in button, update `portal/components/AuthModal.tsx`:

```typescript
// Add this import at the top
import { Auth } from '@supabase/auth-ui-react';
import { ThemeSupa } from '@supabase/auth-ui-shared';

// Add this function to handle GitHub sign-in
const signInWithGitHub = async () => {
  try {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'github',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) throw error;
  } catch (error: any) {
    console.error('GitHub sign-in error:', error);
    setErrorMessage(error?.message || 'Failed to sign in with GitHub');
  }
};

// Add this button in the sign-in modal JSX
<button 
  onClick={signInWithGitHub}
  className="w-full py-2 px-4 bg-gray-800 text-white rounded-md hover:bg-gray-700 font-medium"
>
  Sign in with GitHub
</button>
```

### 4.3 Current Auth Flow (Already Working)

The existing `AuthModal.tsx` and `auth-context.tsx` already support the full OAuth flow:

```typescript
// From auth-context.tsx - already implemented
const { error } = await supabase.auth.signInWithOAuth({
  provider: 'google', // or 'github'
  options: {
    redirectTo: `${window.location.origin}/auth/callback`,
  },
});
```

When a user clicks the existing sign-in buttons and Supabase is properly configured, GitHub will appear as an available option.

---

## 🧪 Step 5: Test GitHub OAuth

### 5.1 Local Testing

1. Start your portal server:
   ```bash
   cd portal
   npm run dev
   ```

2. Go to `http://localhost:3000`

3. Click **"Sign in"**

4. You should see GitHub option alongside Google

5. Click **"GitHub"**

6. You'll be redirected to GitHub login

7. After login, you'll be redirected back to `/auth/callback`

8. User should be created in Supabase and logged in

### 5.2 Verify in Supabase Dashboard

1. Go to your Supabase project: https://app.supabase.com/

2. Navigate to **Authentication** → **Users**

3. You should see your new GitHub user with:
   - Provider: `github`
   - Email: Your GitHub email
   - User ID: GitHub user ID

### 5.3 Test Local Backend Sync

If using backend fallback:
1. User logs in via GitHub/Supabase
2. Backend API syncs user profile to Django
3. Verify in Django admin that user was created

---

## 🔄 Step 6: Deployment

### 6.1 Vercel Deployment

1. Connect your GitHub repo to Vercel
2. Add environment variables:
   ```
   NEXT_PUBLIC_SUPABASE_URL
   NEXT_PUBLIC_SUPABASE_ANON_KEY
   NEXT_PUBLIC_GOOGLE_CLIENT_ID
   NEXT_PUBLIC_API_BASE_URL
   ```

3. Deploy:
   ```bash
   git push origin main
   ```

4. Vercel auto-deploys

5. Update GitHub OAuth app redirect URLs to include your Vercel domain:
   ```
   https://your-project.vercel.app/auth/callback
   https://your-project-git-*.vercel.app/auth/callback
   ```

### 6.2 Production Domain Setup

Once you have your production domain (e.g., `yourdomain.com`):

1. Update GitHub OAuth app:
   - **Homepage URL**: `https://yourdomain.com`
   - **Authorization callback URL**: `https://yourdomain.com/auth/callback`
   - Add redirect URL: `https://yourdomain.com/auth/callback`

2. Update Supabase redirect URLs:
   - Add: `https://yourdomain.com/auth/callback`
   - Add: `https://yourdomain.com/`

3. Update environment variables:
   ```bash
   NEXT_PUBLIC_SUPABASE_URL=https://vpqglrzjfavqdiruxhqc.supabase.co
   NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
   ```

---

## 🐛 Troubleshooting

### Issue: "Authorization callback URL mismatch"

**Solution:**
- Ensure callback URL in GitHub OAuth app matches Supabase redirect URL
- Format must be exact: `https://vpqglrzjfavqdiruxhqc.supabase.co/auth/v1/callback`

### Issue: "GitHub provider not appearing in Supabase"

**Solution:**
1. Go to Supabase Dashboard → Authentication → Providers
2. Toggle GitHub OFF, then ON
3. Re-enter Client ID and Client Secret
4. Click Save
5. Refresh browser

### Issue: "Redirect loop after GitHub login"

**Solution:**
- Check that redirect URL is correctly configured in both:
  - GitHub OAuth app settings
  - Supabase Authentication → Settings → Redirect URLs

### Issue: "User not syncing to backend"

**Solution:**
1. Check auth-context.tsx fallback login is enabled
2. Verify backend API is accessible from frontend
3. Check Django logs for API errors
4. Ensure CORS is configured for frontend domain

### Issue: "Cannot access user profile in frontend"

**Solution:**
```typescript
// In your component
const { user } = useAuth();
console.log(user); // Should show GitHub user data
```

If user is null, check:
1. Supabase session is active: `supabase.auth.getSession()`
2. Token is stored in localStorage
3. Check browser DevTools → Application → Cookies

---

## 📋 GitHub OAuth + Supabase User Flow

### Sign-Up Flow:
```
User clicks "Continue with GitHub"
        ↓
Redirected to GitHub login
        ↓
User grants permissions
        ↓
GitHub redirects to Supabase callback
        ↓
Supabase creates user account
        ↓
Supabase JWT token created
        ↓
Redirect to /auth/callback
        ↓
Frontend stores token in localStorage
        ↓
User profile loaded from Supabase
        ↓
Optional: Backend sync via API
        ↓
User logged in ✅
```

### Sign-In Flow:
```
User clicks "Continue with GitHub"
        ↓
If already logged in: Skip GitHub login
        ↓
Supabase JWT token refreshed
        ↓
User logged in ✅
```

---

## 🔒 Security Best Practices

✅ **Do:**
- Store GitHub Client Secret securely (never in frontend)
- Use HTTPS only for all OAuth callbacks
- Rotate Client Secret if exposed
- Verify redirect URLs match exactly
- Use Supabase Session for state management

❌ **Don't:**
- Commit Client Secret to git
- Use HTTP for OAuth callbacks
- Accept any redirect URL
- Store JWT tokens in localStorage for sensitive operations
- Use Client ID as authentication proof

---

## 📚 Additional Resources

- **Supabase Docs**: https://supabase.com/docs/guides/auth
- **Supabase GitHub Auth**: https://supabase.com/docs/guides/auth/social-login/auth-github
- **GitHub OAuth Docs**: https://docs.github.com/en/developers/apps/building-oauth-apps
- **Redirect URL Debugging**: https://supabase.com/docs/guides/auth/redirect-urls

---

## ✅ Checklist for GitHub OAuth Setup

- [ ] GitHub OAuth app created
- [ ] Client ID and Secret obtained
- [ ] GitHub OAuth enabled in Supabase
- [ ] Client ID and Secret added to Supabase
- [ ] Redirect URLs configured in both GitHub and Supabase
- [ ] Environment variables set (.env.local)
- [ ] Frontend auth context verified
- [ ] Local testing successful
- [ ] Production redirect URLs added
- [ ] Deployment completed
- [ ] Production testing successful

---

## 📞 Support

If you encounter issues:

1. **Check Supabase Logs:**
   - Dashboard → Authentication → Logs

2. **Check Browser Console:**
   - DevTools → Console (look for auth errors)

3. **Check Network Requests:**
   - DevTools → Network → Filter "auth"

4. **Common Error Messages:**
   - `invalid_request`: Missing or invalid parameters
   - `invalid_grant`: Invalid credentials or expired token
   - `redirect_mismatch`: URL doesn't match GitHub OAuth app settings

---

**🎉 GitHub OAuth integration complete!**

Your users can now sign in with GitHub. The integration works across local development, staging, and production environments.
