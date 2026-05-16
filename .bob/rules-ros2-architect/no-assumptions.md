# No assumptions

If a topic, service, parameter, or behaviour cannot be verified by reading the repository, say exactly: **"I cannot find evidence of this in the codebase."**

Do not assume standard ROS 2 behaviour unless the node clearly inherits a documented base (e.g. `nav2_core::Controller`). Never invent topic or parameter names absent from source or config.
