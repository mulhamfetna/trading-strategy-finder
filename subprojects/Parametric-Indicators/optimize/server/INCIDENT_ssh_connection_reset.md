# Incident — SSH to the AMD server reset at the protocol-identification stage

**Date:** 2026-06-12 · context: attempting to deploy the optimizer scaling updates (`remote_wsi.sh push/parity`).
**Severity:** blocks all server deployment + monitoring; **no impact on local work** (which proceeds normally).
**Status:** OPEN — requires action on the server side (we cannot remediate from the client).
**One-line:** the TCP connection to `78.89.209.212:33362` succeeds, but the server **resets it immediately,
before the SSH banner is exchanged** — the signature of an IP-level block (fail2ban) or sshd throttling,
not an auth or code problem.

---

## 1. Symptom

Running the established remote driver:
```
$ bash remote_wsi.sh status
kex_exchange_identification: read: Connection reset by peer
Connection reset by 78.89.209.212 port 33362
$ bash remote_wsi.sh counts
kex_exchange_identification: read: Connection reset by peer
Connection reset by 78.89.209.212 port 33362
```
Every SSH-backed subcommand (`status`, `counts`, and by extension `push`/`parity`/`run`/`pull`) fails the
same way. The failure is at the **SSH protocol-version exchange**, the very first bytes after the TCP
handshake — *before* any key/auth negotiation.

---

## 2. Diagnostics run (and their results)

| # | Probe | Command (abridged) | Result | What it proves |
|--:|-------|--------------------|--------|----------------|
| 1 | Connection config present | `cat meta-prophet/server/server.env` | ✅ `SRV_HOST=78.89.209.212 SRV_PORT=33362 SRV_USER=dev SRV_KEY=~/.ssh/amd_trading` | our side is configured correctly |
| 2 | Raw TCP reachability | `cat </dev/null >/dev/tcp/78.89.209.212/33362` | ✅ **PORT OPEN** (connect succeeds) | the host is up, the port is listening, the network path works |
| 3 | Verbose SSH probe | `ssh -vv … dev@…:33362 true` | `debug1: Connecting…` → `debug1: Connection established.` → `kex_exchange_identification: read: Connection reset by peer` → `Connection reset by 78.89.209.212 port 33362` | TCP completes, then the **peer resets** before the SSH banner |

**The decisive pair:** TCP connect **succeeds** (probe 2) but the SSH banner read is **reset** (probe 3).
The connection reaches the server and is then deliberately dropped at the application layer.

---

## 3. Root-cause analysis

### 3.1 What the signature means
`kex_exchange_identification: read: Connection reset by peer` = the client opened the TCP socket and waited
for the server's `SSH-2.0-…` identification string, but the server (or something in front of it) sent a
TCP RST instead. The reset happens **before** key exchange, so:
- it is **not** a key/passphrase/permission problem (we never reach auth),
- it is **not** our code, the `remote_wsi.sh` logic, or `server.env` (probe 1 confirms config; the same
  symptom hits a bare `ssh … true`),
- it is **not** a dead host or closed port (probe 2 confirms both are fine).

### 3.2 Ranked hypotheses (most → least likely)
1. **fail2ban (or similar IP banning) has banned our egress IP — MOST LIKELY.** fail2ban's common action
   inserts a firewall rule that **rejects/resets** new connections from a banned IP *after* the TCP SYN is
   accepted, producing exactly this "connect then reset at banner" pattern. The previous session ran **many**
   SSH connections (parallel `launch.sh`, repeated `status`/`counts`, backgrounded job launches that exited
   255) — enough auth churn to trip a `maxretry` ban. Bans are time-boxed (often 10 min–hours) and reset on
   expiry.
2. **sshd `MaxStartups` / load throttling.** If sshd has many unauthenticated connections in flight (or is
   under load), it probabilistically drops new pre-auth connections. Possible if leftover workers or
   monitoring are hammering it, but less likely now that the box is reportedly idle.
3. **sshd restarting / mid-reload.** A momentary window during a daemon restart resets in-flight banner reads.
   Would be transient (retry minutes later succeeds).
