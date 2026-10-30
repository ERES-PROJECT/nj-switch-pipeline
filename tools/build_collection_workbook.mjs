import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [inputDir, outputDir, outputName = "20260917_all_current_scrapers_tables.xlsx"] = process.argv.slice(2);
if (!inputDir || !outputDir) throw new Error("Usage: node build_collection_workbook.mjs INPUT_DIR OUTPUT_DIR");

const specs = [
  { file: "offer_prices.csv", sheet: "Offer Prices", table: "OfferPricesTable", color: "#1F4E78" },
  { file: "contract_information.csv", sheet: "Contract Information", table: "ContractInformationTable", color: "#548235" },
  { file: "offer_documents.csv", sheet: "Offer Documents", table: "OfferDocumentsTable", color: "#8064A2" },
  { file: "coverage.csv", sheet: "Coverage", table: "CoverageTable", color: "#C65911" },
  { file: "offer_observations.csv", sheet: "Offer Observations", table: "OfferObservationsTable", color: "#7F8C8D" },
];

const numericHeaders = new Set([
  "rate", "term_months", "monthly_fee", "enrollment_fee",
  "cancellation_fee", "intro_rate", "intro_duration_months", "intro_duration_billing_cycles",
  "renewable_percentage", "document_count", "matched_offer_count", "contract_rate",
  "contract_term_months", "missing_section_count", "offers", "documents", "zip_count",
  "observation_count",
]);
const decimalHeaders = new Set([
  "rate", "rate_cents_per_unit", "monthly_fee", "enrollment_fee", "cancellation_fee",
  "intro_rate", "contract_rate",
]);
const booleanHeaders = new Set(["context_verified", "canonical_observation", "retryable"]);
const dateHeaders = new Set(["captured_at"]);
const textHeaders = new Set([
  "test_zip", "zip", "observed_zip_codes", "offer_fingerprint", "offer_key", "source_offer_keys",
  "product_id", "contract_id", "matched_offer_fingerprints", "matched_offer_keys", "artifact_id",
  "market_key",
]);
const zipHeaders = new Set(["test_zip", "zip", "observed_zip_codes"]);
const longTextHeaders = new Set([
  "renewable_details", "deals_and_incentives", "missing_sections", "warnings", "errors",
  "supplier_information", "price_structure", "supply_price", "savings", "switching_time",
  "incentives", "rescission", "start_date", "term", "cancellation", "renewal",
  "distribution_company", "source_urls",
]);

function columnName(number) {
  let value = number;
  let name = "";
  while (value > 0) {
    value -= 1;
    name = String.fromCharCode(65 + (value % 26)) + name;
    value = Math.floor(value / 26);
  }
  return name;
}

function typedMatrix(matrix) {
  const headers = matrix[0].map(value => String(value).replace(/^\uFEFF/, ""));
  const rows = matrix.slice(1).map(row => row.map((value, index) => {
    const header = headers[index];
    if (value === null || value === undefined || value === "") return null;
    if (textHeaders.has(header)) {
      const text = String(value);
      if ((header === "test_zip" || header === "zip" || header === "observed_zip_codes") && /^\d{1,5}$/.test(text)) {
        return text.padStart(5, "0");
      }
      return text;
    }
    if (numericHeaders.has(header)) {
      const number = Number(value);
      return Number.isFinite(number) ? number : value;
    }
    if (booleanHeaders.has(header)) return String(value).toLowerCase() === "true";
    if (dateHeaders.has(header)) {
      const date = new Date(value);
      return Number.isNaN(date.valueOf()) ? value : date;
    }
    return value;
  }));
  return [headers, ...rows];
}

function widthFor(header) {
  if (["tps", "supplier", "edc_gdc", "utility", "plan_name", "matched_plan_names"].includes(header)) return 24;
  if (["offer_key", "contract_id"].includes(header)) return 24;
  if (["product_id", "document_kind", "parse_status", "match_method", "plan_type", "duplicate_status", "same_rate_status", "resolution_type"].includes(header)) return 22;
  if (["offer_fingerprint", "source_offer_keys", "matched_offer_fingerprints"].includes(header)) return 28;
  if (["source_url", "contract_url", "source_urls"].includes(header)) return 42;
  if (longTextHeaders.has(header)) return 36;
  if (["captured_at"].includes(header)) return 22;
  return 15;
}

const workbook = Workbook.create();
await fs.mkdir(outputDir, { recursive: true });

