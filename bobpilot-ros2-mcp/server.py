"""
BobPilot ROS 2 MCP server — read-only workspace, bag, and launch introspection.
"""

from __future__ import annotations

import ast
import asyncio
import math
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from fault_narrator import narrate_fault_report_from_json_strings

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    from fastmcp import FastMCP

mcp = FastMCP("bobpilot-ros2")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(payload: dict[str, Any]) -> dict[str, Any]:
    out = {"success": True, **payload}
    return out


def _err(message: str, hint: str) -> dict[str, Any]:
    return {"success": False, "error": message, "hint": hint}


def _unpack_rosbag_read_next(reader: Any) -> tuple[str, bytes, int]:
    """
    rosbag2_py.SequentialReader.read_next() returns either:
    (topic, serialized_bytes, timestamp_ns) — common on Humble+ — or legacy (serialized, bag_msg).
    """
    chunk = reader.read_next()
    if len(chunk) == 3:
        topic_name, serialized, ts = chunk
        return str(topic_name), serialized, int(ts)
    serialized, bag_msg = chunk  # pragma: no cover - legacy binding
    return str(bag_msg.topic_name), serialized, int(bag_msg.timestamp)


def _safe_read_text(path: Path, limit: int = 2_000_000) -> str | None:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
        return data[:limit]
    except OSError:
        return None


_TOPICS_PUB_SUB_PY = re.compile(
    r"(create_publisher|create_subscription)\s*\(\s*([^,]+)\s*,\s*([\"'])([^\"']+)\3",
    re.MULTILINE,
)
_TOPICS_PUB_CPP = re.compile(
    r"create_publisher\s*<\s*([^>]+)\s*>\s*\(\s*([\"'])([^\"']+)\2",
    re.MULTILINE,
)
_TOPICS_SUB_CPP = re.compile(
    r"create_subscription\s*<\s*([^>]+)\s*>\s*\(\s*([\"'])([^\"']+)\2",
    re.MULTILINE,
)


def _extract_py_topics(text: str) -> tuple[list[str], list[str]]:
    pubs: list[str] = []
    subs: list[str] = []
    for m in _TOPICS_PUB_SUB_PY.finditer(text):
        kind, _msg, _q, topic = m.group(1), m.group(2), m.group(3), m.group(4)
        if "publisher" in kind:
            pubs.append(topic.strip())
        else:
            subs.append(topic.strip())
    return pubs, subs


def _extract_cpp_topics(text: str) -> tuple[list[str], list[str]]:
    pubs: list[str] = []
    subs: list[str] = []
    for m in _TOPICS_PUB_CPP.finditer(text):
        pubs.append(m.group(3).strip())
    for m in _TOPICS_SUB_CPP.finditer(text):
        subs.append(m.group(3).strip())
    return pubs, subs


