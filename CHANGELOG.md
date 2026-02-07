# Changelog

All notable changes to GhostConnect will be documented in this file.

## [2.1.1] - 2025-02-07

### 🔧 Network Robustness Improvements

### Fixed
- **IPv6 Network Unreachable errors** - Forces IPv4 for all APT operations
  - Added `-o Acquire::ForceIPv4=true` to all apt update and install commands
  - Prevents failures on networks with misconfigured IPv6

### Added
- **Retry logic for LibreWolf installation** - 3 automatic retry attempts with 2-second delays
  - Handles flaky internet connections gracefully
  - Shows retry progress to user
  - Provides clear error message if all retries fail
- **Persistent Mode** - Tool now stays running even after browser closes
  - Tool only exits when user presses CTRL+C
  - Tor remains active for browser reopening
  - Allows closing/reopening LibreWolf without restarting tool
  - Background browser launch (non-blocking)

### Changed
- All dependency installations now force IPv4 (Tor, ProxyChains, extrepo, LibreWolf)
- More resilient to network issues during installation
- Browser launched in background without waiting for exit
- Cleanup only triggered by CTRL+C signal, not browser close
- Added infinite wait loop with clear user instructions

### Technical Details
```bash
# Before (v2.1.0):
apt install librewolf -y
# Could fail with: "Network is unreachable" on misconfigured IPv6

# After (v2.1.1):
apt -o Acquire::ForceIPv4=true install librewolf -y
# Forces IPv4, retries 3 times on failure
```

**Persistent Mode Implementation:**
```python
# Before: Tool waited for browser to exit
self.librewolf_process = subprocess.Popen(...)
self.librewolf_process.wait()  # Blocked until browser closed
self.cleanup()  # Immediate cleanup

# After: Tool stays running until CTRL+C
subprocess.Popen(...)  # Launch in background
while True:
    time.sleep(1)  # Wait indefinitely
# Cleanup only via signal handler (CTRL+C)
```

---

## [2.1.0] - 2025-02-07

### 🚀 Major Improvement: Universal Installation Method

### Changed
- **Complete rewrite of LibreWolf installation** - Now uses `extrepo` for universal compatibility
  - **Method**: Install via `extrepo enable librewolf` instead of manual repository setup
  - **Benefits**: Works universally on Kali, Debian, Ubuntu, and derivatives
  - **Reliability**: No more codename detection/mapping needed
  - **Simplicity**: Reduced installation code by ~60 lines
  - **Maintenance**: extrepo handles repository URLs and GPG keys automatically

### Added
- **Cleanup step** - Automatically removes old/broken LibreWolf configuration files
  - Removes `/etc/apt/sources.list.d/librewolf.list` if exists
  - Removes `/usr/share/keyrings/librewolf.gpg` if exists
  - Ensures clean installation every time

### Technical Details

**Old Method (v2.0.1):**
```bash
# Manual repository setup
1. Detect distro codename (lsb_release -sc)
2. Map kali-rolling → unstable
3. Download GPG key manually
4. Write repository file manually
5. apt update && apt install librewolf
```

**New Method (v2.1.0):**
```bash
# Using extrepo (universal)
1. Clean old files
2. apt install extrepo
3. extrepo enable librewolf  # Handles everything automatically
4. apt update && apt install librewolf
```

### Why This Change?

The previous method had issues:
- ❌ Required distribution-specific codename mapping
- ❌ Broke when LibreWolf changed repository structure
- ❌ Manual GPG key management
- ❌ Kali-specific workarounds needed

The new `extrepo` method:
- ✅ Works on all Debian-based distros automatically
- ✅ No codename detection needed
- ✅ Managed by Debian package maintainers
- ✅ Self-updating repository information
- ✅ Cleaner, more maintainable code

---

## [2.0.1] - 2025-02-07

### 🐛 Critical Bug Fix: Kali Linux Support

