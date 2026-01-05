from pathlib import Path
import json
from typing import Dict, Any


class Workspace:

    def __init__(self, job_id: str, base_dir: str = "runs"):
        self.root = Path(base_dir) / job_id
        self.root.mkdir(parents=True, exist_ok=True)
        self.status_file = self.root / "status.json"

    def save_checkpoint(self, processed_count: int, metrics: Dict):
        with open(self.status_file, "w") as f:
            json.dump(
                {
                    "processed": processed_count,
                    "metrics": metrics,
                    "state": "running"
                }, f)

    def load_checkpoint(self) -> Dict[str, Any]:
        if self.status_file.exists():
            with open(self.status_file) as f:
                return json.load(f)
        return {"processed": 0}
