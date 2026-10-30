# Validation matrix

| Layer | Check | Result | Evidence |
| --- | --- | --- | --- |
| Core simulator | Python unit and integration tests | Passed | `python -m unittest discover -s tests -v` |
| Controlled comparison | Two seeded 500-mission runs | Passed | `results/comparison.json` and `docs/recovery-comparison.svg` |
| ROS 2 build | Humble `colcon build --symlink-install` | Passed | Both workspace packages built successfully |
| ROS 2 runtime | Six-node launch, active-mission fault, quarantine, reassignment and recovery | Passed | `results/ros2/`, `docs/ros2-runtime-validation.md` and `docs/ros2-runtime-validation.svg` |
| Compose topology | YAML parse and required-service wiring | Passed | `python3 scripts/validate_compose.py` under Ubuntu 22.04 |
| Docker deployment | Containers, PostgreSQL, Prometheus and Grafana at runtime | Not executed locally | Docker is not installed in the validation environment |

The Docker limitation is stated explicitly so the repository does not imply evidence that was not collected. The service topology and configuration are checked, while an operator with Docker can run the documented end-to-end deployment command.
