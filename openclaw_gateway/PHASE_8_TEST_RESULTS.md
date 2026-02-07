# Phase 8: Testing Results
**Date:** 2026-02-06  
**Status:** Testing Complete - Issues Found

---

## Test Results Summary

| Step | Test | Status | Notes |
|------|------|--------|-------|
| 8.1 | Install Module | ✅ PASS | Module installed successfully |
| 8.2 | Health Check | ✅ PASS | Returns 200 OK with version info |
| 8.3 | List Skills | ✅ PASS | Returns 9 skills correctly |
| 8.4 | Ping Skill | ⚠️ PARTIAL | Works with `limit: 1`, fails without limit |
| 8.5 | Sales Orders | ✅ PASS | Returns real sales data |
| 8.6 | Create Lead | ❌ FAIL | 500 Internal Server Error |
| 8.7 | Invalid Token | ✅ PASS | Correctly returns 401 with INVALID_TOKEN |
| 8.10a | Invoices | ✅ PASS | Returns invoice data |
| 8.10b | Customers | ✅ PASS | Returns customer data |
| 8.10c | Employees | ❌ FAIL | QUERY_ERROR: Expected singleton: res.users() |
| 8.10d | Products | ✅ PASS | Returns product data |
| 8.10e | Users | ✅ PASS | Returns user data |
| 8.10f | Summary | ❌ FAIL | QUERY_ERROR: Expected singleton: res.users() |

**Pass Rate:** 7/13 tests (54%)

---

## Successful Tests

### ✅ Health Check (Step 8.2)
```bash
curl http://localhost:8069/api/health
```
**Response:**
```json
{
  "status": "ok",
  "version": "18.0.1.0.0",
  "timestamp": "2026-02-06T13:15:26.844..."
}
```

### ✅ List Skills (Step 8.3)
```bash
curl -H "X-OPENCLAW-TOKEN: demo_token_change_in_production" \
  http://localhost:8069/api/skills
```
**Response:**
- Success: true
- Count: 9 skills
- All skills present: ping, sales, invoices, customers, employees, products, users, create_lead, summary

### ✅ Ping Skill (Step 8.4) - With Limit
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-OPENCLAW-TOKEN: demo_token_change_in_production" \
  -d '{"limit": 1}' http://localhost:8069/api/skills/ping
```
**Response:**
```json
{
  "success": true,
  "data": {
    "message": "pong",
    "timestamp": "2026-02-06T13:16:07.014454",
    "version": "18.0.1.0.0"
  },
  "query_time_ms": 0,
  "skill": "ping"
}
```

### ✅ Sales Orders (Step 8.5)
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-OPENCLAW-TOKEN: demo_token_change_in_production" \
  -d '{"limit": 5}' http://localhost:8069/api/skills/sales
```
**Response:**
- Success: true
- Count: 5 orders
- Total available: 20
- Real sales data returned with partner names, amounts, states

### ✅ Invalid Token (Step 8.7)
```bash
curl -X POST -H "X-OPENCLAW-TOKEN: invalid_token_12345" \
  -d '{}' http://localhost:8069/api/skills/ping
```
**Response:**
```json
{
  "success": false,
  "error": "INVALID_TOKEN",
  "message": "Token not found"
}
```

### ✅ Invoices, Customers, Products, Users
All query skills for invoices, customers, products, and users work correctly with proper limit parameters.

---

## Failed/Partial Tests

### ⚠️ Ping Skill - Without Limit (Minor Issue)
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-OPENCLAW-TOKEN: demo_token_change_in_production" \
  -d '{}' http://localhost:8069/api/skills/ping
```
**Error:**
```json
{
  "success": false,
  "error": "LIMIT_EXCEEDED",
  "message": "Requested limit 10 exceeds maximum allowed 1"
}
```

**Root Cause:**
- When no `limit` is provided in payload, executors default to `limit = 10`
- Ping skill has `max_limit = 1`
- Validation correctly rejects the default of 10

**Impact:** Low - Working as designed, validates max_limit enforcement
**Workaround:** Always pass `{"limit": 1}` for ping and create_lead skills

---

### ❌ Create Lead (Critical Issue)
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-OPENCLAW-TOKEN: demo_token_change_in_production" \
  -d '{"limit": 1, "name": "Test Lead", "contact_name": "John", ...}' \
  http://localhost:8069/api/skills/create_lead
```
**Error:**
```
500 Internal Server Error
```

