## Git sync large-file cleanup

- Issue: `git push` rejected by GitHub `GH001` due to oversized tarballs under `agent-tools/graphcore-sdk/` and `agent-tools/graphcore-repo-tarballs/`.
- Action taken: created safety branch `backup/pre-largefile-clean`, then reset `master` to `origin/master` to remove local unpushed commits containing large blobs.
- Verification: `git rev-list --objects origin/master..HEAD` shows no tarballs in unpushed history; branch is no longer ahead of remote.
- Current state: prior local changes from the dropped commits are now present as working-tree changes/untracked files and can be recommitted selectively.