### Fixed
- **LibreWolf installation on Kali Linux** - Fixed 404 Not Found error
  - Issue: Script used `kali-rolling` codename which doesn't exist in LibreWolf repository
  - Solution: Automatically maps Kali codenames to Debian `unstable`
  - Detects: `kali-rolling`, `kali-dev`, and all `kali-*` variants
  - Maps to: `unstable` (compatible with Kali's Debian testing/unstable base)

### Improved
- **GPG key download** - Simplified to single robust command using `wget --quiet`
- **Error messages** - Added verification that GPG key file was created
- **Logging** - Shows detected codename, mapping decision, and final repository line
- **Error handling** - Better messages if repository URL fails

### Technical Details
```python
# Before (Broken on Kali):
distro = "kali-rolling"  # From lsb_release
repo = f"http://deb.librewolf.net {distro} main"
# Result: 404 Not Found

# After (Fixed):
distro = "kali-rolling"  # Detected
if distro == "kali-rolling" or distro.startswith("kali-"):
    distro = "unstable"  # Mapped
repo = f"http://deb.librewolf.net {distro} main"
# Result: Success!
```

---

## [2.0.0] - 2025-02-07

### 🎉 Major Refactor: Firefox → LibreWolf

### Added
- **LibreWolf browser integration** - Privacy-hardened Firefox fork with built-in protections
- **Automated LibreWolf installation** - Auto-detects, adds repository, and installs LibreWolf
- **Repository management** - Automatically adds LibreWolf APT repository and GPG key
- **User privilege handling** - Runs browser as SUDO_USER instead of root (prevents permission issues)
- **Direct Tor check** - Opens https://check.torproject.org on launch to verify connection
- **Enhanced cleanup** - Added `pkill` to ensure all browser processes are terminated

### Changed
- **Browser engine**: Replaced Firefox with LibreWolf (pre-hardened privacy fork)
- **Launch command**: Now uses `proxychains4 librewolf --private-window`
- **User experience**: Browser runs as normal user, not root
- **Banner**: Updated to v2.0 with "Powered by LibreWolf + Tor"

### Removed
- **200+ lines of Firefox hardening code** - No longer needed with LibreWolf
- `create_firefox_profile()` function - Profiles not needed
- `_get_firefox_profile_path()` function - Profile management removed
- `_inject_privacy_settings()` function - LibreWolf is pre-hardened
- `firefox_profile_name` attribute - No longer used
- `firefox_profile_path` attribute - No longer used
- Manual WebRTC disabling - Built into LibreWolf
- Manual telemetry disabling - Built into LibreWolf
- Manual fingerprinting resistance - Built into LibreWolf
- user.js injection logic - Not needed

### Why This Change?

**Before (v1.0 with Firefox):**
- Required creating isolated profiles
- Needed to inject 20+ privacy settings manually
- user.js file generation
- Profile path detection logic
- ~200 lines of hardening code

**After (v2.0 with LibreWolf):**
- Zero configuration needed
- LibreWolf is secure by default
- Cleaner, simpler codebase
- Better user experience
- Runs as normal user (not root)

### Technical Improvements

1. **Simplified dependency management**
   - Separated standard deps (Tor, ProxyChains) from LibreWolf
   - Created dedicated `_install_librewolf()` method
   - Proper repository handling with GPG key verification

2. **Better process management**
   - Uses `preexec_fn` to demote privileges to SUDO_USER
   - Sets proper HOME and XDG_RUNTIME_DIR environment variables
   - Added fallback `pkill` in cleanup for orphaned processes

3. **Code reduction**
   - Removed ~200 lines of Firefox-specific code
   - Cleaner architecture
   - Easier to maintain

### Security Notes

LibreWolf includes by default:
- WebRTC disabled (prevents IP leaks)
- No telemetry or tracking
- Fingerprinting resistance
- First-party isolation
- DNS leak prevention
- Auto-delete cookies/cache
- uBlock Origin built-in
- HTTPS-only mode

### Migration from v1.0

If you were using v1.0:
1. Uninstall: Old Firefox profiles remain but are unused
2. Run v2.0: Will auto-install LibreWolf
3. No data migration needed - fresh anonymous sessions each time

### Breaking Changes

- Firefox is no longer used
- GhostProfile Firefox profile is no longer created/used
- user.js privacy settings are no longer generated

---

## [1.0.0] - 2025-02-06

### Initial Release

- Firefox-based anonymous browsing
- Manual Firefox profile hardening
- Tor + ProxyChains integration
- Automated dependency installation
- Kill switch functionality
- Professional terminal UI
