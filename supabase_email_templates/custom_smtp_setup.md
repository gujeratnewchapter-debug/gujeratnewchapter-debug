# Custom SMTP setup for Supabase Auth

## Why configure custom SMTP?

Supabase's default email service is intended for limited testing and has strict sending and rate limits. Those limits can plausibly cause the site's **"Too many attempts"** message during repeated sign-up or verification-email requests. Custom SMTP gives the project a verified sender domain and controlled delivery, but it does not replace application-level abuse protection or Supabase Auth rate limits.

## Before configuration

1. Choose an email service and a sender domain that your organization controls.
2. Verify that domain with the email provider.
3. Create a branded sender address such as `no-reply@your-verified-domain`.
4. Publish the exact DNS records supplied by the provider:
   - **SPF** authorizes the provider to send for the domain. Keep a single SPF record and merge authorized senders rather than creating competing SPF records.
   - **DKIM** publishes the provider's signing keys so receiving systems can verify message signatures.
   - **DMARC** sets a policy and reporting address for mail that fails SPF/DKIM alignment. Start with a monitoring policy if needed, then strengthen it after reviewing reports.
5. Allow DNS changes to propagate and use the provider's verification tools to confirm each record.

Do not copy example SPF, DKIM, or DMARC values from this guide: use the values generated for your provider and domain. Never commit SMTP credentials, API keys, or `.env` files.

## Configure the sender in Supabase

1. In the Supabase dashboard, open the project's **Project Settings > Authentication** (the exact label can vary by dashboard version).
2. Enable the custom SMTP provider.
3. Enter the provider's SMTP host, port, username, and password using the provider-issued values.
4. Set the sender email to the verified no-reply address and the sender name to **Ethiopian Startup School**.
5. Save the settings in the intended Supabase environment.
6. Keep credentials in the Supabase dashboard's secret fields; do not paste them into repository files, issue comments, or logs.
7. Check the project's Auth email rate limits and redirect URL allow-list independently of SMTP configuration.

## Test plan

- Send a test authentication email to addresses at more than one mailbox provider.
- Verify the sender name and verified sender address.
- Check inbox, spam/junk, and message headers for SPF, DKIM, and DMARC results.
- Exercise sign-up confirmation, magic link, password reset, email change, invitation, and reauthentication templates that the project uses.
- Verify each link or code works and returns to the correct site's allowed redirect URL.
- Confirm Supabase logs and the SMTP provider's delivery events show no authentication or relay failures.
- Repeat after DNS or provider changes, and monitor DMARC reports and delivery rates.
- Test expected rate-limit behavior without repeatedly sending to real users; use controlled test accounts and provider test tooling where available.

Custom SMTP can improve delivery control and branding. It is not a guarantee of inbox placement and may incur provider charges under the provider's own plan.
