import random
import uuid
from typing import List, Tuple, Dict, Any

from backend.app.models.asset import Asset, AssetRelationship

def _gen_id() -> str:
    return str(uuid.uuid4())

class SyntheticDataset:
    def __init__(self, organization_id: str, project_id: str, scan_id: str):
        self.organization_id = organization_id
        self.project_id = project_id
        self.scan_id = scan_id
        self.assets: List[Asset] = []
        self.relationships: List[AssetRelationship] = []

    def add_asset(self, asset_type: str, name: str, algorithm: str = None, location: str = "") -> Asset:
        asset = Asset(
            id=_gen_id(),
            organization_id=self.organization_id,
            project_id=self.project_id,
            scan_id=self.scan_id,
            asset_type=asset_type,
            name=name,
            algorithm=algorithm,
            location=location,
            evidence=f"synthetic_{asset_type}",
            confidence=1.0,
            dependency_count=0
        )
        self.assets.append(asset)
        return asset

    def add_edge(self, source_id: str, target_id: str, rel_type: str = "DEPENDS_ON"):
        rel = AssetRelationship(
            id=_gen_id(),
            organization_id=self.organization_id,
            project_id=self.project_id,
            source_asset_id=source_id,
            target_asset_id=target_id,
            relationship_type=rel_type,
            evidence="synthetic_edge"
        )
        self.relationships.append(rel)
        return rel

def generate_topology(
    seed: int,
    num_assets: int,
    topology_type: str = "scale_free",
    organization_id: str = "benchmark_org",
    project_id: str = "benchmark_proj",
    scan_id: str = "benchmark_scan"
) -> SyntheticDataset:
    """
    Generates a deterministic synthetic cryptographic dependency dataset.
    Supported topologies: scale_free (default), chain, star, scc, disjoint
    """
    random.seed(seed)
    ds = SyntheticDataset(organization_id, project_id, scan_id)

    # 1. Create Nodes
    asset_types = ["application", "service", "library", "certificate"]
    algorithms = ["RSA-2048", "ECC-256", "AES-128", "SHA-256", "None", "RSA-1024", "ECDSA"]

    for i in range(num_assets):
        atype = random.choice(asset_types)
        algo = random.choice(algorithms) if atype in ["certificate", "library", "service"] else None
        ds.add_asset(asset_type=atype, name=f"asset_{i}", algorithm=algo, location=f"loc/{i}")

    # 2. Create Edges
    if topology_type == "chain":
        for i in range(num_assets - 1):
            ds.add_edge(ds.assets[i].id, ds.assets[i+1].id)
    elif topology_type == "star":
        center = ds.assets[0].id
        for i in range(1, num_assets):
            ds.add_edge(center, ds.assets[i].id)
    elif topology_type == "scc":
        # Create a single large strongly connected component (a cycle + some random cross edges)
        for i in range(num_assets):
            ds.add_edge(ds.assets[i].id, ds.assets[(i+1) % num_assets].id)
        # add 10% random edges
        for _ in range(max(1, num_assets // 10)):
            u, v = random.sample(ds.assets, 2)
            ds.add_edge(u.id, v.id)
    elif topology_type == "disjoint":
        # Groups of 5 nodes
        for i in range(0, num_assets, 5):
            group = ds.assets[i:i+5]
            if len(group) > 1:
                for j in range(len(group) - 1):
                    ds.add_edge(group[j].id, group[j+1].id)
    else:  # scale_free / preferential attachment (Barabasi-Albert approximation)
        # Start with a small clique
        m = 2
        if num_assets <= m:
            for i in range(num_assets - 1):
                ds.add_edge(ds.assets[i].id, ds.assets[i+1].id)
        else:
            targets = [ds.assets[0].id, ds.assets[1].id]
            ds.add_edge(ds.assets[0].id, ds.assets[1].id)
            for i in range(2, num_assets):
                # Pick m targets based on degree (approximated by targets list frequency)
                chosen = set()
                while len(chosen) < m and len(chosen) < len(set(targets)):
                    chosen.add(random.choice(targets))
                for target in chosen:
                    ds.add_edge(ds.assets[i].id, target)
                    targets.append(target)
                    targets.append(ds.assets[i].id)

    return ds
