// CLI uses the exact same validation and statistics as the admin page.
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { mergeExports, summarize, exportCSV } from "./review.mjs";
const here = path.dirname(fileURLToPath(import.meta.url));
const load = async (p) => JSON.parse(await readFile(p, "utf8"));
try {
  const files = process.argv.slice(2);
  if (!files.length)
    throw new Error("Pass one or more current human export JSON files.");
  const packet = await load(path.join(here, "output/packet.json"));
  const model = await load(path.join(here, "output/predictions.json"));
  if (model.packet_id !== packet.packet_id)
    throw new Error("Stale prediction packet.");
  const incoming = [];
  for (const file of files) {
    const body = await load(file);
    if (body.format === "longview-human-archive-v1") {
      if (body.packet_id !== packet.packet_id || !Array.isArray(body.exports))
        throw new Error("Stale or invalid archive.");
      incoming.push(...body.exports);
    } else incoming.push(body);
  }
  const exports = mergeExports([], incoming, packet);
  const summary = summarize(packet, exports, model.predictions);
  const destination = path.join(here, "human");
  await mkdir(destination, { recursive: true });
  const stamp = new Date().toISOString().replaceAll(":", "-");
  await writeFile(
    path.join(destination, `${stamp}.json`),
    JSON.stringify(
      {
        format: "longview-human-archive-v1",
        packet_id: packet.packet_id,
        exports,
      },
      null,
      2,
    ),
    { flag: "wx" },
  );
  await writeFile(
    path.join(destination, `${stamp}.csv`),
    exportCSV(packet, summary),
    { flag: "wx" },
  );
  const { items, ...stats } = summary;
  console.log(
    JSON.stringify(
      {
        validation_status: "unvalidated",
        population_accuracy: null,
        note: "Descriptive development agreement. No human reviewer is selected as ground truth.",
        ...stats,
      },
      null,
      2,
    ),
  );
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
