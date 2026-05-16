# Systematic Debugging

Use this skill when encountering any bug, test failure, or unexpected behavior — before proposing a fix.

## When to use

- Error messages or tracebacks appear
- Tests fail unexpectedly
- Code behaves differently than expected

## Process

1. Read the full traceback — do not guess
2. Identify the exact line where the error occurs
3. Check: encoding issues? import conflicts? network errors? data issues?
4. Verify the root cause by reproducing
5. Fix the root cause, not the symptom
6. Verify the fix resolves the issue

## Common issues (this project)

- Encoding: check file contains Chinese characters, ensure encoding="utf-8"
- Import: akshare vs yfinance conflict, sys.path issues
- Network: proxy settings (NO_PROXY vs VPN)
- Data: print raw API response to check structure
