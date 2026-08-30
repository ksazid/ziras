# codex-security plugin

This directory defines the optional boundary for the **codex-security** capability.

- Core repository files must not depend on this plugin unless it is enabled in `.engineering/PROFILE.yaml`.
- Plugins may add skills, scripts, checks or templates, but must not silently change product policy.
- Enabling a plugin requires human approval and a recorded reason.
