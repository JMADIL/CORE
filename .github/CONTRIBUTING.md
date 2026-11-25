# Contributing to Core

Bug reports, documentation improvements, and focused pull requests are welcome.
For larger changes, open an issue first to agree on the scope.

## Local setup

Follow [Run locally](../README.md#run-locally) for dependencies and configuration.
Use your own provider credentials. Never commit `.env`, database files, tokens,
generated private media, or logs containing conversation content.

## Before submitting a pull request

- Explain the problem and the resulting behavior.
- Keep changes focused and update documentation when behavior or setup changes.
- Run the relevant checks described in [Tests](../README.md#tests). Frontend changes
  should pass lint, tests, build, and type checking; backend changes should pass
  the backend tests. Note any checks you could not run.
- Add a regression test when fixing meaningful behavior, and screenshots for UI changes.
- Use synthetic examples and redact private information in issues and screenshots.

Do not use the shared public demo to run automated or paid-media tests. Mock
provider calls for automated tests and use an isolated database.

Report security vulnerabilities privately using the [security policy](SECURITY.md).
Contributions are provided under the repository's [MIT License](../LICENSE).
