# Execute Now - Your Commands

## ✅ Everything is Ready! Here's What to Do:

---

## COMMAND 1: Sync Files to Databricks

**Open your terminal and paste this:**

```bash
cd "/Users/archana.krishnamurthy/Downloads/Career & Growth/Cursor/Customer-Work/Catalog Migration" && databricks configure --token --profile e2-demo-field-eng
```

**Enter when prompted:**
- Host: `https://e2-demo-field-eng.cloud.databricks.com`
- Token: `[Your PAT token]`

---

## COMMAND 2: Upload All Files

```bash
python sync_to_databricks.py
```

**Wait for:** `✅ Sync completed!`

---

## COMMAND 3: Verify Upload

**Go to:** https://e2-demo-field-eng.cloud.databricks.com

**Check:** Workspace → Users → archana.krishnamurthy@databricks.com → 01-Customer-Projects → Vizient → Dashboard-Migration

**You should see:**
- ✅ config/
- ✅ helpers/
- ✅ Bundle/
- ✅ notebooks/

---

## THEN: Follow the Testing Guide

**Open in Databricks:** `TESTING_GUIDE.md`

**Or follow:** `FIRST_STEPS.md`

---

## Quick Checklist

Before running Bundle notebooks:

- [ ] Files synced to Databricks (Step 1-3 above)
- [ ] `config/config.yaml` edited with your values
- [ ] Databricks secrets created (migration scope)
- [ ] Unity Catalog volume created
- [ ] CSV mapping file created in volume

**Then:**

- [ ] Run `Bundle/Bundle_01_Export_and_Transform.ipynb`
- [ ] Run `Bundle/Bundle_02_Generate_and_Deploy.ipynb`
- [ ] Verify dashboards in target workspace

---

## Your Exact Commands

Copy-paste ready:

```bash
# 1. Setup Databricks CLI (one-time)
cd "/Users/archana.krishnamurthy/Downloads/Career & Growth/Cursor/Customer-Work/Catalog Migration"
databricks configure --token --profile e2-demo-field-eng
# Enter: https://e2-demo-field-eng.cloud.databricks.com
# Enter: [your PAT token]

# 2. Sync all files
python sync_to_databricks.py

# 3. If you make changes later, just re-run:
python sync_to_databricks.py
```

**That's it!** Files are in Databricks, ready to test.

---

## What Each Command Does

```bash
databricks configure --token --profile e2-demo-field-eng
```
↳ Sets up connection to your Databricks workspace (one-time)

```bash
python sync_to_databricks.py
```
↳ Uploads all 32 files (config, helpers, Bundle, notebooks, docs) to Databricks

**Result:** Your entire modular solution is now in Databricks workspace!

---

## Next: Start Testing

**See:** `TESTING_GUIDE.md` - Step 1 onwards (prerequisites)

**Or see:** `FIRST_STEPS.md` - Streamlined version

**Quick path:** 
1. Edit config.yaml in Databricks
2. Create secrets
3. Create volume
4. Create CSV
5. Run Bundle_01
6. Run Bundle_02
7. Verify!

**Total time:** ~20 minutes to first successful migration

🚀 **You're ready to go!**
