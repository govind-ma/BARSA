"""FalkorDB Redis RESP Protocol Server Harness for Testing & Local Development.

Implements the FalkorDB Redis module wire protocol on port 6379:
- Responds to standard Redis handshake (PING, CLIENT, COMMAND, INFO)
- Executes GRAPH.QUERY, GRAPH.RO_QUERY, and GRAPH.DELETE
- Returns official FalkorDB RESP2 compact result sets
- Allows live start/stop demonstration of FalkorDB dependency
"""

import argparse
import asyncio
import logging
import re
import sys
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [FalkorDB Server] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("falkordb_server")

# =============================================================================
# In-Memory Property Graph Engine
# =============================================================================


class PropertyGraph:
    def __init__(self, name: str) -> None:
        self.name = name
        # nodes: id -> {id, raw_id, project_id, label, properties}
        self.nodes: dict[str, dict[str, Any]] = {}
        # edges: list of {source_id, target_id, rel_type, properties, project_id}
        self.edges: list[dict[str, Any]] = []

    def clear(self) -> None:
        self.nodes.clear()
        self.edges.clear()


# Global graph registry by graph_name
GRAPHS: dict[str, PropertyGraph] = {}


def get_or_create_graph(name: str) -> PropertyGraph:
    if name not in GRAPHS:
        GRAPHS[name] = PropertyGraph(name)
    return GRAPHS[name]


# =============================================================================
# RESP Protocol Encoding / Decoding
# =============================================================================


def encode_resp_simple_string(s: str) -> bytes:
    return f"+{s}\r\n".encode("utf-8")


def encode_resp_bulk_string(s: str | None) -> bytes:
    if s is None:
        return b"$-1\r\n"
    encoded = s.encode("utf-8")
    return f"${len(encoded)}\r\n".encode("utf-8") + encoded + b"\r\n"


def encode_resp_integer(n: int) -> bytes:
    return f":{n}\r\n".encode("utf-8")


def encode_resp_array(items: list[Any]) -> bytes:
    header = f"*{len(items)}\r\n".encode("utf-8")
    body = b"".join(encode_resp_val(item) for item in items)
    return header + body


def encode_resp_val(val: Any) -> bytes:
    if val is None:
        return b"$-1\r\n"
    if isinstance(val, bool):
        return encode_resp_integer(1 if val else 0)
    if isinstance(val, int):
        return encode_resp_integer(val)
    if isinstance(val, float):
        return encode_resp_bulk_string(str(val))
    if isinstance(val, str):
        return encode_resp_bulk_string(val)
    if isinstance(val, bytes):
        return f"${len(val)}\r\n".encode("utf-8") + val + b"\r\n"
    if isinstance(val, list):
        return encode_resp_array(val)
    if isinstance(val, dict):
        # Maps in RESP arrays
        flat = []
        for k, v in val.items():
            flat.append(k)
            flat.append(v)
        return encode_resp_array(flat)
    return encode_resp_bulk_string(str(val))


def parse_resp_command(buffer: bytes) -> tuple[list[str] | None, bytes]:
    """Parse a single RESP array command from buffer."""
    if not buffer:
        return None, buffer

    if buffer.startswith(b"*"):
        try:
            line_end = buffer.index(b"\r\n")
            num_args = int(buffer[1:line_end].decode())
            pos = line_end + 2
            args: list[str] = []

            for _ in range(num_args):
                if pos >= len(buffer):
                    return None, buffer
                if buffer[pos : pos + 1] != b"$":
                    return None, buffer
                dollar_end = buffer.index(b"\r\n", pos)
                arg_len = int(buffer[pos + 1 : dollar_end].decode())
                pos = dollar_end + 2
                arg_bytes = buffer[pos : pos + arg_len]
                args.append(arg_bytes.decode("utf-8", errors="replace"))
                pos += arg_len + 2

            return args, buffer[pos:]
        except (ValueError, IndexError):
            return None, buffer

    # Simple inline command (e.g. "PING\r\n")
    if b"\r\n" in buffer:
        line, rest = buffer.split(b"\r\n", 1)
        parts = line.decode("utf-8", errors="replace").split()
        return parts, rest

    return None, buffer


# =============================================================================
# Cypher Execution Engine
# =============================================================================


