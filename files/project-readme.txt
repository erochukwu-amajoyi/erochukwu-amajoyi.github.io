# Supply Chain Data & Automation Portfolio

Three connected demonstrations for a graduate data and automation analyst application. All businesses, suppliers and records are fictional. This is an independent portfolio, not work commissioned by Franke and not evidence of access to SAP.

## Start here

1. Open `01_Excel/Inventory_Health.xlsx` and review the inventory dashboard. Change the amber safety-stock and review-cycle assumptions to explore their effect on proposed orders.
2. Open `02_PowerBI/Supply_Chain_Performance.pbix` in Power BI Desktop. This copy was refreshed, visually checked and saved with its data on 22 September 2026. The editable `Supply.pbip` remains available for source-based development; it requires Refresh on first opening. After moving the source folder, run `python 02_PowerBI/set_data_folder.py` before opening the PBIP. For future refreshes of the PBIX after moving the data, update its DataFolder parameter in Power Query.
3. Run the automation commands below. Compare the validated report with the blocked diagnostic report.

The dataset has 80 items, six suppliers, 1,500 purchase-order lines and 60 BOM component lines. The fixed reporting date is 21 September 2026. Currency is GBP; no exchange-rate conversion is modelled.

## Project 1: Inventory health and reorder analysis

**Business question:** Which items need purchasing review, and how much working capital is tied up in stock?

The workbook uses exact-match VLOOKUP, SUMIFS, COUNTIFS, Excel Tables, data validation, conditional formatting and a native chart. Raw item inputs remain separate from the formulas. The dashboard summarises category stock value and proposed purchase cost.

- Available stock position = on hand − allocated + on order.
- Daily demand = trailing 90-day demand / 90.
- Reorder point = daily demand × (supplier lead days + safety-stock days), rounded up.
- Target = daily demand × (lead days + safety-stock days + review-cycle days), rounded up.
- Proposed order = max(0, target − stock position), only when position is at or below the reorder point.
- Annualised turnover = 90-day fulfilled-demand cost / 90-day average stock value × 365 / 90.

**Findings in the generated scenario:** £2,184,017.55 on-hand stock value; 27 items requiring reorder review; £766,792.11 proposed order cost; 12.43× annualised turnover. These are synthetic scenario results, not achieved savings. On-order timing, minimum order quantities, pack sizes and seasonality are not modelled. A proposed order needs buyer review.

The workbook is a fixed 80-item analysis. Editing existing source records recalculates formulas. Adding items requires extending the source and calculation tables, formulas, summary ranges and chart ranges before use. Do not treat it as an automatically refreshing ERP connection.

**Pivot-table practice:** In Excel, select the ReorderTable, insert a PivotTable on a new sheet, place Category in Rows, Stock value GBP and Order cost GBP in Values (Sum), and Decision in Filters. Reconcile the grand totals to the dashboard. The delivered workbook contains formula summaries; a native PivotTable has not been created or verified.

## Project 2: Supplier performance in Power BI

**Business question:** Which suppliers contribute most to late or incomplete delivery?

The editable project contains Power Query CSV imports, four model tables, three single-direction one-to-many relationships, eight DAX measures, two report pages and 12 visuals. Supplier, category and due-month selections filter the measures. Dates connect to Orders by DueDate, so monthly reporting is by promised delivery month, not order month.

**OTIF definition:** an order line counts as on time and in full when it has a recorded receipt on or before its due date and the received quantity meets the ordered quantity. The denominator is every order line due by the reporting date, including overdue unreceived lines. It is line-weighted, not quantity-weighted. One receipt record per line is assumed; partial shipment histories are not available.

Expected unfiltered results after refresh:

| Measure | Expected |
|---|---:|
| Order lines | 1,500 |
| Due lines | 1,488 |
| OTIF lines | 575 |
| OTIF rate | 38.64% |
| Overdue open lines | 18 |
| Ordered value GBP | £18,583,768.14 |
| Mean received lead time | 18.01 days |

Low OTIF is intentional in this scenario. Investigate supplier and month differences before suggesting corrective action. Ordered value is a purchasing commitment measure, not actual cash paid or receipts value.

