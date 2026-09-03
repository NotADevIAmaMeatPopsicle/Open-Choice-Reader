# Public release checklist

This checklist records the approval sequence for the initial public source repository. It does not authorize package publication or deployment.

## Owner decisions

- [x] Use the Apache License 2.0 for original Open Choice Reader source.
- [x] Use **Michael Griffin** and the GitHub no-reply address as public author metadata.
- [x] Use `NotADevIAmaMeatPopsicle` as the GitHub owner.
- [x] Use **Open Choice Reader** as the project name and `Open-Choice-Reader` as the proposed repository slug.
- [x] Use GitHub Private Vulnerability Reporting as the security channel.
- [x] Route private conduct concerns through a maintainer's GitHub profile contact.
- [x] Confirm the owner controls the rights needed to publish and license all original code, prose, theme artwork, and branding in this candidate.

## Technical gates

- [x] Preserve the private source checkout, its data, history, remote, and running environment.
- [x] Build a separate candidate with no inherited Git history and no remote.
- [x] Enforce the public source allowlist and Python package boundary.
- [x] Scan the candidate and all reachable private-source history for credentials.
- [x] Remove private paths, infrastructure, data, internal notes, generated files, and deployment-specific material from the candidate.
- [x] Complete the repository security review and remediate its three findings.
- [x] Pass backend, frontend, and browser-extension test suites.
- [x] Pass lint, type-check, production build, clean migration, package, dependency-audit, script-syntax, and documentation-link checks.
- [x] Exercise signed-out guidance and authenticated selected-text playback with the unpacked Chromium extension against a disposable loopback HTTPS installation.
- [x] Rerun all technical checks and regenerate the private file manifest after the license and public metadata files are settled.

## Publication gates

- [x] Review and approve the exact candidate file manifest and first commit.
- [x] Create a new, empty GitHub repository as **PRIVATE**.
- [x] Push only the approved candidate `main` branch, never `--all` or `--mirror`.
- [x] Confirm local and remote commits and file sets match and that no other branches or tags exist.
- [x] Obtain a separate explicit approval before changing visibility to public.
- [ ] Immediately after an approved public change, verify anonymous access and enable GitHub Private Vulnerability Reporting.
- [ ] Enable and verify available GitHub security features, including Dependabot alerts/security updates and secret scanning or push protection where the repository visibility and account plan support them.
