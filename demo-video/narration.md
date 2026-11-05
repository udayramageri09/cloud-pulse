# Narration script

Exact text passed to the synthesizer for each scene (see [storyboard.md](storyboard.md) for the
matching visual). Spoken by Windows SAPI ("Microsoft David Desktop") at rate 165 -- a functional,
intelligible voice-over, not a studio voice actor; see [README.md](README.md) for why, and for how
to re-record this with a real voice if you want a polished version.

1. "CloudPulse is a lightweight Python toolkit for first response Linux and network diagnostics."
2. "When something breaks, the first few minutes matter most. Is the host healthy? Can the network
   even reach the target? CloudPulse automates asking those questions, consistently, every time."
3. "It starts with the host itself: CPU, memory, disk usage, uptime, and the top processes by
   memory, read straight from Linux proc, with no third party dependencies."
4. "Then the network: DNS resolution, a TCP connection, and an HTTP health check, each with its
   own timeout, so a hung connection never hangs the whole report."
5. "To prove it against real failures, CloudPulse ships its own lab: a demo application behind an
   Nginx reverse proxy, running locally in Docker."
6. "Stop the application, and the proxy can still be reached, but it can no longer reach its
   upstream. CloudPulse reports that precisely: TCP okay, HTTP critical, a gateway timeout."
7. "The real Nginx log confirms it: a connection attempt to the stopped container's address that
   simply timed out."
8. "A different failure: the application is running, but one route deliberately returns an
   internal server error. CloudPulse captures the five hundred status directly from the
   application."
9. "And a third case: the application is up, but reports itself not ready. A five oh three,
   distinct from both the timeout and the application error before it."
10. "Every run also produces a structured incident report: an incident ID, host information, a
    severity for each check, and suggested next steps. Never a guessed root cause."
11. "All of this is backed by a real test suite, continuous integration, and a non root Docker
    image, built to be read end to end, not just demoed."
12. "CloudPulse: a practical approach to Linux and network troubleshooting. Thanks for watching."

Total word count: ~330 words. At the synthesized voice's actual measured pace (~0.8s/word
including pauses), this produces roughly 2:30-3:00 of narration before transitions/padding --
see `demo-video/build/*.wav` (generated at render time, not committed) for the exact per-scene
durations actually used.