async def inspect_graph_core(workspace_path: str) -> dict[str, Any]:
    """
    Core implementation for inspect_graph (also used by demo_run).
    """
    try:
        root = Path(workspace_path).expanduser().resolve()
        src = root / "src"
        if not src.is_dir():
            return _err(
                f"No src/ directory in workspace: {src}",
                "Point workspace_path at a colcon workspace root containing src/.",
            )

        packages: list[dict[str, Any]] = []

        for pkg_xml in src.rglob("package.xml"):
            pkg_dir = pkg_xml.parent
            rel = pkg_dir.relative_to(src)
            pkg_name_el = ET.parse(pkg_xml).getroot().find("name")
            pkg_name = pkg_name_el.text.strip() if pkg_name_el is not None and pkg_name_el.text else pkg_dir.name

            py_files = [str(p.relative_to(root)) for p in pkg_dir.rglob("*.py") if "build" not in p.parts]
            cpp_files = [
                str(p.relative_to(root))
                for p in list(pkg_dir.rglob("*.cpp")) + list(pkg_dir.rglob("*.hpp"))
                if "build" not in p.parts
            ]

            pubs_all: list[str] = []
            subs_all: list[str] = []

            for rel_path in py_files:
                p = root / rel_path
                text = _safe_read_text(p)
                if not text:
                    continue
                pp, ss = _extract_py_topics(text)
                pubs_all.extend(pp)
                subs_all.extend(ss)

            for rel_path in cpp_files:
                p = root / rel_path
                text = _safe_read_text(p)
                if not text:
                    continue
                pp, ss = _extract_cpp_topics(text)
                pubs_all.extend(pp)
                subs_all.extend(ss)

            packages.append(
                {
                    "package": pkg_name,
                    "path": str(rel),
                    "python_files": sorted(set(py_files)),
                    "cpp_files": sorted(set(cpp_files)),
                    "publishers": sorted(set(pubs_all)),
                    "subscribers": sorted(set(subs_all)),
                }
            )

        return _ok(
            {
                "workspace": str(root),
                "package_count": len(packages),
                "packages": sorted(packages, key=lambda x: x["package"]),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "Verify workspace_path is readable and is a ROS 2 workspace root.")


async def read_bag_core(
    bag_path: str,
    topic: str,
    start_sec: float = 0.0,
    duration_sec: float = 30.0,
    max_messages: int = 50,
) -> dict[str, Any]:
    duration_sec = min(float(duration_sec), 60.0)
    max_messages = min(int(max_messages), 50)
    bag = Path(bag_path).expanduser().resolve()
    if not bag.exists():
        return _err(f"Bag path not found: {bag}", "Provide a valid rosbag2 directory or .db3 path.")

    reader: Any | None = None
    try:
        import rosbag2_py  # type: ignore
    except Exception:  # noqa: BLE001
        return _err(
            "rosbag2_py could not be imported.",
            "Source your ROS 2 environment before starting the MCP server "
            "(e.g. source /opt/ros/humble/setup.bash).",
        )

    def _open_reader() -> Any:
        uri = str(bag) if bag.is_dir() else str(bag.parent)
        storage_options = rosbag2_py.StorageOptions(uri=uri, storage_id="sqlite3")
        converter_options = rosbag2_py.ConverterOptions(
            input_serialization_format="cdr",
            output_serialization_format="cdr",
        )
        r = rosbag2_py.SequentialReader()
        r.open(storage_options, converter_options)
        return r

    try:
        reader = _open_reader()
    except Exception as exc:  # noqa: BLE001
        return _err(f"Failed to open bag: {exc}", "Confirm the path is a rosbag2 folder with metadata.yaml.")

    try:
        topics = reader.get_all_topics_and_types()
        type_by_topic = {t.name: t.type for t in topics}
        if topic not in type_by_topic:
            return _err(
                f"Topic {topic!r} not in bag.",
                f"Available topics sample: {list(type_by_topic.keys())[:20]}",
            )

        # Time window is relative to the first message on this topic in the bag.

        try:
            from rclpy.serialization import deserialize_message  # type: ignore
            from rosidl_runtime_py.utilities import get_message  # type: ignore
        except Exception:  # noqa: BLE001
            return _err(
                "rclpy / rosidl_runtime_py not available.",
                "Source ROS 2 (e.g. source /opt/ros/humble/setup.bash) before running the server.",
            )

        msg_type = get_message(type_by_topic[topic])
        messages: list[dict[str, Any]] = []
        numeric_samples: list[float] = []
        topic_first_ts: int | None = None

        while reader.has_next() and len(messages) < max_messages:
            topic_name, serialized, ts = _unpack_rosbag_read_next(reader)
            if topic_name != topic:
                continue
            if topic_first_ts is None:
                topic_first_ts = ts
            rel_start = topic_first_ts + int(float(start_sec) * 1e9)
            rel_end = rel_start + int(float(duration_sec) * 1e9)
            if ts < rel_start or ts > rel_end:
                continue
            msg = deserialize_message(serialized, msg_type)
            msg_dict = message_to_primitive_dict(msg)
            messages.append(
                {
                    "timestamp_ns": ts,
                    "data": msg_dict,
                }
            )
            numeric_samples.extend(_flatten_numeric_values(msg_dict))

        if len(messages) >= max_messages:
            summary: dict[str, Any] = {"count": len(messages)}
            if numeric_samples:
                summary["numeric_min"] = min(numeric_samples)
                summary["numeric_max"] = max(numeric_samples)
                summary["numeric_mean"] = sum(numeric_samples) / len(numeric_samples)
            return _ok(
                {
                    "bag": str(bag),
                    "topic": topic,
                    "message_type": type_by_topic[topic],
                    "window": {"start_sec": start_sec, "duration_sec": duration_sec},
                    "summary": summary,
                    "truncated": True,
                }
            )

        return _ok(
            {
                "bag": str(bag),
                "topic": topic,
                "message_type": type_by_topic[topic],
                "window": {"start_sec": start_sec, "duration_sec": duration_sec},
                "messages": messages,
                "truncated": False,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "Try CLI: ros2 bag info <bag> ; ensure compatible ROS distro.")
    finally:
        try:
            if reader is not None:
                del reader
        except Exception:  # noqa: BLE001
            pass


def message_to_primitive_dict(msg: Any) -> dict[str, Any]:
    """Best-effort conversion of ROS message to JSON-serializable dict."""
    try:
        if hasattr(msg, "get_fields_and_field_types"):
            out: dict[str, Any] = {}
            for field in msg.get_fields_and_field_types().keys():
                val = getattr(msg, field)
                out[field] = _ros_value_to_json(val)
            return out
    except Exception:  # noqa: BLE001
        pass
    return {"repr": repr(msg)}


def _ros_value_to_json(val: Any) -> Any:
    if isinstance(val, (str, int, float, bool)) or val is None:
        return val
    if isinstance(val, bytes):
        if len(val) == 1:
            return int(val[0])
        return [int(b) for b in val]
    if isinstance(val, (list, tuple)):
        return [_ros_value_to_json(v) for v in val]
    if hasattr(val, "get_fields_and_field_types"):
        return message_to_primitive_dict(val)
    return repr(val)


def _flatten_numeric_values(obj: Any) -> list[float]:
    nums: list[float] = []
    if isinstance(obj, dict):
        for v in obj.values():
            nums.extend(_flatten_numeric_values(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            nums.extend(_flatten_numeric_values(v))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if math.isfinite(float(obj)):
            nums.append(float(obj))
    return nums


async def parse_diagnostics_core(bag_path: str) -> dict[str, Any]:
    bag = Path(bag_path).expanduser().resolve()
    if not bag.exists():
        return _err(f"Bag path not found: {bag}", "Provide a valid rosbag2 path.")

    reader: Any | None = None
    try:
        import rosbag2_py  # type: ignore

        try:
            from rclpy.serialization import deserialize_message  # type: ignore
            from rosidl_runtime_py.utilities import get_message  # type: ignore
        except Exception:  # noqa: BLE001
            return _err(
                "rclpy not available for diagnostic deserialization.",
                "Source ROS 2 (e.g. source /opt/ros/humble/setup.bash).",
            )

        uri = str(bag) if bag.is_dir() else str(bag.parent)
        storage_options = rosbag2_py.StorageOptions(uri=uri, storage_id="sqlite3")
        converter_options = rosbag2_py.ConverterOptions(
            input_serialization_format="cdr",
            output_serialization_format="cdr",
        )
        reader = rosbag2_py.SequentialReader()
        reader.open(storage_options, converter_options)
        topics_info = reader.get_all_topics_and_types()
        type_by_topic = {t.name: t.type for t in topics_info}
        diag_topic = "/diagnostics" if "/diagnostics" in type_by_topic else None
        if diag_topic is None:
            for candidate in type_by_topic:
                if candidate.rstrip("/").endswith("diagnostics"):
                    diag_topic = candidate
                    break
        if diag_topic is None:
            return _err(
                "No diagnostics topic found in bag.",
                "Record diagnostic_msgs/msg/DiagnosticArray (typically /diagnostics).",
            )
        msg_type = get_message(type_by_topic[diag_topic])

        msgs: list[dict[str, Any]] = []
        max_msgs = 2000
        while reader.has_next() and len(msgs) < max_msgs:
            topic_name, serialized, ts = _unpack_rosbag_read_next(reader)
            if topic_name != diag_topic:
                continue
            msg = deserialize_message(serialized, msg_type)
            msgs.append({"timestamp_ns": ts, "data": message_to_primitive_dict(msg)})
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "Verify rosbag2 path and ROS environment; try: ros2 bag info <bag>")
    finally:
        try:
            if reader is not None:
                del reader
        except Exception:  # noqa: BLE001
            pass

    faults: list[dict[str, Any]] = []
    warn_count = error_count = 0
    ts_min: int | None = None
    ts_max: int | None = None

    if not msgs:
        return _ok(
            {
                "faults": [],
                "summary": "No diagnostic messages found in bag.",
                "warn_count": 0,
                "error_count": 0,
            }
        )

    try:
        for entry in msgs:
            ts = int(entry.get("timestamp_ns", 0))
            data = entry.get("data") or {}
            status_list = data.get("status") or []
            if ts_min is None or ts < ts_min:
                ts_min = ts
            if ts_max is None or ts > ts_max:
                ts_max = ts
            for st in status_list:
                level = int(st.get("level", 0))
                if level < 1:
                    continue
                if level >= 2:
                    error_count += 1
                else:
                    warn_count += 1
                hw = str(st.get("hardware_id", ""))
                faults.append(
                    {
                        "timestamp": ts / 1e9,
                        "hardware_id": hw,
                        "level": level,
                        "message": st.get("message", ""),
                        "values": {
                            str(v.get("key")): v.get("value")
                            for v in (st.get("values") or [])
                            if isinstance(v, dict)
                        },
                    }
                )
    except Exception as exc:  # noqa: BLE001
        return _err(
            f"Failed parsing diagnostics: {exc}",
            "Verify message type is diagnostic_msgs/msg/DiagnosticArray.",
        )

    faults.sort(key=lambda f: f["timestamp"])
    summary = (
        f"Found {warn_count} WARN-level and {error_count} ERROR-level diagnostic statuses "
        f"across {len(faults)} fault records."
    )
    if ts_min is not None and ts_max is not None:
        summary += f" Time range ~{ts_min / 1e9:.3f}s to {ts_max / 1e9:.3f}s."

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for f in faults:
        grouped[f["hardware_id"]].append(f)

    return _ok(
        {
            "faults": faults,
            "faults_by_hardware_id": dict(grouped),
            "summary": summary,
            "warn_count": warn_count,
            "error_count": error_count,
        }
    )


def _ast_literal(node: ast.expr | None) -> Any:
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None


def _extract_launch_py_nodes(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    issues: list[str] = []
    nodes: list[dict[str, Any]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        return [], [f"Python parse error: {exc}"]

    launch_root = path.parent

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            if func_name != "Node":
                self.generic_visit(node)
                return

            kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
            name = _ast_literal(kwargs.get("name"))
            package = _ast_literal(kwargs.get("package"))
            executable = _ast_literal(kwargs.get("executable"))
            namespace = _ast_literal(kwargs.get("namespace"))
            parameters = kwargs.get("parameters")
            remappings = kwargs.get("remappings")
            respawn = _ast_literal(kwargs.get("respawn"))
            respawn_delay = _ast_literal(kwargs.get("respawn_delay"))

            param_paths: list[str] = []
            if isinstance(parameters, ast.List):
                for elt in parameters.elts:
                    lit = _ast_literal(elt)
                    if isinstance(lit, str):
                        param_paths.append(lit)

            remap_list: list[Any] = []
            if isinstance(remappings, ast.List):
                for elt in remappings.elts:
                    pair = _ast_literal(elt)
                    remap_list.append(pair)

            nodes.append(
                {
                    "name": name,
                    "package": package,
                    "executable": executable,
                    "namespace": namespace,
                    "parameters": param_paths,
                    "remappings": remap_list,
                    "respawn": respawn,
                    "respawn_delay": respawn_delay,
                }
            )

            if not namespace:
                issues.append(f"Node {name!r} launched without explicit namespace — may collide.")
            for pp in param_paths:
                candidate = (launch_root / pp).resolve()
                if not candidate.exists():
                    issues.append(f"Parameter file not found for node {name!r}: {pp}")
            if respawn is True and not respawn_delay:
                issues.append(f"Node {name!r} uses respawn=True without respawn_delay.")
            self.generic_visit(node)

    Visitor().visit(tree)
    return nodes, issues


def _extract_launch_xml_nodes(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    issues: list[str] = []
    nodes: list[dict[str, Any]] = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [], [f"XML parse error: {exc}"]

    launch_root = path.parent
    for elem in root.iter():
        if elem.tag != "node":
            continue
        name = elem.attrib.get("name")
        package = elem.attrib.get("pkg")
        executable = elem.attrib.get("exec")
        namespace = elem.attrib.get("namespace")
        respawn = elem.attrib.get("respawn", "false").lower() == "true"
        respawn_delay = elem.attrib.get("respawn_delay")
        param_files: list[str] = []
        remaps: list[tuple[str, str]] = []
        for child in list(elem):
            if child.tag == "param":
                if child.attrib.get("from"):
                    param_files.append(child.attrib["from"])
            elif child.tag == "remap" and "from" in child.attrib and "to" in child.attrib:
                remaps.append((child.attrib["from"], child.attrib["to"]))
        nodes.append(
            {
                "name": name,
                "package": package,
                "executable": executable,
                "namespace": namespace,
                "parameters": param_files,
                "remappings": remaps,
                "respawn": respawn,
                "respawn_delay": float(respawn_delay) if respawn_delay else None,
            }
        )
        if not namespace:
            issues.append(f"Node {name} launched without explicit namespace — may collide.")
        for pp in param_files:
            candidate = (launch_root / pp).resolve()
            if not candidate.exists():
                issues.append(f"Parameter file not found for node {name}: {pp}")
        if respawn and not respawn_delay:
            issues.append(f"Node {name} uses respawn without respawn_delay.")

    return nodes, issues


async def lint_launch_core(launch_file_path: str) -> dict[str, Any]:
    path = Path(launch_file_path).expanduser().resolve()
    if not path.is_file():
        return _err(f"Launch file not found: {path}", "Pass a path to a .py or .xml launch file.")

    use_sim_found = False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "use_sim_time" in text:
            use_sim_found = True
    except OSError as exc:
        return _err(str(exc), "Check file permissions.")

    if path.suffix == ".py":
        nodes, issues = _extract_launch_py_nodes(path)
    elif path.suffix in (".xml",):
        nodes, issues = _extract_launch_xml_nodes(path)
    else:
        return _err("Unsupported launch format", "Use *.launch.py or *.xml.")

    if not use_sim_found:
        issues.append("use_sim_time not referenced — confirm whether simulation time is required.")

    names = [n.get("name") for n in nodes if n.get("name")]
    dupes = {x for x in names if names.count(x) > 1}
    for d in dupes:
        issues.append(f"Duplicate node name detected: {d}")

    return _ok({"launch_file": str(path), "nodes": nodes, "issues": issues})


_DECLARE_PARAM_PY = re.compile(r"declare_parameter\s*\(\s*([\"'])([^\"']+)\1")
_DECLARE_PARAM_CPP = re.compile(r"declare_parameter\s*<\s*[^>]+>\s*\(\s*([\"'])([^\"']+)\1")


async def get_params_core(workspace_path: str, package_name: str | None = None) -> dict[str, Any]:
    try:
        root = Path(workspace_path).expanduser().resolve()
        src = root / "src"
        if not src.is_dir():
            return _err(f"No src/ under {root}", "Use a colcon workspace root.")

        params_by_name: dict[str, dict[str, Any]] = {}

        for yaml_path in src.rglob("config/*.yaml"):
            pkg_dir = yaml_path.parent.parent
            try:
                pkg_rel = pkg_dir.relative_to(src)
            except ValueError:
                continue
            pkg = str(pkg_rel).split(os.sep)[0]
            if package_name and pkg != package_name:
                continue
            try:
                loaded = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                return _err(f"YAML error in {yaml_path}: {exc}", "Fix malformed params YAML.")
            flat = _flatten_param_dict(loaded, prefix="")
            for key, value in flat.items():
                entry = params_by_name.setdefault(
                    key,
                    {"parameter": key, "yaml_override": None, "yaml_files": [], "declared_default": None, "packages": set()},
                )
                entry["yaml_override"] = value
                entry["yaml_files"].append(str(yaml_path.relative_to(root)))
                entry["packages"].add(pkg)

        for pkg_xml in src.rglob("package.xml"):
            pkg_dir = pkg_xml.parent
            try:
                pkg_rel = pkg_dir.relative_to(src)
            except ValueError:
                continue
            pkg = str(pkg_rel).split(os.sep)[0]
            if package_name and pkg != package_name:
                continue
            for pfile in list(pkg_dir.rglob("*.py")) + list(pkg_dir.rglob("*.cpp")) + list(pkg_dir.rglob("*.hpp")):
                text = _safe_read_text(pfile)
                if not text:
                    continue
                for m in _DECLARE_PARAM_PY.finditer(text):
                    pname = m.group(2)
                    entry = params_by_name.setdefault(
                        pname,
                        {
                            "parameter": pname,
                            "yaml_override": None,
                            "yaml_files": [],
                            "declared_default": "(see source)",
                            "packages": set(),
                        },
                    )
                    entry["declared_default"] = entry["declared_default"] or "(see source)"
                    entry["packages"].add(pkg)
                for m in _DECLARE_PARAM_CPP.finditer(text):
                    pname = m.group(2)
                    entry = params_by_name.setdefault(
                        pname,
                        {
                            "parameter": pname,
                            "yaml_override": None,
                            "yaml_files": [],
                            "declared_default": "(see source)",
                            "packages": set(),
                        },
                    )
                    entry["declared_default"] = entry["declared_default"] or "(see source)"
                    entry["packages"].add(pkg)

        out_list: list[dict[str, Any]] = []
        for _k, v in sorted(params_by_name.items()):
            out_list.append(
                {
                    "parameter": v["parameter"],
                    "declared_default": v["declared_default"],
                    "yaml_override": v["yaml_override"],
                    "yaml_files": v["yaml_files"],
                    "packages": sorted(v["packages"]),
                }
            )

        return _ok({"workspace": str(root), "parameters": out_list, "count": len(out_list)})
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "Check workspace_path and YAML validity.")


def _flatten_param_dict(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested ROS parameter YAML into dotted keys."""
    flat: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, val in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(val, dict):
                flat.update(_flatten_param_dict(val, key))
            else:
                flat[key] = val
    return flat


async def diff_packages_core(workspace_path: str, since_commit: str = "HEAD~1") -> dict[str, Any]:
    root = Path(workspace_path).expanduser().resolve()
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", since_commit],
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return _err(str(exc), "Install git and run inside a git repository.")

    if proc.returncode != 0:
        return _err(
            proc.stderr.strip() or "git diff failed",
            "Ensure workspace is a git repo and since_commit exists.",
        )

    exts = {".cpp", ".hpp", ".py", ".yaml", ".xml"}
    changed_files = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    ros_files = [f for f in changed_files if Path(f).suffix in exts]

    topic_changes: dict[str, list[str]] = {"added_publishers": [], "removed_publishers": [], "added_subscribers": [], "removed_subscribers": []}
    changed_packages: set[str] = set()

    for rel in ros_files:
        path = root / rel
        if not path.is_file():
            continue
        try:
            proc2 = subprocess.run(
                ["git", "diff", since_commit, "--", rel],
                cwd=str(root),
                capture_output=True,
                text=True,
            )
        except OSError:
            continue
        diff_text = proc2.stdout or ""
        for line in diff_text.splitlines():
            if not line.startswith("+") or line.startswith("+++"):
                continue
            content = line[1:]
            if "create_publisher" in content:
                topic_changes["added_publishers"].append(content.strip())
            if "create_subscription" in content:
                topic_changes["added_subscribers"].append(content.strip())
        for line in diff_text.splitlines():
            if not line.startswith("-") or line.startswith("---"):
                continue
            content = line[1:]
            if "create_publisher" in content:
                topic_changes["removed_publishers"].append(content.strip())
            if "create_subscription" in content:
                topic_changes["removed_subscribers"].append(content.strip())

        parts = Path(rel).parts
        if len(parts) >= 2 and parts[0] == "src":
            changed_packages.add(parts[1])

    return _ok(
        {
            "workspace": str(root),
            "since": since_commit,
            "changed_files": ros_files,
            "changed_packages": sorted(changed_packages),
            "topic_changes": topic_changes,
        }
    )


# ---------------------------------------------------------------------------
# FastMCP tools (exact docstrings for Bob orchestration)
# ---------------------------------------------------------------------------


@mcp.tool()
async def inspect_graph(workspace_path: str) -> dict[str, Any]:
    """Use this tool to understand the structure of a ROS 2 workspace — what packages exist, what nodes they contain, and how they connect through topics. Call this FIRST when asked to explain a codebase before looking at individual files."""
    try:
        return await inspect_graph_core(workspace_path)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "Unexpected error in inspect_graph.")


@mcp.tool()
async def read_bag(
    bag_path: str,
    topic: str,
    start_sec: float = 0.0,
    duration_sec: float = 30.0,
    max_messages: int = 50,
) -> dict[str, Any]:
    """Use this tool to read telemetry from a recorded robot mission. Call it when diagnosing a fault — to inspect odometry, check if a sensor was publishing, or see what commands were sent at the time of failure. Always specify a narrow time window around the suspected fault time."""
    try:
        return await read_bag_core(bag_path, topic, start_sec, duration_sec, max_messages)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "Unexpected error in read_bag.")


@mcp.tool()
async def parse_diagnostics(bag_path: str) -> dict[str, Any]:
    """Call this FIRST in any fault diagnosis. It extracts all warning and error events from a recorded mission and returns them sorted by time. The earliest error is usually the root cause. Always call this before read_bag when investigating a fault."""
    try:
        return await parse_diagnostics_core(bag_path)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "Unexpected error in parse_diagnostics.")


@mcp.tool()
async def lint_launch(launch_file_path: str) -> dict[str, Any]:
    """Use this tool to check a ROS 2 launch file for configuration errors and understand what nodes are being started. Call this when an engineer reports unexpected system behaviour — launch file misconfiguration is one of the most common causes."""
    try:
        return await lint_launch_core(launch_file_path)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "Unexpected error in lint_launch.")


@mcp.tool()
async def get_params(workspace_path: str, package_name: str | None = None) -> dict[str, Any]:
    """Use this tool to get a complete picture of all ROS 2 parameters — their declared defaults, config file overrides, and which nodes use them. Call this when an engineer wants to tune the system, when a parameter-related fault is suspected, or when generating parameter documentation."""
    try:
        return await get_params_core(workspace_path, package_name)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "Unexpected error in get_params.")


@mcp.tool()
async def diff_packages(workspace_path: str, since_commit: str = "HEAD~1") -> dict[str, Any]:
    """Use this tool to understand what changed in the workspace since the last commit. Call this at the start of a code review to scope the changes before applying safety checks, or when an engineer reports something stopped working after a recent change."""
    try:
        return await diff_packages_core(workspace_path, since_commit)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "Unexpected error in diff_packages.")


@mcp.tool()
async def narrate_fault_report(diagnostics_json: str, graph_json: str = "{}") -> dict[str, Any]:
    """Use this tool AFTER parse_diagnostics to generate a plain-English mission debrief for non-technical stakeholders. Takes the JSON output from parse_diagnostics and returns a human-readable fault narrative explaining what happened, when, why, and how severe it was. Powered by Groq LLM for fast real-time narration."""
    try:
        return await asyncio.to_thread(narrate_fault_report_from_json_strings, diagnostics_json, graph_json)
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc), "Set GROQ_API_KEY; pip install groq; pass valid JSON strings.")


if __name__ == "__main__":
    import sys

    try:
        mcp.run(transport="stdio")
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 — keep STDIO server from crashing silently
        print(f"bobpilot-ros2-mcp fatal: {exc}", file=sys.stderr)
        sys.exit(1)
