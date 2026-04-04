Pinned Ollama upstream releases (GitHub) for version parity with the Supermicro install.

Populate or refresh:

  cd ollama-hosting
  ./scripts/archive-ollama-release.sh

Optional: OLLAMA_VERSION=0.20.0 to skip SSH. Default: probe SUPER_OLLAMA_REMOTE (x@192.168.8.106) with `ollama --version`.

Artifacts per tag under vX.Y.Z/: ollama-linux-amd64.tar.zst, install.sh, sha256sum.txt, MANIFEST.json

Restore on a Linux amd64 host: extract the tarball so `bin/ollama` exists, or run the pinned install.sh from that directory per Ollama docs.
