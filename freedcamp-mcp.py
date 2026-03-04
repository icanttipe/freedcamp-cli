#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["mcp"]
# ///
"""freedcamp-mcp - MCP server for Freedcamp API"""

import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from mcp.server.fastmcp import FastMCP

BASE_URL = "https://freedcamp.com/api/v1"

mcp = FastMCP("freedcamp")


# ─── Config & Auth ───────────────────────────────────────────────────────────


def load_config():
    path = os.path.join(
        os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
        "freedcamp",
        "config.json",
    )
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config not found: {path}. Run 'freedcamp init' to configure.")
    mode = os.stat(path).st_mode & 0o777
    if mode & 0o077:
        raise PermissionError(f"{path} is accessible by others (mode {oct(mode)}). Run: chmod 600 {path}")
    with open(path) as f:
        return json.load(f)


def auth_params(cfg):
    ts = str(int(time.time()))
    msg = cfg["api_key"] + ts
    h = hmac.new(cfg["api_secret"].encode(), msg.encode(), hashlib.sha1).hexdigest()
    return {"api_key": cfg["api_key"], "timestamp": ts, "hash": h}


def api_request(cfg, method, endpoint, params=None, data=None):
    query = auth_params(cfg)
    if params:
        query.update(params)
    url = f"{BASE_URL}/{endpoint}?{urllib.parse.urlencode(query)}"

    if method == "GET":
        req = urllib.request.Request(url)
    elif method == "DELETE":
        req = urllib.request.Request(url, method="DELETE")
    else:
        boundary = f"----Freedcamp{secrets.token_hex(16)}"
        body = f"--{boundary}\r\nContent-Disposition: form-data; name=\"data\"\r\n\r\n{json.dumps(data)}\r\n--{boundary}--\r\n"
        req = urllib.request.Request(url, data=body.encode(), method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")
        try:
            err = json.loads(err_body)
            raise RuntimeError(f"API error {e.code}: {err.get('msg', err_body)}")
        except json.JSONDecodeError:
            raise RuntimeError(f"API error {e.code}: {err_body[:200]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error: {e.reason}")

    if result.get("http_code", 200) != 200:
        raise RuntimeError(f"API error: {result.get('msg', 'Unknown error')}")

    return result


def api_get(cfg, endpoint, **params):
    return api_request(cfg, "GET", endpoint, params=params)


def api_post(cfg, endpoint, **data):
    return api_request(cfg, "POST", endpoint, data=data)


def api_delete(cfg, endpoint):
    return api_request(cfg, "DELETE", endpoint)


# ─── Tools ───────────────────────────────────────────────────────────────────


@mcp.tool()
def list_projects() -> str:
    """List all accessible Freedcamp projects."""
    cfg = load_config()
    resp = api_get(cfg, "sessions/current")
    projects = resp["data"].get("projects", [])
    if not projects:
        return "No projects found."
    lines = []
    for p in projects:
        lines.append(f"- {p['project_name']} (ID: {p['project_id']})")
    return "\n".join(lines)


@mcp.tool()
def list_tasks(project_id: str, include_completed: bool = False) -> str:
    """List tasks for a project, organized by parent/subtask hierarchy.

    Args:
        project_id: The project ID to list tasks for.
        include_completed: Whether to include completed tasks (default: false).
    """
    cfg = load_config()
    resp = api_get(cfg, "tasks", project_id=project_id, limit="200")
    tasks = resp["data"].get("tasks", [])
    if not tasks:
        return "No tasks found."

    parents = [t for t in tasks if not t["h_parent_id"]]
    children = {}
    for t in tasks:
        if t["h_parent_id"]:
            children.setdefault(t["h_parent_id"], []).append(t)

    icons = {0: "○", 1: "✓", 2: "◐"}
    lines = []
    for p in parents:
        if not include_completed and p["status"] == 1:
            continue
        s = icons.get(p["status"], "?")
        lines.append(f"{s} [{p['id']}] {p['title']}")
        for c in children.get(p["id"], []):
            if not include_completed and c["status"] == 1:
                continue
            cs = icons.get(c["status"], "?")
            lines.append(f"  {cs} [{c['id']}] {c['title']}")

    return "\n".join(lines) if lines else "No tasks found (all completed)."


@mcp.tool()
def get_task(task_id: str) -> str:
    """Get details of a specific task.

    Args:
        task_id: The task ID.
    """
    cfg = load_config()
    resp = api_get(cfg, f"tasks/{task_id}")
    t = resp["data"]["tasks"][0]

    status_names = {0: "Not started", 1: "Completed", 2: "In Progress"}
    lines = [
        f"Title:    {t['title']}",
        f"ID:       {t['id']}",
        f"Status:   {status_names.get(t['status'], t['status'])}",
        f"Priority: {t['priority_title']}",
        f"Assigned: {t.get('assigned_to_fullname', 'N/A')}",
    ]
    if t.get("start_ts"):
        from datetime import datetime as dt
        lines.append(f"Start:    {dt.fromtimestamp(t['start_ts']).strftime('%Y-%m-%d')}")
    if t.get("due_ts"):
        from datetime import datetime as dt
        lines.append(f"Due:      {dt.fromtimestamp(t['due_ts']).strftime('%Y-%m-%d')}")
    if t.get("description"):
        lines.append(f"Desc:     {t['description']}")
    lines.append(f"URL:      {t['url']}")
    return "\n".join(lines)


@mcp.tool()
def create_task(
    title: str,
    project_id: str,
    description: str = "",
    assigned_to_id: str = "0",
    priority: str = "0",
    status: str = "0",
    start_date: str = "",
    due_date: str = "",
    parent_id: str = "",
    task_group_id: str = "",
) -> str:
    """Create a new task.

    Args:
        title: Task title.
        project_id: Project ID to create the task in.
        description: Task description.
        assigned_to_id: User ID to assign the task to (0 = unassigned).
        priority: Priority level (0=none, 1=low, 2=medium, 3=high).
        status: Initial status (0=not started, 1=completed, 2=in progress).
        start_date: Start date in YYYY-MM-DD format.
        due_date: Due date in YYYY-MM-DD format.
        parent_id: Parent task ID to create as subtask.
        task_group_id: Task group ID.
    """
    cfg = load_config()
    data = {
        "title": title,
        "project_id": project_id,
        "priority": priority,
        "assigned_to_id": assigned_to_id,
    }
    if task_group_id:
        data["task_group_id"] = task_group_id
    if description:
        data["description"] = description
    if start_date:
        data["start_date"] = start_date
    if due_date:
        data["due_date"] = due_date
    if parent_id:
        data["h_parent_id"] = parent_id

    resp = api_request(cfg, "POST", "tasks", data=data)
    task_id = resp["data"]["tasks"][0]["id"]

    if status and status != "0":
        api_post(cfg, f"tasks/{task_id}", status=status)

    return f"Task created (ID: {task_id})"


@mcp.tool()
def update_task(
    task_id: str,
    title: str = "",
    description: str = "",
    status: str = "",
    start_date: str = "",
    due_date: str = "",
    assigned_to_id: str = "",
    priority: str = "",
) -> str:
    """Update an existing task. Only provided fields are modified.

    Args:
        task_id: The task ID to update.
        title: New title.
        description: New description.
        status: New status (0=not started, 1=completed, 2=in progress).
        start_date: New start date (YYYY-MM-DD).
        due_date: New due date (YYYY-MM-DD).
        assigned_to_id: New assignee user ID.
        priority: New priority (0=none, 1=low, 2=medium, 3=high).
    """
    cfg = load_config()
    data = {}
    if title:
        data["title"] = title
    if description:
        data["description"] = description
    if status:
        data["status"] = status
    if start_date:
        data["start_date"] = start_date
    if due_date:
        data["due_date"] = due_date
    if assigned_to_id:
        data["assigned_to_id"] = assigned_to_id
    if priority:
        data["priority"] = priority

    if not data:
        return "Nothing to update — no fields provided."

    resp = api_request(cfg, "POST", f"tasks/{task_id}", data=data)
    return f"Task updated: {resp['data']['tasks'][0]['status_title']}"


@mcp.tool()
def complete_task(task_id: str) -> str:
    """Mark a task as completed.

    Args:
        task_id: The task ID to complete.
    """
    cfg = load_config()
    resp = api_post(cfg, f"tasks/{task_id}", status="1")
    return f"Task completed: {resp['data']['tasks'][0]['status_title']}"


@mcp.tool()
def delete_task(task_id: str) -> str:
    """Delete a task.

    Args:
        task_id: The task ID to delete.
    """
    cfg = load_config()
    api_delete(cfg, f"tasks/{task_id}")
    return f"Task {task_id} deleted."


@mcp.tool()
def raw_api(method: str, endpoint: str, data: str = "") -> str:
    """Make a raw API call to the Freedcamp API.

    Args:
        method: HTTP method (GET, POST, or DELETE).
        endpoint: API endpoint (e.g. "tasks", "sessions/current").
        data: For GET: query params as "key=val&key2=val2". For POST: JSON string.
    """
    cfg = load_config()
    method = method.upper()
    if method not in ("GET", "POST", "DELETE"):
        return "Error: method must be GET, POST, or DELETE."

    if method == "GET":
        params = dict(p.split("=", 1) for p in data.split("&") if "=" in p) if data else {}
        resp = api_get(cfg, endpoint, **params)
    elif method == "POST":
        try:
            parsed = json.loads(data) if data else {}
        except json.JSONDecodeError as e:
            return f"Error: invalid JSON — {e}"
        resp = api_request(cfg, "POST", endpoint, data=parsed)
    else:
        resp = api_delete(cfg, endpoint)

    return json.dumps(resp, indent=2, ensure_ascii=False)


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
