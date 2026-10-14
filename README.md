# Pitch In releases

The published fingerprints of every [Pitch In](https://pitchinhelp.com) release, so anyone can check that the site is running exactly the code that was released, and that no one has changed it.

Pitch In encrypts names on your device before they're sent, so the server can't read them. Like every website, though, the server sends your device the code that does the encrypting. If someone took over the server and changed that code, names typed while it was changed could be captured. These fingerprints make such a change visible.

## What's here

- `releases/<version>/fingerprints.json` lists:
  - the SHA-384 of every script and stylesheet the site serves;
  - the SHA-384 of the notification helper (`/sw.js`);
  - the security policy header, which decides what code pages may run.
- `releases/<version>/fingerprints.json.sigstore.json` is the file's signature. It was made by the release workflow in Pitch In's own repository when that version was tagged, and recorded in the public [Sigstore](https://www.sigstore.dev) log.
- `releases/<version>/NOTES.md` has what changed in that version.
- `latest.json` and `previous.json` are copies of the newest two releases' fingerprints.
- `check.py` is the check itself: about a hundred lines of Python, standard library only.

## Checking it yourself

```sh
python3 check.py https://pitchinhelp.com latest.json
```

It loads the public pages and every file the release lists, and compares each with the published fingerprint. It prints `OK: … matches release …`, or exactly what differs.

To confirm the fingerprints themselves came from Pitch In's release workflow (needs [cosign](https://docs.sigstore.dev/cosign/system_config/installation/)):

```sh
cosign verify-blob releases/2026.10/fingerprints.json \
  --bundle releases/2026.10/fingerprints.json.sigstore.json \
  --certificate-identity-regexp '^https://github.com/atapha-code/pitchin/\.github/workflows/release\.yml@refs/tags/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## Checked automatically

`.github/workflows/watch.yml` runs the check every 3 hours, from GitHub, not from Pitch In's server. The operator is alerted if the live site ever differs from a published release.

## What it can't see

- **Code served to one person only:** someone who had taken over the server could serve different code to a single visitor and the normal code to everyone else, including this check. Only that visitor, checking their own browser, would see it.
- **Pages behind a group's passcode:** they use the same published files. The check covers every published file, but not a page that loads something extra only behind a passcode.

Questions: contact@pitchinhelp.com
