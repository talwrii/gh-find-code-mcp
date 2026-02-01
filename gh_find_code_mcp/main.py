import json
import shutil
import subprocess

from mcp.server.fastmcp import FastMCP

server = FastMCP(
    "gh-find-code-mcp",
    instructions=(
        "Use this server to find existing code, libraries, and projects on GitHub. "
        "When the user needs a library, tool, or example code for something, "
        "search GitHub before trying to write it from scratch. "
        "It is cheaper to find something than to make it. "
        "Results are sorted by stars (most popular first). "
        "If you cannot find what you need in the results, DO NOT ask the user — "
        "refine your search with more specific terms, language filters, "
        "topic filters, or more precise keywords. "
        "Keep searching with different queries until you find a good match."
    ),
)


def _run_gh(args: list[str]) -> str:
    gh = shutil.which("gh")
    if gh is None:
        return "Error: gh CLI not found in PATH"
    result = subprocess.run(
        [gh, *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return f"Error: {result.stderr.strip()}"
    return result.stdout.strip()


@server.tool()
def search_repos(
    query: str,
    language: str = "",
    topic: str = "",
    owner: str = "",
    sort: str = "stars",
    limit: int = 20,
) -> str:
    """Search GitHub for repositories matching a query.

    Use this to find libraries, tools, projects, and example code.
    Returns JSON with repo name, description, stars, language, and URL.

    Args:
        query: Search terms. Use quotes for exact phrases, e.g. "vim plugin".
               Supports GitHub search syntax like "topic:cli language:python".
        language: Filter by programming language, e.g. "python", "go", "rust".
        topic: Filter by topic, e.g. "cli" or "mcp-server". Comma-separate multiple.
        owner: Filter by GitHub user or org, e.g. "anthropics".
        sort: Sort by: stars, best-match, forks, updated, help-wanted-issues. Default: stars.
        limit: Max results to return (1-30, default 20).
    """
    limit = min(max(limit, 1), 30)
    args = [
        "search", "repos", query,
        "--json", "fullName,description,stargazersCount,language,url",
        "--limit", str(limit),
    ]
    if sort != "best-match":
        args.extend(["--sort", sort])
    if language:
        args.extend(["--language", language])
    if topic:
        for t in topic.split(","):
            args.extend(["--topic", t.strip()])
    if owner:
        args.extend(["--owner", owner])

    raw = _run_gh(args)
    if raw.startswith("Error:"):
        return raw

    try:
        repos = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    if not repos:
        return "No repositories found. Try broader or different search terms."

    results = []
    for r in repos:
        desc = r.get("description") or ""
        if len(desc) > 1000:
            desc = desc[:997] + "..."
        results.append({
            "name": r["fullName"],
            "stars": r.get("stargazersCount", 0),
            "language": r.get("language") or "?",
            "description": desc,
            "url": r["url"],
        })

    return json.dumps({"count": len(results), "repos": results}, indent=2)


def main():
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