for (const spec of specs) {
  const csvText = await fs.readFile(path.join(inputDir, spec.file), "utf8");
  const imported = await Workbook.fromCSV(csvText, { sheetName: "Imported" });
  const matrix = typedMatrix(imported.worksheets.getItem("Imported").getUsedRange().values);
  const sheet = workbook.worksheets.add(spec.sheet);
  sheet.showGridLines = false;
  sheet.tabColor = spec.color;
  sheet.getRange("A1").write(matrix);

  const rowCount = matrix.length;
  const columnCount = matrix[0].length;
  const lastColumn = columnName(columnCount);
  const used = sheet.getRange(`A1:${lastColumn}${rowCount}`);
  used.format.font = { name: "Aptos", size: 10, color: "#222222" };
  used.format.verticalAlignment = "center";
  used.format.wrapText = false;
  used.format.borders = { preset: "inside", style: "thin", color: "#E7E6E6" };

  const header = sheet.getRange(`A1:${lastColumn}1`);
  header.format.fill = spec.color;
  header.format.font = { name: "Aptos Display", size: 10, bold: true, color: "#FFFFFF" };
  header.format.rowHeight = 28;
  header.format.wrapText = true;

  matrix[0].forEach((name, index) => {
    const column = sheet.getRange(`${columnName(index + 1)}1:${columnName(index + 1)}${rowCount}`);
    column.format.columnWidth = widthFor(name);
    if (numericHeaders.has(name) && rowCount > 1) {
      const body = sheet.getRange(`${columnName(index + 1)}2:${columnName(index + 1)}${rowCount}`);
      body.format.numberFormat = decimalHeaders.has(name) ? "0.0000" : "0";
    }
    if (textHeaders.has(name) && rowCount > 1) {
      sheet.getRange(`${columnName(index + 1)}2:${columnName(index + 1)}${rowCount}`).format.numberFormat = zipHeaders.has(name) ? "00000" : "@";
    }
    if (dateHeaders.has(name) && rowCount > 1) {
      sheet.getRange(`${columnName(index + 1)}2:${columnName(index + 1)}${rowCount}`).format.numberFormat = "yyyy-mm-dd hh:mm";
    }
  });

  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(spec.sheet === "Coverage" ? 2 : 4);
  const table = sheet.tables.add(`A1:${lastColumn}${rowCount}`, true, spec.table);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;

  if (spec.sheet === "Coverage" && rowCount > 1) {
    const statusIndex = matrix[0].indexOf("status") + 1;
    const statusRange = sheet.getRange(`${columnName(statusIndex)}2:${columnName(statusIndex)}${rowCount}`);
    statusRange.conditionalFormats.add("containsText", { text: "failed", format: { fill: "#F4CCCC", font: { color: "#9C0006", bold: true } } });
    statusRange.conditionalFormats.add("containsText", { text: "blocked", format: { fill: "#FCE5CD", font: { color: "#9C6500" } } });
    statusRange.conditionalFormats.add("containsText", { text: "partial", format: { fill: "#FFF2CC", font: { color: "#7F6000" } } });
    statusRange.conditionalFormats.add("containsText", { text: "empty", format: { fill: "#D9EAD3", font: { color: "#274E13" } } });
    statusRange.conditionalFormats.add("containsText", { text: "unsupported", format: { fill: "#D9D2E9", font: { color: "#351C75" } } });
  }
  if ((spec.sheet === "Offer Prices" || spec.sheet === "Offer Observations") && rowCount > 1) {
    const duplicateIndex = matrix[0].indexOf("duplicate_status") + 1;
    const duplicateRange = sheet.getRange(`${columnName(duplicateIndex)}2:${columnName(duplicateIndex)}${rowCount}`);
    duplicateRange.conditionalFormats.add("containsText", { text: "consolidated_across_zips", format: { fill: "#FFF2CC", font: { color: "#7F6000", bold: true } } });
    const commodityIndex = matrix[0].indexOf("commodity");
    const firstGasOffset = matrix.slice(1).findIndex(row => String(row[commodityIndex]).toLowerCase() === "gas");
    if (firstGasOffset >= 0) {
      const firstGasRow = firstGasOffset + 2;
      const separator = sheet.getRange(`A${firstGasRow}:${lastColumn}${firstGasRow}`);
      separator.format.borders = { top: { style: "thick", color: "#C65911" } };
      separator.format.fill = "#FCE4D6";
    }
  }
}

workbook.recalculate();
const inspection = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 8000,
  tableMaxRows: 4,
  tableMaxCols: 8,
  tableMaxCellChars: 60,
});
console.log(inspection.ndjson);

for (const spec of specs) {
  const preview = await workbook.render({ sheetName: spec.sheet, range: "A1:L25", scale: 1, format: "png" });
  await fs.writeFile(path.join(outputDir, `${spec.file.replace(".csv", "")}_preview.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(path.join(outputDir, outputName));
