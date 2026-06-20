# VPN Troubleshooting Guide

## Common Symptoms
- User cannot connect to the VPN from home.
- VPN client shows authentication failed, timeout, or no network available.
- VPN connects but internal sites, file shares, or remote desktop do not load.

## Tier-1 Checklist
1. Confirm the user has working internet access outside the VPN by opening a public website.
2. Confirm the user is using the approved VPN client and the correct company VPN profile.
3. Ask the user to fully close and reopen the VPN client, then try signing in again.
4. Verify the user's username format, password, and MFA approval prompt.
5. Check whether the account is locked, password expired, or MFA method unavailable.
6. Ask the user to restart the computer if the VPN adapter appears stuck.
7. Confirm the date and time on the device are correct.
8. Ask whether other users are reporting similar VPN issues.

## When VPN Connects But Apps Do Not Work
- Ask the user to disconnect and reconnect to the VPN.
- Confirm the user is trying to access the correct internal hostname or URL.
- Test a known internal resource such as the intranet homepage.
- Run `ipconfig /all` and confirm the VPN adapter has a company DNS server.
- If DNS appears incorrect, escalate to Network Support.

## Escalation Notes
Escalate to Network Support if multiple users are affected, the VPN gateway appears unavailable, DNS routes are missing, or the user receives repeated connection timeouts after basic checks.
