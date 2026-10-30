import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [workbookPath, sheetName, range, outputPath] = process.argv.slice(2);
if (!workbookPath || !sheetName || !range || !outputPath) {
  throw new Error("Usage: node render_workbook_range.mjs WORKBOOK.xlsx SHEET RANGE OUTPUT.png");
}

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(workbookPath));
const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
await fs.writeFile(outputPath, new Uint8Array(await preview.arrayBuffer()));
