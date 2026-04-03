#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  GHOST-v3 — Docker Execution Wrapper (scanner_wrapper.py)                    ║
║                                                                            ║
║  Purpose:                                                                  ║
║    Provides a structured way for the host machine to execute tools (nmap,  ║
║    msfconsole, etc.) inside the isolated ghost-workstation container.      ║
║                                                                            ║
║  Philosophy:                                                               ║
║    No Python code should attempt to route directly into the container      ║
║    network. All interaction is done securely via the Docker Engine socket. ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import logging
import subprocess
from typing import List

# Setup module-level logger matching the orchestrator's format
logger = logging.getLogger("ghost.scanner_wrapper")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s", 
        datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class DockerExecutor:
    """
    Executes commands securely inside the 'ghost-workstation' container
    using `docker exec`. Follows the fail-closed philosophy.
    """
    
    def __init__(self, container_name: str = "ghost-workstation"):
        self.container_name = container_name

    def verify_container_running(self) -> bool:
        """
        Checks if the target container is currently active/running.
        """
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", self.container_name],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip() == "true"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def run_command(self, user_command: List[str], interactive: bool = True) -> subprocess.CompletedProcess:
        """
        Executes a given command array inside the configured container.
        
        Args:
            user_command (List[str]): The command and args (e.g., ["nmap", "-sS", "target.com"]).
            interactive (bool): If True, passes '-it' and attaches standard streams.
            
        Returns:
            subprocess.CompletedProcess: The result of the execution.
        """
        if not self.verify_container_running():
            logger.error(f"Container '{self.container_name}' is not running.")
            logger.error("Please ensure the GHOST stack is active before executing scans.")
            sys.exit(1)

        exec_cmd = ["docker", "exec"]
        if interactive:
            exec_cmd.extend(["-it"])
            
        exec_cmd.append(self.container_name)
        exec_cmd.extend(user_command)
        
        logger.info(f"Executing secured command -> {' '.join(user_command)}")
        try:
            if interactive:
                # Let the subprocess inhabit the current terminal (interactive TTY)
                return subprocess.run(exec_cmd)
            else:
                # Capture output invisibly
                return subprocess.run(exec_cmd, capture_output=True, text=True, check=True)
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Scanner command failed with exit code {e.returncode}")
            if hasattr(e, 'stderr') and e.stderr:
                logger.error(f"Error output:\n{e.stderr}")
            return e
        except KeyboardInterrupt:
            # Handle Ctrl+C cleanly without stack dumping during long nmap scans
            logger.info("\nExecution cleanly interrupted by operator.")
            return subprocess.CompletedProcess(args=exec_cmd, returncode=130)
        except Exception as e:
            logger.critical(f"Unexpected error during scanner execution: {e}")
            sys.exit(1)


# ── Standalone CLI Usage ─────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="GHOST-v3 Scanner Wrapper: Run tools in the secure workstation."
    )
    # REMAINDER lets us capture all args and treat them as the command
    parser.add_argument(
        "command", 
        nargs=argparse.REMAINDER, 
        help="The full command to execute (e.g., nmap -sS -p- scanme.nmap.org)"
    )
    args = parser.parse_args()

    command_to_run = args.command
    
    # Optional bash compat for people using -- to separate arguments
    if command_to_run and command_to_run[0] == "--":
        command_to_run = command_to_run[1:]

    if not command_to_run:
         logger.error("No command provided.")
         logger.info("Usage: python scanner_wrapper.py -- <tool> <args>")
         logger.info("Example: python scanner_wrapper.py -- nmap sqlmap.org")
         sys.exit(1)

    executor = DockerExecutor()
    executor.run_command(command_to_run)