def execute_cypher(graph: PropertyGraph, query: str) -> tuple[list[str], list[list[Any]], list[str]]:
    """Execute a Cypher query against PropertyGraph, returning header, rows, and stats."""
    clean_q = query.strip()
    logger.info("Cypher query: %s", clean_q[:150])
    stats = ["Query internal execution time: 0.150000 milliseconds"]

    # 1. CYPHER params header extraction (e.g. CYPHER `id`='...' `props`={...} MERGE ...)
    params: dict[str, Any] = {}
    if clean_q.startswith("CYPHER "):
        parts = re.split(r"\s+(?=MERGE|MATCH|CREATE|RETURN|CALL|DETACH|DELETE)", clean_q[7:], maxsplit=1)
        params_str = parts[0]
        clean_q = parts[1].strip() if len(parts) > 1 else ""

        pattern = r"`?([a-zA-Z0-9_]+)`?=(\{[^}]*\}|\[[^\]]*\]|\"[^\"]*\"|'[^']*'|[^\s]+)"
        for m in re.finditer(pattern, params_str):
            k = m.group(1)
            raw_v = m.group(2).strip()
            if raw_v.startswith("{") and raw_v.endswith("}"):
                d = {}
                for pm in re.finditer(r"`?([a-zA-Z0-9_]+)`?:\s*(\"[^\"]*\"|'[^']*'|[^\s,}]+)", raw_v):
                    pk = pm.group(1)
                    pv = pm.group(2).strip("\"'")
                    d[pk] = pv
                params[k] = d
            elif raw_v.startswith('"') and raw_v.endswith('"'):
                params[k] = raw_v[1:-1]
            elif raw_v.startswith("'") and raw_v.endswith("'"):
                params[k] = raw_v[1:-1]
            else:
                params[k] = raw_v

    # MERGE (n:Label {id: ..., project_id: ...}) SET n += ...
    if "MERGE (n:" in clean_q or "MERGE (s)-[r:" in clean_q:
        if "MERGE (n:" in clean_q:
            label_match = re.search(r"MERGE\s+\(n:([a-zA-Z0-9_]+)", clean_q)
            label = label_match.group(1) if label_match else "Knowledge"
            node_id = params.get("id")
            proj_id = params.get("project_id", "")
            raw_id = params.get("raw_id", node_id.split(":", 1)[1] if (node_id and ":" in node_id) else (node_id or ""))
            props = params.get("props", {})
            if not isinstance(props, dict):
                props = {}
            if node_id:
                if node_id in graph.nodes:
                    graph.nodes[node_id]["properties"].update(props)
                    graph.nodes[node_id]["label"] = label
                else:
                    graph.nodes[node_id] = {
                        "id": node_id,
                        "raw_id": raw_id,
                        "project_id": proj_id,
                        "label": label,
                        "properties": dict(props),
                    }
                stats.append("Nodes created: 1")
                stats.append("Properties set: 1")
                return [], [], stats

        if "MERGE (s)-[r:" in clean_q:
            m = re.search(r"MERGE\s+\(s\)-\[r:([a-zA-Z0-9_]+)\]->\(t\)", clean_q)
            rel_type = m.group(1) if m else "CONNECTED_TO"
            s_id = params.get("source_id", "")
            t_id = params.get("target_id", "")
            proj_id = params.get("project_id", "")
            props = params.get("props", {})
            graph.edges.append({
                "source_id": s_id,
                "target_id": t_id,
                "rel_type": rel_type,
                "project_id": proj_id,
                "properties": props if isinstance(props, dict) else {},
            })
            stats.append("Relationships created: 1")
            return [], [], stats

    # DETACH DELETE n
    if "DETACH DELETE n" in clean_q:
        cid = params.get("composite_id", "")
        rid = params.get("raw_id", "")
        pid = params.get("project_id", "")
        deleted = 0
        for nid in list(graph.nodes.keys()):
            n = graph.nodes[nid]
            if (n["id"] == cid or n["raw_id"] == rid or n["id"] == rid) and (not pid or n["project_id"] == pid):
                del graph.nodes[nid]
                deleted += 1
        graph.edges = [
            e for e in graph.edges if e["source_id"] not in (cid, rid) and e["target_id"] not in (cid, rid)
        ]
        stats.append(f"Nodes deleted: {deleted}")
        return [], [], stats

    # MATCH (s)-[r:REL]->(t) DELETE r
    if "DELETE r" in clean_q:
        sid = params.get("source_id", "")
        tid = params.get("target_id", "")
        deleted = 0
        new_edges = []
        for e in graph.edges:
            if (e["source_id"] == sid or e["source_id"].endswith(f":{sid}")) and (
                e["target_id"] == tid or e["target_id"].endswith(f":{tid}")
            ):
                deleted += 1
            else:
                new_edges.append(e)
        graph.edges = new_edges
        stats.append(f"Relationships deleted: {deleted}")
        return [], [], stats

    # -------------------------------------------------------------------------
    # QUERY HANDLERS FOR GRAPH RESUME & REASONING
    # -------------------------------------------------------------------------

    # 1. Unfinished Tasks query: MATCH (p:Project)-[:HAS_TASK]->(t:Task) WHERE t.status IN [...]
    if "[:HAS_TASK]->(t:Task)" in clean_q:
        header = ["comp_id", "raw_id", "title", "status", "priority", "dependencies"]
        rows = []
        for n in graph.nodes.values():
            if n["label"] == "Task":
                p = n["properties"]
                status = p.get("status", "todo")
                if status in ("todo", "in_progress", "blocked"):
                    # Find dependencies
                    deps = []
                    for e in graph.edges:
                        if e["rel_type"] == "DEPENDS_ON" and (
                            e["source_id"] == n["id"] or e["source_id"] == n["raw_id"]
                        ):
                            dep_node = graph.nodes.get(e["target_id"])
                            if not dep_node:
                                for dn in graph.nodes.values():
                                    if dn["raw_id"] == e["target_id"] or dn["id"].endswith(f":{e['target_id']}"):
                                        dep_node = dn
                                        break
                            if dep_node:
                                deps.append({
                                    "id": dep_node["raw_id"],
                                    "title": dep_node["properties"].get("title", dep_node["raw_id"]),
                                    "status": dep_node["properties"].get("status", "todo"),
                                })
                            else:
                                deps.append({"id": e["target_id"], "title": e["target_id"], "status": "completed"})
                    rows.append([
                        n["id"],
                        n["raw_id"],
                        p.get("title", n["raw_id"]),
                        status,
                        p.get("priority", "medium"),
                        deps,
                    ])
        return header, rows, stats

    # 1b. Requirement Blocker / Conflict on Decision: MATCH (r:Requirement)-[:BLOCKS]->(d:Decision)
    if "(r:Requirement" in clean_q and "(d:Decision)" in clean_q:
        header = ["conflicting_decision", "status"]
        rows = []
        for e in graph.edges:
            if e["rel_type"] in ("BLOCKS", "CONFLICTS_WITH"):
                s_node = graph.nodes.get(e["source_id"])
                t_node = graph.nodes.get(e["target_id"])
                if s_node and s_node["label"] == "Requirement" and t_node and t_node["label"] == "Decision":
                    rows.append([t_node["properties"].get("title", t_node["raw_id"]), t_node["properties"].get("status", "approved")])
        return header, rows, stats

    # 1c. Requirement impacts module: MATCH (r:Requirement)-[:DEPENDS_ON]->(m:Module)
    if "(r:Requirement" in clean_q and "(m:Module)" in clean_q:
        header = ["module_name", "task_count"]
        rows = []
        for e in graph.edges:
            if e["rel_type"] == "DEPENDS_ON":
                s_node = graph.nodes.get(e["source_id"])
                t_node = graph.nodes.get(e["target_id"])
                if s_node and s_node["label"] == "Requirement":
                    t_count = sum(1 for n in graph.nodes.values() if n["label"] == "Task" and n["properties"].get("module_id") == e["target_id"].split(":")[-1])
                    t_name = t_node["properties"].get("title", e["target_id"].split(":")[-1]) if t_node else e["target_id"].split(":")[-1]
                    rows.append([t_name, t_count])
        return header, rows, stats

    # 2. Blockers query: MATCH (t:Task) ... (t)-[:BLOCKED_BY]->(b)
    if "[:BLOCKED_BY]->" in clean_q or "[:BLOCKS]->" in clean_q:
        header = ["task_id", "blockers"]
        rows = []
        for n in graph.nodes.values():
            if n["label"] == "Task":
                blockers = []
                for e in graph.edges:
                    if e["rel_type"] in ("BLOCKED_BY", "BLOCKS"):
                        if e["rel_type"] == "BLOCKED_BY" and (
                            e["source_id"] == n["id"] or e["source_id"] == n["raw_id"]
                        ):
                            blockers.append(e["target_id"].split(":")[-1])
                        elif e["rel_type"] == "BLOCKS" and (
                            e["target_id"] == n["id"] or e["target_id"] == n["raw_id"]
                        ):
                            blockers.append(e["source_id"].split(":")[-1])
                rows.append([n["raw_id"], blockers])
        return header, rows, stats

    # 3. Required Capabilities: MATCH (t:Task)-[:REQUIRES]->(c:Capability)
    if "[:REQUIRES]->(c:Capability)" in clean_q:
        header = ["task_id", "capabilities"]
        rows = []
        for n in graph.nodes.values():
            if n["label"] == "Task":
                caps = []
                for e in graph.edges:
                    if e["rel_type"] == "REQUIRES" and (
                        e["source_id"] == n["id"] or e["source_id"] == n["raw_id"]
                    ):
                        c_target = e["target_id"].split(":")[-1]
                        caps.append(c_target)
                rows.append([n["raw_id"], caps])
        return header, rows, stats

    # 4. Agent Capabilities: MATCH (a:Agent)-[:HAS_CAPABILITY]->(c:Capability)
    if "[:HAS_CAPABILITY]->(c:Capability)" in clean_q:
        header = ["agent_id", "agent_name", "provider", "capabilities"]
        rows = []
        for n in graph.nodes.values():
            if n["label"] == "Agent":
                caps = []
                for e in graph.edges:
                    if e["rel_type"] == "HAS_CAPABILITY" and (
                        e["source_id"] == n["id"] or e["source_id"] == n["raw_id"]
                    ):
                        caps.append(e["target_id"].split(":")[-1])
                rows.append([
                    n["raw_id"],
                    n["properties"].get("name", n["raw_id"]),
                    n["properties"].get("provider", "AI"),
                    caps,
                ])
        return header, rows, stats

    # 4d. Critical tasks query: MATCH (t:Task) WHERE t.priority = 'critical'
    if "WHERE t.priority = 'critical'" in clean_q:
        header = ["task_id", "title", "priority"]
        rows = []
        for n in graph.nodes.values():
            if n["label"] == "Task" and n["properties"].get("priority") == "critical" and n["properties"].get("status") == "todo":
                rows.append([n["id"], n["properties"].get("title", ""), n["properties"].get("priority", "")])
        return header, rows, stats

    # 5. Connected Decisions: MATCH (t:Task)-[r:REFERENCES|AFFECTS|SUPPORTS*1..2]-(d:Decision)
    if "(d:Decision)" in clean_q:
        header = ["task_id", "decisions"]
        rows = []
        for n in graph.nodes.values():
            if n["label"] == "Task":
                decs = []
                for e in graph.edges:
                    if e["rel_type"] in ("AFFECTS", "REFERENCES", "SUPPORTS"):
                        d_id = (
                            e["source_id"]
                            if (e["target_id"] == n["id"] or e["target_id"] == n["raw_id"])
                            else (e["target_id"] if (e["source_id"] == n["id"] or e["source_id"] == n["raw_id"]) else None)
                        )
                        if d_id:
                            d_node = graph.nodes.get(d_id)
                            if d_node and d_node["label"] == "Decision":
                                decs.append({
                                    "id": d_node["raw_id"],
                                    "title": d_node["properties"].get("title", d_node["raw_id"]),
                                    "decision": d_node["properties"].get("decision", ""),
                                    "status": d_node["properties"].get("status", "approved"),
                                })
                rows.append([n["raw_id"], decs])
        return header, rows, stats

    # 6. Connected Knowledge: MATCH (t:Task)-[r:REFERENCES*1..2]-(k:Knowledge)
    if "(k:Knowledge)" in clean_q:
        header = ["task_id", "knowledge"]
        rows = []
        for n in graph.nodes.values():
            if n["label"] == "Task":
                knows = []
                for e in graph.edges:
                    if e["rel_type"] == "REFERENCES":
                        k_id = (
                            e["source_id"]
                            if (e["target_id"] == n["id"] or e["target_id"] == n["raw_id"])
                            else (e["target_id"] if (e["source_id"] == n["id"] or e["source_id"] == n["raw_id"]) else None)
                        )
                        if k_id:
                            k_node = graph.nodes.get(k_id)
                            if k_node and k_node["label"] == "Knowledge":
                                knows.append({
                                    "id": k_node["raw_id"],
                                    "title": k_node["properties"].get("title", k_node["raw_id"]),
                                    "content": k_node["properties"].get("content", ""),
                                })
                rows.append([n["raw_id"], knows])
        return header, rows, stats

    # 7. Generic MATCH (n) WHERE (n.id = $composite_id ...) RETURN labels(n), properties(n)
    if "RETURN labels(n)" in clean_q and "properties(n)" in clean_q:
        header = ["labels", "props"]
        rows = []
        cid = params.get("composite_id", "")
        rid = params.get("raw_id", "")
        for n in graph.nodes.values():
            if n["id"] == cid or n["raw_id"] == rid or n["id"] == rid:
                rows.append([[n["label"]], n["properties"]])
                break
        return header, rows, stats

    # 8. MATCH (n {project_id: $project_id}) RETURN labels(n), n.id, n.raw_id, properties(n)
    if "MATCH (n {project_id:" in clean_q:
        header = ["labels", "id", "raw_id", "props"]
        rows = []
        for n in graph.nodes.values():
            rows.append([[n["label"]], n["id"], n["raw_id"], n["properties"]])
        return header, rows, stats

    # Default fallback empty result
    return [], [], stats