4. **TCP-wrapper / `hosts.deny` / firewall RST rule.** A `hosts.deny`, an explicit `iptables -j REJECT
   --reject-with tcp-reset`, or a cloud/edge ACL change could reset post-accept. Less likely without a config
   change on the box.
5. **MTU/middlebox interference.** Possible in theory; de-prioritised because the reset is consistent and
   immediate (a path/MTU issue would more often hang or fail intermittently).

### 3.3 Explicitly ruled out
- **Auth/key issues** — reset precedes auth.
- **Wrong host/port** — TCP connects to that exact host:port.
- **Our tooling/code** — bare `ssh` reproduces it; config verified.
- **Host down / network outage** — TCP handshake completes.

---

## 4. Remediation (server-side — needs console/physical access as `dev@amd`)

Try in order; #1 is the most probable fix.

1. **Clear a fail2ban ban on our client IP:**
   ```bash
   sudo fail2ban-client status sshd                 # shows banned IPs + jail config
   sudo fail2ban-client set sshd unbanip <CLIENT_IP> # unban just us
   # or, blunt: sudo fail2ban-client unban --all
   ```
   Then **allowlist** our IP so automated runs don't get re-banned:
   `ignoreip = 127.0.0.1/8 <CLIENT_IP>` in `/etc/fail2ban/jail.local` → `sudo systemctl reload fail2ban`.
2. **If not fail2ban — check sshd health/throttle:**
   ```bash
   systemctl status ssh        # is it up / recently restarted?
   uptime                       # load
   journalctl -u ssh --since "30 min ago" | tail   # drops / MaxStartups messages
   ```
   If `MaxStartups` is the cause, raise it (e.g. `MaxStartups 30:50:100`) or reduce concurrent connections.
3. **Check for an explicit block:** `sudo iptables -L -n | grep 33362`, `cat /etc/hosts.deny`.
4. **Confirm recovery from the client:**
   ```bash
   ssh -p 33362 -i ~/.ssh/amd_trading -o BatchMode=yes dev@78.89.209.212 true && echo OK
   ```

> **Finding our egress IP** (the one to unban/allowlist): from this client run `curl -s ifconfig.me`
> (an outbound call — not run here to avoid an unnecessary external request). It is the public IP of the
> machine running the `remote_wsi.sh` scripts, not the server.

---

## 5. Prevention (so automated deploys stop tripping the ban)

- **Allowlist the automation IP in fail2ban** (`ignoreip`) — the cleanest fix for a trusted runner.
- **Reuse one SSH connection** instead of opening many: add to the `SSH_OPTS` in `remote_wsi.sh`
  `-o ControlMaster=auto -o ControlPath=~/.ssh/cm-%r@%h:%p -o ControlPersist=60s`, so `status`/`counts`/`push`
  multiplex over a single TCP/auth session. Fewer auth events → far less chance of a `maxretry` trip.
- **Back off on transient resets:** wrap `srv()` with a small retry-with-sleep so a momentary sshd reload
  doesn't abort a deploy.
- **Avoid the exit-255 backgrounding pattern** (`ssh host 'nohup … &'`) that produced churn last session; the
  current single-launcher approach already reduces this.

---

## 6. Impact & current posture
- **Deployment (Phase D of `ACTION_PLAN_scaling_tiers.md`) is blocked** until SSH is restored.
- **Local work is unaffected** — Tiers 1–4 are implemented and verified locally without the server; only the
  final `push/parity/run` needs connectivity.
- No data loss: the server scratch + studies are untouched (we never connected). The local repo is fully
  committed/pushed.

---

## 7. Evidence log (verbatim)
```
# probe 2 — TCP reachability
PORT OPEN (TCP connect ok)

# probe 3 — ssh -vv
debug1: Connecting to 78.89.209.212 [78.89.209.212] port 33362.
debug1: Connection established.
kex_exchange_identification: read: Connection reset by peer
Connection reset by 78.89.209.212 port 33362
```
