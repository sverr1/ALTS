# ALTS - Automated Lecture Transcription & Summary System

Komplett pipeline for å laste ned forelesninger fra Panopto, transkribere med WhisperX, og generere faglige oppsummeringer med AI.

## Mappestruktur

```
ALTS/
├── venv/                    # Python virtual environment
├── downloads/               # yt-dlp temp, MP4 under prosessering, MP3 arkiv
├── transcriptions/          # Transkripsjonsfiler (.txt)
├── forelesninger/           # Strukturerte oppsummeringer (.md)
│   └── EMNEKODE/
│       └── YYYY_måned/
├── pipeline.py             # 🚀 Alt-i-ett: Download → Transcribe → Summarize
├── download.py             # Last ned fra Panopto → MP3
├── transcribe.py           # Transkriber med WhisperX
├── process.py              # Generer oppsummering med AI
├── prompt.md               # System prompt for AI-prosessering
├── cookies.txt             # Panopto autentisering (påkrevd)
├── .env                    # API-nøkler (lag fra .env.example)
└── README.md
```

## Oppsett

### 1. Aktiver virtual environment

```bash
source venv/bin/activate
```

### 2. Konfigurer API-nøkler

Lag `.env` fil basert på `.env.example`:

```bash
cp .env.example .env
```

Rediger `.env` og legg inn din OpenRouter API-nøkkel:

```
OPENROUTER_API_KEY=sk-or-v1-...
```

**Få API-nøkkel:**
1. Gå til https://openrouter.ai/
2. Logg inn / Opprett konto
3. Gå til "Keys" → "Create Key"
4. Kopier nøkkelen til `.env`

### 3. Hent Panopto cookies

For at `download.py` skal fungere, må du eksportere cookies fra nettleseren når du er logget inn på Panopto.

