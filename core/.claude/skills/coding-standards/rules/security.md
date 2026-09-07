# Cursor AI Development Rules - Security & Best Practices

## Critical Security Rules

These rules apply to ALL projects regardless of language or framework.

## Secrets & Credentials Management

1. **NEVER commit sensitive data**: API keys, passwords, tokens, credentials, private keys, or any secrets. Use environment variables (.env files) and add .env to .gitignore. **Exception**: For Azure Functions projects, use `local.settings.json` instead of `.env` files (see CURSOR_RULES_AZURE.md).

2. **Include configuration template**: Create a template showing required environment variables without actual values. Use `.env.example` for standard projects, or `local.settings.json.template` for Azure Functions projects.
```
   # .env.example (standard projects)
   API_KEY=your_api_key_here
   DATABASE_URL=your_database_url_here
   
   # OR local.settings.json.template (Azure Functions)
   {
     "Values": {
       "API_KEY": "your_api_key_here",
       "DATABASE_URL": "your_database_url_here"
     }
   }
```

3. **Use different credentials for each environment**: Never use production credentials in development or staging. Keep environments isolated.

4. **Rotate secrets regularly**: Especially after team member departures or suspected compromise.

5. **Use secret management tools**: For production, use AWS Secrets Manager, Azure Key Vault, HashiCorp Vault, or similar. Never hardcode production secrets.

## Input Validation & Sanitization

6. **Validate ALL user inputs**: Never trust client-side data. Validate on the server side.

7. **Sanitize user inputs**: Strip or escape potentially dangerous characters before processing or storing data.

8. **Whitelist over blacklist**: Define what IS allowed rather than trying to block what ISN'T. Blacklists are incomplete.

9. **Type validation**: Ensure data matches expected types. Use TypeScript interfaces, Pydantic models, or JSON schemas.

10. **Range and format validation**: Check that numbers are in acceptable ranges, strings match expected patterns (email, phone, etc.).

## Authentication & Authorization

11. **Server-side authentication**: Never rely solely on client-side checks. Always verify on the server.

12. **Principle of least privilege**: Users should only have access to what they need. Check authorization on every protected operation.

13. **Use established auth libraries**: Don't roll your own authentication. Use NextAuth.js, Passport.js, Django Auth, etc.

14. **Secure session management**: Use httpOnly cookies, secure flags, appropriate expiration times.

15. **Multi-factor authentication**: Implement or support MFA for sensitive operations.

## Database Security

16. **Use parameterized queries or ORMs**: NEVER concatenate user input into SQL queries. Prevents SQL injection.
```javascript
   // BAD - SQL injection vulnerability
   const query = `SELECT * FROM users WHERE id = ${userId}`;
   
   // GOOD - parameterized query
   const query = 'SELECT * FROM users WHERE id = ?';
   db.query(query, [userId]);
```

17. **Principle of least privilege for DB access**: Application database users should only have necessary permissions.

18. **Encrypt sensitive data at rest**: PII, financial data, health information should be encrypted in the database.

19. **Use connection pooling securely**: Don't expose database connection strings in logs or error messages.

## API Security

20. **Rate limiting**: Implement rate limiting on all public APIs to prevent abuse and DoS attacks.

21. **Use HTTPS only**: Never transmit sensitive data over HTTP. Enforce HTTPS in production.

22. **CORS configuration**: Be specific about allowed origins. Never use `*` in production.

23. **API key security**: If using API keys, rotate them regularly, use different keys for different services, never expose in client code.

24. **Input size limits**: Limit request body sizes, file upload sizes, and query parameter lengths to prevent DoS.

## Frontend Security

25. **XSS prevention**: Sanitize user-generated content before rendering. Use frameworks that escape by default (React does this).

26. **Content Security Policy (CSP)**: Implement CSP headers to prevent XSS and injection attacks.

27. **Avoid eval() and similar**: Never use eval(), Function constructor, or innerHTML with user data.

28. **Secure localStorage/sessionStorage usage**: Don't store sensitive data (tokens, passwords) in localStorage. Use httpOnly cookies instead.

## Dependency Security

29. **Keep dependencies updated**: Regularly update packages to patch security vulnerabilities.

30. **Audit dependencies**: Run `npm audit`, `pip-audit`, or similar regularly. Fix critical vulnerabilities immediately.

31. **Review dependencies before adding**: Check package popularity, maintenance status, and security history before adding new dependencies.

32. **Lock file usage**: Commit package-lock.json, yarn.lock, or poetry.lock to ensure consistent dependency versions.

## Error Handling & Logging

33. **Never expose stack traces in production**: Users shouldn't see detailed error messages. Log them server-side instead.

34. **Sanitize error messages**: Don't leak sensitive information (paths, database structure, internal IPs) in error messages.

35. **Log security events**: Log authentication attempts, authorization failures, unusual access patterns.

36. **Secure logging**: Don't log sensitive data (passwords, tokens, credit cards, SSNs). Redact if necessary.

