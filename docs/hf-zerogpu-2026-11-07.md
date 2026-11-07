# HF-Doku-Aussagen ZeroGPU (abgerufen 2026-11-07)

Quelle: `https://huggingface.co/docs/hub/spaces-zerogpu`, abgerufen am
2026-11-07. Zitate in Englisch, Stand des Abrufs.

## Hosting

- „Free personal accounts: accounts in good standing (verified email,
  account older than 30 days) can host up to 2 ZeroGPU Spaces for free.“
- „ZeroGPU Spaces are exclusively compatible with the Gradio SDK.“

## Hardware

| Groesse | Hardware | VRAM | Quota-Kosten |
| --- | --- | --- | --- |
| `large` (Standard) | halbe NVIDIA RTX Pro 6000 Blackwell | 48 GB | 1x |
| `xlarge` | volle NVIDIA RTX Pro 6000 Blackwell | 96 GB | 2x |

- „`xlarge` consumes 2x more daily quota than `large` (e.g. a 45s
  effective task duration consumes 90s of quota)“

## Dauer

- „For functions expected to exceed the default 60-second of GPU runtime,
  you can specify a custom duration.“
- „This sets the maximum function runtime to 120 seconds. Specifying
  shorter durations for quicker functions will improve queue priority
  for Space visitors.“

## Quote je Tag

| Konto | Tagesquote GPU | Prioritaet |
| --- | --- | --- |
| unangemeldet | 2 Minuten | niedrig |
| gratis Konto | 5 Minuten | mittel |
| PRO Konto | 40 Minuten (erweiterbar) | hoechst |

- „Included daily quota resets exactly 24 hours after your first GPU
  usage.“
- „PRO, Team, and Enterprise users can continue using ZeroGPU Spaces
  beyond their included daily quota by consuming pre-paid credits at
  the rate of $1 per 10 minutes of GPU time.“

## Modellladung

- Modelle werden auf Modulebene beim Start geladen und mit `.to('cuda')`
  platziert, wie im Doku-Beispiel. Die Doku sagt woertlich, Modelle
  „must be placed on cuda at the root module level“.
- „Lazy-loading or moving models to CUDA inside `@spaces.GPU` is
  discouraged, as it is significantly less efficient.“
- „The `@spaces.GPU` decorator is designed to be effect-free in
  non-ZeroGPU environments, ensuring compatibility across different
  setups.“
