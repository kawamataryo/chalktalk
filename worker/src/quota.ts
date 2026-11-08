// 中継（Claude・読み上げ・Jev）の 1 日の上限（#176）。
// 審査員用のトークンのように、上限のある家族だけ数える。上限のない家族（わが家）はクエリを増やさない。

// JST の日付（例 2026-11-08）。日本の家庭で使うので、日付の区切りは JST にする
export function jstDay(now: Date = new Date()): string {
  return new Date(now.getTime() + 9 * 60 * 60 * 1000).toISOString().slice(0, 10);
}

// 1 回ぶん数えて、上限の内なら true。数えるのと比べるのを 1 文にして、同時に呼ばれても数えもれしない
export async function consumeRelay(db: D1Database, familyId: string, limit: number, now: Date = new Date()): Promise<boolean> {
  const row = await db
    .prepare(
      `INSERT INTO relay_usage (family_id, day, count) VALUES (?, ?, 1)
       ON CONFLICT (family_id, day) DO UPDATE SET count = count + 1
       RETURNING count`,
    )
    .bind(familyId, jstDay(now))
    .first<{ count: number }>();
  return (row?.count ?? Infinity) <= limit;
}
