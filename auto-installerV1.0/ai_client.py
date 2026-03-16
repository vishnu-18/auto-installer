"""AI API client using Hugging Face Router (chat completions)."""

import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "qwen-3-235b-a22b-instruct-2507")
CEREBRAS_API_URL = "https://api.cerebras.ai/v1/chat/completions"

HEADERS = {
    "Authorization": f"Bearer {CEREBRAS_API_KEY}",
    "Content-Type": "application/json",
}

SYSTEM_PROMPT_LINUX = (
    "You are a Linux system administrator. "
    "Always use DEBIAN_FRONTEND=noninteractive for apt commands. "
    "Always pass -y or --yes flags to avoid interactive prompts. "
    "Never use apt-key (it is deprecated). "
    "For GPG keys: always download to /tmp first with curl, then use 'gpg --dearmor' piped to a file in /tmp, "
    "then sudo mv to /usr/share/keyrings/ (NEVER use /etc/apt/keyrings/). "
    "In sources.list entries always use signed-by=/usr/share/keyrings/<keyfile>. "
    "Always prepend sudo to commands that modify system files or install packages. "
    "Never add deb-src lines unless explicitly asked. "
    "Prefer apt/apt-get package installation over manual tar/binary downloads whenever possible. "
    "When writing multi-line files use: sudo tee /path/to/file > /dev/null << 'EOF' ... EOF format. "
    "After extracting a tar archive, verify the expected directories exist before running chmod or chown on them. "
    "For New Relic on Ubuntu/Debian use the correct repo: "
    "  GPG: https://download.newrelic.com/infrastructure_agent/gpg/newrelic-infra.gpg "
    "  Repo: deb [signed-by=...] https://download.newrelic.com/infrastructure_agent/linux/apt <codename> main "
    "  (use 'linux/apt' NOT 'linux/debian' for Ubuntu). "
    "For New Relic CLI do NOT use the install.sh script. Instead download the binary directly: "
    "  curl -L https://github.com/newrelic/newrelic-cli/releases/latest/download/newrelic_Linux_x86_64.tar.gz -o /tmp/newrelic-cli.tar.gz && "
    "  sudo tar -xzf /tmp/newrelic-cli.tar.gz -C /usr/local/bin newrelic && sudo chmod +x /usr/local/bin/newrelic. "
    "When apt-get fails with 'Could not get lock', wait and retry: "
    "  sudo flock /var/lib/dpkg/lock-frontend -c 'DEBIAN_FRONTEND=noninteractive apt-get install -y <pkg>'"
)

SYSTEM_PROMPT_WINDOWS = (
    "You are a Windows system administrator. "
    "Use winget or chocolatey (choco) to install packages. "
    "Prefer winget if available. "
    "Never use sudo — Windows does not have sudo. "
    "Use PowerShell commands where needed. "
    "Always pass --silent or -y flags to avoid interactive prompts. "
    "For winget use: winget install --silent --accept-package-agreements --accept-source-agreements"
)


def _system_prompt(os_info: str) -> str:
    if "windows" in os_info.lower():
        return SYSTEM_PROMPT_WINDOWS
    return SYSTEM_PROMPT_LINUX


