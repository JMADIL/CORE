import { test } from "node:test";
import assert from "node:assert/strict";
import { responseWords } from "../lib/responseWords.ts";

test("word animation preserves whitespace, Unicode, and formatted text", () => {
  const tree = {
    type: "root",
    children: [{
      type: "element", tagName: "p", children: [
        { type: "text", value: "Hello  مرحبا\n" },
        { type: "element", tagName: "strong", children: [{ type: "text", value: "bold text" }] },
      ],
    }],
  };
  responseWords()(tree);
  const text = node => node.type === "text" ? node.value : node.children.map(text).join("");
  assert.equal(text(tree), "Hello  مرحبا\nbold text");
  assert.equal(tree.children[0].children[0].properties.className[0], "response-word");
  assert.equal(tree.children[0].children.at(-1).tagName, "strong");
});

test("inline and fenced code remain untouched", () => {
  const tree = { type: "root", children: [
    { type: "element", tagName: "code", children: [{ type: "text", value: "const x = 1;" }] },
    { type: "element", tagName: "pre", children: [{ type: "element", tagName: "code", children: [{ type: "text", value: "a\n  b" }] }] },
  ] };
  const before = structuredClone(tree);
  responseWords()(tree);
  assert.deepEqual(tree, before);
});
