from __future__ import annotations

import shlex


def quote_remote_arg(arg: str) -> str:
    text = str(arg)
    if text == "~":
        return "~"
    if text.startswith("~/"):
        rest = text[2:]
        return "~/" + shlex.quote(rest) if rest else "~/"
    return shlex.quote(text)


def build_remote_slidebridge_command(
    remote_runner: str,
    subcommand_args: list[str],
    remote_workdir: str | None = None,
) -> str:
    runner = str(remote_runner or "slidebridge").strip()
    if not runner:
        raise ValueError("remote_runner must not be empty")
    command = " ".join([runner] + [quote_remote_arg(arg) for arg in subcommand_args])
    if remote_workdir:
        return f"cd {quote_remote_arg(remote_workdir)} && {command}"
    return command


def build_find_command(
    remote_dir: str,
    patterns: list[str],
    max_depth: int = 2,
    limit: int = 100,
) -> str:
    safe_patterns = [pattern.strip() for pattern in patterns if pattern.strip()]
    if not safe_patterns:
        safe_patterns = ["*.svs", "*.tif", "*.tiff"]
    name_expr = " -o ".join(f"-name {quote_remote_arg(pattern)}" for pattern in safe_patterns)
    return (
        f"find {quote_remote_arg(remote_dir)} -maxdepth {max(1, int(max_depth))} "
        f"-type f \\( {name_expr} \\) "
        f"-printf '%p\\t%s\\t%TY-%Tm-%Td %TH:%TM\\n' | head -n {max(1, int(limit))}"
    )
