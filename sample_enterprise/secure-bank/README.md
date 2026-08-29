# SecureBank discovery fixture

This intentionally mixed-language repository is a safe demonstration target for the Phase 1.5
cryptographic discovery workflow. It contains source-level cryptographic API calls, dependency
manifests, TLS configuration, and a Dockerfile. The certificate paths are examples only; no
private keys or live credentials are included.

Create an uploadable archive from the `sample_enterprise` directory:

```bash
zip -r secure-bank.zip secure-bank
```

Upload `secure-bank.zip` in the Upload Center and follow the scan through asset discovery, risk
scoring, CBOM generation, and graph exploration.
