#!/usr/bin/env python3
"""
One-time cleanup for Bundle_04_Generate_and_Deploy_V2.ipynb:
- Replace every IP-check code cell with a short WorkspaceClient-only cell.
- Remove create_target_workspace_client from imports.
- Replace every "if auth_method == 'sp_oauth': ... else: ... create_target_workspace_client"
  block with "from databricks.sdk import WorkspaceClient; target_client = WorkspaceClient()".

Run from repo root: python3 scripts/cleanup_bundle04_oauth_only.py
"""
import json

NOTEBOOK = "src/notebooks/Bundle_04_Generate_and_Deploy_V2.ipynb"

SHORT_IP_SOURCE = [
    "# IP check removed; use target workflow (Deploy_Dashboards_Target) for OAuth-only deploy.\n",
    "from databricks.sdk import WorkspaceClient\n",
    "target_client = WorkspaceClient()\n",
    'print("(Pre-deployment IP check removed; deploy on target with Deploy_Dashboards_Target.)")\n',
    'print("")\n',
]


def main():
    with open(NOTEBOOK) as f:
        nb = json.load(f)

    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", [])
        raw = "".join(src)
        if "Import IP ACL manager" in raw and "PRE-DEPLOYMENT IP WHITELIST" in raw:
            cell["source"] = SHORT_IP_SOURCE

        # Drop create_target_workspace_client from imports
        if "from helpers import" in raw and "create_target_workspace_client" in raw:
            cell["source"] = [l for l in src if "create_target_workspace_client" not in l]

        # Replace every auth block: remove "if auth_method == 'sp_oauth':" through end of "else: ... create_target_workspace_client(...)"
        # Match only the block starter (not the ternary in print(...))
        lines = list(cell["source"])
        while True:
            block_start = None
            for idx, line in enumerate(lines):
                if "if auth_method == 'sp_oauth':" in line and "print(" not in line and "get_target_client_sp" in "".join(lines[idx : idx + 3]):
                    block_start = idx
                    break
            if block_start is None:
                break
            out = []
            i = 0
            while i < len(lines):
                line = lines[i]
                if i == block_start and "if auth_method == 'sp_oauth':" in line and "print(" not in line:
                    indent = len(line) - len(line.lstrip())
                    pad = " " * indent
                    out.append(pad + "from databricks.sdk import WorkspaceClient\n")
                    out.append(pad + "target_client = WorkspaceClient()\n")
                    i += 1
                    # Skip until past the else branch (closing ")" of create_target_workspace_client)
                    seen_else = False
                    while i < len(lines):
                        cur = lines[i]
                        if cur.strip() == "else:":
                            seen_else = True
                        if cur.strip() == ")" and seen_else and i > 0:
                            prev = "".join(lines[max(0, i - 3) : i])
                            if "secret_scope" in prev or "target_workspace" in prev:
                                i += 1
                                if i < len(lines) and lines[i].strip() == "":
                                    i += 1
                                break
                        i += 1
                    continue
                out.append(line)
                i += 1
            cell["source"] = out
            lines = out

    # Remove any orphaned get_target_client_sp / create_target_workspace_client blocks (lines that were left behind)
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        lines = cell["source"]
        out = []
        skip_until = 0
        for i, line in enumerate(lines):
            if i < skip_until:
                continue
            if "get_target_client_sp" in line or ("create_target_workspace_client" in line and "target_client =" in line):
                # Skip this line and the next few (target_url, secret_scope, ) )
                j = i + 1
                while j < len(lines) and (lines[j].strip() in ("", ")") or "target_url" in lines[j] or "secret_scope" in lines[j]):
                    j += 1
                skip_until = j
                continue
            if "from helpers.auth import create_target_workspace_client" in line or "from helpers.sp_oauth_auth import get_target_client_sp" in line:
                continue
            out.append(line)
        if len(out) < len(lines):
            cell["source"] = out

    with open(NOTEBOOK, "w") as f:
        json.dump(nb, f, indent=2)
    print("Done. Open the notebook and run 'Kernel > Restart & Run All' to verify.")


if __name__ == "__main__":
    main()
