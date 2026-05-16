# Test-Driven Development

Use this skill before implementing any feature or fixing any bug.

## When to use

- Before writing implementation code
- When adding new functionality
- When fixing a bug that can be reproduced

## Process

1. Define expected behavior clearly
2. Write a minimal test that fails (proves the bug or missing feature)
3. Run the test to confirm it fails
4. Write the minimal implementation to make the test pass
5. Run the test to confirm it passes
6. Refactor if needed, keeping tests green

## Testing pattern (this project)

- Python: use pytest or a standalone test script
- Verify with real data where possible (not mocks)
- Test edge cases: empty data, None values, network failures, encoding issues
- Run the actual script after unit tests pass