**Chrome/Edge:**
1. Installer [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
2. Gå til Panopto-siden din
3. Klikk på utvidelsen → "Export"
4. Lagre som `cookies.txt` i ALTS-mappen

**Firefox:**
1. Installer [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)
2. Følg samme prosedyre

## 🆕 Nye Features (Feature Parity med ALTS)

### ✅ Automatisk Chunking
Store transkrip (>150k tegn) deles automatisk i overlappende chunks og prosesseres hierarkisk for best kvalitet.

### ✅ Git-publisering
Oppsummeringer kan automatisk committes og pushes til Git:
```bash
python process.py transcript.txt          # Publiserer til Git
python process.py transcript.txt --no-publish  # Hopper over Git
```

### ✅ Språk-autodeteksjon
Språk detekteres automatisk fra emnekode:
- **FYS, KJE** → Engelsk (fysikk, kjemi)
- **DAT, MAT** → Norsk (informatikk, matematikk)
- Ingen `--language` parameter nødvendig (men kan overstyres)

### ✅ Batch-regenerering
Regenerer alle oppsummeringer med nye innstillinger:
```bash
python regenerate_summaries.py --dry-run  # Se hva som ville skjedd
python regenerate_summaries.py            # Regenerer alle
```

---

## Workflow

### ⚡ Quick Start (Alt-i-ett pipeline)

**Den enkleste måten:**

```bash
source venv/bin/activate
python pipeline.py "https://uis.cloud.panopto.eu/..."
```

Dette kjører automatisk:
1. Download → MP3
2. Transcribe → TXT
3. Summarize → MD

**Med språkvalg (valgfritt - autodetekteres fra emnekode):**
```bash
python pipeline.py "https://url" --language en  # Tving engelsk
python pipeline.py "https://url" --language no  # Tving norsk
python pipeline.py "https://url"                 # Auto-detect
```

**Standard-innstillinger:**
- **Modell:** Claude 3.5 Sonnet (best for akademiske oppsummeringer)
- **Temperature:** 0.2 (fokusert, konsistent, minimal variasjon)

**Automatisk Git-publisering:**
```bash
python pipeline.py "https://url"  # Publiserer til Git automatisk
```

---

### 📋 Manuell workflow (steg-for-steg)

#### Steg 1: Last ned forelesning

```bash
python download.py <PANOPTO_URL>
```

- Laster ned video fra Panopto
- Konverterer automatisk til MP3 (høy kvalitet, ~190 kbps)
- Sletter original video for å spare plass
- Lagrer som `<EMNEKODE>_<DATO>.mp3` i `downloads/`

**Eksempel:**
```bash
python download.py "https://ntnu.cloud.panopto.eu/Panopto/Pages/Viewer.aspx?id=..."
# Output: downloads/KJE101_2025-10-03.mp3
```

**Automatisk filnavn-rensing:**
- Panopto-videoer har ofte "-1", "-2" i tittel (f.eks. "FYS102-1 03.10.2024")
- `download.py` fjerner automatisk disse tallene
- Resultat: Ren emnekode (FYS102, MAT100, DAT120, KJE101)

### Steg 2: Transkriber

**Auto-detect språk fra emnekode (anbefalt):**
```bash
python transcribe.py downloads/KJE101_2025-10-03.mp3
# Detekterer automatisk norsk for KJE-kurs
```

**Manuelt språkvalg (overstyrer autodeteksjon):**
```bash
python transcribe.py downloads/KJE101_2025-10-03.mp3 --language en
python transcribe.py downloads/KJE101_2025-10-03.mp3 --language no
```

Output: `transcriptions/KJE101_2025-10-03.txt`

**Språkstøtte:**
- ✅ Engelsk: Full alignment-støtte (best kvalitet)
- ⚠️ Norsk/Svensk: Kun transkribering, ingen alignment
- **Tips:** Bruk `--language en` for blandede forelesninger

### Steg 3: Generer oppsummering

```bash
python process.py transcriptions/KJE101_2025-10-03.txt
# Prosesserer med automatisk chunking og publiserer til Git
```

Output: `forelesninger/KJE101/2025_oktober/KJE101_2025-10-03.md`

**Avansert:**
```bash
# Bruk annen modell
python process.py transcript.txt --model anthropic/claude-3.5-sonnet

# Juster kreativitet
python process.py transcript.txt --temperature 0.5

# Hopp over Git-publisering
python process.py transcript.txt --no-publish
```

**Store filer (>150k tegn):**
- Deles automatisk i chunks med 5k overlap
- Hierarkisk oppsummering (chunks → del-sammendrag → final)
- Kritisk for 3-timers forelesninger

**Støttede modeller (via OpenRouter):**
- `anthropic/claude-3.5-sonnet` (default) - Best for akademiske oppsummeringer
- `openai/gpt-4o` - Rask og god
- `google/gemini-pro-1.5` - God gratis-tier
- Se https://openrouter.ai/models for flere

**Temperature-anbefaling:**
- **0.2** (default) - Anbefalt for faglig innhold (konsistent, deterministisk)
- **0.3-0.5** - Litt mer variasjon (hvis ønskelig)
- **0.7+** - Kreativt innhold (ikke anbefalt for forelesninger)

### Steg 4 (valgfritt): Batch-regenerering

Regenerer alle oppsummeringer med nye innstillinger:

```bash
# Se hva som ville skjedd
python regenerate_summaries.py --dry-run

# Regenerer alle med default modell
python regenerate_summaries.py

# Bruk annen modell
python regenerate_summaries.py --model anthropic/claude-3.5-sonnet

# Hopp over Git-publisering
python regenerate_summaries.py --no-publish
```

Nyttig når du:
- Oppdaterer `prompt.md`
- Bytter AI-modell
- Vil fikse feil i gamle oppsummeringer

---

## Eksempler

### Alt-i-ett pipeline (anbefalt)

```bash
source venv/bin/activate

# Auto-detect språk og publiser til Git
python pipeline.py "https://uis.cloud.panopto.eu/Panopto/Pages/Viewer.aspx?id=..."

# Manuelt språkvalg
python pipeline.py "https://url" --language no

# Bruk annen AI-modell
python pipeline.py "https://url" --model openai/gpt-4o

# Juster kreativitet
python pipeline.py "https://url" --temperature 0.5
```

### Manuell workflow

```bash
source venv/bin/activate

# 1. Last ned forelesning (→ MP3)
python download.py "https://panopto.url..."

# 2. Transkriber (→ TXT) med auto-detect språk
python transcribe.py downloads/KJE101_2025-10-03.mp3

# 3. Generer oppsummering (→ MD) med Git-publisering
python process.py transcriptions/KJE101_2025-10-03.txt

# 4 (valgfritt). Regenerer alle oppsummeringer
python regenerate_summaries.py --dry-run  # Se endringer
python regenerate_summaries.py            # Utfør

# Ferdig! Resultat:
# - downloads/KJE101_2025-10-03.mp3                           (lydfil)
# - transcriptions/KJE101_2025-10-03.txt                      (transkript)
# - forelesninger/KJE101/2025_oktober/KJE101_2025-10-03.md   (oppsummering)
# - Automatisk committed og pushet til Git ✨
```

## prompt.md - AI-prosessering

`prompt.md` inneholder system-promptet som styrer hvordan AI prosesserer transkripsjonen.

**Fag-spesifikk tilpasning:**
- **DAT120:** Python-kode, algoritmer
- **MAT100:** LaTeX-formler, beviser
- **FYS102:** Enheter, numeriske eksempler
- **KJE101:** Reaksjonsligninger, støkiometri

**Output-struktur:**
- Kort sammendrag (200-300 ord)
- Nøkkelbegreper
- Viktige formler/teoremer (LaTeX)
- Eksempler og typiske feil
- Cornell-spørsmål
- m.m.

Du kan redigere `prompt.md` for å tilpasse til dine behov!

## Systemkrav

### Påkrevd programvare
- **Python 3.12**
- **NVIDIA GPU** med CUDA-støtte
- **ffmpeg** - For audio/video-konvertering
- **yt-dlp** - For Panopto-nedlasting

### Python-pakker (i venv)
- **whisperx** - AI transkribering
- **torch, torchaudio** - PyTorch GPU
- **nvidia-cublas-cu12, nvidia-cudnn-cu12** - CUDA
- **openai** - OpenRouter API-klient
- **python-dotenv** - Environment-variabler
- **pyannote.audio** - Voice activity detection
- Og flere avhengigheter...

## Ytelse

- **GPU:** RTX 3080 eller bedre anbefales
- **Transkribering:** ~5-10x real-time (1t video = 6-12 min)
- **AI-prosessering:** ~30-60 sekunder per forelesning
- **Lagringsplass:** MP3 ~50-100 MB per time (vs. MP4 ~500-1000 MB)

## Feilsøking

### "Library libcublas.so.12 is not found"

Dette er automatisk fikset i `venv/bin/activate`. Sørg for at du aktiverer venv:
```bash
source venv/bin/activate
```

### "No default align-model for language: sv/no"

Forventet for norsk/svensk. Alignment hoppes over, transkribering fortsetter.

### "OPENROUTER_API_KEY not found"

Du mangler `.env` fil. Lag den fra `.env.example` og legg inn API-nøkkel.

### Download feiler med autentiseringsfeil

`cookies.txt` er utdatert. Eksporter på nytt fra nettleseren mens du er logget inn.

### FFmpeg ikke funnet

**Arch Linux:**
```bash
sudo pacman -S ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

### yt-dlp ikke funnet

**Arch Linux:**
```bash
sudo pacman -S yt-dlp
```

**Ubuntu/Debian:**
```bash
sudo apt install yt-dlp
```

## Output-formater

### Transkript (.txt)
```
[2.83s -> 27.84s] Tekst fra første segment...
[29.19s -> 55.48s] Tekst fra andre segment...
```

### Oppsummering (.md)
```markdown
# KJE101 - Forelesning 8: Syrer og baser

## Kort sammendrag
Forelesningen introduserer Arrhenius og Brønsted-Lowry...

## Nøkkelbegreper
- **Arrhenius syre:** Substans som øker [H₃O⁺] i vann
- **Brønsted syre:** Protondonor
...

## Viktige formler
$$K_w = [\text{H}_3\text{O}^+][\text{OH}^-] = 1.0 \times 10^{-14}$$
...
```

## Sikkerhet

- **cookies.txt** inneholder autentisering - ikke del!
- **.env** inneholder API-nøkler - ikke commit til Git!
- Begge er i `.gitignore` (hvis du lager Git repo)

## Lisens

Personlig bruk for transkribering og oppsummering av forelesninger.

## Git-integrering

### Oppsett

Initier Git-repo i ALTS-mappen:
```bash
cd ALTS
git init
git remote add origin <din-repo-url>
```

### Automatisk publisering

`process.py` og `regenerate_summaries.py` publiserer automatisk til Git:
- ✅ Commits oppsummeringer med beskrivende meldinger
- ✅ Pusher til remote hvis konfigurert
- ⚠️ Hopp over med `--no-publish` flag

**Commit-format:**
```
ALTS: KJE101 2025-10-03 - forelesningsnotat
ALTS: Regenerated 15 summaries
```

## Tips

1. **Git-backup:** Alt committes automatisk - gratis versjonskontroll!
2. **Batch-prosessering:** Bruk `regenerate_summaries.py` etter endringer i prompt
3. **Eksporter oppsummeringer:** Pandoc kan konvertere MD → PDF/DOCX
4. **Søk i transkripter:** Bruk `grep` til å finne nøkkelord på tvers av forelesninger
5. **Språk-autodeteksjon:** Kun overstyring ved behov - spar tid!
