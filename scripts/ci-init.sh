#!/bin/sh
set -eu
: "${TF_STATE_BUCKET:?Set TF_STATE_BUCKET}"
: "${TF_LOCK_TABLE:?Set TF_LOCK_TABLE}"
: "${AWS_REGION:?Set AWS_REGION}"
: "${AWS_ROLE_ARN:?Set AWS_ROLE_ARN}"
: "${GITLAB_OIDC_TOKEN:?GitLab ID token required}"
umask 077
export AWS_WEB_IDENTITY_TOKEN_FILE="$(mktemp)"
printf '%s' "$GITLAB_OIDC_TOKEN" > "$AWS_WEB_IDENTITY_TOKEN_FILE"
trap 'rm -f "$AWS_WEB_IDENTITY_TOKEN_FILE"' EXIT HUP INT TERM
export AWS_ROLE_SESSION_NAME="gitlab-${CI_PROJECT_ID}-${CI_PIPELINE_ID}"
terraform -chdir=infra init -input=false -lockfile=readonly   -backend-config="bucket=$TF_STATE_BUCKET"   -backend-config="key=project26/terraform.tfstate"   -backend-config="region=$AWS_REGION"   -backend-config="dynamodb_table=$TF_LOCK_TABLE"   -backend-config="encrypt=true"
# Execute within this process so the temporary token exists through the command.
terraform -chdir=infra "$@"
