# Phase 39 — Versioned container releases

## Release workflow

A version tag matching vMAJOR.MINOR.PATCH triggers the release image workflow. It builds and publishes two images to GitHub Container Registry:

- ghcr.io/hashir1191/timedrop-api
- ghcr.io/hashir1191/timedrop-web

Each image receives semantic-version and latest tags. The workflow also publishes image labels, an SBOM, and build provenance. It uses the repository-scoped GITHUB_TOKEN with packages: write; no long-lived registry password is stored in GitHub secrets.

The workflow publishes images only. It does not deploy to a server or modify a database.

## Create a release

1. Merge the intended changes into main and confirm the CI suite is green.
2. Create and push an annotated version tag, for example:

~~~bash
git checkout main
git pull origin main
git tag -a v1.0.0 -m "TimeDrop v1.0.0"
git push origin v1.0.0
~~~

3. Follow the TimeDrop Release Images workflow in GitHub Actions.
4. Confirm both API and web images exist in the repository's Packages page and include the expected version tag and build attestations.

Do not reuse an existing version tag for different source code. Publish a new patch version instead.

## Deploy a published version

Authenticate the deployment host to GitHub Container Registry if the packages are private. Set explicit version tags in the production .env file:

~~~dotenv
TIMEDROP_API_IMAGE=ghcr.io/hashir1191/timedrop-api:1.0.0
TIMEDROP_WEB_IMAGE=ghcr.io/hashir1191/timedrop-web:1.0.0
~~~

Then run:

~~~bash
docker compose --env-file .env -f docker-compose.production.yml config
docker compose --env-file .env -f docker-compose.production.yml pull
docker compose --env-file .env -f docker-compose.production.yml up -d
docker compose --env-file .env -f docker-compose.production.yml ps
~~~

The API image applies database migrations at startup. Keep a verified backup and the single-API-replica constraint from Phase 34. Confirm API and web readiness before reopening traffic.

## Rollback

Pin both image variables to the previous known-good release and pull/up again. A container rollback does not automatically reverse database migrations. Review migration compatibility before deploying; if a migration is not backward-compatible, follow the approved database recovery procedure rather than assuming an image rollback is sufficient.

## Security and scope

- Release publishing uses GitHub's short-lived workflow token; no PAT is required.
- Keep the registry packages private until the project owner deliberately chooses a public distribution model.
- Do not put secrets into Docker build arguments or image layers.
- Use explicit semantic-version tags in production. The latest tag is convenient for discovery but is mutable and should not be the production pin.
- The workflow does not provision a host, DNS, TLS, secrets manager, or cloud deployment target.
