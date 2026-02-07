#!/usr/bin/env python3
"""
GhostConnect Test Suite
Verifies installation and configuration
"""

import sys
import subprocess
import socket
from pathlib import Path


def print_status(message, status):
    """Print colored status messages"""
    colors = {
        "success": "\033[0;32m",
        "error": "\033[0;31m",
        "warning": "\033[1;33m",
        "info": "\033[0;36m"
    }
    reset = "\033[0m"

    symbols = {
        "success": "✓",
        "error": "✗",
        "warning": "!",
        "info": "*"
    }

    color = colors.get(status, "")
    symbol = symbols.get(status, "*")

    print(f"{color}[{symbol}] {message}{reset}")


def check_command(command):
    """Check if a command exists"""
    try:
        result = subprocess.run(
            ["which", command],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return result.returncode == 0
    except Exception:
        return False


def check_port(port):
    """Check if a port is listening"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            return result == 0
    except Exception:
        return False


def main():
    print("\n" + "=" * 60)
    print("GhostConnect System Verification")
    print("=" * 60 + "\n")

    all_passed = True

    # Check Python version
    print("[1] Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 7:
        print_status(f"Python {version.major}.{version.minor}.{version.micro}", "success")
    else:
        print_status(f"Python {version.major}.{version.minor}.{version.micro} - Requires 3.7+", "error")
        all_passed = False

    # Check required commands
    print("\n[2] Checking required commands...")
    commands = ["tor", "proxychains4", "firefox"]

    for cmd in commands:
        if check_command(cmd):
            result = subprocess.run(
                ["which", cmd],
                capture_output=True,
                text=True
            )
            print_status(f"{cmd}: {result.stdout.strip()}", "success")
        else:
            print_status(f"{cmd}: Not found", "error")
            all_passed = False

    # Check Python modules
    print("\n[3] Checking Python dependencies...")
    modules = ["rich", "colorama"]

    for module in modules:
        try:
            __import__(module)
            print_status(f"{module} installed", "success")
        except ImportError:
            print_status(f"{module} not found", "warning")
            print_status("  Run: pip3 install -r requirements.txt", "info")

    # Check files
    print("\n[4] Checking configuration files...")
    proxychains_conf = Path("/etc/proxychains4.conf")

    if proxychains_conf.exists():
        print_status(f"ProxyChains config exists: {proxychains_conf}", "success")

        # Check if it has socks5 configured
        content = proxychains_conf.read_text()
        if "socks5" in content and "9050" in content:
            print_status("  SOCKS5 proxy configured", "success")
        else:
            print_status("  SOCKS5 proxy not configured", "warning")
    else:
        print_status("ProxyChains config not found", "error")
        all_passed = False

    # Check Tor service
    print("\n[5] Checking Tor service...")
    result = subprocess.run(
        ["service", "tor", "status"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if "active (running)" in result.stdout.decode().lower() or result.returncode == 0:
        print_status("Tor service is running", "success")

        # Check if port 9050 is open
        if check_port(9050):
            print_status("Tor SOCKS port (9050) is listening", "success")
        else:
            print_status("Tor SOCKS port (9050) not listening", "warning")
    else:
        print_status("Tor service not running (this is OK - will start when needed)", "info")

    # Check Firefox profiles
    print("\n[6] Checking Firefox profiles...")
    profile_dirs = [
        Path.home() / ".mozilla" / "firefox",
        Path("/root/.mozilla/firefox")
    ]

    profile_found = False
    for profile_dir in profile_dirs:
        if profile_dir.exists():
            print_status(f"Firefox profile directory exists: {profile_dir}", "success")

            profiles_ini = profile_dir / "profiles.ini"
            if profiles_ini.exists():
                content = profiles_ini.read_text()
                if "GhostProfile" in content:
                    print_status("  GhostProfile found", "success")
                    profile_found = True
                else:
                    print_status("  GhostProfile not found (will be created on first run)", "info")
            break

    if not any(pd.exists() for pd in profile_dirs):
        print_status("Firefox profile directory not found (will be created)", "info")

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print_status("All critical checks passed!", "success")
        print_status("GhostConnect is ready to use", "success")
        print_status("\nRun: sudo python3 ghostconnect.py", "info")
    else:
        print_status("Some checks failed", "error")
        print_status("Please install missing dependencies", "warning")
        print_status("\nRun: sudo bash install.sh", "info")

    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
