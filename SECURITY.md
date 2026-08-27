# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in PRIVUM DNS Manager, please report it responsibly:

1. **Do not** open a public issue
2. Email security concerns
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a detailed response within 7 days.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Security Best Practices

### Installation Security

1. **Use strong secrets**
   ```bash
   # Generate a secure secret key
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **Change default passwords immediately**
   - The installer generates a random admin password
   - Delete `/opt/dns-manager/admin-password.txt` after noting the password

3. **Enable HTTPS**
   ```nginx
   # /etc/nginx/sites-available/dns-manager
   server {
       listen 443 ssl;
       ssl_certificate /etc/ssl/certs/dns-manager.crt;
       ssl_certificate_key /etc/ssl/private/dns-manager.key;
       # ... rest of config
   }
   ```

### Network Security

1. **Firewall Configuration**
   ```bash
   # Allow DNS only from trusted networks
   ufw allow from 192.168.0.0/16 to any port 53

   # Allow web interface only from management network
   ufw allow from 10.0.0.0/8 to any port 443
   ```

2. **Restrict zone transfers**
   - Zone transfers (AXFR) should only be allowed to known slave servers
   - The default configuration restricts this in `named.conf.options`

3. **DNS query logging**
   - Enable query logging for security monitoring
   - Logs are stored in `/var/log/named/named.log`

### Authentication Security

1. **Enable Two-Factor Authentication**
   - Go to Profile > Security > Enable 2FA
   - Use a TOTP app like Google Authenticator or Authy
   - Store backup codes securely

2. **SSO Integration (Recommended for enterprises)**
   - Configure Keycloak or another OIDC provider
   - Centralized authentication and audit logging
   - Group-based role mapping

3. **Password Policy**
   - Minimum 12 characters
   - Mix of uppercase, lowercase, numbers, symbols
   - No password reuse

### API Security

1. **CORS Configuration**
   ```bash
   # In .env - restrict to your domains
   CORS_ORIGINS=https://dns.example.com,https://admin.example.com
   ```

2. **Rate Limiting**
   - Login: 5 attempts per minute
   - API: 200 requests per minute
   - Backup: 5 per hour

3. **JWT Token Security**
   - Tokens expire after 30 minutes
   - Refresh tokens are rotated on each use
   - Tokens are invalidated on logout

### Database Security

1. **SQLite (default)**
   - Database file has 600 permissions
   - Located in `/opt/dns-manager/data/`
   - Regular backups recommended

2. **PostgreSQL (optional)**
   - Use strong database passwords
   - Enable SSL connections
   - Restrict network access

### Backup Security

1. **Encrypt backups**
   - Backups contain zone files and database
   - Store in secure location with restricted access

2. **Retention Policy**
   - Default: 7 daily, 4 weekly, 12 monthly
   - Old backups are automatically deleted

### Audit Logging

All administrative actions are logged including:
- User authentication (success/failure)
- Zone creation, modification, deletion
- Record changes
- User management
- Configuration changes

Logs are stored in the database and can be viewed in the web interface under **Audit Log**.

## Security Checklist

### Before Going to Production

- [ ] Changed admin password from installation default
- [ ] Deleted `/opt/dns-manager/admin-password.txt`
- [ ] Enabled HTTPS with valid SSL certificate
- [ ] Configured firewall rules
- [ ] Enabled 2FA for all admin accounts
- [ ] Reviewed CORS origins in `.env`
- [ ] Set up backup schedule
- [ ] Tested backup restoration
- [ ] Configured log monitoring/alerting

### Regular Maintenance

- [ ] Review audit logs weekly
- [ ] Rotate SSL certificates before expiration
- [ ] Update system packages monthly
- [ ] Test backups quarterly
- [ ] Review user access annually

## Known Security Considerations

1. **DNS Amplification**
   - Recursion is disabled by default
   - Only authoritative queries are served

2. **Zone File Injection**
   - Input validation on all record data
   - Special characters are escaped

3. **Session Management**
   - Sessions stored server-side
   - HTTP-only, secure cookies in production

## Compliance

This software can be configured to meet common compliance requirements:

- **Access Control**: RBAC with Admin/Operator/Viewer roles
- **Audit Trail**: Complete logging of all changes
- **Data Protection**: Encryption in transit (HTTPS), secure storage
- **Authentication**: 2FA, SSO support

---

For additional security questions, contact the PRIVUM team.
