# Security Audit Standards — Web Application

## Scope

Audit the web application source code for common security vulnerabilities and best practices.

## Standards

### SEC-01: No Hardcoded Secrets
Credentials, API keys, tokens, and passwords must not appear in source code.
- Check: `grep -rn "password\|secret\|api_key\|token" --include="*.js" --include="*.ts" --include="*.py"`
- Severity if violated: **Critical**

### SEC-02: Input Validation
All user inputs must be validated before use. No direct use of `req.body`, `req.query`, or `req.params` without validation.
- Check: Look for unvalidated input in route handlers
- Severity if violated: **High**

### SEC-03: No eval() or Dynamic Code Execution
`eval()`, `Function()`, `setTimeout(string)` must not be used with user-controlled input.
- Check: `grep -rn "eval\|new Function" --include="*.js" --include="*.ts"`
- Severity if violated: **Critical**

### SEC-04: Dependency Security
All dependencies should be up-to-date without known vulnerabilities.
- Check: `npm audit` or `pip audit`
- Severity if violated: **High**

### SEC-05: Error Handling
Errors must not leak stack traces or internal details to end users.
- Check: Look for unhandled promise rejections, raw error forwarding
- Severity if violated: **Medium**

### SEC-06: Authentication & Authorization
Protected routes must verify authentication. Authorization checks must be present for resource access.
- Check: Look for routes without auth middleware
- Severity if violated: **High**
