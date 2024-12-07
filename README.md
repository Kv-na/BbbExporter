# BbbExporter

**BbbExporter** is a command-line tool to export BigBlueButton (BBB) presentations as a self-contained HTML file. This tool allows users to download the presentation's SVG content and prepare it for standalone viewing in a web browser.

---

## Features

- Extracts SVG presentation data from a given BigBlueButton URL.
- Adjusts the SVG content to be viewable independently.
- Saves the presentation as an HTML file for easy sharing and offline access.

---

## Requirements

- **Rust**: The tool is written in Rust, so you need to have Rust installed to compile and run it.
- **Dependencies**:
  - `reqwest`: For handling HTTP requests.
  - `std`: Standard Rust library for filesystem and I/O operations.

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/JoroKudo/BbbExporter.git
   cd BbbExporter
   ```

2. Build the project using Cargo:
   ```bash
   cargo build --release
   ```

3. The executable will be available in the `target/release/` directory:
   ```bash
   ./target/release/BbbExporter
   ```

---

## Usage

1. Run the executable:
   ```bash
   ./BbbExporter
   ```

2. Follow the prompts:
   - Enter the BigBlueButton presentation URL (e.g., `https://example.com/presentation/<presentation_id>`).
   - Enter the desired name for the output file (without the extension).

3. The tool will:
   - Fetch the SVG data from the specified URL.
   - Modify the content to ensure the presentation is fully viewable.
   - Save the result as an HTML file in the current directory.

---

## Example

### Input:
- BBB Presentation URL: `https://example.com/presentation/[UUID]`
- Output filename: `my_presentation`

### Output:
- An HTML file: `my_presentation.html`

You can open this file in any modern web browser to view the presentation.

---

## Code Overview

- **`extract_id_from_url(url: &str) -> Option<&str>`**: Extracts the presentation ID from the given URL.
- **`extract_domain_from_url(url: &str) -> Option<&str>`**: Extracts the domain name from the given URL.
- **`main()`**:
  - Reads the URL and output filename from the user.
  - Constructs the URL for the SVG data.
  - Fetches and modifies the SVG content.
  - Writes the modified content into an HTML file.

---

## Limitations

- Assumes the SVG files are structured in a specific way.
- Requires a valid BigBlueButton presentation URL.
- Internet connectivity is required to fetch the SVG data.
