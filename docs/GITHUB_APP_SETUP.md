# InDE v5.1b.0 - GitHub App Setup Guide

This guide walks you through creating a GitHub App for InDE enterprise connector integration.

## Prerequisites

- GitHub organization owner or admin access
- InDE deployed in CINDE mode
- Access to InDE server environment variables

## Step 1: Create the GitHub App

1. Go to your GitHub organization settings:
   ```
   https://github.com/organizations/YOUR-ORG/settings/apps
   ```

2. Click **"New GitHub App"**

3. Fill in the basic information:

   | Field | Value |
   |-------|-------|
   | **GitHub App name** | `InDE Connector - YOUR-ORG` |
   | **Description** | InDE enterprise integration for team and membership sync |
   | **Homepage URL** | `https://your-inde-domain.com` |

## Step 2: Configure Callback URL

Set the **Callback URL** to your InDE OAuth callback endpoint:

```
https://your-inde-domain.com/api/v1/connectors/github/callback
```

**Important:** This must be HTTPS in production.

## Step 3: Configure Webhook URL

Set the **Webhook URL** to your InDE webhook receiver:

```
https://your-inde-domain.com/api/v1/webhooks/github
```

Enable **Active** checkbox.

## Step 4: Generate Webhook Secret

Generate a secure webhook secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Enter this value in the **Webhook secret** field.

Save this value - you'll need it for `GITHUB_APP_WEBHOOK_SECRET`.

## Step 5: Set Permissions

Navigate to **Permissions & events** section.

### Repository Permissions

| Permission | Access |
|------------|--------|
| Metadata | Read-only |

### Organization Permissions

| Permission | Access |
|------------|--------|
| Members | Read-only |
| Administration | Read-only |

### Account Permissions

None required.

## Step 6: Subscribe to Events

Check the following webhook events:

- [x] **Membership** - Organization membership changes
- [x] **Organization** - Organization events
- [x] **Team** - Team changes
- [x] **Team add** - Repository added to team
- [x] **Repository** - Repository events (optional)

## Step 7: Installation Options

Under **Where can this GitHub App be installed?**:

- Select **Only on this account** for single-org deployment
- Select **Any account** if InDE serves multiple GitHub orgs

## Step 8: Create the App

Click **"Create GitHub App"**

You'll be taken to the app settings page. Note the following values:

- **App ID** - Numeric ID at the top of the page
- **Client ID** - In the "About" section
- **Client secret** - Click "Generate a new client secret" and save it immediately

## Step 9: Generate Private Key

1. Scroll to **Private keys** section
2. Click **"Generate a private key"**
3. A `.pem` file will be downloaded
4. Store this file securely on your InDE server

Example location:
```
/opt/inde/secrets/github-app-private-key.pem
```

Secure the file:
```bash
chmod 600 /opt/inde/secrets/github-app-private-key.pem
chown inde:inde /opt/inde/secrets/github-app-private-key.pem
```

## Step 10: Configure InDE Environment

Add the following to your InDE deployment environment:

```bash
# GitHub App Configuration
GITHUB_APP_ID=123456                                    # Your App ID
GITHUB_APP_CLIENT_ID=Iv1.abc123def456                   # Your Client ID
GITHUB_APP_CLIENT_SECRET=your-client-secret             # From Step 8
GITHUB_APP_WEBHOOK_SECRET=your-webhook-secret           # From Step 4
GITHUB_APP_PRIVATE_KEY_PATH=/opt/inde/secrets/github-app-private-key.pem

# Connector encryption key (generate once, never change)
CONNECTOR_ENCRYPTION_KEY=your-64-char-hex-key
```

Generate encryption key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Step 11: Restart InDE

Restart the InDE application to load the new configuration:

```bash
docker-compose restart inde-app
```

Or if using systemd:
```bash
systemctl restart inde
```

## Step 12: Install the App

1. Log into InDE as an organization admin
2. Navigate to Settings → Connectors
3. Find GitHub in the connector list
4. Click **Install**
5. You'll be redirected to GitHub to authorize the app
6. Select your organization and confirm

## Verification

After installation, verify the connection:

1. Check connector status in Settings → Connectors
   - Status should show "HEALTHY"

2. Check API endpoint:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        https://your-inde-domain.com/api/v1/connectors/github/status
   ```

3. Trigger a test webhook:
   - Add a member to your GitHub organization
   - Check InDE logs for webhook receipt
   - Verify in Settings → Connectors → GitHub → Events

## Troubleshooting

### "Invalid signature" on webhooks

1. Verify `GITHUB_APP_WEBHOOK_SECRET` matches GitHub App settings
2. Check for any proxy/load balancer modifying request body

### "Invalid or expired OAuth state"

1. OAuth states expire after 10 minutes
2. Ensure clocks are synchronized (NTP)
3. Check MongoDB `connector_oauth_states` collection

### Health check shows "DEGRADED"

1. Installation access token may have expired
2. GitHub API may be rate limited
3. Check InDE logs for specific error

### App not appearing in connector list

1. Ensure `DEPLOYMENT_MODE=CINDE`
2. Verify all GitHub App environment variables are set
3. Check startup logs for connector initialization errors

## Security Best Practices

1. **Rotate client secret** periodically
2. **Store private key** in secure location with restricted permissions
3. **Use HTTPS** for all callback and webhook URLs
4. **Monitor webhook events** for unexpected activity
5. **Limit app permissions** to minimum required
6. **Audit installations** regularly

## Revoking Access

To disconnect GitHub from InDE:

1. In InDE: Settings → Connectors → GitHub → Uninstall
2. In GitHub: Organization Settings → GitHub Apps → Configure → Uninstall

Both steps are recommended for complete removal.

## Support

For issues with the GitHub connector:

1. Check InDE logs: `docker-compose logs inde-app`
2. Review webhook events in MongoDB
3. Verify GitHub App configuration matches InDE environment
4. Check GitHub status page for API issues
