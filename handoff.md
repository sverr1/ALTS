# ALTS - Development Handoff

## Prosjektoversikt

ALTS er et komplett pipeline-system for å laste ned forelesninger fra Panopto, transkribere med WhisperX (GPU-akselerert), og generere faglige oppsummeringer med AI via OpenRouter.

## Nåværende status

### ✅ Ferdigstilt funksjonalitet

1. **GPU-akselerert transkripsjon**
   - WhisperX large-v3 på NVIDIA RTX 3080
   - CUDA 12 biblioteker installert via pip i venv
   - Automatisk LD_LIBRARY_PATH konfigurasjon i `venv/bin/activate`
   - Støtte for språkvalg (--language en/no/sv)
   - Graceful degradation for språk uten alignment-modeller

2. **Komplett pipeline**
   - `download.py`: Panopto → MP3 (med ffmpeg kompresjon ~190 kbps VBR)
   - `transcribe.py`: MP3 → TXT (med timestamps)
   - `process.py`: TXT → MD (AI-generert oppsummering)
   - `pipeline.py`: Alt-i-ett automatisering

3. **File existence checks**
   - Alle 3 steg sjekker om output-fil allerede eksisterer
   - Hopper over redundant prosessering
   - Sparer tid og ressurser

4. **AI-prosessering**
   - OpenRouter API integrasjon
   - Claude 3.5 Sonnet som standard (temp 0.2)
   - Fagspesifikk prompt i `prompt.md` (DAT120, MAT100, FYS102, KJE101)
   - Chain-of-Density prompting for presise sammendrag

### 🔧 Teknisk oppsett

**Python environment:**
- Python 3.12 (ikke 3.13 - WhisperX kompatibilitet)
- Virtual environment: `venv/`
- CUDA 12 biblioteker: nvidia-cublas-cu12, nvidia-cudnn-cu12

**Kritiske modifikasjoner:**
- `venv/bin/activate` setter automatisk LD_LIBRARY_PATH for CUDA libs:
  ```bash
  LD_LIBRARY_PATH="$VIRTUAL_ENV/lib/python3.12/site-packages/nvidia/cublas/lib:$VIRTUAL_ENV/lib/python3.12/site-packages/nvidia/cudnn/lib:${LD_LIBRARY_PATH:-}"
  ```

**Eksterne avhengigheter:**
- ffmpeg (audio/video konvertering)
- yt-dlp (Panopto nedlasting)
- cookies.txt (Panopto autentisering - må oppdateres manuelt)

### 📁 Prosjektstruktur

```
ALTS/
├── venv/                    # Python 3.12 virtual environment
├── downloads/               # yt-dlp temp, MP4 under prosessering, MP3 arkiv
├── transcriptions/          # TXT filer fra WhisperX
├── forelesninger/           # Strukturerte MD-sammendrag
│   ├── KJE101/
│   │   └── 2025_oktober/
│   │       └── KJE101_2025-10-03.md
│   ├── DAT120/
│   │   └── 2025_oktober/
│   │       └── DAT120_2025-10-01.md
│   └── ...
├── pipeline.py             # 🚀 Alt-i-ett: Download → Transcribe → Summarize
├── download.py             # Panopto → MP3 (sjekker file existence)
├── transcribe.py           # MP3 → TXT (sjekker file existence)
├── process.py              # TXT → MD (sjekker file existence)
├── prompt.md               # System prompt for AI-prosessering
├── cookies.txt             # Panopto auth (ikke i git)
├── .env                    # OPENROUTER_API_KEY (ikke i git)
├── .env.example            # Template for API nøkkel
├── .gitignore              # Beskytter sensitive filer
├── README.md               # Brukerdokumentasjon
└── handoff.md              # Denne filen
```

### 🎯 Typisk workflow

**Quick start:**
```bash
source venv/bin/activate
python pipeline.py "https://uis.cloud.panopto.eu/..." --language en
```

**Manuelt:**
```bash
source venv/bin/activate
python download.py "https://url"                      # → downloads/EMNEKODE_YYYY-MM-DD.mp3
python transcribe.py downloads/FIL.mp3 --language en  # → transcriptions/EMNEKODE_YYYY-MM-DD.txt
python process.py transcriptions/FIL.txt              # → forelesninger/EMNEKODE/YYYY_måned/EMNEKODE_YYYY-MM-DD.md
```

## Løste problemer

### Problem 1: CUDA library not found
**Error:** `Library libcublas.so.12 is not found`
**Årsak:** CTranslate2 krever CUDA 12, system hadde CUDA 13
**Løsning:**
- `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`
- Modifisert `venv/bin/activate` for automatisk LD_LIBRARY_PATH

### Problem 2: WhisperX Python 3.13 inkompatibilitet
**Error:** WhisperX installasjon feilet
**Løsning:** Opprettet ny venv med Python 3.12

### Problem 3: Språkdeteksjon (svensk i stedet for engelsk)
**Årsak:** WhisperX detekterer språk fra første 30s
**Løsning:** `--language en` parameter for å tvinge språk

### Problem 4: Redundant nedlasting/prosessering
**Løsning:** File existence checks i alle 3 steg
- download.py: Bruker `yt-dlp --get-filename` for å predikere output i downloads/
- transcribe.py: Sjekker for eksisterende .txt i transcriptions/
- process.py: Sjekker for eksisterende .md i forelesninger/EMNEKODE/YYYY_måned/

