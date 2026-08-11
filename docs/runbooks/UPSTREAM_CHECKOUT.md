# Runbook — DevilutionX-Checkout

1. `upstream.lock.toml` lesen.
2. Fetch-Skript ausführen.
3. `git -C third_party/DevilutionX status --short` muss leer sein.
4. `git rev-parse HEAD` muss dem Lock entsprechen.
5. Upstream-Lizenz erneut lesen.
6. Ohne Assets einen Sourcebuild/Testbuild versuchen; Assets nie committen.
7. Integrationsänderungen auf eigenem Branch.
