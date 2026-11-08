-- 審査員用のトークン（#176）。漏れても被害が小さくなるよう、期限と 1 日の上限を持てるようにする
-- expires_at は UTC の ISO 8601。NULL なら期限なし（今までの家族はこのまま）
ALTER TABLE family_tokens ADD COLUMN expires_at TEXT;
-- 中継（Claude・読み上げ・Jev）を 1 日に何回まで呼べるか。NULL なら上限なし
ALTER TABLE families ADD COLUMN daily_relay_limit INTEGER;
-- 中継を呼んだ回数。day は JST の日付（例 2026-11-08）。上限のある家族だけ数える
CREATE TABLE relay_usage (
  family_id TEXT NOT NULL REFERENCES families(id) ON DELETE CASCADE,
  day TEXT NOT NULL,
  count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (family_id, day)
);