**Odoo Log Error:**
```python
ValueError: Expected singleton: res.users()
  at /opt/odoo/odoo-server/odoo/addons/base/models/res_users.py:1298
  in _is_public -> self.ensure_one()
```

**Root Cause:**
- Controller routes use `auth='none'`
- This creates an incomplete environment with no user context
- When calling `env['crm.lead'].sudo().create()`, Odoo tries to access `env.user._is_public()`
- But `env.user` is an empty recordset, causing singleton error

---

### ❌ Employees Query (Critical Issue)
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-OPENCLAW-TOKEN: demo_token_change_in_production" \
  -d '{"limit": 2}' http://localhost:8069/api/skills/employees
```
**Error:**
```json
{
  "success": false,
  "error": "QUERY_ERROR",
  "message": "Failed to query employees: Expected singleton: res.users()"
}
```

**Root Cause:** Same as create_lead - missing user context due to `auth='none'`

---

### ❌ Summary (Critical Issue)
```bash
curl -X POST -H "Content-Type: application/json" \
  -H "X-OPENCLAW-TOKEN: demo_token_change_in_production" \
  -d '{"limit": 1}' http://localhost:8069/api/skills/summary
```
**Error:**
```json
{
  "success": false,
  "error": "QUERY_ERROR",
  "message": "Failed to get summary: Expected singleton: res.users()"
}
```

**Root Cause:** Same as create_lead - missing user context due to `auth='none'`

---

## Root Cause Analysis

### Problem: Missing User Context in Environment

**Affected Routes:**
- `/api/skills` (GET) - List skills
- `/api/skills/<code>` (POST) - Execute skill

**Current Implementation:**
```python
@http.route('/api/skills', type='http', auth='none', methods=['GET'])
def list_skills(self):
    ...
    Skill = request.env['openclaw.skill'].sudo()
    # request.env has no user when auth='none'
```

**Why Some Skills Work:**
- **Sales, Invoices, Customers, Products, Users:** These use simple `search_read()` operations that don't trigger user context checks
- **Employees, Summary, Create Lead:** These operations (or the models they access) internally check `env.user._is_public()` or similar, which fails when there's no user

**Odoo Authentication Modes:**
- `auth='none'`: No user context at all - environment is incomplete
- `auth='public'`: Public user context - environment is complete, suitable for sudo()
- `auth='user'`: Requires logged-in user session

---

## Fix Plan

### Issue 1: User Context Missing (CRITICAL)
**Priority:** HIGH  
**Affected:** create_lead, employees, summary skills

**Solution:**
Change `auth='none'` to `auth='public'` in controller routes that execute skills. This provides a complete environment with the public user, which can then be elevated with `.sudo()`.

**Files to Modify:**
- `controllers/api.py`

**Changes:**
1. Line ~230: `@http.route('/api/skills', type='http', auth='none', methods=['GET'])`
   - Change to: `auth='public'`

2. Line ~270: `@http.route('/api/skills/<code>', type='http', auth='none', methods=['POST'])`
   - Change to: `auth='public'`

**Verification:**
After fix, test:
```bash
# Should work without 500 error
curl -X POST -H "Content-Type: application/json" \
  -H "X-OPENCLAW-TOKEN: demo_token_change_in_production" \
  -d '{"limit": 1, "name": "Test Lead"}' \
  http://localhost:8069/api/skills/create_lead

# Should return employee data
curl -X POST -H "Content-Type: application/json" \
  -H "X-OPENCLAW-TOKEN: demo_token_change_in_production" \
  -d '{"limit": 2}' http://localhost:8069/api/skills/employees

# Should return summary counts
curl -X POST -H "Content-Type: application/json" \
  -H "X-OPENCLAW-TOKEN: demo_token_change_in_production" \
  -d '{"limit": 1}' http://localhost:8069/api/skills/summary
