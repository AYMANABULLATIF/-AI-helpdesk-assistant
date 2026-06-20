# Password Reset and Account Lockout Guide

## Common Symptoms
- User cannot sign in after several failed attempts.
- Account locked message appears.
- Password expired or must be changed.
- User replaced a phone and cannot approve MFA.

## Tier-1 Identity Verification
Before resetting a password or changing MFA, verify the user's identity using the approved company process. Do not reset credentials based only on an email request.

## Tier-1 Checklist
1. Confirm the affected username and contact method.
2. Verify the user's identity according to policy.
3. Check whether the account is locked, disabled, or expired.
4. Unlock the account if policy allows and no suspicious activity is present.
5. Guide the user through self-service password reset when available.
6. Confirm the user updates saved passwords on phone email apps, VPN clients, and mapped drives.
7. Check whether repeated lockouts are caused by old credentials on another device.
8. Escalate suspicious sign-in activity to Security Operations.

## MFA Issues
If the user cannot access MFA, verify identity first. Then follow the approved MFA reset process. Ask whether the user changed phones, phone numbers, authenticator apps, or notification settings.

## Escalation Notes
Escalate to Identity and Access Management if the account is disabled, permissions are missing, MFA cannot be reset by Tier-1, or repeated lockouts continue after saved credentials are updated.
