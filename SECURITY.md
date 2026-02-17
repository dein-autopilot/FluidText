# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| Latest  | ✅ Yes             |

## Reporting a Vulnerability

If you discover a security vulnerability in FluidText, please report it responsibly:

1. **Do NOT open a public issue.** Security vulnerabilities should be reported privately.
2. **Email:** Open a [private security advisory](https://github.com/dein-autopilot/FluidText/security/advisories/new) on GitHub.
3. **Include:** A clear description of the vulnerability, steps to reproduce, and the potential impact.

We will acknowledge your report within 48 hours and aim to release a fix within 7 days for critical issues.

## Scope

The following are considered in scope:

- Code execution vulnerabilities
- Unauthorized data access or exfiltration
- Settings file injection or manipulation
- Dependency supply chain issues

The following are **not** in scope:

- Issues requiring physical access to the machine
- Denial of service on a local application
- Social engineering attacks
- Issues in third-party dependencies (report those upstream)

## Security Design

FluidText is designed with privacy and security in mind:

- **No network access during normal operation** — The app only connects to the internet for the initial model download from Hugging Face (public, unauthenticated). After that, all processing is local.
- **No telemetry or analytics** — No usage data is collected or transmitted.
- **No authentication or user accounts** — The app has no login, no tokens, no API keys.
- **Local-only storage** — Settings are stored as plain JSON in the user's local app data directory. No sensitive data (passwords, tokens) is stored.
- **No remote code execution** — The app does not execute any remotely fetched code.

### Known Security Considerations

- The `keyboard` library requires elevated privileges (or root on Linux) to capture global hotkeys. This is inherent to push-to-talk functionality.
- Model downloads use HTTPS from Hugging Face. SSL certificates are verified via `certifi`.
- The app uses `keyboard.write()` to inject text at the cursor. This simulates keystrokes and could theoretically be observed by keyloggers — this is the same mechanism used by any text expansion tool.
