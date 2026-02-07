# Changelog

All notable changes to GhostConnect will be documented in this file.

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
