# 🐛 Bug Report and Code Issues - Dental Assistant Project

## Critical Issues 🔴

### 1. **CRITICAL: GPU Detection Not Used in LLM Inference**
**File:** `app/llm/local_llm.py` (Line 74)
**Severity:** CRITICAL
**Impact:** HIGH

**Problem:**
```python
self._llm = Llama(
    model_path=str(model_path),
    n_ctx=4096,
    n_threads=None,
    n_gpu_layers=0,  # ❌ HARDCODED TO 0!
    verbose=False,
)
```

The project has comprehensive GPU detection that:
- Detects NVIDIA, AMD, and Apple Silicon GPUs
- Determines VRAM amounts
- Returns hardware profiles (high_vram, low_vram, cpu_only)

**BUT** the LocalLLM class completely ignores this and always uses CPU!

**Consequences:**
- Users with GPUs will have 10-100x slower inference
- The entire GPU detection system is wasted
- Poor user experience on capable hardware
- Waste of computational resources

**Fix Required:**
```python
# Should be:
from app.config import get_hardware_info

hw_info = get_hardware_info()
gpu_layers = 0
if hw_info['profile'] == 'high_vram':
    gpu_layers = 35  # Offload most layers to GPU
elif hw_info['profile'] == 'low_vram':
    gpu_layers = 20  # Offload some layers to GPU

self._llm = Llama(
    model_path=str(model_path),
    n_ctx=4096,
    n_threads=None,
    n_gpu_layers=gpu_layers,
    verbose=False,
)
```

---

## High Priority Issues 🟠

### 2. **Race Condition in Rate Limiting**
**File:** `app/middleware.py` (Lines 62-84)
**Severity:** HIGH
**Impact:** MEDIUM

**Problem:**
```python
self.clients[client_host] = (count, start)  # ❌ No lock protection!
```

The `SimpleRateLimitMiddleware` accesses `self.clients` dictionary without any synchronization. Multiple concurrent requests can cause:
- Incorrect rate limit counting
- Lost updates
- Potential crashes

**Additional Issue:**
```python
if len(self.clients) > 5000:
    self.clients.clear()  # ❌ Resets ALL clients!
```

This clears rate limits for ALL clients, allowing burst attacks.

**Fix Required:**
Use `asyncio.Lock()` or `threading.Lock()` to protect dictionary access.

---

### 3. **Unused Imports After Platform Refactoring**
**File:** `app/config.py` (Lines 1, 134-136)
**Severity:** MEDIUM
**Impact:** LOW

**Problem:**
After the platform refactoring, several imports are no longer used:

```python
import os  # ❌ Unused - platform modules handle this
# In _check_backend_gpu_support():
from llama_cpp import Llama  # ❌ Unused
import llama_cpp  # ❌ Unused
```

**Fix Required:**
Remove unused imports to clean up code.

---

### 4. **API Key Security Configuration**
**File:** `app/security.py` (Lines 12-14)
**Severity:** HIGH
**Impact:** MEDIUM

**Problem:**
```python
expected = os.getenv("APP_API_KEY")
if expected is None or api_key != expected:
    raise HTTPException(status_code=403, detail="Could not validate credentials")
```

Issues:
1. If `APP_API_KEY` is not set, ALL requests fail silently
2. No distinction between "API key not configured" vs "wrong API key"
3. No startup warning if API key is missing

**Fix Required:**
```python
# At startup (main.py):
if not os.getenv("APP_API_KEY"):
    logger.warning("APP_API_KEY not set! All authenticated endpoints will fail.")

# In verify_api_key():
expected = os.getenv("APP_API_KEY")
if expected is None:
    raise HTTPException(
        status_code=500,
        detail="Server misconfiguration: API key not set"
    )
if api_key != expected:
    raise HTTPException(
        status_code=403,
        detail="Invalid API key"
    )
```

---

### 5. **Frontend: Hardcoded Backend URL**
**File:** `FrontEnd/src/api.ts` (Line 3)
**Severity:** MEDIUM
**Impact:** MEDIUM

