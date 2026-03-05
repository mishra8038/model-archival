# Obtaining HuggingFace Access Tokens for Gated Models

This guide covers every token and access-request step needed to download
all priority-2 (gated) models in the archiver registry.

---

## Overview

Nine models in the registry require a HuggingFace account and model-specific
access approval before they can be downloaded:

| Model | Provider | Licence | HF Repo |
|-------|----------|---------|---------|
| Llama 3.1 405B Instruct | Meta | Llama 3.1 Community | [meta-llama/Llama-3.1-405B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-405B-Instruct) |
| Llama 3.1 70B Instruct | Meta | Llama 3.1 Community | [meta-llama/Llama-3.1-70B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-70B-Instruct) |
| Llama 3.3 70B Instruct | Meta | Llama 3.3 Community | [meta-llama/Llama-3.3-70B-Instruct](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct) |
| Llama 3.1 8B Instruct | Meta | Llama 3.1 Community | [meta-llama/Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) |
| Gemma 3 27B IT | Google | Gemma Terms of Use | [google/gemma-3-27b-it](https://huggingface.co/google/gemma-3-27b-it) |
| Gemma 3 27B PT | Google | Gemma Terms of Use | [google/gemma-3-27b-pt](https://huggingface.co/google/gemma-3-27b-pt) |
| Gemma 3 12B IT | Google | Gemma Terms of Use | [google/gemma-3-12b-it](https://huggingface.co/google/gemma-3-12b-it) |
| Mistral Large 2 246B | Mistral AI | Mistral Research | [mistralai/Mistral-Large-Instruct-2407](https://huggingface.co/mistralai/Mistral-Large-Instruct-2407) |
| Codestral 22B | Mistral AI | Mistral MNPL | [mistralai/Codestral-22B-v0.1](https://huggingface.co/mistralai/Codestral-22B-v0.1) |

A single HuggingFace account and one API token covers all of them.
Access is per-model — you request it separately on each model's page.

---

## Part 1 — Create a HuggingFace Account

1. Go to **<https://huggingface.co/join>**
2. Enter your email, choose a username and password, click **Create Account**
3. Verify your email address (check spam if not received within a few minutes)
4. Complete your profile — providers (Meta, Google) may reject requests from
   accounts with no profile picture or bio. Add at least a name and country.

---

## Part 2 — Generate an API Token

The archiver uses a single token (`HF_TOKEN`) for all downloads.

1. Log in and go to **<https://huggingface.co/settings/tokens>**
2. Click **New token**
3. Settings:
   - **Name**: `model-archiver` (or anything you'll recognise)
   - **Type**: `Read` — sufficient for downloading; no write permissions needed
4. Click **Generate a token**
5. Copy the token immediately — it starts with `hf_` and is shown only once

Store it securely (password manager). You will set it as an environment
variable on the VM — do not commit it to git.

---

## Part 3 — Request Access to Each Model

Access approvals are independent per model family. You only need to do this
once per account; approval persists indefinitely.

### Meta — Llama Models (4 models)

All Llama models share a single access gate per licence version.
Approving Llama 3.1 covers the 405B, 70B, and 8B variants.
Approving Llama 3.3 covers the 70B 3.3 variant separately.

**Llama 3.1** (covers 405B Instruct, 70B Instruct, 8B Instruct):

1. Go to <https://huggingface.co/meta-llama/Llama-3.1-405B-Instruct>
2. Click the **Agree and access repository** button
3. Fill in the form:
   - **Name** and **email** (must match your HF account)
   - **Organisation / affiliation**: personal use is fine
   - **Intended use**: "offline archival and research"
4. Submit. Approval is automated and typically instant.
5. You will receive an email confirmation from Meta.

**Llama 3.3** (covers Llama-3.3-70B-Instruct):

1. Go to <https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct>
2. Repeat the same form — same process, separate gate.
3. Also instant approval.

> **Tip**: Once approved for Llama 3.1, all 3.1-family repos
> (405B, 70B, 8B, distilled variants) become accessible with the same token.

---

### Google — Gemma Models (3 models)

All Gemma 3 models share a single access gate.
Approving one (e.g. 27b-it) typically covers all Gemma 3 variants.

1. Go to <https://huggingface.co/google/gemma-3-27b-it>
2. Click **Acknowledge licence and access repository**
3. You must be logged in with a Google account linked to your HF account,
   **or** simply agree to the Gemma Terms of Use on the HF page — a Google
   account is not strictly required
4. Read and agree to the [Gemma Terms of Use](https://ai.google.dev/gemma/terms)
5. Click **Submit**. Approval is instant and automated.

After approval, also verify access works for:
- <https://huggingface.co/google/gemma-3-27b-pt>
- <https://huggingface.co/google/gemma-3-12b-it>

If those show "Access granted" in the banner, you're done. If not, click
**Request access** on each page — it takes 30 seconds each.

---

### Mistral AI — Mistral Large + Codestral (2 models)

Mistral models have two separate licences and two separate gates.

**Mistral Large 2 (Mistral Research Licence)**:

1. Go to <https://huggingface.co/mistralai/Mistral-Large-Instruct-2407>
2. Click **Agree and access repository**
3. Read the [Mistral Research Licence](https://mistral.ai/licenses/MRL-0.1.md)
   — permits research and non-commercial use
4. Submit. Approval is automated and instant.

**Codestral 22B (Mistral Non-Production Licence)**:

1. Go to <https://huggingface.co/mistralai/Codestral-22B-v0.1>
2. Click **Agree and access repository**
3. Read the [Mistral MNPL](https://mistral.ai/licenses/MNPL-0.1.md)
   — permits non-production / research use only
4. Submit. Approval is automated and instant.

> **Note**: The MNPL explicitly prohibits use in production services or
> commercial products. Archival for personal research is permitted.

---

## Part 4 — Set the Token on the VM

Once you have the token and all access approvals:

```bash
# Set for the current session
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx

# Persist across reboots and new SSH sessions
echo 'export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx' >> ~/.bashrc
source ~/.bashrc
```

Verify the token works and all models are accessible:

```bash
cd ~/model-archival
archiver tokens check
```

This will show a table like:

```
Model                        Accessible
─────────────────────────────────────────
llama-405b                   ✓ yes
llama-3.1-70b                ✓ yes
llama-3.3-70b                ✓ yes
llama-3.1-8b                 ✓ yes
gemma-3-27b-it               ✓ yes
gemma-3-27b-pt               ✓ yes
gemma-3-12b-it               ✓ yes
mistral-large-2              ✓ yes
codestral-22b                ✓ yes
```

If any show `✗ no`, revisit that model's HuggingFace page and confirm
the access banner says "You have been granted access to this model".

---

## Part 5 — Download Gated Models

With priority-1 downloads already running or complete:

```bash
# Download only the gated models
archiver download --all --priority-only 2
```

Or to download everything remaining (will skip already-complete models):

```bash
archiver download --all
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `401 Unauthorized` | Token not set or expired | Re-export `HF_TOKEN`; generate a new token if needed |
| `403 Forbidden` | Access not approved for that model | Visit the model page and submit the access form |
| `archiver tokens check` shows `✗ no` despite approval | Approval email received but HF propagation delay | Wait 5–10 minutes, retry |
| Meta approval email never arrives | Spam filter | Check spam; resubmit if not received within 1 hour |
| Gemma page shows "Request pending" | Unusual — normally instant | Reload the page; if stuck > 30 min, log out and back in |
| Mistral gate asks for company details | Some accounts get extended form | Fill in "Individual / personal research" for all fields |

---

## Approval Time Summary

| Provider | Typical approval time | Manual review? |
|----------|-----------------------|----------------|
| Meta (Llama) | Instant (automated) | No |
| Google (Gemma) | Instant (automated) | No |
| Mistral (MRL) | Instant (automated) | No |
| Mistral (MNPL) | Instant (automated) | No |

All four providers use fully automated gates — no human review, no waiting
days. The entire process from account creation to all tokens approved takes
under 15 minutes.