```

---

### Issue 2: Default Limit Validation (MINOR)
**Priority:** LOW  
**Affected:** ping, create_lead, summary (max_limit=1 skills)

**Current Behavior:**
- Empty payload `{}` defaults to `limit = 10` in executors
- Skills with `max_limit = 1` correctly reject this

**Options:**

**Option A: Keep Current Behavior (RECOMMENDED)**
- Pro: Validates max_limit enforcement correctly
- Pro: Forces clients to be explicit about limits
- Con: Requires `{"limit": 1}` in payload even for ping

**Option B: Change Default in Executors**
- Modify `BaseExecutor._validate_limit()` to use `min(default, max_limit)`
- Pro: More convenient for clients
- Con: Hides max_limit from clients

**Option C: Remove Limit from Skills That Don't Need It**
- Modify ping, create_lead executors to not call `_validate_limit()`
- Pro: Ping doesn't need a limit conceptually
- Con: Inconsistent executor pattern

**Recommendation:** Keep Option A (current behavior). It's working as designed and enforces proper API usage.

**Documentation Note:**
Update API docs to clarify that skills with `max_limit = 1` require `{"limit": 1}` in payload.

---

## Implementation Steps

### Step 1: Fix User Context Issue
1. Open `controllers/api.py`
2. Find line ~230: `@http.route('/api/skills', type='http', auth='none', methods=['GET'])`
3. Change to: `auth='public'`
4. Find line ~270: `@http.route('/api/skills/<code>', type='http', auth='none', methods=['POST'])`
5. Change to: `auth='public'`
6. Save file

### Step 2: Restart Odoo
```bash
sudo systemctl restart odoo
# Wait 10 seconds for Odoo to restart
sleep 10
```

### Step 3: Re-test Failed Skills
```bash
# Test create_lead
curl -X POST -H "Content-Type: application/json" \
  -H "X-OPENCLAW-TOKEN: demo_token_change_in_production" \
  -d '{"limit": 1, "name": "Test Lead from API", "contact_name": "John Doe", "email_from": "john@example.com"}' \
  http://localhost:8069/api/skills/create_lead

# Test employees
curl -X POST -H "Content-Type: application/json" \
  -H "X-OPENCLAW-TOKEN: demo_token_change_in_production" \
  -d '{"limit": 3}' \
  http://localhost:8069/api/skills/employees

# Test summary
curl -X POST -H "Content-Type: application/json" \
  -H "X-OPENCLAW-TOKEN: demo_token_change_in_production" \
  -d '{"limit": 1}' \
  http://localhost:8069/api/skills/summary
```

### Step 4: Verify All Tests Pass
Run complete test suite again to ensure:
- ✅ All 13 tests pass
- ✅ No regressions in previously working skills
- ✅ Request logging still works
- ✅ Token authentication still works

### Step 5: Commit Fix
```bash
cd /root/odoo_18_module/openclaw_gateway
git add controllers/api.py
git commit -m "Fix: Change auth='none' to auth='public' for proper user context

- Resolves singleton error: Expected singleton: res.users()
- Fixes create_lead, employees, summary skills (500 errors)
- auth='public' provides complete environment for sudo() calls
- All 13 Phase 8 tests now pass

Tested:
- create_lead: Creates CRM leads successfully
- employees: Returns employee data
- summary: Returns database counts
- All other skills: Still working correctly
"
```

---

## Expected Outcome After Fix

All 13 tests should pass:

| Step | Test | Expected Status |
|------|------|-----------------|
| 8.1 | Install Module | ✅ PASS |
| 8.2 | Health Check | ✅ PASS |
| 8.3 | List Skills | ✅ PASS |
| 8.4 | Ping Skill | ✅ PASS (with limit: 1) |
| 8.5 | Sales Orders | ✅ PASS |
| 8.6 | Create Lead | ✅ PASS ← **FIXED** |
| 8.7 | Invalid Token | ✅ PASS |
| 8.10a | Invoices | ✅ PASS |
| 8.10b | Customers | ✅ PASS |
| 8.10c | Employees | ✅ PASS ← **FIXED** |
| 8.10d | Products | ✅ PASS |
| 8.10e | Users | ✅ PASS |
| 8.10f | Summary | ✅ PASS ← **FIXED** |

**Pass Rate:** 13/13 tests (100%)

---

## Notes

### auth='public' vs auth='none'

**auth='none':**
- No database access
- No environment setup
- Use for static responses only (like health check)
- `request.env` exists but has no user

**auth='public':**
- Database access allowed
- Public user context established
- Can use `.sudo()` for elevated access
- `request.env.user` is the public user
- Perfect for API endpoints with custom authentication

**Decision:** Keep health check as `auth='none'`, change skills routes to `auth='public'`

---

## Remaining Phase 8 Tasks

After implementing fix:
- [ ] Step 8.8: Verify Request Logging (check Odoo UI)
- [ ] Step 8.9: Test Permission Denial (create restricted token)
- [ ] Update LAZY_PLAN.md with completed steps
- [ ] Mark Phase 8 as complete

---

**Generated:** 2026-02-06  
**Test Duration:** ~10 minutes  
**Issues Found:** 3 (1 critical, 1 minor design decision)  
**Fix Complexity:** Low (2 line changes)  
**Estimated Fix Time:** 5 minutes + testing