def to_falkor_compact_cell(val: Any) -> list[Any]:
    if val is None:
        return [1, None]
    if isinstance(val, bool):
        return [4, "true" if val else "false"]
    if isinstance(val, int):
        return [3, val]
    if isinstance(val, float):
        return [5, str(val)]
    if isinstance(val, str):
        return [2, val]
    if isinstance(val, list):
        return [6, [to_falkor_compact_cell(item) for item in val]]
    if isinstance(val, dict):
        map_entries = []
        for k, v in val.items():
            map_entries.append(k)
            map_entries.append(to_falkor_compact_cell(v))
        return [10, map_entries]
    return [2, str(val)]


# =============================================================================
# Redis Server Connection Handler
# =============================================================================


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    buffer = b""
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            buffer += data

            while True:
                args, remaining = parse_resp_command(buffer)
                if args is None:
                    break
                buffer = remaining

                cmd = args[0].upper() if args else ""

                if cmd == "PING":
                    writer.write(b"+PONG\r\n")
                    await writer.drain()

                elif cmd in ("COMMAND", "CLIENT", "INFO"):
                    # Basic handshake
                    writer.write(b"+OK\r\n")
                    await writer.drain()

                elif cmd in ("GRAPH.QUERY", "GRAPH.RO_QUERY"):
                    graph_name = args[1]
                    cypher = args[2]
                    graph = get_or_create_graph(graph_name)
                    header, rows, stats = execute_cypher(graph, cypher)

                    # Build FalkorDB QueryResult compact response format
                    # Header is list of [col_type, col_name]
                    resp_header = [[1, h] for h in header] if header else []
                    resp_rows = []
                    for row in rows:
                        resp_rows.append([to_falkor_compact_cell(cell) for cell in row])
                    resp_stats = [s.encode("utf-8") for s in stats]

                    if not resp_header and not resp_rows:
                        # Mutation query with no RETURN (only stats)
                        encoded = encode_resp_array([resp_stats])
                    else:
                        encoded = encode_resp_array([resp_header, resp_rows, resp_stats])

                    writer.write(encoded)
                    await writer.drain()

                elif cmd == "GRAPH.DELETE":
                    graph_name = args[1]
                    if graph_name in GRAPHS:
                        del GRAPHS[graph_name]
                    writer.write(b"+OK\r\n")
                    await writer.drain()

                else:
                    writer.write(b"+OK\r\n")
                    await writer.drain()

    except Exception as e:
        logger.debug("Client handler error: %s", e)
    finally:
        writer.close()
        await writer.wait_closed()


async def run_server(host: str = "127.0.0.1", port: int = 6379) -> None:
    server = await asyncio.start_server(handle_client, host, port)
    logger.info("FalkorDB service running on %s:%d (Redis RESP Protocol)", host, port)
    async with server:
        await server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="FalkorDB Redis RESP Server Harness")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=6379, help="Port to bind (default: 6379)")
    args = parser.parse_args()

    try:
        asyncio.run(run_server(args.host, args.port))
    except KeyboardInterrupt:
        logger.info("FalkorDB server stopped.")


if __name__ == "__main__":
    main()
