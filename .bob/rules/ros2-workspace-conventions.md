# ROS 2 workspace conventions

**Packages** use `package.xml` plus either `CMakeLists.txt` (**ament_cmake**, C++) or `setup.py` (**ament_python**, Python). Typical layout: `src/` (C++ sources), `include/<package>/` (headers), `launch/`, `config/`, `test/`.

**Identify build type:** `CMakeLists.txt` + C++ sources ⇒ ament_cmake; `setup.py` with `ament_python` ⇒ ament_python.

**Ignore build artefacts:** `build/`, `install/`, `log/` — never commit; regenerate with `colcon build`.

**Names:** `snake_case` for nodes, topics, parameters; **message types** use `PascalCase` (e.g. `geometry_msgs/msg/Twist`).

**Common system topics:** `/tf`, `/tf_static`, `/diagnostics`, `/rosout`, `/parameter_events`.

**Node vs executable:** The *node name* (graph identity) may differ from the *executable* binary; remappings and namespacing apply to the node name.

**Remappings:** In launch, `remappings=[('from', 'to')]` rewrite topic/service names for that node instance without changing source code.
