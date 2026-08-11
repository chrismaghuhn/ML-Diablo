#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from dxai.data.trajectory import read_episode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode_directory", type=Path)
    args = parser.parse_args()
    manifest, records = read_episode(args.episode_directory)
    actions = Counter(record.action.kind.value for record in records)
    reward_components: Counter[str] = Counter()
    for record in records:
        for key, value in record.info.get("reward_components", {}).items():
            reward_components[key] += float(value)
    print(
        json.dumps(
            {
                "manifest": manifest.to_dict(),
                "action_counts": dict(sorted(actions.items())),
                "reward_component_totals": dict(sorted(reward_components.items())),
                "first_step": None if not records else records[0].to_dict(),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
