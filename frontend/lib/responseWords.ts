interface TextTree {
  type: string;
  tagName?: string;
  value?: string;
  properties?: Record<string, unknown>;
  children?: TextTree[];
}

// Keep word positions stable between streamed updates so existing text does
// not animate again. Preserve code blocks and inline code exactly as rendered.
export function responseWords() {
  return function transform(tree: TextTree) {
    function visit(node: TextTree) {
      if (!node.children || node.tagName === "code" || node.tagName === "pre")
        return;
      node.children = node.children.flatMap((child) => {
        if (child.type !== "text" || !child.value) {
          visit(child);
          return [child];
        }
        return (child.value.match(/\s+|\S+/gu) || []).map((value) =>
          /^\s+$/u.test(value)
            ? { type: "text", value }
            : {
                type: "element",
                tagName: "span",
                properties: { className: ["response-word"] },
                children: [{ type: "text", value }],
              },
        );
      });
    }
    visit(tree);
  };
}
