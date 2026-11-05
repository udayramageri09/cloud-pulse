# Architecture and design notes

## Data flow

`cli.py` validates user input and selects checks. `checks.py` returns one JSON-compatible dictionary per check, including a status and measured values. Linux host metrics use `/proc`; disk usage uses the standard library. `report.py` renders the same report object as readable text or JSON. `main()` sets a failing process status if any check is not `ok`.

## Failure handling

DNS, TCP, and HTTP checks catch expected network exceptions and return the exception text with an `error` status. TCP and HTTP operations use finite timeouts. Process enumeration skips processes that exit during collection or deny access. Metrics are observations; thresholds are limited to a 90% warning for memory and disk.

## Boundaries

The tool inspects the machine where it runs. It does not SSH to remote systems, collect logs, infer root cause, or persist reports unless the user specifies an output path. The Docker lab is an isolated local target and demonstrates observable symptoms (503, 500, and proxy upstream failure).
