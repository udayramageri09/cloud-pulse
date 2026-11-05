# CloudPulse interview preparation

Explain what is implemented and where it stops. Run each demo yourself before discussing it.

## Walk-through

1. **Why a CLI?** It makes repeatable first-response checks easy to run and script without hiding the underlying signals.
2. **How do checks work?** Host metrics are parsed from Linux `/proc` (`/proc/stat`, `/proc/meminfo`, `/proc/uptime`, `/proc/<pid>/status`) plus `shutil.disk_usage`, with no third-party dependencies; DNS uses `getaddrinfo`; TCP uses `create_connection`; HTTP uses `urllib` with a timeout. Each returns structured data consumed by two renderers.
3. **How is failure handled?** Expected socket/URL failures become error results. A failed result affects the CLI exit code. The tool does not assert a root cause.
4. **What does the lab prove?** The same URL can show 200, 500, 503, or a proxy upstream failure depending on the app state/configuration. TCP reachability alone does not prove application health.
5. **What remains limited?** It inspects only the local host, has simple fixed thresholds, does not gather logs automatically, and has no cloud deployment or continuous monitoring.

## Scenario prompts

- **High CPU:** Compare process activity and repeated measurements; check whether load is sustained and inspect the relevant service before restarting it.
- **Disk full:** Use `df -h` to identify the filesystem and `du` to locate large directories; check logs/temp files and preserve evidence before cleanup.
- **DNS fails but IP works:** Separate name resolution from routing/TCP; inspect resolver configuration and query the same name with a second approved resolver.
- **TCP succeeds but HTTP fails:** The listener is reachable, but the application/proxy may return an error, reject a path, or time out; inspect status, latency, and server logs.
- **502 vs 503:** 502 commonly indicates a gateway could not obtain a valid upstream response; 503 says the service is unavailable/overloaded/under maintenance. Confirm with proxy and application logs rather than relying on status alone.
- **Process disappears during collection:** Processes are dynamic; handle `NoSuchProcess` and access-denied conditions without aborting the entire report.

## Before claiming the project

- Run the automated tests and host-only CLI locally.
- If mentioning Docker simulation, run all four scenarios and inspect container logs.
- Be ready to explain timeout choices, exit codes, test mocks, and why checks report symptoms rather than root causes.
