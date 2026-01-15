# MTA Audio Extractor

A Python tool for extracting audio samples from MTA (Multi-Track Audio) files and converting them to WAV format.

## About

This project was created through reverse engineering to extract audio samples from the **Yamaha DTX Multi 12** electronic drum module. The MTA file format used by Yamaha's DTX series stores multiple audio samples in a proprietary container format. This tool allows users to extract individual samples from these files for backup, analysis, or use in other applications.

The reverse engineering process involved analyzing the binary structure of MTA files to understand:
- The DWAV section layout and entry table structure
- Audio sample header format and metadata encoding
- PCM data storage format and channel configuration
- Big Endian byte order used by the Yamaha hardware

## Features

- Extracts individual audio samples from MTA files
- Automatically detects sample rate and channel configuration
- Handles both mono and stereo audio formats
- Converts audio data from Big Endian to Little Endian format
- Generates clean, sanitized filenames for output files

## Requirements

- Python 3.6 or higher
- Standard library only (no external dependencies required)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd mta-extractor
```

2. Make the script executable (optional):
```bash
chmod +x mta_extractor.py
```

## Usage

### Basic Usage

Extract all audio samples from an MTA file:

```bash
python mta_extractor.py --mta input.mta --out output_directory/
```

### Verbose Mode

Get detailed progress information:

```bash
python mta_extractor.py --mta input.mta --out output_directory/ --verbose
```

### Command Line Arguments

- `--mta` (required): Path to the input MTA file
- `--out` (required): Output directory where WAV files will be saved
- `--verbose` or `-v` (optional): Enable verbose output showing extraction progress

## How It Works

1. **DWAV Section Detection**: The tool reads the MTA file and locates the DWAV section at offset `0xC4-0xC8`.

2. **Entry Parsing**: It parses the audio entry table starting 32 bytes after the DWAV section, reading index and pointer information for each audio sample.

3. **Header Extraction**: For each entry, it reads the 80-byte header containing:
   - Sample name (16 bytes, ASCII)
   - Sample rate (offset 0x36-0x38)
   - Channel configuration (offset 0x49)

4. **PCM Processing**:
   - Extracts raw PCM data starting at offset 80 from each sample header
   - For mono channels, handles planar stereo format by taking only the first half of the data
   - Converts audio data from Big Endian to Little Endian format

5. **WAV Generation**: Creates standard WAV files with proper headers and writes the processed PCM data.

## Output Format

Extracted files are named using the pattern:
```
{index:03d}_{sample_name}.wav
```

Where:
- `index` is the zero-padded 3-digit sample index
- `sample_name` is the sanitized name from the MTA header (or "sample_{index}" if no name is found)

## File Format Details

### MTA File Structure

- **DWAV Section Offset**: Located at bytes `0xC4-0xC8` (Big Endian)
- **Entry Table**: Starts 32 bytes after DWAV section, each entry is 32 bytes
  - Bytes 0-3: Sample index
  - Bytes 8-11: Relative audio pointer (offset from DWAV section)
- **Audio Sample Header**: 80 bytes per sample
  - Bytes 0-15: Sample name (ASCII, null-terminated)
  - Bytes 0x36-0x37: Sample rate (Big Endian)
  - Byte 0x49: Channel configuration (0x00 = Mono, 0x02 = Stereo)
- **PCM Data**: Starts at offset 80 from sample header, 16-bit Big Endian samples

## Error Handling

The tool includes robust error handling:
- Validates file existence before processing
- Checks for valid DWAV section offsets
- Skips invalid or corrupted entries
- Provides clear error messages for common issues

## Compatible Hardware

This tool was specifically developed and tested with:
- **Yamaha DTX Multi 12** - Electronic drum module

The MTA file format is used by Yamaha's DTX series, so this tool should work with other DTX models that use the same file format. However, it has been primarily tested with the DTX Multi 12.

## Limitations

- Currently supports 16-bit PCM audio only
- Assumes Big Endian byte order for input data
- Mono samples are assumed to be stored in planar stereo format
- File format structure is based on reverse engineering and may not support all MTA file variations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is provided as-is for educational and research purposes.

## Troubleshooting

### "Could not find DWAV section"
- Verify that the input file is a valid MTA file
- Check that the file is not corrupted

### "No audio entries found"
- The MTA file may not contain any audio samples
- The file format may differ from expected structure

### Output files are silent or distorted
- Verify the source MTA file is not corrupted
- Check that the sample rate and channel configuration are being detected correctly
- Try using verbose mode to see detailed extraction information
