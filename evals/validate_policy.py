from pathlib import Path
import yaml

p = Path("policies/v1/policy.yaml")
yaml.safe_load(p.read_text(encoding="utf-8"))
print("policy.yaml is valid YAML ✅")
