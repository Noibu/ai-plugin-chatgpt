# Site-save permission preflight and recovery

Read this before every Save as Live Site build/publish, including natural-language requests and resumes. It is a readiness check for the current execution environment, not permission to change security settings. No Codex installation is required. Noibu authentication, Sites availability, shell/network access and approval policy are separate controls.

## Before starting a publishing helper

1. Discover the actual Sites tools/skill and read their current publishing instructions. Use native permission metadata/current execution restrictions when available; do not scan unrelated configuration or ask for credentials. A selected menu label, editable config file, or successful HTTPS check alone does not prove a source upload can be approved.
2. Check the intended project directory is writable, build dependencies can be obtained through the permitted path, and the documented Sites publishing operation can use its secure credential-input workflow. Check only relevant capability metadata or safe read-only diagnostics; never start a credentialed upload merely to test permissions. Unknown approval support is unknown, not a failure or success.
3. If the current tools support a narrow permission request for the required directory/network/publish operation, present that native approval at the point of need. Request only the necessary scope, once. Do not request unrestricted access or change the user's global settings as part of saving a dashboard. Use any required escalation mode on the process launch itself; a later terminal write is not an escalation request and cannot upgrade an already-running process.
4. If approval is disabled or rejected, stop at the failed phase, preserve the report/project/source/audience, and use the applicable recovery below. Do not loop on `write_stdin`, start duplicate uploaders, change credential transport, or route around policy. A network grant does not imply terminal/sandbox approval. Report the exact denial category without inventing which filesystem/network action triggered it.

A completed Sites connector listing without Noibu is a missing integration, not a policy denial. The [dashboard connection fallback](connected-dashboard.md#optional-visitor-connected-mode) may use supported direct server-side OAuth after capability checks. This never overrides an explicit security/administrator restriction, rejected approval, or unsupported runtime.

## Desktop/local: guide the user, do not silently switch modes

Explain: “Publishing needs permission for the Sites source-upload operation. Open the permission control below this chat's composer and select an allowed mode that can request approval. If you use your local configuration, select **Custom (config.toml)** in this chat. Then tell me to resume.” Check what is actually selected, not just which modes are listed. Ask for approval is normally a reasonable starting point; Custom is useful when a reviewed local configuration is intended. Do not claim either guarantees publishing or tell the user to use Full access.

There is no permission-switch API supplied by this plugin. Do not invent one or automate the security menu. Native scoped approval requests are the automatic path when supported; changing the selected mode remains the user's action. If the control is missing, distinguish web/cloud from local desktop and check current platform guidance rather than sending the user to a guessed admin menu.

### Optional non-managed local configuration

Use this only when the user controls their local configuration and wants this setup. It is not an install prerequisite for ordinary analytics or a universal requirement for Sites. Explain that this grants sandboxed commands network access and allows approval requests for operations outside the boundary. The user can review/merge the following **TOML** settings into `~/.codex/config.toml`, then select **Custom (config.toml)** below the current chat's composer:

```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true
```

Do not overwrite the whole file or duplicate tables. Root settings belong at the TOML root, not inside another table. Preserve unrelated configuration. Do not combine this legacy sandbox configuration with a modern `default_permissions` / named-permissions profile setup; use the current platform's profile guidance instead. A granular approval policy that disables `sandbox_approval` can still block the operation; replacing it is a security-setting change that the user must deliberately review, not an automatic repair. Managed requirements take precedence and must not be removed or bypassed. Do not edit configuration unless the user separately requests that exact change and the available tools/policy authorize it.

After a setting change, let any current code/shell run finish and allow the execution environment to refresh. Recheck effective permissions on resume. Do not claim a file edit changed an already-running helper. If the app requires a fresh chat, carry over the exact existing project/source identity and report so it can resume without creating a second Site.

## Web/cloud or managed environment

ChatGPT web has no local composer sandbox-mode selector. Use its supported network/approval controls and Sites workflow if available; do not instruct web users to edit a local file. A managed/local restriction needs the administrator responsible for the actual execution policy. State the specific failed operation and denial; do not promise an “Agent security” page is available in every workspace. A missing tool, approval category, or control is an explicit blocker—not a request to use another transport or weaken workspace security.

## Resume safely

Inspect the existing helper/job, saved versions and deployment state before retrying. Stop only the identified helper through supported controls if needed. If its state cannot be established or stopping it is denied, report that uncertainty and do not start a parallel upload. Once it has ended and permissions are effective, resume the current Sites skill's supported workflow from the last verified phase, using a fresh properly authorized process only if required. Keep credentials in the documented secure input path, never in arguments, files, logs or copyable prompts.

Return a real published URL only after a successful deployment. Distinguish build success, publication, persisted-data verification and scheduled-refresh readiness. A successful local grant or the user's prior successful Site does not prove this execution context's permissions. Conversely, a historical denial is not proof the user's newly configured session is still blocked.

Official guidance: [permission modes](https://learn.chatgpt.com/docs/permission-modes), [sandboxing](https://learn.chatgpt.com/docs/sandboxing), [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference), [managed configuration](https://learn.chatgpt.com/docs/enterprise/managed-configuration).