**Problem:**
```typescript
const BASE_URL = "http://127.0.0.1:9000";  // ❌ Hardcoded!
```

This prevents:
- Using different backend ports
- Deploying to different environments
- Configuration flexibility

**Fix Required:**
Use environment variables:
```typescript
const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:9000";
```

---

### 6. **Frontend: Hardcoded Dev API Key**
**File:** `FrontEnd/src/api.ts` (Line 6)
**Severity:** HIGH
**Impact:** HIGH (Security)

**Problem:**
```typescript
const DEV_API_KEY = "dev-api-key-12345";  // ❌ Hardcoded and committed!
```

This is a **security vulnerability**:
- Dev key is in version control
- Anyone can access the API with this key
- No distinction between dev and production

**Fix Required:**
1. Move to environment variables
2. Never commit API keys to git
3. Use different keys for dev/prod

---

## Medium Priority Issues 🟡

### 7. **Misleading Error Message**
**File:** `app/llm/whisper.py` (Lines 39-44)
**Severity:** MEDIUM
**Impact:** LOW

**Problem:**
```python
def _ensure_model_dir(self) -> None:
    model_path = Path(WHISPER_MODEL_PATH)
    if not model_path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Whisper model not found at {model_path}. Run setup/download first.",
        )
```

The directory is created in `config.py` but the model might not be downloaded.
Error message is confusing when directory exists but is empty.

---

### 8. **Generic Exception Handling**
**File:** `main.py` (Lines 84-91)
**Severity:** MEDIUM
**Impact:** LOW

**Problem:**
```python
except Exception:  # ❌ Too broad!
    logger.exception("Model download failed")
    # ... cleanup code that could also fail
```

Catches all exceptions, potentially hiding important errors like:
- Permission denied
- Disk full
- Network issues

---

### 9. **Frontend: Type Safety Issue**
**File:** `FrontEnd/src/app.tsx` (Line 79)
**Severity:** LOW
**Impact:** LOW

**Problem:**
```typescript
<MedicalLoader text={t("initializing") as string} />
```

Type assertion (`as string`) bypasses TypeScript safety. If translation returns non-string, runtime error occurs.

**Fix Required:**
```typescript
const initText = t("initializing");
<MedicalLoader text={typeof initText === 'string' ? initText : 'Initializing...'} />
```

---

## Low Priority / Code Quality Issues 🟢

### 10. **Unused Type Imports**
**Files:** Multiple files
**Severity:** LOW
**Impact:** NONE

Several files import `annotations` from `__future__` and `Tuple` from `typing` but don't use them:
- `app/llm/local_llm.py`
- `app/llm/whisper.py`
- `app/llm/api/transcribe.py`

These are minor and can be cleaned up.

---

### 11. **SimpleRateLimitMiddleware Deprecated But Still Loaded**
**File:** `app/middleware.py` (Lines 40-86)
**Severity:** LOW
**Impact:** LOW

**Problem:**
The middleware is marked as "Deprecated for MVP" but is still instantiated and added to the app, even when disabled.

**Fix Required:**
Remove from `main.py` or completely remove the class if not needed.

---

## Summary

| Severity | Count | Priority |
|----------|-------|----------|
| 🔴 Critical | 1 | Fix immediately |
| 🟠 High | 5 | Fix before production |
| 🟡 Medium | 3 | Fix soon |
| 🟢 Low | 2 | Nice to have |

**Total Issues Found:** 11

**Most Critical:** GPU detection not being used in LLM inference (Issue #1)

**Recommended Fix Order:**
1. Issue #1 (GPU not used) - Critical performance bug
2. Issue #6 (Hardcoded API key) - Security vulnerability
3. Issue #4 (API key configuration) - Better error handling
4. Issue #2 (Race condition) - Concurrency bug
5. Issue #5 (Hardcoded URL) - Configuration issue
6. Issues #3, #7-11 - Code quality improvements