def _chat(messages: list[dict], max_tokens: int = 512) -> str:
    """Send chat messages to HF router and return assistant reply."""
    payload = {
        "model": CEREBRAS_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }
    response = requests.post(CEREBRAS_API_URL, headers=HEADERS, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def _clean_commands(raw: str) -> list[str]:
    """Extract clean shell commands from AI response, collapsing heredocs into single commands."""
    # First pass: strip markdown/numbering into raw lines
    raw_lines = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("```"):
            continue
        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        line = re.sub(r"^[-*]\s*", "", line)
        if line and not line.lower().startswith("#") and not line.lower().startswith("note"):
            raw_lines.append(line)

    # Second pass: collapse heredoc blocks into single printf commands
    commands = []
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        # Detect heredoc: line contains << 'EOF' or << "EOF" or <<EOF
        heredoc_match = re.search(r"<<\s*['\"]?(\w+)['\"]?\s*$", line)
        if heredoc_match:
            marker = heredoc_match.group(1)
            # Collect the tee/redirect target from the triggering line
            tee_cmd = line
            body_lines = []
            i += 1
            while i < len(raw_lines) and raw_lines[i].strip() != marker:
                body_lines.append(raw_lines[i])
                i += 1
            # i now points at the EOF marker line — skip it
            # Build a single printf | sudo tee command
            escaped_body = "\\n".join(
                l.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
                for l in body_lines
            )
            # Replace the heredoc part with printf piped to tee
            base_cmd = re.sub(r"\s*<<\s*['\"]?\w+['\"]?\s*$", "", tee_cmd).strip()
            # base_cmd is e.g. "sudo tee /etc/systemd/system/tomcat.service > /dev/null"
            commands.append(f'printf "{escaped_body}\\n" | {base_cmd}')
        else:
            commands.append(line)
        i += 1

    return commands


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[mGKHF]", "", text)


def _cap_output(output: str, max_lines: int = 80) -> str:
    lines = output.splitlines()
    if len(lines) > max_lines:
        return "\n".join(lines[-max_lines:])
    return output


def get_install_commands(software_name: str, os_info: str = "Linux/Ubuntu", local_package_path: str = "") -> list[str]:
    """Ask AI for the list of shell commands to install the given software."""
    if local_package_path:
        pkg_hint = (
            f"The package files have already been uploaded to '{local_package_path}' on the remote machine. "
            f"Use those local files for installation instead of downloading from the internet. "
            f"List the files in that directory first if needed to determine the correct installer file."
        )
    else:
        pkg_hint = ""

    messages = [
        {"role": "system", "content": _system_prompt(os_info)},
        {
            "role": "user",
            "content": (
                f"List the shell commands to install '{software_name}' on {os_info}. "
                + (pkg_hint + " " if pkg_hint else "")
                + "Output ONLY the commands, one per line, no explanations, no markdown, no numbering. "
                "Each line must be a single executable shell command."
            ),
        },
    ]
    raw = _chat(messages, max_tokens=600)
    return _clean_commands(raw)


def get_check_commands(software_name: str, os_info: str = "Linux/Ubuntu") -> list[str]:
    """Ask AI for commands to check if software is already installed."""
    messages = [
        {"role": "system", "content": _system_prompt(os_info)},
        {
            "role": "user",
            "content": (
                f"List shell commands to check if '{software_name}' is already installed on {os_info}. "
                "Each command should print 'INSTALLED' if found or 'NOT INSTALLED' if not. "
                "Output ONLY the commands, one per line, no explanations, no markdown, no numbering."
            ),
        },
    ]
    raw = _chat(messages, max_tokens=300)
    return _clean_commands(raw)


def assess_install_status(software_name: str, check_outputs: list[tuple[str, str]], os_info: str = "Linux/Ubuntu") -> tuple[str, str]:
    """
    Given check command outputs, return (status, reason).
    status is one of: 'installed', 'partial', 'not_installed'
    """
    summary = "\n".join(
        f"Command: {cmd}\nOutput: {out}" for cmd, out in check_outputs
    )
    messages = [
        {"role": "system", "content": _system_prompt(os_info)},
        {
            "role": "user",
            "content": (
                f"Based on these check results for '{software_name}':\n{summary}\n\n"
                "Is the software: fully installed, partially installed, or not installed? "
                "Reply with exactly one of: INSTALLED, PARTIAL, NOT_INSTALLED on the first line, "
                "then a brief one-line reason on the second line. No other text."
            ),
        },
    ]
    text = _chat(messages, max_tokens=80)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    status_line = lines[0].upper() if lines else "NOT_INSTALLED"
    reason = lines[1] if len(lines) > 1 else status_line

    if "PARTIAL" in status_line:
        return "partial", reason
    if "NOT_INSTALLED" in status_line or "NOT INSTALLED" in status_line:
        return "not_installed", reason
    return "installed", reason


def verify_command_output(command: str, output: str, exit_code: int, os_info: str = "Linux/Ubuntu") -> tuple[bool, str]:
    """Ask AI whether the command output indicates success or failure."""
    clean_output = _cap_output(_strip_ansi(output))

    # Short-circuit: idempotent "already done" cases are always success
    already_done_phrases = [
        "already exists", "already installed", "already the newest version",
        "already enabled", "already active", "nothing to do", "up to date",
    ]
    lower_out = clean_output.lower()
    if exit_code == 0 or any(p in lower_out for p in already_done_phrases):
        reason = next((p for p in already_done_phrases if p in lower_out), "exit code 0")
        return True, f"Already done or succeeded — {reason}"

    messages = [
        {"role": "system", "content": _system_prompt(os_info)},
        {
            "role": "user",
            "content": (
                f"A shell command was executed:\n"
                f"Command: {command}\n"
                f"Exit code: {exit_code}\n"
                f"Output:\n{clean_output}\n\n"
                "Did this command succeed? Reply with exactly 'SUCCESS' or 'FAILURE' on the first line, "
                "then a brief one-line reason on the second line. No other text."
            ),
        },
    ]
    text = _chat(messages, max_tokens=80)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    verdict = lines[0].upper() if lines else "FAILURE"
    success = "SUCCESS" in verdict
    reason = lines[1] if len(lines) > 1 else verdict
    return success, reason


def get_fix_commands(command: str, output: str, software_name: str, os_info: str = "Linux/Ubuntu") -> list[str]:
    """Ask AI for fix commands when a command fails."""
    clean_output = _cap_output(_strip_ansi(output))
    messages = [
        {"role": "system", "content": _system_prompt(os_info)},
        {
            "role": "user",
            "content": (
                f"The following command failed while installing '{software_name}':\n"
                f"Command: {command}\n"
                f"Output:\n{clean_output}\n\n"
                "Provide shell commands to fix this issue. "
                "Output ONLY the commands, one per line, no explanations, no markdown, no numbering."
            ),
        },
    ]
    raw = _chat(messages, max_tokens=400)
    return _clean_commands(raw)


def should_rerun_after_fix(original_cmd: str, fix_cmds: list[str], os_info: str = "Linux/Ubuntu") -> bool:
    """Ask AI whether the original command should be re-run after fix commands."""
    messages = [
        {"role": "system", "content": _system_prompt(os_info)},
        {
            "role": "user",
            "content": (
                f"Original command that failed: {original_cmd}\n"
                f"Fix commands that were run:\n" + "\n".join(fix_cmds) + "\n\n"
                "Should the original command be re-run after these fixes? "
                "Reply with exactly RERUN or SKIP. No other text."
            ),
        },
    ]
    text = _chat(messages, max_tokens=20)
    return "RERUN" in text.upper()


def get_uninstall_commands(
    software_name: str, completed_commands: list[str], os_info: str = "Linux/Ubuntu"
) -> list[str]:
    """Ask AI for uninstall/rollback commands based on what was already executed."""
    history = "\n".join(completed_commands) if completed_commands else "None"
    messages = [
        {"role": "system", "content": _system_prompt(os_info)},
        {
            "role": "user",
            "content": (
                f"The following commands were executed to install '{software_name}' on {os_info}:\n"
                f"{history}\n\n"
                "Provide shell commands to completely uninstall and rollback this installation. "
                "Output ONLY the commands, one per line, no explanations, no markdown, no numbering."
            ),
        },
    ]
    raw = _chat(messages, max_tokens=400)
    return _clean_commands(raw)


def get_alternative_commands(
    failed_cmd: str, fix_output: str, software_name: str, os_info: str = "Linux/Ubuntu"
) -> list[str]:
    """Ask AI for a completely different approach when both original and fix commands failed."""
    messages = [
        {"role": "system", "content": _system_prompt(os_info)},
        {
            "role": "user",
            "content": (
                f"Installing '{software_name}' on {os_info} failed. "
                f"The command that failed: {failed_cmd}\n"
                f"Fix attempts also failed with: {fix_output}\n\n"
                "Provide an ALTERNATIVE set of shell commands using a completely different approach "
                "(e.g. use apt instead of manual download, or different package name, or different repo). "
                "Output ONLY the commands, one per line, no explanations, no markdown, no numbering."
            ),
        },
    ]
    raw = _chat(messages, max_tokens=400)
    return _clean_commands(raw)
