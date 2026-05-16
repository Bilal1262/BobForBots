# Test generation

- Every fix ships with a **gtest** (C++) or **pytest** (Python) unit test under the package `test/` directory.
- **Naming:** `test_<node_name>_<fault_scenario>.cpp` or `.py`.
- **Structure:** three sections — *arrange* (fault setup), *act* (invoke code under test), *assert* (prove the fault cannot recur).
- Prefer **`launch_testing`** for multi-node fault scenarios.
- Tests must run with: `colcon test --packages-select <package>`.
