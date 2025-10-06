import whisperx
import gc
import sys
import os
from utils import get_language_for_course, extract_course_code_from_filename

def transcribe_with_whisperx(audio_file, model_size="large-v3", batch_size=16, compute_type="float16", hf_token=None, language=None):
    """
    Transcribe audio using WhisperX with optional speaker diarization.

    Args:
        audio_file: Path to audio/video file
        model_size: Whisper model size (default: large-v3)
        batch_size: Batch size for transcription (default: 16)
        compute_type: Compute type - "float16" or "int8" (default: float16)
        hf_token: HuggingFace token for diarization (optional)
        language: Force language code (e.g., 'en', 'no', 'sv') - auto-detect if None
    """
    device = "cuda"

    print(f"--- Starting WhisperX Transcription for {audio_file} ---")

    # 1. Transcribe with whisper (batched)
    print(f"Loading model '{model_size}' on GPU ({compute_type})...")
    model = whisperx.load_model(model_size, device, compute_type=compute_type)

    print("Loading audio...")
    audio = whisperx.load_audio(audio_file)

    print(f"Transcribing with batch_size={batch_size}...")
    if language:
        print(f"Forcing language: {language}")
        result = model.transcribe(audio, batch_size=batch_size, language=language)
    else:
        result = model.transcribe(audio, batch_size=batch_size)

    print(f"\nDetected language: '{result['language']}'")
    print("\n=== Transcription BEFORE alignment ===")
    for segment in result["segments"]:
        print(f"[{segment['start']:.2f}s -> {segment['end']:.2f}s] {segment['text']}")

    # Delete model if low on GPU resources
    gc.collect()
    import torch
    torch.cuda.empty_cache()
    del model

    # 2. Align whisper output
    print("\n\nAligning transcription...")
    try:
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

        print("\n=== Transcription AFTER alignment ===")
        for segment in result["segments"]:
            print(f"[{segment['start']:.2f}s -> {segment['end']:.2f}s] {segment['text']}")

        # Delete alignment model
        gc.collect()
        torch.cuda.empty_cache()
        del model_a
    except ValueError as e:
        print(f"\nWarning: Could not perform alignment: {e}")
        print("Skipping alignment and continuing with original timestamps...")

    # 3. Assign speaker labels (optional - requires HuggingFace token)
    if hf_token:
        print("\n\nPerforming speaker diarization...")
        try:
            diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
            diarize_segments = diarize_model(audio)
            result = whisperx.assign_word_speakers(diarize_segments, result)

            print("\n=== Transcription WITH speaker labels ===")
            for segment in result["segments"]:
                speaker = segment.get('speaker', 'UNKNOWN')
                print(f"[{segment['start']:.2f}s -> {segment['end']:.2f}s] Speaker {speaker}: {segment['text']}")
        except Exception as e:
            print(f"Warning: Could not perform diarization: {e}")
    else:
        print("\n\nSkipping speaker diarization (no HuggingFace token provided)")
        print("To enable diarization, set HF_TOKEN environment variable or pass --hf-token argument")

    # 4. Save transcription to file
    # Create transcriptions directory if it doesn't exist
    os.makedirs("transcriptions", exist_ok=True)

    # Get base filename without path and extension
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    output_filename = f"transcriptions/{base_name}.txt"

    with open(output_filename, "w", encoding="utf-8") as f:
        for segment in result["segments"]:
            speaker = segment.get('speaker', '')
            speaker_label = f"[{speaker}] " if speaker else ""
            f.write(f"{speaker_label}{segment['text']}\n")

    print(f"\n\nTranscription saved to '{output_filename}'")
    print("--- WhisperX Transcription complete ---")


if __name__ == "__main__":
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file> [model_size] [--language LANG] [--hf-token TOKEN]")
        print("Example: python transcribe.py audio.mp4 large-v3 --language en")
        print("Languages: en (English), no (Norwegian), sv (Swedish), etc.")
        sys.exit(1)

    audio_file = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "large-v3"

    # Check for language override
    language = None
    if "--language" in sys.argv:
        idx = sys.argv.index("--language")
        if idx + 1 < len(sys.argv):
            language = sys.argv[idx + 1]
    else:
        # Auto-detect language from course code in filename
        filename = os.path.basename(audio_file)
        course_code = extract_course_code_from_filename(filename)
        if course_code:
            language = get_language_for_course(course_code)
            print(f"Auto-detected language '{language}' for course {course_code}")
        else:
            print("Could not extract course code, using auto-detect")

    # Check for HuggingFace token
    hf_token = None
    if "--hf-token" in sys.argv:
        idx = sys.argv.index("--hf-token")
        if idx + 1 < len(sys.argv):
            hf_token = sys.argv[idx + 1]
    elif "HF_TOKEN" in os.environ:
        hf_token = os.environ["HF_TOKEN"]

    # Check if file exists
    if not os.path.exists(audio_file):
        print(f"Error: File not found at '{audio_file}'")
        sys.exit(1)

    # Check if transcription already exists
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    output_filename = f"transcriptions/{base_name}.txt"
    if os.path.exists(output_filename):
        print(f"✓ Transcription already exists: {output_filename}")
        print(f"  Skipping transcription.")
        sys.exit(0)
    else:
        print(f"  Transcription not found, will create: {output_filename}")

    transcribe_with_whisperx(audio_file, model_size=model_size, hf_token=hf_token, language=language)
