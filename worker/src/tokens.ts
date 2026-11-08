// D1 に保存する家族トークン（ダッシュボードで発行・再発行する）。
// トークンは 32 バイトの乱数なので、保存はソルトなしの SHA-256 で十分（総当たりできない）。

export async function sha256Hex(s: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// 新しいトークンを発行し、その家族の古いトークンは消す。平文を返すのはこのときだけ
export async function issueFamilyToken(db: D1Database, familyId: string): Promise<string> {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  const token = "ht_" + base64url(bytes);
  await db.batch([
    db.prepare("DELETE FROM family_tokens WHERE family_id = ?").bind(familyId),
    db
      .prepare("INSERT INTO family_tokens (token_hash, family_id) VALUES (?, ?)")
      .bind(await sha256Hex(token), familyId),
  ]);
  return token;
}

export type TokenFamily = {
  familyId: string;
  // 中継を 1 日に何回まで呼べるか。null なら上限なし
  dailyRelayLimit: number | null;
};

// 期限の切れたトークンは見つからない扱いにする。上限も同じ 1 回の検索で引く（会話の速さを落とさない）
export async function familyForToken(db: D1Database, token: string): Promise<TokenFamily | null> {
  const row = await db
    .prepare(
      `SELECT t.family_id, f.daily_relay_limit FROM family_tokens t JOIN families f ON f.id = t.family_id
       WHERE t.token_hash = ? AND (t.expires_at IS NULL OR t.expires_at > strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))`,
    )
    .bind(await sha256Hex(token))
    .first<{ family_id: string; daily_relay_limit: number | null }>();
  return row ? { familyId: row.family_id, dailyRelayLimit: row.daily_relay_limit ?? null } : null;
}

export async function currentTokenIssuedAt(db: D1Database, familyId: string): Promise<string | null> {
  const row = await db
    .prepare("SELECT created_at FROM family_tokens WHERE family_id = ? ORDER BY created_at DESC LIMIT 1")
    .bind(familyId)
    .first<{ created_at: string }>();
  return row?.created_at ?? null;
}

export function base64url(bytes: Uint8Array): string {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
