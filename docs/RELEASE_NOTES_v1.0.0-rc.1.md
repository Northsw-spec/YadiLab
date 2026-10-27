# YadiLab v1.0.0-rc.1

This release candidate promotes the verified v0.79.0 Foundation into a genuinely dependency-resolved, locally runnable offline product candidate on Parrot Security 7.2 x86-64.

Release-gate work completed:

- generated and verified the exact npm v3 lock/install closure;
- executed every pinned browser/build dependency, including native esbuild and ELK;
- built and integrity-verified the bundled React browser application with no runtime CDN dependency;
- fixed React Flow component attestation for the pinned forward-ref export;
- fixed local paths containing spaces by using decoded file-URL conversion;
- fixed CSP compatibility with the existing Ajv in-browser schema compiler while keeping script loading same-origin-only;
- fixed React Flow selection feedback that prevented the real application from mounting;
- statically bundled ELK instead of leaving a browser-unresolvable package specifier;
- fixed Chromium Blob-download lifetime, combined-session autosave status, and current acceptance selectors;
- recognized current Parrot releases that identify as Debian but explicitly name Parrot Security;
- verified real Chromium Builder/Runtime/package/persistence workflows and server-stopped offline reload;
- verified Firefox loopback rendering and the native static x86-64 launcher.

External boundary: dependency-snapshot signing remains fail-closed because no `YADILAB_SNAPSHOT_SIGNING_KEY` was supplied. Private signing material is not part of this release.
