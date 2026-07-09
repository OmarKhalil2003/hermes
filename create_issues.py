import os
import re
import sys
from typing import Any

import httpx

# GitHub Repository Configuration
REPO_OWNER = "OmarKhalil2003"
REPO_NAME = "hermes"
BACKLOG_PATH = "docs/TICKET_BACKLOG.md"


def parse_backlog(filepath: str) -> list[dict[str, Any]]:
    """Parses docs/TICKET_BACKLOG.md to extract ticket metadata."""
    if not os.path.exists(filepath):
        sys.stderr.write(f"Error: Backlog file '{filepath}' not found.\n")
        return []

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # Split the backlog content by ticket blocks
    ticket_blocks = re.split(r"### Ticket ", content)
    tickets = []

    for block in ticket_blocks[1:]:
        lines = block.strip().split("\n")
        if not lines:
            continue

        header = lines[0].strip()
        ticket_id_match = re.match(r"`(TASK-\d+)`:\s*(.*)", header)
        if not ticket_id_match:
            continue

        ticket_id = ticket_id_match.group(1)
        name = ticket_id_match.group(2)

        rest = "\n".join(lines[1:])

        # Parse key fields
        title_match = re.search(r"- \*\*Title\*\*:\s*`(.*?)`", rest)
        points_match = re.search(r"- \*\*Story Points\*\*:\s*(\d+)", rest)
        assignee_match = re.search(r"- \*\*Assignee\*\*:\s*(.*)", rest)

        title = title_match.group(1) if title_match else name
        points = points_match.group(1) if points_match else "0"
        assignee_text = (
            assignee_match.group(1).strip() if assignee_match else "Unassigned"
        )

        # Determine assignees labels
        labels = ["task", f"SP: {points}"]
        if "Developer A" in assignee_text:
            labels.append("dev-a")
        elif "Developer B" in assignee_text:
            labels.append("dev-b")
        elif "Pair" in assignee_text:
            labels.append("pair")

        # Extract description body
        body_start = rest.find("- **Description**:")
        if body_start == -1:
            body_start = rest.find("Description:")

        body = rest[body_start:] if body_start != -1 else rest

        # Build clean GitHub markdown issue body
        full_body = (
            f"### 📋 {ticket_id}: {title}\n\n"
            f"- **Estimated Complexity**: {points} Story Points\n"
            f"- **Target Role**: {assignee_text}\n"
            f"\n---\n\n"
            f"{body.strip()}"
        )

        tickets.append(
            {"title": f"[{ticket_id}] {title}", "body": full_body, "labels": labels}
        )

    return tickets


def create_github_issues(token: str, tickets: list[dict[str, Any]]) -> None:
    """Invokes GitHub API to populate issues in the repository."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    client = httpx.Client(headers=headers)
    print(  # noqa: T201
        f"Creating {len(tickets)} issues on {REPO_OWNER}/{REPO_NAME}..."
    )

    for i, ticket in enumerate(tickets, 1):
        response = client.post(url, json=ticket)
        if response.status_code == 201:
            print(f"[{i}/{len(tickets)}] Created: {ticket['title']}")  # noqa: T201
        else:
            sys.stderr.write(
                f"Error creating '{ticket['title']}': Status {response.status_code}\n"
                f"Response: {response.text}\n"
            )


def main() -> None:
    # Retrieve Personal Access Token
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("GitHub token not found in GITHUB_TOKEN env var.")  # noqa: T201
        token = input("Please enter your GitHub Personal Access Token (PAT): ").strip()

    if not token:
        sys.stderr.write("Error: A valid GitHub PAT is required to create issues.\n")
        sys.exit(1)

    tickets = parse_backlog(BACKLOG_PATH)
    if not tickets:
        sys.stderr.write("No tickets found in backlog file.\n")
        sys.exit(0)

    create_github_issues(token, tickets)
    print("\nDone! All issues populated successfully.")  # noqa: T201


if __name__ == "__main__":
    main()
