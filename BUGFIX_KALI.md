# Bug Fix: Kali Linux LibreWolf Installation (404 Error)

## Issue Report

### Problem
GhostConnect v2.0 failed to install LibreWolf on Kali Linux with a **404 Not Found** error.

### Root Cause
The script detected the distribution codename as `kali-rolling` using `lsb_release -sc`, but the LibreWolf repository doesn't have a release for `kali-rolling`. The repository structure is:
```
http://deb.librewolf.net/dists/
├── bookworm/
├── bullseye/
├── unstable/
├── testing/
└── (no kali-rolling)
```

When the script tried to access `http://deb.librewolf.net/dists/kali-rolling/`, it returned **404 Not Found**.

### Error Flow
1. Script runs: `lsb_release -sc` → Returns: `kali-rolling`
2. Script creates repository line:
   ```
   deb [arch=amd64 signed-by=/usr/share/keyrings/librewolf.gpg] http://deb.librewolf.net kali-rolling main
   ```
3. Script runs: `apt update` → APT tries to access the repository
4. Server returns: **404 Not Found** for `kali-rolling/main`
5. Installation fails

## The Fix

### Solution Overview
Map Kali Linux codenames to compatible Debian codenames that exist in the LibreWolf repository.

### Mapping Logic
```python
# Detected codename: kali-rolling
# ↓
# Mapped codename: unstable (Debian unstable)
```

Kali Linux is based on Debian testing/unstable, so using `unstable` is compatible.

### Code Changes

#### Before (Buggy)
```python
# Get distribution codename
result = self._run_command(["lsb_release", "-sc"], check=False, capture=True)
distro = result.stdout.strip()
self._print(f"Detected distribution: {distro}", "info")

# Directly use the detected codename (WRONG for Kali!)
repo_line = f"deb ... http://deb.librewolf.net {distro} main"
```

#### After (Fixed)
```python
# Get distribution codename
result = self._run_command(["lsb_release", "-sc"], check=False, capture=True)
distro = result.stdout.strip()
self._print(f"Detected distribution codename: {distro}", "info")

# KALI FIX: Map kali-rolling to valid Debian codename
if distro == "kali-rolling":
    distro = "unstable"
    self._print(f"Kali Linux detected - Using Debian '{distro}' repository", "info")

# Map other Kali variants
elif distro.startswith("kali-"):
    distro = "unstable"
    self._print(f"Kali variant detected - Using Debian '{distro}' repository", "info")

self._print(f"Using repository codename: {distro}", "success")

# Now use the corrected codename
repo_line = f"deb ... http://deb.librewolf.net {distro} main"
```

### Additional Improvements

1. **Robust GPG Key Download**
   ```python
   # Before: Two-step process with potential failure
   wget -qO- https://deb.librewolf.net/keyring.gpg

   # After: Single reliable command
   wget --quiet -O- https://deb.librewolf.net/keyring.gpg | gpg --dearmor -o /usr/share/keyrings/librewolf.gpg
   ```

2. **Better Error Messages**
   - Added verification that GPG key file was created
   - Display the repository line being added
   - Show helpful message if apt update fails

3. **Enhanced Logging**
   - Show detected codename
   - Show when Kali is detected and mapping occurs
   - Show final codename being used

## Testing

### Test Scenarios

#### Scenario 1: Kali Linux Rolling
```bash
$ lsb_release -sc
kali-rolling

# Expected behavior:
[*] Detected distribution codename: kali-rolling
[*] Kali Linux detected - Using Debian 'unstable' repository
[✓] Using repository codename: unstable
[*] Repository line: deb [arch=amd64 signed-by=/usr/share/keyrings/librewolf.gpg] http://deb.librewolf.net unstable main
```

#### Scenario 2: Regular Debian
```bash
$ lsb_release -sc
bookworm

# Expected behavior:
[*] Detected distribution codename: bookworm
[✓] Using repository codename: bookworm
[*] Repository line: deb [arch=amd64 signed-by=/usr/share/keyrings/librewolf.gpg] http://deb.librewolf.net bookworm main
```

