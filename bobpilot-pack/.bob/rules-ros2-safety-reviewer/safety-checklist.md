1. **Missing try/catch in lifecycle transitions** (CRITICAL) — Pattern: `on_activate`, `on_deactivate`, or `on_cleanup` callbacks with no try/catch around logic that can throw. Risk: an exception leaves the lifecycle stuck mid-transition.

2. **Blocking calls on real-time threads** (CRITICAL) — Pattern: `sleep`, `sleep_for`, file I/O, or large allocations inside timer or subscription callbacks. Risk: missed control-loop deadlines.

3. **Undeclared ROS 2 parameters** (WARNING) — Pattern: `get_parameter` / `get_parameter_or` for names never passed to `declare_parameter`. Risk: runtime failure or wrong values when parameters are listed or overridden.

4. **Missing QoS on safety-critical topics** (WARNING) — Pattern: publisher or subscriber using default QoS on topics whose name contains `cmd_vel`, `joint_commands`, `safety`, or `emergency`. Risk: `KEEP_LAST` depth can drop safety-critical messages.

5. **Unsafe TF lookups without timeout** (CRITICAL) — Pattern: `lookupTransform` without a timeout or with `tf2::TimePointZero` where a timeout is required. Risk: indefinite block if a frame never appears.

6. **No watchdog on external sensor input** (CRITICAL) — Pattern: subscribing to a sensor or odometry stream with no timer-driven staleness check or fault escalation. Risk: acting on stale data after sensor loss.

7. **Hard-coded velocity or force limits** (INFO) — Pattern: numeric literals above **0.5 m/s** or **10 N** in source for limits instead of declared parameters. Risk: limits cannot be tuned per robot.

8. **Missing error propagation from action servers** (WARNING) — Pattern: action result or goal completion path that always reports success regardless of internal `GoalStatus`. Risk: higher-level behavior never sees failure.