## File Upload Security

37. **Validate file types**: Check both extension AND content type (magic bytes). Don't trust client-provided MIME types.

38. **Limit file sizes**: Prevent DoS through large file uploads.

39. **Scan for malware**: Use antivirus scanning for user-uploaded files.

40. **Store uploads outside webroot**: Uploaded files shouldn't be directly accessible via URL without authorization check.

41. **Generate random filenames**: Don't use user-provided filenames. Generate random names to prevent path traversal attacks.

## Data Privacy & Compliance

42. **Minimal data collection**: Only collect data you actually need. Follow data minimization principles.

43. **Anonymize PII**: Personal Identifiable Information should be anonymized in logs, analytics, and non-production environments.

44. **Data retention policies**: Delete data when no longer needed. Document retention policies.

45. **GDPR/CCPA compliance**: If applicable, implement right to access, right to deletion, data portability.

46. **Secure data transmission**: Use TLS 1.2+ for all data in transit. Disable older protocols.

## Session & Token Security

47. **Short-lived tokens**: Use short expiration times for access tokens. Implement refresh token rotation.

48. **Token storage**: Store tokens securely (httpOnly cookies or secure storage, never localStorage for sensitive tokens).

49. **Logout implementation**: Properly invalidate sessions/tokens on logout. Clear client-side storage.

50. **CSRF protection**: Implement CSRF tokens for state-changing operations.

## Security Testing

51. **Security testing in CI/CD**: Include security scans (SAST, dependency checks) in your pipeline.

52. **Penetration testing**: For production applications, conduct regular penetration testing.

53. **Code review for security**: Security-focused code reviews for authentication, authorization, and data handling code.

## Incident Response

54. **Have a plan**: Document incident response procedures. Who to contact, what to do.

55. **Monitor for anomalies**: Set up alerts for unusual activity (failed login attempts, unusual API usage, etc.).

56. **Security updates**: Have a process for quickly deploying security patches.

## Documentation

57. **Document security decisions**: Explain why certain security measures were chosen, what threats they mitigate.

58. **Security onboarding**: New team members should be trained on security practices.

59. **Threat modeling**: For complex features, document potential threats and mitigations.

## Git & Version Control Security

60. **Scan commits for secrets**: Use tools like git-secrets, truffleHog, or GitGuardian to catch accidentally committed secrets.

61. **Review commit history**: Before open-sourcing, audit entire history for secrets.

62. **Protected branches**: Require reviews for main/production branches. Prevent force pushes.

## Cloud & Infrastructure Security

63. **Principle of least privilege for cloud**: IAM roles should have minimal necessary permissions.

64. **Network segmentation**: Use VPCs, security groups, and firewalls appropriately.

65. **Backup security**: Encrypt backups. Test restoration procedures. Store backups securely.

66. **Regular security audits**: Review cloud configurations, access logs, and permissions regularly.

---

## Security Checklist by Phase

### Before Writing Code
- [ ] Understand data sensitivity and compliance requirements
- [ ] Plan authentication and authorization strategy
- [ ] Set up secret management (environment variables, or local.settings.json for Azure Functions)
- [ ] Configure .gitignore to exclude secrets and sensitive files (.env or local.settings.json)

### During Development
- [ ] Validate ALL user inputs server-side
- [ ] Use parameterized queries or ORMs
- [ ] Implement proper error handling (no stack traces to users)
- [ ] Use established auth libraries
- [ ] Never hardcode secrets
- [ ] Sanitize data before rendering
- [ ] Implement rate limiting on APIs

### Before Deployment
- [ ] Audit dependencies (`npm audit`, `pip-audit`)
- [ ] Review code for security issues
- [ ] Ensure HTTPS is enforced
- [ ] Configure CSP headers
- [ ] Set up proper CORS
- [ ] Test authentication and authorization
- [ ] Verify secrets are not in code or version control
- [ ] Set up logging and monitoring

### Production Monitoring
- [ ] Monitor for unusual activity
- [ ] Regularly update dependencies
- [ ] Review access logs
- [ ] Rotate credentials periodically
- [ ] Conduct security audits

## Quick Reference by Threat

### SQL Injection Prevention
- Use parameterized queries or ORMs
- Never concatenate user input into queries
- Validate input types and formats

### XSS Prevention
- Use frameworks that escape by default
- Sanitize user-generated content
- Implement CSP headers
- Never use eval() or innerHTML with user data

### Authentication Bypass Prevention
- Server-side verification always
- Short-lived tokens with refresh rotation
- Secure session management
- MFA for sensitive operations

### Data Breach Prevention
- Encrypt sensitive data at rest and in transit
- Principle of least privilege
- Never commit secrets
- Anonymize PII in non-production
- Regular security audits

### DoS Prevention
- Rate limiting on all APIs
- Input size limits
- File size limits
- Timeout configurations

### CSRF Prevention
- CSRF tokens for state-changing operations
- SameSite cookie attributes
- Verify origin headers