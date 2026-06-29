# Arcade Deployment Guide

> TODO: Document during Phase 11 (Deployment & Packaging) or when deploying to production.
>
> Key topics: PyInstaller packaging, Electron builder, installation on client machines, license activation workflow, hardware requirements.

## Security — `arcade.config.json` Permissions

`arcade.config.json` contains Argon2id-hashed PINs, the JWT signing secret, and per-seat `agent_secret` tokens. It **must never be readable by anyone except the owner**.

### Linux / macOS

Set the file permissions to `600` (owner read-write only):

```bash
chmod 600 arcade.config.json
```

### Windows

Restrict the file via ACL by removing inherited permissions and granting only the owner full access:

1. Right-click `arcade.config.json` → **Properties** → **Security** tab.
2. Click **Advanced** → **Disable inheritance** → **Remove all inherited permissions**.
3. Click **Add** → **Select a principal** → enter your username → **Full control**.
4. Confirm with **OK** on all dialogs.
