# Managed SSH key profiles

Create one directory per SSH identity and place exactly one private key inside:

```text
ssh-keys/
  foreman/
    id_rsa_foreman_proxy
  production/
    id_ed25519
```

Public keys may be stored beside private keys. SteamRoller recognizes standard
OpenSSH and PEM private-key headers and ignores `*.pub` files. Key material is
excluded from Git; only this documentation file is tracked.

Recommended permissions:

```bash
chmod 700 ssh-keys ssh-keys/foreman
chmod 600 ssh-keys/foreman/id_rsa_foreman_proxy
```

With one managed private key, `connectivity`, `precheck`, and `repo-off` select
it automatically. With multiple profiles, select one using `-sk PROFILE` or
`--ssh-key PROFILE`.
