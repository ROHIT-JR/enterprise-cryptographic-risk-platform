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

The `business-context.json` file drives the Phase 2 demonstration: customer financial records are
retained for 20 years, the payment service is business-critical, and one RSA-2048 certificate is
shared by 43 dependent services. The intelligence engine turns this into HNDL exposure, blast
radius, final quantum risk, PQC recommendations, and dependency-aware migration waves.
