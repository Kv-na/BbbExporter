
# BbbExporter

**BbbExporter** is a Python script to export BigBlueButton (BBB) presentations as a PDF file.

Based on [this project](https://github.com/Cra-ban/BBBExporter) which in turn is based on the previous version of this project right here.

---

## Features

- Extracts SVG presentation data from a given BigBlueButton URL.
- Adjusts the SVG content to be viewable independently.
- Saves the presentation as a PDF file for easy sharing and offline access.

---

## Prerequisites

You need Python 3.x installed. You will also need to install a few third-party libraries. 
Run the following command to install the required Python packages:

```bash
pip install weasyprint svgutils
```

*Note: `weasyprint` relies on some system-level libraries (like Pango and Cairo) to render fonts and layouts. If you run into installation errors regarding WeasyPrint, check out their [official installation guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) for your specific operating system.*

---

## Usage

Run the launcher script from the terminal, passing the target presentation URL as the single argument:

```bash
python launcher.py <presentation_url>
```
*Note: make sure you are using the PRESENTATION url and NOT the VIDEO url*

*also: the reason why there is a launcher and a seperate script is because i built this to be running on the backend of my [website](https://kuna.fish/bbbexp.html)*

---


## Output:
You will find your generated file in the pdf folder:
- A PDF file: `pdfs/my_presentation_id.pdf`
