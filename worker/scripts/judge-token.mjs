// 審査員用の家族とトークンを作る（#176）。
// わが家のデータには触れない別の家族を作り、期限と 1 日の上限つきのトークンを 1 つ発行する。
// トークンは標準出力にだけ出す。リポジトリ・issue・PR には書かず、提出フォームの審査員向けの欄にだけ書く。
//
//   node scripts/judge-token.mjs --expires 2026-12-31 --limit 300           # 本番（--remote）
//   node scripts/judge-token.mjs --expires 2026-12-31 --limit 300 --local   # wrangler dev のローカル D1
//   node scripts/judge-token.mjs --revoke                                   # 審査が終わったら消す
//
// --expires は JST のその日の終わりまで有効。--limit は中継（Claude・読み上げ・Jev）の 1 日の回数。
// 同じ家族で作り直すと、古いトークンは消える。

import { execFileSync } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parseArgs } from "node:util";

const FAMILY_ID = "judge";

const { values } = parseArgs({
  options: {
    expires: { type: "string" },
    limit: { type: "string", default: "300" },
    local: { type: "boolean", default: false },
    revoke: { type: "boolean", default: false },
  },
});

function d1(sql) {
  // SQL はファイルで渡す（トークンのハッシュをコマンドラインの履歴に残さない）
  const dir = mkdtempSync(join(tmpdir(), "judge-token-"));
  const file = join(dir, "judge.sql");
  try {
    writeFileSync(file, sql);
    execFileSync("npx", ["wrangler", "d1", "execute", "DB", values.local ? "--local" : "--remote", "--file", file], {
      stdio: ["ignore", "ignore", "inherit"],
    });
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

if (values.revoke) {
  // 家族ごと消す（トークン・回数・審査中の記録もまとめて消える）
  d1(`DELETE FROM families WHERE id = '${FAMILY_ID}';`);
  console.error("審査員用の家族とトークンを消しました");
  process.exit(0);
}

if (!values.expires || !/^\d{4}-\d{2}-\d{2}$/.test(values.expires)) {
  console.error("--expires YYYY-MM-DD を指定してください（JST のその日の終わりまで有効）");
  process.exit(1);
}
const limit = Number(values.limit);
if (!Number.isInteger(limit) || limit <= 0) {
  console.error("--limit は正の整数にしてください");
  process.exit(1);
}

// JST のその日の 23:59:59.999 を UTC にする
const expiresAt = new Date(new Date(`${values.expires}T23:59:59.999+09:00`).getTime()).toISOString();
// ダッシュボードで発行するトークンと同じ形（tokens.ts の issueFamilyToken）
const token = "ht_" + randomBytes(32).toString("base64url");
const hash = createHash("sha256").update(token).digest("hex");

d1(`
INSERT INTO families (id, name, daily_relay_limit) VALUES ('${FAMILY_ID}', '審査員', ${limit})
  ON CONFLICT (id) DO UPDATE SET daily_relay_limit = excluded.daily_relay_limit;
INSERT OR IGNORE INTO children (id, family_id, nickname, grade) VALUES ('judge-child', '${FAMILY_ID}', 'しんさいん', 5);
DELETE FROM family_tokens WHERE family_id = '${FAMILY_ID}';
INSERT INTO family_tokens (token_hash, family_id, expires_at) VALUES ('${hash}', '${FAMILY_ID}', '${expiresAt}');
`);

console.error(`審査員用のトークンを作りました（期限 ${values.expires} JST まで、1 日 ${limit} 回まで）`);
console.log(token);
