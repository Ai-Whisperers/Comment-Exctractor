# Excel Export Validator Skill

Validates Customer Feedback Analyzer Excel exports against v3.8.0+ specifications.

## Metadata

- **Name**: Excel Export Validator
- **Category**: Testing & Quality Assurance
- **Activation**: Automatic when Excel validation mentioned
- **Model**: Haiku (fast validation) or Sonnet (complex issues)
- **Token Cost**: ~500 tokens

## When to Activate

Trigger this skill when user mentions:
- "Validate Excel export"
- "Check Excel file"
- "Verify Excel output"
- "Excel formatting issues"
- "Dashboard not showing correctly"
- Testing Excel generation

## Validation Checklist

### 1. Sheet Count & Structure (v3.8.0+)

Expected sheets (in order):
1. Management Dashboard View (RED tab)
2. Churn Risk Analysis View (ORANGE tab)
3. Pain Point Analysis View (YELLOW tab)
4. Sentiment Analysis View (BLUE tab)
5. Quality Control View (PURPLE tab)
6. Duplicate Analysis View (GRAY tab)
7. Management Dashboard (legacy)
8. Executive Summary
9. Summary Dashboard
10. Quick Analysis
11-18. Analysis sheets (various)
19. Calculated Data (position 90 - END)
20-23. Reference sheets (position 91-99)

### 2. Calculated Data Columns (36 total)

**GROUP 1: Primary Review (10 columns)**
- User Score
- Customer Comment
- AI Sentiment (Spanish NLP)
- Analysis Score
- Score Source
- Sentiment Category
- Emotion
- Churn Risk
- Review Priority Score
- Pain Point Category (Primary)

**GROUP 2: Secondary Analysis (7 columns)**
- Pain Point Category (Secondary)
- Pain Point Keywords
- Sentiment Score Alignment
- Actionability Score
- Word Count
- Has Deep Insights
- Deep Insights JSON

**GROUP 3: Duplicate Detection (5 columns)**
- Is Duplicate
- Duplicate Count
- Duplicate Group ID
- First Occurrence ID
- Is First Occurrence

**GROUP 4: Quality Control (3 columns)**
- Quality Flags
- Analysis Tier
- Problemas Detectados

**GROUP 5: AI Correction Details (4 columns)**
- Original User Score
- Sentiment Score (Before Discrepancy Check)
- Discrepancy Flag
- Discrepancy Explanation

**GROUP 6: Technical Scores (2 columns)**
- Sentiment Score (GPT-4o-mini)
- Confidence Score

### 3. Tab Colors

Verify professional color scheme:
- Management Dashboard View: RED (FF0000)
- Churn Risk Analysis View: ORANGE (FF6600)
- Pain Point Analysis View: YELLOW (FFD700)
- Sentiment Analysis View: BLUE (0066CC)
- Quality Control View: PURPLE (9933CC)
- Duplicate Analysis View: GRAY (808080)

### 4. Conditional Formatting

**Review Priority Score:**
- Red (80-100): URGENT
- Yellow (60-80): HIGH
- Green (40-60): MEDIUM
- None (<40): LOW

**Churn Risk:**
- Red (>70%): High risk
- Yellow (40-70%): Medium risk
- Green (<40%): Low risk

### 5. Management Dashboard KPIs

Verify KPI cards display:
- NPS Score (calculation correct)
- Promoters % (score 9-10)
- Passives % (score 7-8)
- Detractors % (score 0-6)
- Total Reviews count
- Average Sentiment Score

### 6. Data Quality

**No Missing Critical Columns:**
- All AI analysis columns populated
- No "N/A" in required fields
- Sentiment scores in valid ranges (-1 to 1, 0-10)
- Churn risk (0-100%)

**Formula-Free (v3.7.0+):**
- No Excel formulas (static values only)
- Google Sheets compatible
- All calculations done in Python

### 7. Progressive Disclosure Pattern

**View Sheets First (positions 1-6):**
- Task-focused subsets
- 7-19 columns per view
- Filtered for specific use cases
- Professional tab colors

**Summary Sheets (positions 7-10):**
- High-level overviews
- Visual dashboards

**Complete Data at End (position 90):**
- All 36 columns
- For power users
- Not overwhelming initial view

## Validation Commands

### Quick Validation (Haiku - 30 seconds)

```python
# Run validator
python scripts/validation/validate_excel_export.py <excel_file>

# Expected output:
# Sheet count: PASS (23 sheets)
# Column count: PASS (36 columns in Calculated Data)
# Tab colors: PASS (6 view sheets colored)
# Conditional formatting: PASS
# Data quality: PASS
# Progressive disclosure: PASS
# Formula-free: PASS
```

