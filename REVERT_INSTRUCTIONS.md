# How to Revert to Original Pipeline

If you need to revert the "Extract Once, Analyze Many" changes, here are the exact steps:

## Quick Revert (30 seconds)

**Option 1: Simple Import Change**
```bash
# Edit app.py line 31, change this:
from core.structured_pipeline import StructuredBAAssistant as BAAssistant

# Back to this:
from core.pipeline import BAAssistant
```

**Option 2: Git Revert**
```bash
# Find the commit hash for the structured pipeline change
git log --oneline -5

# Revert the structured pipeline commit (look for "Extract Once, Analyze Many")
git revert <commit-hash>
```

## Manual Step-by-Step Revert

**Step 1: Revert app.py import**
```bash
# Open app.py and find line ~31
# Change:
# STRUCTURED PIPELINE: "Extract Once, Analyze Many" architecture 
# Old: from core.pipeline import BAAssistant
from core.structured_pipeline import StructuredBAAssistant as BAAssistant

# Back to:
from core.pipeline import BAAssistant
```

**Step 2: Remove comment lines (optional)**
```bash
# In app.py, you can remove these comment lines:
# STRUCTURED PIPELINE: "Extract Once, Analyze Many" architecture 
# Old: from core.pipeline import BAAssistant
```

**Step 3: Test the revert**
```bash
source .venv/bin/activate
python -c "from core.pipeline import BAAssistant; print('✅ Reverted successfully')"
```

## Verification After Revert

**Test that everything works:**
```bash
# 1. Check imports
source .venv/bin/activate
python -c "from core.pipeline import BAAssistant; print('Original pipeline restored')"

# 2. Test Streamlit app starts
streamlit run app.py --server.headless true --server.port 8502 &
sleep 3
curl -s http://localhost:8502 | grep -q "IDPETECH" && echo "✅ App working" || echo "❌ App failed"
pkill -f "streamlit run app.py"
```

## What Gets Reverted

**Files that revert to original state:**
- `app.py` - Goes back to using original `BAAssistant`
- All functionality returns to pre-structured-pipeline behavior

**Files that remain (safe to keep):**
- `core/models/` - New structured intelligence models (unused when reverted)
- `core/extraction/` - New extraction engine (unused when reverted) 
- `core/reasoning/` - New reasoning stages (unused when reverted)
- `core/intelligence/` - Intelligence graph and serialization (unused when reverted)
- `core/structured_pipeline.py` - New pipeline orchestrator (unused when reverted)

These new files don't interfere with the original pipeline, so they can be safely left in place.

## What You Lose When Reverting

**Features lost after revert:**
- ~60% token usage reduction
- Evidence traceability 
- Reasoning consistency improvements
- Data quality scoring
- Intelligence caching

**What stays the same:**
- All existing functionality works identically
- Same UI and user experience
- Same database schema
- Same outputs and formats

## Troubleshooting Revert Issues

**If revert fails:**

1. **ImportError after revert:**
   ```bash
   # Make sure you're importing from the right place
   grep -n "BAAssistant" app.py
   # Should show: from core.pipeline import BAAssistant
   ```

2. **App won't start:**
   ```bash
   # Check for syntax errors
   python -m py_compile app.py
   ```

3. **Still seeing structured pipeline:**
   ```bash
   # Check the import line carefully
   head -35 app.py | grep -A2 -B2 "BAAssistant"
   ```

## Re-enabling Structured Pipeline

**To switch back to structured pipeline:**
```bash
# Change app.py import back to:
from core.structured_pipeline import StructuredBAAssistant as BAAssistant
```

## Emergency Rollback via Git

**If something goes wrong, full git rollback:**
```bash
# See recent commits
git log --oneline -10

# Find the commit BEFORE the structured pipeline changes
# Roll back to that commit
git reset --hard <commit-before-changes>

# This will undo ALL changes since that commit - use carefully!
```

## File Backup Approach

**Before making the original change, backup the working app.py:**
```bash
cp app.py app.py.backup.working

# To restore from backup:
cp app.py.backup.working app.py
```

## Support

**If you have issues with revert:**

1. Check that `core/pipeline.py` still exists and contains `BAAssistant` class
2. Ensure no other imports in app.py reference structured pipeline components
3. Verify that the original pipeline still works: `python -c "from core.pipeline import BAAssistant"`
4. Restart your Python environment/kernel if imports are cached

The revert is designed to be simple and safe - just changing one import line should restore full original functionality.