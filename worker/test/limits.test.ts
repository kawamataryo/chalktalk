// 審査員用のトークン（#176）：期限と 1 日の上限
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import app, { type Env } from "../src/index";
import { consumeRelay, jstDay } from "../src/quota";
import { sha256Hex } from "../src/tokens";
import { useD1 } from "./helpers/d1";

const d1 = useD1();

function env(): Env {
  return {
    ANTHROPIC_API_KEY: "x",
    ELEVENLABS_API_KEY: "x",
    TYPESAFE_API_KEY: "x",
    FAMILY_TOKEN: "family-secret",
    ELEVENLABS_VOICE_ID: "x",
    DB: d1.db(),
  };
}

function send(method: string, path: string, token: string, body?: unknown) {
  return app.request(
    path,
    {
      method,
      headers: { "content-type": "application/json", Authorization: `Bearer ${token}` },
      body: body === undefined ? undefined : JSON.stringify(body),
    },
    env(),
  );
}

const claude = (token: string) => send("POST", "/v1/claude", token, { model: "claude-haiku-5-5", messages: [] });

async function addFamily(id: string, opts: { token: string; limit?: number | null; expiresAt?: string | null }) {
  const db = d1.db();
  await db.batch([
    db.prepare("INSERT INTO families (id, name, daily_relay_limit) VALUES (?, ?, ?)").bind(id, id, opts.limit ?? null),
    db
      .prepare("INSERT INTO family_tokens (token_hash, family_id, expires_at) VALUES (?, ?, ?)")
      .bind(await sha256Hex(opts.token), id, opts.expiresAt ?? null),
  ]);
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn(async () => Response.json({ ok: true }));
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("トークンの期限", () => {
  it("期限の前は通る", async () => {
    await addFamily("judge", { token: "judge-token", expiresAt: "2099-01-01T00:00:00.000Z" });
    expect((await claude("judge-token")).status).toBe(200);
  });

  it("期限を過ぎたトークンは 401 で、上流を呼ばない", async () => {
    await addFamily("judge", { token: "judge-token", expiresAt: "2020-01-01T00:00:00.000Z" });
    expect((await claude("judge-token")).status).toBe(401);
    expect((await send("GET", "/v1/sessions", "judge-token")).status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("期限のないトークン（今までの家族）はそのまま通る", async () => {
    await addFamily("home", { token: "home-token" });
    expect((await claude("home-token")).status).toBe(200);
  });
});

describe("1 日の上限", () => {
  it("上限までは通り、超えたら 429 で上流を呼ばない", async () => {
    await addFamily("judge", { token: "judge-token", limit: 2 });
    expect((await claude("judge-token")).status).toBe(200);
    expect((await send("POST", "/v1/tts", "judge-token", { text: "こんにちは" })).status).toBe(200);
    const over = await send("POST", "/v1/decide", "judge-token", {});
    expect(over.status).toBe(429);
    expect(await over.json()).toEqual({ error: "daily limit reached" });
    expect((await send("POST", "/v1/tts/azure", "judge-token", { text: "こんにちは" })).status).toBe(429);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("同期 API は数えず、上限を超えても使える", async () => {
    await addFamily("judge", { token: "judge-token", limit: 1 });
    for (let i = 0; i < 3; i++) {
      expect((await send("GET", "/v1/sessions", "judge-token")).status).toBe(200);
    }
    expect((await claude("judge-token")).status).toBe(200);
    expect((await claude("judge-token")).status).toBe(429);
    expect((await send("GET", "/v1/sessions", "judge-token")).status).toBe(200);
  });

  it("上限のない家族は数えない（relay_usage に行を作らない）", async () => {
    await addFamily("home", { token: "home-token" });
    for (let i = 0; i < 3; i++) expect((await claude("home-token")).status).toBe(200);
    expect((await claude("family-secret")).status).toBe(200);
    const { count } = (await d1.db().prepare("SELECT count(*) AS count FROM relay_usage").first<{ count: number }>())!;
    expect(count).toBe(0);
  });

  it("家族ごと・JST の日ごとに数える", async () => {
    const db = d1.db();
    await addFamily("a", { token: "a", limit: 1 });
    await addFamily("b", { token: "b", limit: 1 });
    // 2026-11-08 14:59Z は JST で 23:59、15:00Z は翌日の 0:00
    const before = new Date("2026-11-08T14:59:00Z");
    const after = new Date("2026-11-08T15:00:00Z");
    expect(jstDay(before)).toBe("2026-11-08");
    expect(jstDay(after)).toBe("2026-11-09");
    expect(await consumeRelay(db, "a", 1, before)).toBe(true);
    expect(await consumeRelay(db, "a", 1, before)).toBe(false);
    expect(await consumeRelay(db, "b", 1, before)).toBe(true);
    expect(await consumeRelay(db, "a", 1, after)).toBe(true);
  });
});
