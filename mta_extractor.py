#!/usr/bin/env python3
"""
MTA Audio Extractor

Extracts audio samples from MTA (Multi-Track Audio) files and converts them
to WAV format. This tool reads the DWAV section from MTA files and extracts
individual audio samples with proper channel handling.

This project was created through reverse engineering to extract audio samples
from the Yamaha DTX Multi 12 electronic drum module. The MTA file format is
a proprietary container used by Yamaha's DTX series to store multiple audio
samples in a single file.
"""

import argparse
import wave
import array
from pathlib import Path
from typing import List, Tuple, Optional


def find_dwav_section(data: bytes) -> Optional[int]:
    """
    Find the DWAV section start offset in the MTA file.

    Args:
        data: Raw bytes of the MTA file

    Returns:
        Offset to the DWAV section, or None if not found
    """
    if len(data) < 0xC8:
        return None

    dwav_section_start = int.from_bytes(data[0xC4:0xC8], "big")

    if dwav_section_start >= len(data):
        return None

    return dwav_section_start


def parse_audio_entries(data: bytes, dwav_offset: int) -> List[Tuple[int, int]]:
    """
    Parse audio entry table from the DWAV section.

    Args:
        data: Raw bytes of the MTA file
        dwav_offset: Offset to the DWAV section

    Returns:
        List of tuples (index, absolute_offset) for each audio entry
    """
    entries = []
    offset = dwav_offset + 32

    while offset + 32 <= len(data):
        idx = int.from_bytes(data[offset:offset+4], "big")

        # Stop if we encounter an invalid index
        if idx == 0 or idx > 0xFFFF:
            break

        # Read relative audio pointer and convert to absolute offset
        audio_ptr = int.from_bytes(data[offset+8:offset+12], "big")
        abs_offset = dwav_offset + audio_ptr

        if abs_offset >= len(data):
            break

        entries.append((idx, abs_offset))
        offset += 32

    return entries


def extract_sample_name(header: bytes) -> str:
    """
    Extract sample name from the audio header.

    Args:
        header: First 16 bytes of the audio sample header

    Returns:
        Cleaned sample name, or empty string if invalid
    """
    try:
        name = header[:16].decode('ascii', errors='ignore').strip().replace('\x00', '')
        return name
    except Exception:
        return ""


def parse_audio_header(header: bytes) -> Tuple[int, int]:
    """
    Parse audio header to extract sample rate and channel count.

    Args:
        header: Audio sample header (first 80 bytes)

    Returns:
        Tuple of (sample_rate, channels)
    """
    # Extract sample rate from offset 0x36-0x38
    sample_rate = int.from_bytes(header[0x36:0x38], "big")
    if sample_rate == 0:
        sample_rate = 44100  # Default sample rate

    # Extract channel count from offset 0x49
    # 0x00 -> Mono (1 channel)
    # 0x02 -> Stereo (2 channels)
    channels_byte = header[0x49]
    channels = 2 if channels_byte == 2 else 1

    return sample_rate, channels


def process_pcm_data(pcm_data: bytes, channels: int) -> bytes:
    """
    Process PCM data based on channel configuration.

    For mono channels, the data appears to be stored in planar format
    (left channel followed by right channel), so we take only the first half.

    Args:
        pcm_data: Raw PCM audio data
        channels: Number of audio channels

    Returns:
        Processed PCM data ready for WAV conversion
    """
    # Ensure even length (16-bit samples)
    if len(pcm_data) % 2 != 0:
        pcm_data = pcm_data[:-1]

    # For mono, take only first half (planar stereo format)
    if channels == 1:
        pcm_data = pcm_data[:len(pcm_data)//2]

    # Convert from Big Endian to Little Endian
    pcm_array = array.array('h', pcm_data)
    pcm_array.byteswap()

    return pcm_array.tobytes()


def sanitize_filename(name: str, idx: int) -> str:
    """
    Sanitize filename to remove invalid characters.

    Args:
        name: Original filename
        idx: Sample index as fallback

    Returns:
        Sanitized filename
    """
    if not name:
        return f"sample_{idx:03d}"

    clean_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
    if not clean_name:
        clean_name = f"sample_{idx:03d}"

    return clean_name


def extract_mta(mta_path: Path, out_dir: Path, verbose: bool = False) -> int:
    """
    Extract audio samples from an MTA file.

    Args:
        mta_path: Path to the input MTA file
        out_dir: Directory to save extracted WAV files
        verbose: If True, print detailed progress information

    Returns:
        Number of files successfully extracted
    """
    if not mta_path.exists():
        print(f"Error: File not found: {mta_path}")
        return 0

    try:
        data = mta_path.read_bytes()
    except Exception as e:
        print(f"Error: Could not read file {mta_path}: {e}")
        return 0

    # Find DWAV section
    dwav_section_start = find_dwav_section(data)
    if dwav_section_start is None:
        print("Error: Could not find DWAV section in file")
        return 0

    if verbose:
        print(f"DWAV section found at offset: {hex(dwav_section_start)}")

    # Parse audio entries
    entries = parse_audio_entries(data, dwav_section_start)

    if not entries:
        print("No audio entries found in file")
        return 0

    if verbose:
        print(f"Found {len(entries)} audio entries")

    # Create output directory
    out_dir.mkdir(parents=True, exist_ok=True)

    extracted_count = 0

    # Extract each audio sample
    for i, (idx, start) in enumerate(entries):
        try:
            # Calculate sample size
            if i + 1 < len(entries):
                size = entries[i+1][1] - start
            else:
                size = len(data) - start

            if size < 80:  # Minimum header size
                continue

            # Read header
            header = data[start:start+80]

            # Extract metadata
            name = extract_sample_name(header)
            sample_rate, channels = parse_audio_header(header)

            # Extract PCM data
            pcm_start = start + 80
            pcm_data = data[pcm_start:start+size]

            if len(pcm_data) < 2:
                continue

            # Process PCM data
            processed_pcm = process_pcm_data(pcm_data, channels)

            # Generate output filename
            clean_name = sanitize_filename(name, idx)
            out_path = out_dir / f"{idx:03d}_{clean_name}.wav"

            # Write WAV file
            with wave.open(str(out_path), "wb") as wav:
                wav.setnchannels(channels)
                wav.setsampwidth(2)  # 16-bit samples
                wav.setframerate(sample_rate)
                wav.writeframes(processed_pcm)

            extracted_count += 1

            if verbose:
                print(f"[{i+1}/{len(entries)}] Extracted: {out_path.name}")

        except Exception as e:
            if verbose:
                print(f"Warning: Failed to extract entry {idx}: {e}")
            continue

    print(f"Extraction complete. {extracted_count} files extracted to {out_dir}")
    return extracted_count


def main():
    """Main entry point for the MTA extractor."""
    parser = argparse.ArgumentParser(
        description="Extract audio samples from MTA (Multi-Track Audio) files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mta audio.mta --out output/
  %(prog)s --mta audio.mta --out output/ --verbose
        """
    )
    parser.add_argument(
        "--mta",
        type=Path,
        required=True,
        help="Path to the input MTA file"
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output directory for extracted WAV files"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()
    extract_mta(args.mta, args.out, args.verbose)


if __name__ == "__main__":
    main()
