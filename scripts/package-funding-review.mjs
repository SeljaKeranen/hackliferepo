import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { createCipheriv, randomBytes, createHash } from "node:crypto";
const body = readFileSync("data/funding/review-packet.json", "utf8");
const packet = JSON.parse(body);
if (packet.records.some((r) => "abstract" in r || r.classification !== null))
  throw Error("Reviewer records must be blinded and contain no raw abstracts");
mkdirSync("outputs", { recursive: true });
mkdirSync("public/review/funding", { recursive: true });
const path = "outputs/funding-reviewer.key";
const key = existsSync(path)
  ? Buffer.from(readFileSync(path, "utf8").trim(), "base64url")
  : randomBytes(32);
writeFileSync(path, key.toString("base64url"), { mode: 0o600 });
const iv = randomBytes(12),
  cipher = createCipheriv("aes-256-gcm", key, iv);
const encrypted = Buffer.concat([
  cipher.update(body),
  cipher.final(),
  cipher.getAuthTag(),
]);
writeFileSync(
  "public/review/funding/packet.json",
  JSON.stringify({
    id: createHash("sha256").update(body).digest("hex").slice(0, 16),
    iv: iv.toString("base64"),
    ciphertext: encrypted.toString("base64"),
  }),
);
console.log(
  `Encrypted funding packet: ${packet.records.length} blinded source records. Key remains in ignored outputs/funding-reviewer.key.`,
);
