## Roleplay Frontend Source

This folder is now the maintained React source for the roleplay screen.
It started as an imported prototype, but it is now part of the implementation.

## Workflow

- Install dependencies with `npm.cmd install`
- Run local development with `npm.cmd run dev`
- Export the production bundle with `npm.cmd run build`

## Build Output

The Vite build is configured to write directly to:

- `backend/static/roleplay-app/roleplay-app.js`
- `backend/static/roleplay-app/roleplay-app.css`

Those generated files are the Django-served bundle used by `roleplay.html`.
