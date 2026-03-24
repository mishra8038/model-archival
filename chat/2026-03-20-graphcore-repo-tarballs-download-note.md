## Graphcore Org Repo Tarballs Download

- Date: 2026-03-20
- User requested downloading all available projects from:
  - https://github.com/orgs/graphcore/repositories
  - https://github.com/orgs/graphcore-research/repositories
- Initial run to `agent-tools/graphcore-repo-tarballs` was stopped on user request.
- Active run started to workspace path:
  - `d5/graphcore-projects`
- Download method:
  - Enumerate public repos via `gh api --paginate orgs/<org>/repos`
  - Download each tarball via `https://api.github.com/repos/<owner>/<repo>/tarball`
  - Output naming: `<owner>__<repo>.tar.gz`
  - Tracks failures in `failed.txt`
- Current observed total repos: 138
