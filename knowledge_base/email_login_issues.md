# Email Login Issues Guide

## Common Symptoms
- User cannot access Outlook or webmail.
- User repeatedly receives a password prompt.
- MFA prompt does not appear or is sent to an old phone.
- Outlook says disconnected, trying to connect, or needs password.

## Tier-1 Checklist
1. Confirm whether the user can sign in to webmail in a browser.
2. Verify the username format and whether the password works for other company services.
3. Check for account lockout, expired password, disabled account, or recent password change.
4. Confirm MFA method availability and whether push notifications are blocked.
5. Ask the user to try a private browser window to rule out cached credentials.
6. Check service health or internal alerts for email outages.
7. If webmail works but Outlook fails, restart Outlook and clear saved credentials if approved.
8. Confirm the user's mailbox is licensed and active.

## Outlook Client Isolation
If webmail works but Outlook does not, the issue is likely local to the Outlook profile, cached credentials, add-ins, or network connectivity. Escalate if profile repair or recreation is required by policy.

## Escalation Notes
Escalate to Messaging Support if the mailbox is missing, licensing is incorrect, many users are affected, or the user cannot receive MFA despite verified identity.