**Validation status:** 20 Power BI project/report JSON files pass Microsoft's public schemas. CSV keys and relationships were checked separately. On 22 September 2026 the report was refreshed successfully in Power BI Desktop, executing Power Query and DAX. Both pages rendered, the headline figures matched the controls, and selecting one supplier filtered the scorecard correctly. The supplier selection was cleared and a populated `Supply_Chain_Performance.pbix` was saved. The original opening warnings concerned missing model data and relationships awaiting refresh; they cleared after the first refresh.

Add genuine screenshots and a published report link when publishing the portfolio. No report has been deployed to Power BI Service. The dataset can be used without access to an employer system.

## Project 3: ERP export validation and reporting automation

**Business question:** How can a recurring reporting process avoid publishing incorrect data?

The Python pipeline uses only the standard library. It validates keys, item/supplier references, supplier-item consistency, quantities, date sequences, receipt consistency, BOM quantities, units and cycles. It writes accepted records, a detailed quality-issue log, a JSON summary and an HTML report. A failed run produces diagnostic output but never advances `latest.json` to a faulty report. Run identifiers incorporate input content and the reporting date.

From this portfolio directory, with Python 3 installed:

```powershell
python -m unittest discover -s 03_Automation -v
python 03_Automation/pipeline.py --input data/clean
python 03_Automation/pipeline.py --input data/raw
```

The clean run should exit 0 with PASS. The deliberately faulty run should exit 2 with BLOCKED, nine issues and five rejected order rows. Nine issues include multiple rules on some records and BOM issues; issue count is not rejected-row count. The supplied clean dataset is a known-good fixture, not an automated repair of the dirty file. Resolve faulty source records explicitly before rerunning a production process.

The standard-library code is runnable on Windows or macOS. `generate_data.py` recreates the input fixtures deterministically using seed 42. It does not refresh the Excel workbook or Power BI model automatically.

### Process map

Before: export files → copy/paste → reconcile manually → build report → email attachment.

After: export to controlled folder → run validations → retain issues and diagnostics on failure → publish a validated dated report on success → optionally trigger an approved delivery flow.

### Power Automate implementation blueprint (not deployed)

1. Use an approved scheduled desktop flow to run the Python command against a controlled export folder. Set an explicit reporting date for each run.
2. Capture the exit code. A nonzero result must take the failure branch and must not distribute a report.
3. On exit 0, read `latest.json`, then load the pointed-to summary and verify that the run ID and reporting date match this run. Do not send a prior report simply because a latest file exists.
4. Copy the validated output to the organisation's approved SharePoint/OneDrive location if authorised. A cloud flow can trigger from that location and notify a configured recipient.
5. Add a failure notification, concurrency limit of one and a run-ID delivery ledger to prevent duplicate notifications after retries. Configure recipients and permissions inside the organisation's environment.

No cloud flow, schedule, SAP connection, SharePoint upload or email delivery has been configured. There is no measured labour saving yet. Time the manual and automated processes over repeated runs before reporting a reduction.

## Interview walkthrough

- Explain why open overdue lines belong in the OTIF denominator.
- Change safety-stock days from 7 to 14 and explain the effect on stock coverage and purchase cost.
- Show the dirty run and the exact records rejected. Explain why the last validated report is preserved but must not be mistaken for today's success.
- Explain star-schema filter direction and why supplier-to-item relationships are omitted to avoid multiple supplier filter paths.
- Explain that the inventory snapshot and order history are independently generated demonstrations: they share identifiers but do not form a reconciled stock-movement ledger.
- Explain how an approved SAP export could map to these schemas. Do not claim SAP configuration, integration or production experience from this simulation.

## CV wording

Use only after reviewing and being able to explain the work yourself:

**Supply Chain Analytics & Reporting Automation — Excel, Python, Power BI project**

Developed an Excel inventory analysis covering 80 synthetic items and a Python validation pipeline for 1,500 purchase-order lines, with exception logging, BOM checks and quality-gated report output. Built and validated a Power BI model and supplier-performance report using Power Query and DAX.

Add a portfolio or repository link when published.

## References

- [Microsoft Power BI project format](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview)
- [Microsoft report definitions and PBIR](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report)
- [Microsoft semantic model project format](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset)

All numeric records are generated locally. The only external references are product-format documentation.
