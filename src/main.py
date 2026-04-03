#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  GHOST-v3 — Lifecycle Orchestrator (main.py)                               ║
║                                                                            ║
║  Purpose:                                                                  ║
║    Manages the full docker-compose lifecycle for the GHOST pentesting       ║
║    architecture. This is the single entry point that brings the entire      ║
║    containerised SOA (Gateway → Workstation → Browser) up and guarantees    ║
║    a clean teardown — no matter how the process exits.                      ║
║                                                                            ║
║  Teardown Strategy (defense-in-depth, 3 layers):                           ║
║    1. Signal trapping   — SIGINT (Ctrl+C) / SIGTERM are caught and routed  ║
║                           through the same cleanup path.                   ║
║    2. Context manager   — `GhostOrchestrator.__exit__` runs on any         ║
║                           exception that propagates out of the `with`      ║
║                           block, including KeyboardInterrupt.              ║
║    3. atexit handler    — Last-resort hook that fires when the Python      ║
║                           interpreter itself is shutting down.             ║
║                                                                            ║
║  All three layers are idempotent: calling cleanup() N times is harmless.   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# ──────────────────────────── Standard Library ────────────────────────────
import os
import sys
import signal
import atexit
import logging
import subprocess
import threading
from pathlib import Path
from typing import Optional, Dict

# ────────────────────────── Third-Party Imports ───────────────────────────
# python-dotenv is used to parse the .env file and inject its values into
# the subprocess environment so docker-compose can interpolate ${VAR} refs.
from dotenv import dotenv_values

# ──────────────────────────── Logging Setup ───────────────────────────────
# We log to stderr so stdout remains clean for any future TUI layer.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("ghost.orchestrator")


# ══════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════

# Resolve paths relative to *this* file so the script works regardless of
# the caller's working directory.  The layout is:
#
#   GHOST/
#   ├── docker-compose.yml   ← PROJECT_ROOT
#   ├── .env
#   └── src/
#       └── main.py          ← THIS FILE
#
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
COMPOSE_FILE: Path = PROJECT_ROOT / "docker-compose.yml"
ENV_FILE: Path     = PROJECT_ROOT / ".env"

# docker-compose / docker compose — we auto-detect which binary is
# available so the script works on both legacy and modern Docker installs.
COMPOSE_CMD: Optional[list] = None


