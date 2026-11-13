# Console sign in and roles

The console has two modes, set with `CTI_AUTH` when the backend starts.

- **`off`** (the default): one person on this machine, who may do everything. Nothing on
  this page applies.
- **`oidc`**: people sign in with Entra ID or Cognito, and see and change only what their
  role allows.

## Roles

Roles come from groups (Cognito) or app roles (Entra ID), named like this:

| Group or app role | May |
|---|---|
| `cti-platform-admin` | See every company, change any company, add companies |
| `cti-admin-<slug>` | See that company, and change its branding and stakeholders |
| `cti-viewer-<slug>` | See that company: reports, runs, CVEs, stakeholders, branding |

`<slug>` is the company's short name, such as `cti-admin-genelabs`. Someone can hold
several. Someone with none sees "Your account has no company yet". A change of group at
the provider applies at that person's next sign in. A session lasts 8 hours
(`CTI_SESSION_HOURS`).

Each signed in person keeps their own shown company, so one person switching never
changes what another sees. The page offers only what the role allows, and the backend
refuses everything else.

## How sign in works

The backend runs the OpenID Connect authorization code flow with PKCE itself. The provider
sends the browser back to `<console>/api/auth/callback`; the backend checks the ID token
(signature against the provider's published keys, issuer, audience, expiry and nonce),
keeps only the `cti-` groups, and sets a signed, HttpOnly session cookie. The page never
holds a token.

## Settings

| Variable | Example | Meaning |
|---|---|---|
| `CTI_AUTH` | `oidc` | Turn sign in on |
| `CTI_OIDC_ISSUER` | see below | The provider's issuer URL |
| `CTI_OIDC_CLIENT_ID` | see below | The app's client ID |
| `CTI_OIDC_CLIENT_SECRET` | from the provider | The app's client secret. Keep it in a vault or your shell, never in the repo |
| `CTI_OIDC_GROUPS_CLAIM` | `roles` or `cognito:groups` | Which ID token claim holds the groups |
| `CTI_SESSION_SECRET` | 48 random characters | Signs the session cookie. At least 32 characters |
| `CTI_CONSOLE_URL` | `http://localhost:5173` | The page's address, where the provider sends people back |
| `CTI_OIDC_ROLE_PREFIX` | `cti-` | The prefix the role names above start with |

Make a session secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Changing it signs everyone out.

## Entra ID

1. In the Entra admin center, open **App registrations, New registration**. Pick the
   **Web** platform and set the redirect URI to `http://localhost:5173/api/auth/callback`
   (Entra accepts plain http only for localhost).
2. Under **Certificates and secrets**, add a client secret.
3. Under **App roles**, add one role per row of the table above that you need, with the
   role name as its **Value**, for example `cti-platform-admin` and `cti-admin-genelabs`.
4. In **Enterprise applications**, open the app, then **Users and groups**, and assign
   people or groups to those roles.
5. Start the console with:
   - `CTI_OIDC_ISSUER=https://login.microsoftonline.com/<tenant id>/v2.0`
   - `CTI_OIDC_CLIENT_ID=<application (client) id>`
   - `CTI_OIDC_CLIENT_SECRET=<the secret>`
   - `CTI_OIDC_GROUPS_CLAIM=roles`
   - `CTI_CONSOLE_URL=http://localhost:5173`

   Then open the console at `http://localhost:5173`.

Sign out also signs out at Entra, when `http://localhost:5173` is registered as a redirect
URI too.

## Cognito

1. In a user pool, add a domain, then an app client with a client secret. Allow the
   authorization code grant and the `openid`, `profile` and `email` scopes. Set the
   callback URL to `http://localhost:5173/api/auth/callback` (Cognito accepts plain http
   only for localhost).
2. Under **Groups**, add the groups you need from the table above, and add users to them.
3. Start the console with:
   - `CTI_OIDC_ISSUER=https://cognito-idp.<region>.amazonaws.com/<user pool id>`
   - `CTI_OIDC_CLIENT_ID=<app client id>`
   - `CTI_OIDC_CLIENT_SECRET=<the secret>`
   - `CTI_OIDC_GROUPS_CLAIM=cognito:groups`
   - `CTI_CONSOLE_URL=http://localhost:5173`

Sign out ends the console session. Cognito does not publish a sign out page in its
discovery document, so its own session stays until it expires, and the next sign in may
not ask for a password.

## Sharing it

The console listens on this machine only. To let others reach it, share it through a dev
tunnel with `scripts/console-share.ps1`: see `docs/console-share.md`. With an `https://`
`CTI_CONSOLE_URL`, the cookies are marked Secure. Hosting it in a cloud is a later step.
