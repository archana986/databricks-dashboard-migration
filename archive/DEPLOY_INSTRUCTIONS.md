# Category Insights - Deployment Instructions

## 📋 Overview

This prototype uses Unity Catalog Volumes to store the CSV data and creates a Delta table for the Lakeview dashboard.

**Catalog:** `archana_krish_fe_dsa`  
**Schema:** `vizient_deep_dive`  
**Volume:** `data_files`  
**Table:** `category_insights_delta`

## 🚀 Deployment Steps

### Step 1: Upload CSV to Databricks Workspace

Upload the CSV file to your Databricks workspace (this is temporary, just for easy access):

```bash
# Using Databricks CLI
databricks workspace import \
  "category_insights_data.csv" \
  "/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration/category_insights_data.csv" \
  --format AUTO \
  --overwrite
```

**Or manually:**
1. Go to Databricks Workspace
2. Navigate to: `/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration/`
3. Click "Create" → "File" → Upload `category_insights_data.csv`

### Step 2: Upload Notebook to Databricks

Upload the notebook:

```bash
databricks workspace import \
  "01_Load_Category_Insights.ipynb" \
  "/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration/01_Load_Category_Insights" \
  --format JUPYTER \
  --overwrite
```

**Or manually:**
1. Go to Databricks Workspace
2. Navigate to: `/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration/`
3. Click "Create" → "Notebook" → "Import" → Upload `01_Load_Category_Insights.ipynb`

### Step 3: Run the Notebook

1. Open the notebook in Databricks
2. Attach to a cluster (any cluster with DBR 13.3+ will work)
3. Run Cell 1-2 to create the schema and volume
4. **Important:** The notebook will create the volume structure. Now you need to upload the CSV:

#### Upload CSV to Unity Catalog Volume

**Option A: Using Databricks UI**
1. Go to **Data** → **Volumes** in the Databricks UI
2. Navigate to: `archana_krish_fe_dsa` → `vizient_deep_dive` → `data_files`
3. Click **"Upload"**
4. Upload the `category_insights_data.csv` file

**Option B: Using dbutils in notebook**
```python
# Run this in a notebook cell after creating the volume
dbutils.fs.cp(
  "file:/Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration/category_insights_data.csv",
  "/Volumes/archana_krish_fe_dsa/vizient_deep_dive/data_files/category_insights_data.csv"
)
```

5. Continue running the remaining notebook cells to load and validate the data

### Step 4: Verify Table Creation

After the notebook completes, verify:

```sql
-- Check table exists
DESCRIBE EXTENDED archana_krish_fe_dsa.vizient_deep_dive.category_insights_delta;

-- Check row count
SELECT COUNT(*) FROM archana_krish_fe_dsa.vizient_deep_dive.category_insights_delta;

-- Preview data
SELECT * FROM archana_krish_fe_dsa.vizient_deep_dive.category_insights_delta LIMIT 10;
```

Expected: **230 rows**

### Step 5: Import Lakeview Dashboard

#### Option A: Import the .lvdash.json file (Recommended)

1. Go to **Dashboards** in Databricks
2. Click **"Create Dashboard"** → **"Import dashboard"**
3. Upload `category_insights_dashboard.lvdash.json`
4. The dashboard will be created with all visualizations pre-configured

#### Option B: Create manually using SQL

If import doesn't work, create manually:

1. Go to **Dashboards** in Databricks
2. Click **"Create Dashboard"**
3. Add widgets using the SQL queries below:

#### KPIs (Top Row)
```sql
-- Total Spend
SELECT SUM(AnnualSpend) as TotalSpend 
FROM archana_krish_fe_dsa.vizient_deep_dive.category_insights_delta

-- Savings Opportunity
SELECT SUM(SavingsOpportunity) as TotalSavings 
FROM archana_krish_fe_dsa.vizient_deep_dive.category_insights_delta

-- Price Index
SELECT AVG(PriceIndex) as AvgPriceIndex 
FROM archana_krish_fe_dsa.vizient_deep_dive.category_insights_delta
```

#### Outlier Analysis (Scatter Plot)
```sql
SELECT 
  Category,
  SUM(AnnualSpend) as TotalSpend,
  AVG(PriceIndex) as AvgPriceIndex
FROM archana_krish_fe_dsa.vizient_deep_dive.category_insights_delta
GROUP BY Category
```

**Chart Type:** Scatter Plot  
**X-axis:** TotalSpend  
**Y-axis:** AvgPriceIndex  
**Group By:** Category

#### Cardiology Deep Dive (Table)
```sql
SELECT 
  ItemName,
  SKU,
  VendorName,
  YourPrice,
  BenchmarkPrice,
  PriceIndex,
  UnitsPerYear,
  AnnualSpend,
  SavingsOpportunity
FROM archana_krish_fe_dsa.vizient_deep_dive.category_insights_delta
WHERE Category = 'Cardiology'
ORDER BY SavingsOpportunity DESC
```

**Chart Type:** Table

#### Category Summary (Table)
```sql
SELECT 
  Category,
  ROUND(SUM(AnnualSpend), 2) as CategorySpend,
  ROUND(AVG(PriceIndex), 2) as CategoryPriceIndex,
  ROUND(SUM(SavingsOpportunity), 2) as CategorySavings,
  COUNT(*) as ItemCount
FROM archana_krish_fe_dsa.vizient_deep_dive.category_insights_delta
GROUP BY Category
ORDER BY CategorySpend DESC
```

**Chart Type:** Table

## 🔄 Re-running / Testing

To reload data with changes:

1. Update the CSV file
2. Upload to the volume (overwrite existing)
3. Re-run the notebook from Step 3 onwards
4. Refresh the dashboard

## 📁 Files in This Package

- **category_insights_data.csv** - Synthetic healthcare supply chain data (230 rows)
- **01_Load_Category_Insights.ipynb** - Databricks notebook to create volume and load data
- **category_insights_dashboard.lvdash.json** - Lakeview AI/BI dashboard file (ready to import)
- **DEPLOY_INSTRUCTIONS.md** - This file

## 🎯 Quick Test Commands

```bash
# Upload CSV to workspace
databricks workspace import category_insights_data.csv /Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration/category_insights_data.csv --format AUTO --overwrite

# Upload notebook
databricks workspace import 01_Load_Category_Insights.ipynb /Workspace/Users/archana.krishnamurthy@databricks.com/01-Customer-Projects/Vizient/Dashboard-Migration/01_Load_Category_Insights --format JUPYTER --overwrite
```

Then:
1. Open notebook in Databricks
2. Run all cells
3. Upload CSV to the created volume via UI
4. Import the dashboard: Dashboards → Create Dashboard → Import → Upload `category_insights_dashboard.lvdash.json`

## 🆘 Troubleshooting

### "Schema not found"
Run: `CREATE SCHEMA IF NOT EXISTS archana_krish_fe_dsa.vizient_deep_dive;`

### "Volume not found"
Run: `CREATE VOLUME IF NOT EXISTS archana_krish_fe_dsa.vizient_deep_dive.data_files;`

### "CSV file not found in volume"
Make sure you uploaded the CSV to: `/Volumes/archana_krish_fe_dsa/vizient_deep_dive/data_files/category_insights_data.csv`

### "Permission denied"
- Check catalog permissions: `SHOW GRANTS ON CATALOG archana_krish_fe_dsa`
- You need `USE CATALOG`, `CREATE SCHEMA`, `CREATE VOLUME`, and `CREATE TABLE` permissions

---

**Last Updated:** January 2026  
**Version:** 2.0 (Unity Catalog Volumes)
