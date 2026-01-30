# Dashboard Migration - Documentation & Instruction Changes Plan

This file tracks pending and completed documentation/instruction changes. Reference this for all instruction updates going forward.

## Guidelines

- Store instruction changes here before committing
- Update this file with each code commit that includes doc changes
- Keep it organized by component (README, configs, notebooks)
- Mark items as completed with date and commit hash

---

## Pending Changes

*No pending changes*

---

## Completed Changes

### 2026-01-28 - Cluster Configuration Documentation (commit: 1ad184a)

**Component:** `Bundle/README.md`

**Changes Made:**
- Added comprehensive "Cluster Configuration" section
- Documented serverless vs standard cluster differences
- Explained why each job uses specific cluster type
- Added performance notes for serverless compute
- Updated troubleshooting with cluster-related tips
- Clarified that 17.3 LTS should always be used going forward

**Rationale:** 
Users needed clear guidance on cluster setup. Previous config was misleading (claimed serverless but wasn't).

---

### 2026-01-28 - Remove Warning Language (commit: pending)

**Component:** `Bundle/README.md`

**Changes Made:**
- Removed emoji warnings and "never use" language from Important Notes
- Made text more neutral and instructional
- Kept technical requirements without prescriptive warnings

**Rationale:**
Instructions should be factual, not include warnings. Keep documentation professional.

---

## Future Tracking

When making documentation changes:

1. Add entry to "Pending Changes" section
2. Make the code/doc changes
3. Move entry to "Completed Changes" with commit hash
4. Reference this file in commit messages if needed

## Change Categories

- **README Updates** - Bundle/README.md, root README.md
- **Config Documentation** - config.yaml.template, inline comments
- **Notebook Instructions** - Cell markdown in notebooks
- **Architecture Docs** - INVENTORY_FIELDS.md, TESTING_GUIDE.md
- **Troubleshooting** - Error messages, debug guides
