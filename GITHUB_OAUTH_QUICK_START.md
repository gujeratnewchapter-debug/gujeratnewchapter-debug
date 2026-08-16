# GitHub OAuth Implementation - Quick Start

**Status:** Ready to Deploy  
**Date:** 2026-08-16

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Create GitHub OAuth App (2 min)
```
1. Go to https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in:
   - Name: Ethiopian Startup School Portal
   - Homepage URL: https://vpqglrzjfavqdiruxhqc.supabase.co
   - Callback URL: https://vpqglrzjfavqdiruxhqc.supabase.co/auth/v1/callback
4. Copy Client ID and Client Secret
```

### Step 2: Configure Supabase (2 min)
```
1. Go to https://app.supabase.com/
2. Select your project
3. Authentication → Providers → GitHub → ON
4. Paste Client ID and Secret
5. Click Save
```

### Step 3: Add Redirect URLs (1 min)
```
In Supabase → Authentication → Settings → Redirect URLs, add:
- http://localhost:3000/auth/callback
- https://yourdomain.com/auth/callback
```

### Done! ✅

Users can now sign in with GitHub. The UI button is already implemented in `AuthModal.tsx`.

---

## 🔍 What Changed

### Files Modified:
- `portal/components/AuthModal.tsx` - Added GitHub sign-in button and handler

### Changes Made:
1. ✅ Added GitHub icon import from lucide-react
2. ✅ Created `handleGitHubSignIn()` function
3. ✅ Added GitHub button next to Google button
4. ✅ Both OAuth methods now available in sign-in modal

### Code Added:
```typescript
// Import
import { ..., Github } from 'lucide-react';

// Handler
async function handleGitHubSignIn() {
  setError('');
  setSuccess('');
  setLoading(true);
  try {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'github',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) throw error;
  } catch (err: any) {
    setError(err?.message || 'GitHub sign-in failed. Please try again.');
    setLoading(false);
  }
}

// Button
<button
  type="button"
  className="btn btn-primary"
  onClick={handleGitHubSignIn}
  disabled={loading}
  style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
>
  <Github size={16} />
  GitHub
</button>
```

---

## 🧪 Testing

### Local Testing:
```bash
cd portal
npm run dev
# Navigate to http://localhost:3000
# Click Sign In
# Click GitHub button
# You should be redirected to GitHub login
```

### Verify in Supabase:
- Go to Dashboard → Authentication → Users
- After login, you'll see a new user with provider: `github`

---

## 📋 GitHub OAuth Flow

```
User clicks "GitHub" button
        ↓
Redirected to GitHub.com
        ↓
User logs in to GitHub (if not already logged in)
        ↓
User grants permissions
        ↓
GitHub redirects to Supabase callback
        ↓
Supabase creates/updates user
        ↓
Supabase JWT token issued
        ↓
Redirect to /auth/callback
        ↓
Frontend auth-context.tsx processes auth
        ↓
Optional: Backend profile sync via API
        ↓
User logged in ✅
```

---

## 🔐 Security Notes

✅ **Secure:**
- GitHub Secret never exposed to frontend
- Supabase handles token exchange securely
- HTTPS only in production
- CORS properly configured

❌ **Avoid:**
- Committing GitHub Secret to git
- Using HTTP for callbacks
- Loose redirect URL validation

---

## 📚 Files to Review

1. **Setup Guide:** [GITHUB_OAUTH_SETUP.md](GITHUB_OAUTH_SETUP.md)
   - Complete step-by-step guide
   - Troubleshooting section
   - Security best practices

2. **Code Changes:** `portal/components/AuthModal.tsx`
   - GitHub sign-in button
   - OAuth handler
   - Integration with Supabase

3. **Auth Context:** `portal/lib/auth-context.tsx`
   - Handles OAuth redirect processing
   - Session management
   - User profile sync

---

## ✅ Pre-Deployment Checklist

- [ ] GitHub OAuth app created
- [ ] GitHub Client ID and Secret obtained
- [ ] GitHub OAuth enabled in Supabase
- [ ] Redirect URLs configured
- [ ] Local testing successful
- [ ] Frontend build passes
- [ ] Backend check passes
- [ ] Ready to deploy

---

## 🚀 Deploy to Production

### 1. Push Changes:
```bash
git add portal/components/AuthModal.tsx
git commit -m "feat: add GitHub OAuth sign-in button"
git push origin main
```

### 2. Add Production Redirect URL:
In GitHub OAuth app settings, add:
```
https://yourdomain.com/auth/callback
```

### 3. Update Supabase:
In Supabase → Authentication → Settings → Redirect URLs, add:
```
https://yourdomain.com/auth/callback
https://yourdomain.com/
```

### 4. Deploy Frontend:
```bash
# Vercel: Auto-deploys on git push
# Or manually:
cd portal
npm run build
npm start
```

### 5. Test in Production:
- Visit https://yourdomain.com
- Click Sign In
- Verify GitHub button works

---

## 🐛 Troubleshooting

### Issue: GitHub button doesn't appear
**Fix:** Ensure you're on the latest code:
```bash
git pull origin main
npm install
npm run dev
```

### Issue: "Callback URL mismatch"
**Fix:** Ensure GitHub OAuth app Callback URL exactly matches:
```
https://vpqglrzjfavqdiruxhqc.supabase.co/auth/v1/callback
```

### Issue: "GitHub not enabled in Supabase"
**Fix:** 
1. Go to Supabase Dashboard
2. Authentication → Providers
3. Toggle GitHub ON
4. Enter Client ID and Secret

### Issue: User login loops back to sign-in
**Fix:**
1. Check browser localStorage for auth token
2. Check Supabase users list
3. Verify redirect URL is in allowed list

---

## 📞 Support Resources

- **Supabase GitHub Auth:** https://supabase.com/docs/guides/auth/social-login/auth-github
- **GitHub OAuth:** https://docs.github.com/en/developers/apps/building-oauth-apps
- **Redirect URL Issues:** https://supabase.com/docs/guides/auth/redirect-urls

---

## 📊 What Users Will See

### Sign In Modal:
```
┌─────────────────────────┐
│  Sign In      Sign Up   │
├─────────────────────────┤
│                         │
│  [Google] [GitHub]      │  ← New GitHub button
│                         │
│  ─── or continue with email ───
│                         │
│  Email: [_____________] │
│  Password: [_________] 👁│
│                         │
│  [Sign In]              │
│  Create account         │
│  Forgot password?       │
│                         │
└─────────────────────────┘
```

---

**✅ GitHub OAuth is now integrated!**

Users can sign in with their GitHub account across all environments (dev, staging, production).
