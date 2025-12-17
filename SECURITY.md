# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow these steps:

### Do NOT

- Open a public GitHub issue
- Disclose the vulnerability publicly before it's fixed
- Test vulnerabilities on production systems

### Do

1. **Email us directly** at security@nodo.ai
2. Include a detailed description of the vulnerability
3. Provide steps to reproduce if possible
4. Allow reasonable time for us to fix the issue

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix Timeline**: Depends on severity (critical: 24-48h, high: 1 week, medium: 2 weeks)

### Rewards

We currently do not have a formal bug bounty program, but we acknowledge security researchers who responsibly disclose vulnerabilities.

## Security Best Practices for Users

### API Keys

- Never commit API keys to version control
- Use environment variables for all secrets
- Rotate keys regularly
- Use different keys for development and production

### Self-Hosting

- Keep dependencies updated
- Use HTTPS in production
- Set up proper firewall rules
- Enable rate limiting
- Monitor for unusual activity

### Solana Wallet Security

- Never share your private key
- Use a dedicated wallet for NODO payments
- Start with small amounts
- Verify transaction details before signing

## Known Security Measures

### In Place

- ✅ Input validation on all API endpoints
- ✅ Rate limiting
- ✅ Secure payment verification
- ✅ No storage of sensitive credentials in plaintext
- ✅ Dependency vulnerability scanning in CI

### Planned

- 🔄 Two-factor authentication for accounts
- 🔄 API key scoping (read-only vs read-write)
- 🔄 Webhook signature verification

