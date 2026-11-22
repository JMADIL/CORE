# Core frontend

Next.js App Router application with shadcn/ui (Base UI / Nova) with a neutral, minimal layout and light, dark, and system themes. From this directory:

```sh
npm ci
npm run dev
npm run lint
npm run typecheck
npm test
npm run build
```

- `app/`: route composition, global styles, and page metadata.
- `components/`: chat UI components.
- `components/ui/`: editable shadcn primitives, configured in `components.json`.
- `hooks/`: React streaming and conversation state.
- `lib/`: API requests, SSE parsing, and browser history utilities.
- `types/`: shared chat data types, independent of hooks and storage.
- `tests/`: offline stream and history regressions.
- `public/`: assets shipped to browsers.

The default API path `/backend` is proxied to `http://127.0.0.1:8000`.
Set `API_PROXY_URL` before starting development or building to change that target,
or `NEXT_PUBLIC_API_URL` at build time for a separately hosted backend.

See the [project README](../README.md) for backend setup and Docker configuration.

Add additional shadcn components from this directory with `npx shadcn@latest add <component>`.
Theme tokens live in `app/globals.css`. The scoped minimatch override keeps the
shadcn CLI’s ts-morph dependency on its patched matcher; it does not change chat behavior.
