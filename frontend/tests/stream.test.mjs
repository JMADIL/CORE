import { test } from "node:test";
import assert from "node:assert/strict";
import { completedText, readSSE } from "../lib/sse.ts";
import { parseSessions, mergeSession } from "../lib/history.ts";

function response(chunks) {
  const encoder = new TextEncoder();
  return new Response(new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(typeof chunk === "string" ? encoder.encode(chunk) : chunk);
      controller.close();
    },
  }), { headers: { "Content-Type": "text/event-stream" } });
}

test('final answers recover missing tokens and replace partial text without duplication', () => {
  assert.equal(completedText('', 'Image ready.'), 'Image ready.');
  assert.equal(completedText('Image', 'Image ready.'), 'Image ready.');
  assert.equal(completedText('Image ready.', 'Image ready.'), 'Image ready.');
  assert.equal(completedText('Legacy stream', undefined), 'Legacy stream');
  assert.throws(() => completedText('', undefined), /without returning an answer/);
  assert.throws(() => completedText('Partial', ''), /without returning an answer/);
  assert.throws(() => completedText('', {}), /Invalid final answer/);
});
async function collect(chunks) {
  return Array.fromAsync(readSSE(response(chunks), new AbortController().signal));
}

test("parses fragmented CRLF events and multiline JSON", async () => {
  const result = await collect(['event: token\r', '\ndata: {\r\ndata: "token":"hello"}\r\n\r', '\nevent: done\r\ndata: {}\r\n\r\n']);
  assert.deepEqual(result, [{ event: "token", data: { token: "hello" } }, { event: "done", data: {} }]);
});
test("preserves multibyte unicode split across network reads", async () => {
  const bytes = new TextEncoder().encode('event: token\ndata: {"token":"☀"}\n\nevent: done\ndata: {}\n\n');
  const result = await collect(Array.from(bytes, byte => new Uint8Array([byte])));
  assert.equal(result[0].data.token, "☀");
});
test("accepts CR-only framing at EOF", async () => {
  assert.equal((await collect(['event: done\rdata: {}\r\r']))[0].event, "done");
});
test("rejects an oversized event even when it ends in the same chunk", async () => {
  await assert.rejects(collect(['event: token\ndata: {"token":"' + 'x'.repeat(1_000_001) + '"}\n\n']), /too large/);
});
test("fails on unexpected EOF instead of leaving a pending response", async () => {
  await assert.rejects(collect(['event: token\ndata: {"token":"partial"}\n\n']), /ended unexpectedly/);
});
test("fails on malformed JSON", async () => {
  await assert.rejects(collect(['event: token\ndata: INVALID\n\n']), SyntaxError);
});
test("returns server errors as terminal events", async () => {
  const events = await collect(['event: error\ndata: {"detail":"failed"}\n\n']);
  assert.equal(events[0].event, "error");
});
test("rejects non-SSE responses", async () => {
  await assert.rejects(Array.fromAsync(readSSE(new Response("error"), new AbortController().signal)), /event stream/);
});
test("abort cancels a stalled reader", async () => {
  const controller = new AbortController();
  const source = new Response(new ReadableStream({ start() {} }), { headers: { "Content-Type": "text/event-stream" } });
  const pending = Array.fromAsync(readSSE(source, controller.signal));
  controller.abort();
  await assert.rejects(pending, { name: "AbortError" });
});
test("invalid storage is discarded and valid old sessions migrate", () => {
  for (const raw of ['{', '{}', 'null', '[null, {"id":"x","messages":[null]}]']) {
    assert.doesNotThrow(() => parseSessions(raw));
  }
  const old = [{ id: "old", messages: [{ id: "m", role: "user", content: "hello" }] }];
  assert.deepEqual(parseSessions(JSON.stringify(old))[0].messages[0].thoughts, []);
});
test("active thread merge preserves other threads without mutating storage", () => {
  const saved = [{ id: "old", title: "Old", createdAt: 1, updatedAt: 1, messages: [] }];
  const result = mergeSession(saved, "new", [{ id: "m", role: "user", content: "hello", thoughts: [], timestamp: 2 }]);
  assert.equal(result[0].id, "new");
  assert.equal(result[1].id, "old");
  assert.equal(saved.length, 1);
});

test("limit notices survive history reload without becoming response text", () => {
  const error = "We've reached our AI model's daily usage limit.";
  const saved = mergeSession([], "limited", [{ id: "m", role: "assistant", content: "", error, thoughts: [] }]);
  const restored = parseSessions(JSON.stringify(saved))[0].messages[0];
  assert.equal(restored.error, error);
  assert.equal(restored.content, "");
  const invalid = [{ id: "limited", messages: [{ id: "m", role: "assistant", content: "", error: { private: "invalid" } }] }];
  assert.equal(parseSessions(JSON.stringify(invalid))[0].messages[0].error, undefined);
});
