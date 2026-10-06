# contentmytrip-site

The public website for Content My Trip LLP at https://www.contentmytrip.com — a static
showcase served by GitHub Pages while the full platform's cloud deployment is pending.

- `build.py` renders every page into `dist/` from `data/*.json`, `templates/legal/*.html`
  (the same Jinja templates the platform's auth-service serves at `/auth/terms` etc.),
  `templates/site.css` and `assets/`. It fails if any internal link is broken.
- `snapshot.sh` re-exports the data from the local platform stack (needs the compose stack
  running), after which new images under the containers' `/app/static/uploads` are copied
  into `assets/img/<kind>/<name>.jpg`.
- `.github/workflows/deploy.yml` builds and deploys `dist/` to GitHub Pages on every push
  to `main`. Generated HTML is not committed.

Local preview: `python3 build.py && python3 -m http.server -d dist 8765`