#### Scenario 3: Kali Variant (e.g., kali-dev)
```bash
$ lsb_release -sc
kali-dev

# Expected behavior:
[*] Detected distribution codename: kali-dev
[*] Kali variant detected - Using Debian 'unstable' repository
[✓] Using repository codename: unstable
```

## Verification Steps

After applying the fix:

1. **On Kali Linux:**
   ```bash
   sudo python3 ghostconnect.py
   ```

2. **Check output:**
   - Should see: "Kali Linux detected - Using Debian 'unstable' repository"
   - Should see: "LibreWolf installed successfully"
   - No 404 errors

3. **Verify installation:**
   ```bash
   which librewolf
   # Expected: /usr/bin/librewolf

   librewolf --version
   # Expected: LibreWolf version info

   cat /etc/apt/sources.list.d/librewolf.list
   # Expected: deb ... http://deb.librewolf.net unstable main
   ```

## Supported Distributions

After the fix, GhostConnect supports:

| Distribution | Detected Codename | Mapped Codename | Status |
|-------------|-------------------|-----------------|---------|
| Kali Rolling | `kali-rolling` | `unstable` | ✅ Fixed |
| Kali Dev | `kali-dev` | `unstable` | ✅ Fixed |
| Debian Bookworm | `bookworm` | `bookworm` | ✅ Works |
| Debian Bullseye | `bullseye` | `bullseye` | ✅ Works |
| Debian Unstable | `unstable` | `unstable` | ✅ Works |
| Debian Testing | `testing` | `testing` | ✅ Works |
| Ubuntu | `jammy`, `focal`, etc. | (no mapping)* | ⚠️ May fail |

*Note: Ubuntu support may require additional mapping if LibreWolf repo doesn't support Ubuntu codenames.

## Alternative Solutions Considered

### Option 1: Use Debian Sid/Unstable (Chosen)
**Pros:**
- Simple mapping
- Kali is based on Debian unstable/testing
- High compatibility
- Minimal code changes

**Cons:**
- May get bleeding-edge versions

### Option 2: Use Debian Bookworm (Stable)
**Pros:**
- More stable versions
- Well-tested packages

**Cons:**
- May be older versions
- Less aligned with Kali's bleeding-edge nature

### Option 3: Prompt User
**Pros:**
- User choice

**Cons:**
- Bad UX (requires user input)
- Defeats "automated" goal

**Decision:** Chose Option 1 (unstable) as it best matches Kali's philosophy.

## Future Considerations

1. **Ubuntu Support**
   - Add similar mapping for Ubuntu codenames
   - Map to nearest Debian equivalent

2. **Version Checking**
   - Check LibreWolf repository structure dynamically
   - Auto-select best available release

3. **Fallback Options**
   - If unstable fails, try testing
   - If all Debian releases fail, try alternative installation methods

## Changelog Entry

```markdown
## [2.0.1] - 2025-02-07

### Fixed
- **Kali Linux LibreWolf Installation** - Fixed 404 error when installing on Kali Linux
  - Added codename mapping: `kali-rolling` → `unstable`
  - Supports all Kali variants (kali-rolling, kali-dev, etc.)
  - Improved GPG key download reliability
  - Enhanced error messages and logging

### Changed
- GPG key download now uses single robust command
- Better distribution detection messages
- Added repository line verification
```

## Deployment Notes

This is a **critical bug fix** for Kali Linux users. Without this fix, the tool is **completely non-functional** on Kali Linux (the primary target platform).

**Priority:** HIGH
**Impact:** All Kali Linux users
**Breaking Changes:** None
**Backward Compatibility:** Yes (still works on Debian)

---

**Fixed by:** Python Developer
**Date:** 2025-02-07
**Version:** 2.0.1
