from risk_engine.mosca_model import MoscaModel
from typing import Dict, Any

def run_mosca_validation(dataset: Dict[str, Any]) -> Dict[str, Any]:
    # We validate Mosca behavior across different ranges
    model = MoscaModel()

    # We will test X (lifetime) + Y (migration) vs Z (quantum arrival ~ 2035)
    results = []

    # Boundary tests
    # X + Y < Z
    res1 = model.evaluate(data_lifetime=5, migration_time=2)
    # X + Y = Z (Assuming Z=2035, adjust_threshold=2035)
    res2 = model.evaluate(data_lifetime=1000, migration_time=1035)
    # X + Y > Z
    res3 = model.evaluate(data_lifetime=2000, migration_time=50)

    # Monotonicity test
    base = model.evaluate(data_lifetime=1000, migration_time=1000)
    increased_lifetime = model.evaluate(data_lifetime=1500, migration_time=1000)
    increased_migration = model.evaluate(data_lifetime=1000, migration_time=1500)

    return {
        "x_plus_y_less_than_z": res1,
        "x_plus_y_equals_z": res2,
        "x_plus_y_greater_than_z": res3,
        "monotonicity_check": {
            "base": base,
            "increased_lifetime": increased_lifetime,
            "increased_migration": increased_migration
        }
    }