### Deep Validation (Sonnet - 2 minutes)

```python
# Run comprehensive check
python scripts/validation/validate_excel_export.py <excel_file> --deep

# Checks:
# - All formulas removed
# - AI analysis columns populated
# - Pain point classification
# - Duplicate detection working
# - Deep insights JSON structure
# - Score alignment calculations
```

### Visual Validation (Screenshot)

1. Open Excel file
2. Take screenshots of:
   - Management Dashboard (full view)
   - Calculated Data (first 50 rows)
   - Tab color strip
3. Drag screenshots to Claude Code
4. Ask: "Validate this Excel export"

## Common Issues & Fixes

### Issue 1: Missing AI Columns

**Symptom:** Sentiment Score, Churn Risk, Emotion columns empty
**Cause:** AI analysis not running (calculated_data_sheet.py lines 163-248)
**Fix:** Verify AI analysis uncommented, asyncio.run() wrapper present

### Issue 2: Wrong Tab Colors

**Symptom:** All tabs same color or wrong colors
**Cause:** Tab color assignment missing in view sheet creation
**Fix:** Check dashboard_builder.py applies colors (RED/ORANGE/YELLOW/BLUE/PURPLE/GRAY)

### Issue 3: Calculated Data Not at End

**Symptom:** Calculated Data appears first
**Cause:** Sheet position not set to 90
**Fix:** wb.move_sheet(ws, offset=90) in calculated_data_sheet.py

### Issue 4: Formulas Present

**Symptom:** =SUM(), =AVERAGE() formulas in cells
**Cause:** Using old formula-based approach
**Fix:** Replace with Python-calculated static values

### Issue 5: 33 Columns Instead of 36

**Symptom:** Missing Analysis Score, Score Source, or v3.8.0+ columns
**Cause:** Old schema version
**Fix:** Update to latest calculated_metrics.py

## Test Cases

### Test Case 1: FTTH 846 Dataset

```bash
/analyze-feedback datasets/telecom/FTTH_846.csv

Expected result:
- 846 rows in Calculated Data
- Management Dashboard shows ~120 high-priority reviews
- Churn Risk View shows ~250 at-risk customers
- All 36 columns present
- 6 view sheets with correct colors
```

### Test Case 2: Empty Dataset

```bash
/analyze-feedback datasets/telecom/empty.csv

Expected result:
- Graceful handling
- No crashes
- Message: "No data to analyze"
```

### Test Case 3: Large Dataset (10K+ rows)

```bash
/analyze-feedback datasets/telecom/FTTH_10000.csv

Expected result:
- Completes within 5 minutes
- No memory errors
- All sheets generated
- Performance metrics logged
```

## Integration with Testing

### Unit Tests

```bash
/test-excel

Runs: api/tests/domain/export/excel/
- test_calculated_data_sheet.py
- test_dashboard_sheet.py
- test_view_sheets.py
- test_tab_colors.py
```

### Integration Tests

```bash
python api/tests/integration/test_column_generation.py

Validates:
- All 36 columns generated
- AI analysis runs
- Data flow from upload to export
```

## Success Criteria

Excel export is valid when:
- [ ] 23 sheets present (or expected count for schema)
- [ ] 36 columns in Calculated Data
- [ ] 6 view sheets with professional tab colors
- [ ] Management Dashboard with KPI cards
- [ ] Conditional formatting applied
- [ ] No formulas (formula_helpers.py deprecated)
- [ ] Progressive disclosure pattern (views first, data at end)
- [ ] AI analysis columns populated
- [ ] All validation tests pass

## References

- [api/app/domain/export/excel/sheets/calculated_data_sheet.py](api/app/domain/export/excel/sheets/calculated_data_sheet.py)
- [api/app/domain/export/excel/sheets/dashboard_sheet.py](api/app/domain/export/excel/sheets/dashboard_sheet.py)
- [api/app/domain/export/excel/sheets/view_sheets.py](api/app/domain/export/excel/sheets/view_sheets.py)
- [CLAUDE.md](CLAUDE.md) - Excel Export Columns section

## Token Optimization

- Use Haiku for quick validation (5x cheaper)
- Use Sonnet for complex debugging
- Use Extended Thinking (4K) for architecture issues
- Batch read multiple sheet files in parallel

---

**Last Updated:** 2025-11-16
**Project Version:** v3.8.0+
**Maintained by:** Customer Feedback Analyzer team