def _detect_compose_binary() -> list:
    """
    Detect whether the system uses `docker compose` (v2 plugin) or the
    legacy standalone `docker-compose` binary.

    Returns the base command as a list (e.g. ["docker", "compose"]).
    Raises FileNotFoundError if neither is found.
    """
    # ── Try the modern v2 plugin first ──────────────────────────────────
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        logger.info("Detected Docker Compose v2 plugin.")
        return ["docker", "compose"]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # ── Fall back to legacy standalone binary ───────────────────────────
    try:
        subprocess.run(
            ["docker-compose", "version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        logger.info("Detected legacy docker-compose binary.")
        return ["docker-compose"]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    raise FileNotFoundError(
        "Neither 'docker compose' (v2) nor 'docker-compose' (legacy) was "
        "found on PATH.  Please install Docker Desktop or docker-compose."
    )


def _build_env() -> Dict[str, str]:
    """
    Build the environment dict that will be passed to every subprocess call.

    Strategy:
      1. Start with a *copy* of the current OS environment (so Docker
         inherits PATH, DOCKER_HOST, etc.).
      2. Layer the .env values on top — these override any colliding keys
         in the OS env, which is the expected docker-compose behaviour.
    """
    env = os.environ.copy()

    if ENV_FILE.is_file():
        dotenv_vars = dotenv_values(ENV_FILE)
        env.update(dotenv_vars)
        logger.info("Loaded %d variable(s) from %s", len(dotenv_vars), ENV_FILE)
    else:
        logger.warning(".env file not found at %s — proceeding without it.", ENV_FILE)

    return env


# ══════════════════════════════════════════════════════════════════════════
#  THE ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════

class GhostOrchestrator:
    """
    Context manager that owns the full lifecycle of the GHOST container
    stack.  Usage:

        with GhostOrchestrator() as ghost:
            ghost.wait()       # block until user hits Ctrl+C
    """

    def __init__(self) -> None:
        # ── Idempotency lock ────────────────────────────────────────────
        # `_torn_down` ensures cleanup() only runs its destructive logic
        # once, even if multiple layers (signal, context, atexit) all
        # fire in rapid succession.
        self._torn_down: bool = False
        self._lock: threading.Lock = threading.Lock()

        # ── Resolve the compose binary once ─────────────────────────────
        global COMPOSE_CMD
        if COMPOSE_CMD is None:
            COMPOSE_CMD = _detect_compose_binary()

        # ── Build the enriched subprocess environment ───────────────────
        self._env: Dict[str, str] = _build_env()

    # ──────────────────────────────────────────────────────────────────
    #  COMPOSE HELPERS
    # ──────────────────────────────────────────────────────────────────

    def _compose(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """
        Run a docker-compose sub-command with the project's compose file
        and enriched environment.

        Example:
            self._compose("up", "-d")
            self._compose("down", "-v")
        """
        cmd = [
            *COMPOSE_CMD,
            "-f", str(COMPOSE_FILE),   # Explicit compose file path.
            *args,
        ]
        logger.info("Running: %s", " ".join(cmd))

        return subprocess.run(
            cmd,
            env=self._env,
            # Inherit the parent's stdout/stderr so the operator can see
            # Docker's build & pull output in real time.
            stdout=sys.stdout,
            stderr=sys.stderr,
            check=check,
        )

    # ──────────────────────────────────────────────────────────────────
    #  LIFECYCLE: BRING UP
    # ──────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """
        Build (if needed) and start every service defined in
        docker-compose.yml in detached mode.

        The `--build` flag ensures local Dockerfiles are rebuilt when
        source changes — crucial during active development.
        """
        logger.info("═══ GHOST-v3 — Bringing containers UP ═══")
        self._compose("up", "-d", "--build")
        logger.info("═══ Containers pushed to Docker. Waiting for Tor network synchronization ═══")
        
        # Dynamically import to avoid circular references during package boot
        import time
        import sys
        import socket
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from network.tor_controller import TorController
        
        logger.info("Waiting for Tor Gateway to open Control Port (9051)...")
        port_open = False
        for _ in range(30):
            try:
                with socket.create_connection(('127.0.0.1', 9051), timeout=1):
                    port_open = True
                    break
            except (ConnectionRefusedError, socket.timeout, OSError):
                time.sleep(1)
        
        if port_open:
            tc = TorController()
            # Give Tor a fractional second to initialize its API after binding the port
            time.sleep(0.5)
            if tc.connect_and_authenticate():
                if tc.wait_for_bootstrap(timeout=120):
                    logger.info("═══ All containers are synchronized and fully operational. ═══")
                else:
                    logger.error("═══ Tor bootstrap timeout! Network may be degraded. ═══")
            else:
                logger.error("═══ Could not authenticate to Tor Gateway control port. ═══")
            
            tc.disconnect()
        else:
            logger.error("═══ Could not connect to Tor Gateway for synchronization. Port 9051 refused connection. ═══")

    # ──────────────────────────────────────────────────────────────────
    #  LIFECYCLE: TEAR DOWN  (the critical path)
    # ──────────────────────────────────────────────────────────────────

    def cleanup(self) -> None:
        """
        Idempotent teardown.

        Executes `docker-compose down -v` which:
          • Stops all containers defined in the project.
          • Removes the stopped containers.
          • Removes the `ghost_net` bridge network.
          • `-v` removes anonymous volumes (no data ghosts left behind).

        The `--timeout` flag gives each container 10 s to shut down
        gracefully before Docker SIGKILLs it.

        This method is safe to call from any thread, any number of times.
        """
        with self._lock:
            if self._torn_down:
                # Already executed — nothing to do.
                return
            self._torn_down = True

        logger.info("═══ GHOST-v3 — Tearing down containers ═══")

        try:
            self._compose("down", "-v", "--timeout", "10", check=False)
            logger.info("═══ Teardown complete — no zombie containers. ═══")
        except Exception as exc:
            # Even if teardown fails we must not crash the interpreter.
            # Log the error so the operator can investigate manually.
            logger.error(
                "Teardown encountered an error (manual cleanup may "
                "be required): %s",
                exc,
            )

    # ──────────────────────────────────────────────────────────────────
    #  BLOCKING WAIT
    # ──────────────────────────────────────────────────────────────────

    def wait(self) -> None:
        """
        Block the main thread until a termination signal arrives.

        We use `signal.pause()` on POSIX and a polling fallback on
        Windows (which does not support signal.pause).
        """
        logger.info(
            "GHOST-v3 is live.  Press Ctrl+C to initiate secure shutdown."
        )
        try:
            if hasattr(signal, "pause"):
                # POSIX — efficient, no CPU burn.
                while True:
                    signal.pause()
            else:
                # Windows fallback — sleep in 1 s intervals so we can
                # still respond to KeyboardInterrupt promptly.
                import time
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            # Ctrl+C lands here if the signal handler re-raises or if
            # we're on Windows.  Cleanup is handled by __exit__.
            logger.info("KeyboardInterrupt received inside wait().")

    # ──────────────────────────────────────────────────────────────────
    #  CONTEXT MANAGER PROTOCOL
    # ──────────────────────────────────────────────────────────────────

    def __enter__(self) -> "GhostOrchestrator":
        """Start the stack when entering the `with` block."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        Guarantee cleanup when leaving the `with` block — whether the
        exit was clean, caused by an exception, or triggered by
        KeyboardInterrupt.

        Returning True would suppress the exception; we return False so
        unexpected errors still propagate after cleanup.
        """
        self.cleanup()
        return False


# ══════════════════════════════════════════════════════════════════════════
#  SIGNAL HANDLERS
# ══════════════════════════════════════════════════════════════════════════

# We keep a module-level reference to the orchestrator so signal handlers
# and the atexit hook can reach it.  This is set inside main().
_orchestrator: Optional[GhostOrchestrator] = None


def _signal_handler(signum: int, frame) -> None:
    """
    Unified handler for SIGINT and SIGTERM.

    Design note: We do NOT call sys.exit() here because that can cause
    messy interactions with threading.  Instead we call cleanup() directly
    and then re-raise KeyboardInterrupt so Python's normal shutdown path
    triggers (which will also hit __exit__ and atexit — both are
    idempotent, so that's fine).
    """
    sig_name = signal.Signals(signum).name
    logger.info("Caught %s — initiating secure shutdown…", sig_name)

    if _orchestrator is not None:
        _orchestrator.cleanup()

    # Re-raise so the interpreter exits with the correct return code.
    raise KeyboardInterrupt


def _atexit_cleanup() -> None:
    """
    Last-resort cleanup hook.  This fires when the Python interpreter is
    tearing itself down — e.g. if someone calls sys.exit() from another
    module, or an unhandled exception causes a crash.

    Because cleanup() is idempotent, calling it again here is harmless.
    """
    if _orchestrator is not None:
        _orchestrator.cleanup()


# ══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Orchestrator entry point.

    Flow:
      1. Intercept CLI args (e.g. --new-identity).
      2. Register atexit handler (layer 3).
      3. Install signal handlers for SIGINT + SIGTERM (layer 1).
      4. Enter the context manager which calls start() (layer 2).
      5. Block on wait() until a signal arrives.
      6. __exit__ fires cleanup() on the way out.
    """
    import argparse
    parser = argparse.ArgumentParser(description="GHOST-v3 Secure Pentesting Architecture")
    parser.add_argument("--new-identity", action="store_true", help="Instantly drop Tor circuits and request a new exit node IP.")
    # We parse known args so we don't break if Docker ever passed args to the script later
    args, _ = parser.parse_known_args()

    if args.new_identity:
        # Dynamically load modules so we don't slow down the boot if they aren't needed right away
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from network.tor_controller import TorController
        from ui.interface import GhostUI
        
        tc = TorController()
        ui = GhostUI(tc)
        
        if not tc.connect_and_authenticate():
            logger.error("Gateway is not responding. Please make sure the GHOST stack is running.")
            sys.exit(1)
            
        # Issue rotation signal
        tc.rotate_ip()
        
        # Launch transient graphical feedback (e.g., rendering DE -> JP visually)
        ui.render_transient_action(seconds=4)
        sys.exit(0)

    global _orchestrator

    # ── Preflight checks ────────────────────────────────────────────
    if not COMPOSE_FILE.is_file():
        logger.critical(
            "docker-compose.yml not found at %s — aborting.", COMPOSE_FILE
        )
        sys.exit(1)

    # ── Layer 3: atexit (catches interpreter shutdown) ──────────────
    atexit.register(_atexit_cleanup)

    # ── Layer 1: signal traps ───────────────────────────────────────
    # SIGTERM may not exist on Windows, so we guard the registration.
    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)

    # ── Layer 2: context manager ────────────────────────────────────
    try:
        _orchestrator = GhostOrchestrator()
        with _orchestrator:
            _orchestrator.wait()
    except KeyboardInterrupt:
        # This is expected — cleanup has already run via the handler
        # or __exit__.  Just log and exit cleanly.
        logger.info("GHOST-v3 shutdown complete.")
        sys.exit(0)
    except Exception as exc:
        logger.critical("Fatal error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
