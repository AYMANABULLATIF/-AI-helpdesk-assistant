# Basic Network Troubleshooting Guide

## Common Symptoms
- User has no internet access.
- User cannot reach internal websites or shared drives.
- Wi-Fi disconnects frequently.
- Only one application cannot connect.

## Tier-1 Checklist
1. Confirm whether the issue affects Wi-Fi, wired network, VPN, or all connections.
2. Ask whether other users in the same area are affected.
3. Have the user restart the affected application and browser.
4. Confirm airplane mode is off and Wi-Fi is connected to the correct network.
5. Ask the user to forget and reconnect to Wi-Fi if credentials may be stale.
6. Restart the device if network adapters appear stuck.
7. Test access to a public website and a known internal website.
8. Collect the user's location, device name, IP address, and error message.

## Useful Commands
- `ipconfig` shows the current IP address.
- `ipconfig /release` and `ipconfig /renew` can refresh a DHCP lease when approved.
- `ping` can test basic reachability.
- `nslookup` can test DNS resolution.

## Escalation Notes
Escalate to Network Support if multiple users are affected, the device cannot obtain an IP address, DNS fails for internal resources, or network equipment may be down.
