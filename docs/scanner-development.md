# Scanner development

Third-party scanners implement `scanners.plugins.Scanner` and return the existing normalized
`ScanResult`; persistence, CBOM, risk, graph, and migration services remain unchanged.

```python
from scanners.plugins import Scanner
from scanners.base import ScanResult

class KubernetesScanner(Scanner):
    source_type = "kubernetes"
    name = "Kubernetes cryptographic discovery"
    version = "1.0.0"

    async def scan(self, target, **options):
        return ScanResult(source=self.source_type, target=str(target), assets=[])
```

Publish it with a Python entry point:

```toml
[project.entry-points."ecdat_x.scanners"]
kubernetes = "my_package:KubernetesScanner"
```

The registry rejects duplicate source types and invalid contracts. Plugins must validate targets,
bound resources, avoid returning secrets, produce stable relationships, expose health metadata,
and include safe/adversarial input tests.
