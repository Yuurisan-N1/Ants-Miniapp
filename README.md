<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=Ants%20Miner%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Daily%20Protocol%20Reward%20%7C%20Ad%20Rewards%20%7C%20Community%20Check%20%7C%20Referral%20Vault%20%7C%20Multi-Account&descAlign=50&descAlignY=58"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Daily+Protocol+Reward+%7C+Claim+%26+Streak+Tracking;Ad+Rewards+%7C+Credited+Amount+Read+From+Server;Community+Check+%7C+Server+Verdict+Per+Account;Referral+Vault+%7C+Unlocked+Only+When+Claimable;Multi-Account+%7C+Proxy+%26+Live+Countdown"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-Ants%20Miner%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>Ants Miner Bot</b> is a full automation bot for the Ants Miner Telegram Miniapp.<br/>
  It handles the complete daily cycle: claiming the daily protocol reward, checking community membership, collecting ad rewards per provider, unlocking the referral vault, tracking the referral state, all running automatically across multiple accounts with its own referral link per account, proxy support, and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.12+`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/Ants-Miniapp.git
cd Ants-Miniapp
```

**Install dependencies:**

```bash
pip install aiohttp yuurisan
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with Telegram WebApp `initData` for each account, one per line:

```
user=%7B%22id%22...&hash=abc123
user=%7B%22id%22...&hash=def456
```

> `initData` can be obtained from the browser DevTools when opening Ants Miner on Telegram Web.

> An optional `|address` suffix is tolerated and ignored, because no phase in this bot needs a wallet address.

### 2. Proxy (proxy.txt)

Fill `proxy.txt` with proxies, one per line (optional, leave empty to run without proxy):

```
host:port
host:port:user:pass
http://user:pass@host:port
```

Proxies are assigned to accounts by index in round-robin order.

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. If `config.json` is missing, it is created automatically with a default of `3600` seconds.

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Auto Sign In
Every account signs in with its own `initData` through the app sign in endpoint, and the returned account token authorises every later call. The account state is then read back from the server so all numbers logged are server numbers, never local estimates.

### Auto Mining Harvest
The mining engine is started on the account, and on every later cycle the accrued harvest is claimed through the reward endpoint. The credited amount is confirmed with a fresh read of the account state, and the engine is restarted so the next cycle keeps accruing.

### Auto Daily Protocol Reward
The last protocol day and the current streak are read from the account state first, and the reward is only written when today is still open. The credited amount is confirmed with a fresh read after the write, and an already collected day is reported instead of being retried.

### Auto Community Check
Community membership is verified through the server check endpoint, and the server verdict is logged per account. A membership that genuinely needs a real channel or group join is reported with the server reason instead of being retried in a loop.

### Auto Ad Rewards
Every ad provider the app supports is driven through the ad reward endpoint, and the reward amount is taken from the server response, never sent by the bot. When a provider reports that its daily allowance is used up, that provider stops for the day instead of hammering the endpoint.

### Auto Referral Vault
The vault state is read from the server first, and the unlock is only sent when the server reports a claimable amount. A vault with nothing claimable, or one that was already unlocked, is reported instead of being retried.

### Auto Referral State
The referral friend count and the per-account referral code are read from the server account state, so the invite link printed for each account is that account's own link and nothing is hardcoded.

### Multi Account
All accounts in `data.txt` are processed sequentially within every cycle. Each account signs in with its own `initData`, and the balance plus the credited amount per phase are logged per account. The cycle number is tracked and logged at the start of each round.

### Proxy Support
Proxies are loaded from `proxy.txt` and assigned to accounts by position in round-robin order. Proxy credentials are masked in log output. Running without proxies is fully supported.

### Auto Countdown
After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown until the next cycle starts.

---

## File Structure

```text
AntsMiner-Miniapp/
├── bot.py          # Main bot, full daily cycle automation
├── config.json     # Sleep duration between cycles
├── data.txt        # Account initData, one per line
├── proxy.txt       # Proxy list, one per line (optional)
├── LICENSE         # License file
└── utils/
    └── banner.py   # Banner using yuurisan module
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>