## Potensielle forbedringspunkter

### 🔮 Framtidige features

1. **Batch-prosessering**
   - Script for å prosessere flere forelesninger samtidig
   - CSV/JSON input med liste av URLer

2. **Kvalitetsforbedringer**
   - Speaker diarization (krever HuggingFace token)
   - Timestamp-synkronisering i sammendrag
   - Support for flere output-formater (PDF, DOCX)

3. **Robusthet**
   - Automatisk cookies.txt refresh
   - Retry-logikk for API-feil
   - Progress bar for lange transkripsjoner

4. **Organisering**
   - Automatisk mappestruktur per emne/semester
   - Metadata-tracking (forelesningsnummer, dato, emne)
   - Søkefunksjonalitet på tvers av transkripsjoner

5. **AI-forbedringer**
   - Flere modeller (GPT-4o, Gemini Pro)
   - Dynamisk prompt basert på emne-deteksjon
   - Multi-shot prompting for konsistente sammendrag

### ⚠️ Kjente begrensninger

1. **Språk-alignment:**
   - Kun engelsk har full alignment-støtte
   - Norsk/svensk: kun transkripsjon, ingen alignment
   - **Workaround:** Bruk `--language en` for blandede forelesninger

2. **Panopto cookies:**
   - Må oppdateres manuelt når de utløper
   - Ingen automatisk refresh-mekanisme

3. **Storage:**
   - MP3-filer blir ikke automatisk slettet etter transkripsjon
   - Kun original MP4 blir slettet etter MP3-konvertering

4. **Error handling:**
   - Begrenset retry-logikk
   - Ingen fallback hvis AI API feiler

## Viktige kommandoer

```bash
# Aktiver environment (VIKTIG: setter LD_LIBRARY_PATH)
source venv/bin/activate

# Kjør komplett pipeline
python pipeline.py "https://url" --language en

# Teste GPU
python -c "import torch; print(torch.cuda.is_available())"

# Sjekke CUDA libraries
ls -la venv/lib/python3.12/site-packages/nvidia/cublas/lib/

# Oppdatere cookies.txt
# 1. Logg inn på Panopto i Chrome/Firefox
# 2. Installer "Get cookies.txt LOCALLY" extension
# 3. Eksporter og lagre som cookies.txt i prosjektmappen

# Sjekke API-nøkkel
cat .env | grep OPENROUTER_API_KEY
```

## Environment variabler

```bash
# .env fil (ikke i git)
OPENROUTER_API_KEY=sk-or-v1-...

# Valgfri (for speaker diarization)
HF_TOKEN=hf_...
```

## Dependencies

**Python packages (se requirements.txt):**
- whisperx
- torch, torchaudio (CUDA)
- nvidia-cublas-cu12, nvidia-cudnn-cu12
- openai (for OpenRouter API)
- python-dotenv
- pyannote.audio

**System:**
- NVIDIA GPU med CUDA-støtte
- ffmpeg
- yt-dlp

## Testing

```bash
# Test pipeline med eksisterende fil
python pipeline.py "https://test-url" --language en

# Test file existence checks
touch downloads/TEST_2025-01-01.mp3
python download.py "https://url"  # Skal hoppe over hvis URL matcher TEST

# Test transcribe existence
mkdir -p transcriptions
touch transcriptions/TEST_2025-01-01.txt
python transcribe.py downloads/TEST_2025-01-01.mp3  # Skal hoppe over

# Test process existence
mkdir -p forelesninger/TEST/2025_januar
touch forelesninger/TEST/2025_januar/TEST_2025-01-01.md
python process.py transcriptions/TEST_2025-01-01.txt  # Skal hoppe over
```

## Kontaktpunkter / Ressurser

- **OpenRouter:** https://openrouter.ai/
- **WhisperX GitHub:** https://github.com/m-bain/whisperX
- **yt-dlp:** https://github.com/yt-dlp/yt-dlp
- **CUDA toolkit:** https://developer.nvidia.com/cuda-toolkit

## Siste endringer (2025-10-06)

1. **Ny mappestruktur:**
   - `downloads/`: Kun for yt-dlp temp, MP4 under prosessering, og MP3 arkiv
   - `transcriptions/`: Alle .txt filer fra WhisperX (uten _whisperx suffix)
   - `forelesninger/EMNEKODE/YYYY_måned/`: MD-sammendrag (uten _summary suffix)

2. **Navnekonvensjoner:**
   - Transkripsjoner: `EMNEKODE_YYYY-MM-DD.txt` (uten _whisperx)
   - Sammendrag: `EMNEKODE_YYYY-MM-DD.md` (uten _summary)
   - Månedsformat: `YYYY_måned` (f.eks. 2025_oktober)

3. **Filnavn opprydding:**
   - `transcribe_whisperx.py` → `transcribe.py`

4. File existence checks implementert i alle steg
5. Prosjektet er fullstendig funksjonelt og klart for bruk

---

**Status:** ✅ Production ready
**Sist oppdatert:** 2025-10-06
**Python versjon:** 3.12
**CUDA versjon:** 12 (via pip packages)
