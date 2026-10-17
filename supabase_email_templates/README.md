# Supabase authentication email templates

These files are branded starting points for Ethiopian Startup School authentication emails. Review the sender and redirect settings in Supabase before enabling them. The Amharic, Afaan Oromo, and Tigrinya confirmation templates are drafts and **need native review** before use.

## Templates and subjects

| Supabase template | Suggested subject | Files |
| --- | --- | --- |
| Confirm signup | Welcome to Ethiopian Startup School! Please confirm your email | `confirm_signup.html`, `confirm_signup.txt` |
| Magic link | Your Ethiopian Startup School sign-in link | `magic_link.html`, `magic_link.txt` |
| Reset password | Reset your Ethiopian Startup School password | `reset_password.html`, `reset_password.txt` |
| Change email address | Confirm your Ethiopian Startup School email change | `change_email.html`, `change_email.txt` |
| Invite user | Your Ethiopian Startup School invitation | `invite.html`, `invite.txt` |
| Reauthentication | Confirm your Ethiopian Startup School identity | `reauthentication.html`, `reauthentication.txt` |

The confirmation drafts are provided as `confirm_signup.am.*`, `confirm_signup.om.*`, and `confirm_signup.ti.*`. Their language codes are Amharic (`am`), Afaan Oromo (`om`), and Tigrinya (`ti`).

## Paste templates into Supabase

1. Open the Supabase project dashboard for the intended environment.
2. Go to **Authentication > Email Templates**.
3. Choose the matching template type from the table above.
4. Set the subject to the suggested subject shown above.
5. Open the corresponding `.html` file and paste its contents into the HTML body/editor.
6. Where the Supabase editor provides a plain-text body field, paste the corresponding `.txt` file into it.
7. Save the template, then repeat for each authentication email type you use.
8. Keep the confirmation templates labelled `needs native review` out of production until reviewed by a fluent native speaker.
9. Verify the project's **Authentication > URL Configuration** site URL and allowed redirect URLs match the intended environment. The templates use Supabase's `{{ .SiteURL }}` and `{{ .ConfirmationURL }}` variables.

Do not paste the language-draft filenames into a production template before their review. Supabase authentication templates are configured per project; confirm you are editing the intended project before saving.

## Sign-up email test checklist

- Sign up using a new test email address.
- Confirm the email uses the intended sender name, subject, and branded layout.
- Check the inbox and spam/junk folder.
- Confirm the recipient's name displays, and verify the fallback greeting by testing an account without `user_metadata.full_name`.
- Click **Confirm my email** and verify that the confirmation completes successfully.
- Confirm the browser returns to the correct environment and redirect URL.
- Test the visible `{{ .ConfirmationURL }}` fallback link as well as the button.
- Confirm the sign-in flow behaves correctly after confirmation.
- Check that a generated URL or token from one environment is never sent as part of a test for another environment.
