# Share the console from this PC

`scripts/console-share.ps1` puts the console on a public HTTPS address through a
Microsoft dev tunnel, with sign in on. Nothing moves to a cloud: the console reads the
reports on this PC, as it does locally, and the branded PDF view keeps working because
Word is here. The address works only while the script runs and this PC is on.

## What protects it

- **Sign in is required.** The script always starts the console with `CTI_AUTH=oidc`, so
  everyone signs in with Entra ID (or Cognito) and sees only what their role allows. See
  `docs/console-sign-in.md` for the roles.
- **The local console cannot be shared by mistake.** With sign in off, the console refuses
  any request that came through a proxy or tunnel, so running `devtunnel host` next to the
  everyday console shows visitors a refusal, not your reports.
- **The tunnel can be a second lock.** Dev tunnels can admit only your own Entra tenant
  before the console is even reached (step 4).
- **HTTPS end to end for visitors.** The tunnel terminates TLS 1.2 or later; the hop from
  the tunnel client to the console stays on this PC.

## One time setup

1. Install the tunnel client and sign in to it with your Microsoft account:

   ```bash
   winget install Microsoft.devtunnel
   ```

   ```bash
   devtunnel user login
   ```

2. Create a persistent tunnel. Let it pick the ID: a random ID is harder to find than a
   name.

   ```bash
   devtunnel create
   ```

   Note the tunnel ID it prints.

3. Add the console's port:

   ```bash
   devtunnel port create <tunnel id> -p 8765 --protocol http
   ```

4. Choose who may reach the sign in page:
   - Only people in your Entra tenant (two locks; they sign in to the tunnel, then to the
     console):

     ```bash
     devtunnel access create <tunnel id> --tenant
     ```

   - Anyone, with the console's own sign in as the lock (needed for people outside your
     tenant, such as a customer's staff):

     ```bash
     devtunnel access create <tunnel id> --anonymous
     ```

5. Find the tunnel's address for port 8765, of the form
   `https://<tunnel id>-8765.<region>.devtunnels.ms`:

   ```bash
   devtunnel show <tunnel id>
   ```

6. In your Entra ID app registration (see `docs/console-sign-in.md`), add two redirect
   URIs: that address followed by `/api/auth/callback`, and the address alone (so sign out
   returns to the console).

7. Copy `.env.console.example` to `.env.console` at the repo root and fill it in: the
   tunnel ID, the address from step 5 as `CTI_CONSOLE_URL`, the app's issuer, client ID and
   secret, and a session secret. Git ignores `.env.console`; keep it on this PC only.

## Each time

Stop the everyday console first, if it is running (Ctrl+C in its window). Then:

```bash
powershell -ExecutionPolicy Bypass -File scripts/console-share.ps1
```

The script builds the page if needed, starts the console with sign in on, renews the
tunnel for another 30 days, and hosts it. It prints the address to share. Ctrl+C stops the
tunnel and the console together.

The first time someone opens the address, Dev Tunnels shows its own warning page about
visiting a tunnel; they continue once, then see the sign in page.

## Limits

- **Only while this PC is on** and the script runs. Sleep or a restart takes it down.
- **Dev Tunnels is a preview service** with no uptime promise. It suits demos and a few
  colleagues, not a customer's daily use; hosting in a cloud is the route for that.
- **A persistent tunnel lasts at most 30 days.** Each start renews it, so it only lapses
  after 30 days unused; then run step 2 onward again and update `.env.console` and the
  redirect URIs.
- **Everyone shares this PC's console:** one Word for PDFs and this PC's disk and network.
