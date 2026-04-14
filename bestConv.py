import json
import os
import sys
import xml.etree.ElementTree as ET
from urllib.request import urlopen
from weasyprint import HTML #weasyprint is bad but everything else failed
import svgutils.transform as sg #we love svgutils
from collections import defaultdict
import shutil
import concurrent.futures # paralellism better fix the speed

# config
TARGET_WIDTH, TARGET_HEIGHT = 1438, 876
MERGED_DIR, HTML_DIR, PDF_DIR = "merged_svgs", "html", "pdfs"

# util

def splitString(strng, sep, pos):
    parts = strng.split(sep)
    return sep.join(parts[:pos]), sep.join(parts[pos:])


def shape_to_svg_path(shape):
    # tldraw json structure is weird
    sd = shape.get("shape_data", {})
    if not sd: 
        # print("missing shape data")
        return None
        
    props = sd.get("props", {})
    
    # float because sometimes string?
    offset_x = float(sd.get("x", 0.0))
    offset_y = float(sd.get("y", 0.0))
    
   
    is_closed = bool(props.get("isClosed", False))
    color = str(props.get("color", "black"))
    size = str(props.get("size", "m")).lower()
    is_pen = bool(sd.get("isPen", False))

    # tldraw syntax fixer
    if "light-" in color:
        color = color.replace("light-", "light")

    stroke_width = 1 if size == 's' else (5 if size == 'l' else 3)
    
    raw_segments = props.get("segments", [])
    points = []
    for seg in raw_segments:
        for p in seg.get("points", []):
            px = float(p.get("x", 0.0)) + offset_x
            py = float(p.get("y", 0.0)) + offset_y
            points.append((px, py))

    if len(points) < 2:
        return None

    #svg path maker
    try:
        start_cmd = f"M {points[0][0]:.3f} {points[0][1]:.3f}"
        line_cmds = [f"L {pt[0]:.3f} {pt[1]:.3f}" for pt in points[1:]]
        
        path_parts = [start_cmd] + line_cmds
        if is_closed:
            path_parts.append("Z")
            
        path_d = " ".join(path_parts)
    except Exception as e:
        print(f"[!] Path string generation failed: {e}")
        return None

    stroke_linecap = "round" if is_pen else "butt"
    fill = props.get("fill", "none")
    
    dash_prop = props.get("dash", "")
    dash_str = ""
    if dash_prop == "dashed":
        dash_str = ' stroke-dasharray="5,5"'
    elif dash_prop == "dotted":
        dash_str = ' stroke-dasharray="1,4"'

    #tadaaa
    return f'<path d="{path_d}" stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="{stroke_linecap}" fill="{fill}"{dash_str} />'

def export_page_to_svg_content(page):
    if not page:
        print("[!] Warning: Page missing, creating empty SVG content.")
        page = {}

    shapes = list(page.get("shapes", {}).values()) if isinstance(page.get("shapes"), dict) else page.get("shapes", [])
    svg_elems = [shape_to_svg_path(s) for s in shapes if shape_to_svg_path(s)]
    svg_content = "\n  ".join(svg_elems)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 {TARGET_WIDTH} {TARGET_HEIGHT}"
    width="{TARGET_WIDTH}" height="{TARGET_HEIGHT}">
  {svg_content}
</svg>'''
    return svg


def merge_and_fix_svg_in_memory(page_svg_content, slide_svg_content, output_path):
    try:
        # loading content for merge
        overlay = sg.fromstring(page_svg_content).getroot()
        background = sg.fromstring(slide_svg_content).getroot()
    except Exception as e:
        print(f"[!] Error loading SVG content for merge: {e}")
        return

    # funny magic number 453.543
    background.scale(TARGET_WIDTH / 453.543) 
    background.moveto(0, 0)

    final_fig = sg.SVGFigure(str(TARGET_WIDTH), str(TARGET_HEIGHT))
    final_fig.append([background, overlay])
    final_fig.root.set("viewBox", f"0 0 {TARGET_WIDTH} {TARGET_HEIGHT}")
    final_fig.root.set("width", str(TARGET_WIDTH))
    final_fig.root.set("height", str(TARGET_HEIGHT))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    # saves to disk here because push_g_styles_to_paths is picky
    final_fig.save(output_path) 
    
    push_g_styles_to_paths(output_path)
    print(f"[+] Merged & fixed SVG saved -> {output_path}")


def parse_shapes_svg(svg_string):
    root = ET.fromstring(svg_string)
    ns = {"svg": "http://www.w3.org/2000/svg", "xlink": "http://www.w3.org/1999/xlink"}
    return [(img.attrib.get("id"), img.attrib.get("{http://www.w3.org/1999/xlink}href")) for img in root.findall(".//svg:image", ns)]


def push_g_styles_to_paths(svg_path):
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

    tree = ET.parse(svg_path)
    root = tree.getroot()

    defs = root.find(".//{http://www.w3.org/2000/svg}defs")
    if defs is None:
        print("[!] No <defs> found in SVG.")
        return

    defs_group = defs.find("{http://www.w3.org/2000/svg}g")
    if defs_group is None:
        print("[!] No <g> inside <defs> found in SVG.")
        return

    #symbols get ids
    symbol_map = {el.attrib["id"]: el for el in root.findall(".//{http://www.w3.org/2000/svg}symbol") if "id" in el.attrib}

    # tracks applied styles
    applied_styles = defaultdict(set)

    # counts suffix for clones
    suffix_counters = defaultdict(int)

    for g in root.findall(".//{http://www.w3.org/2000/svg}g"):
        if g in defs_group.iter():
            continue

        g_style = g.attrib.get("style")
        if not g_style:
            continue

        for use in g.findall("{http://www.w3.org/2000/svg}use"):
            href = use.attrib.get("{http://www.w3.org/1999/xlink}href")
            if not href or not href.startswith("#"):
                continue

            original_id = href[1:]
            if original_id not in symbol_map:
                continue

            #important for checking the styles applied to the clones
            found_existing = False
            if g_style in applied_styles[original_id]:
                for sym_id in symbol_map:
                    if sym_id.startswith(original_id) and sym_id != original_id:
                        sym_paths = symbol_map[sym_id].findall(".//{http://www.w3.org/2000/svg}path")
                        if any(g_style in (p.attrib.get("style") or "") for p in sym_paths):
                            use.attrib["{http://www.w3.org/1999/xlink}href"] = f"#{sym_id}"
                            found_existing = True
                            break
                if found_existing:
                    continue

            # important for symbol cloning stuff
            suffix_counters[original_id] += 1
            suffix = chr(96 + suffix_counters[original_id])  # a, b, c...
            new_id = f"{original_id}{suffix}"

            original_symbol = symbol_map[original_id]
            # the affirmentioned "symbol cloning stuff"
            new_symbol = ET.fromstring(ET.tostring(original_symbol))
            new_symbol.attrib["id"] = new_id

            # applies g styles to the paths
            for path in new_symbol.findall(".//{http://www.w3.org/2000/svg}path"):
                existing_style = path.attrib.get("style", "")
                path.attrib["style"] = f"{existing_style};{g_style}" if existing_style else g_style

            defs_group.append(new_symbol)
            symbol_map[new_id] = new_symbol
            applied_styles[original_id].add(g_style)

            # href updater
            use.attrib["{http://www.w3.org/1999/xlink}href"] = f"#{new_id}"

    tree.write(svg_path, encoding="utf-8", xml_declaration=True)


def cleanup_temp_dirs(dirs):
    for d in dirs:
        if os.path.isdir(d):
            try:
                shutil.rmtree(d)
                print(f"[+] Cleaned up temporary directory: {d}")
            except OSError as e:
                print(f"[!] Error cleaning up directory {d}: {e}")

# simutaineously logic 

def process_slide(idx, slide_path, data, base_url):

    page_key = str(idx)
    page_data = data.get(page_key)

    #generates svg shapes content (in to memory now wooo)
    page_svg_content = export_page_to_svg_content(page_data)

    #gets slide BG svg content (from the netWOKE)
    try:
        # puts the content into the memory
        slide_url = base_url + slide_path
        slide_svg_content = urlopen(slide_url).read().decode("utf-8")
    except Exception as e:
        print(f"[!] Could not fetch slide SVG for index {idx} ({slide_path}): {e}")
        return None

    #merge and fix 
    output_path = os.path.join(MERGED_DIR, f"merged_{idx}.svg")
    merge_and_fix_svg_in_memory(page_svg_content, slide_svg_content, output_path)
    
    return output_path

# main

def main():
    if len(sys.argv) < 2:
        print("Usage: python newconv.py <presentation_url>")
        sys.exit(1)
        
    print(r"""
   ___  ___  ___      ____                    __         
  / _ )/ _ )/ _ )____/ __/_ __ ___  ___  ____/ /____ ____
 / _  / _  / _  /___/ _/ \ \ // _ \/ _ \/ __/ __/ -_) __/
/____/____/____/   /___//_\_\/ .__/\___/_/  \__/\__/_/   
                            /_/  (not endorsed by H.D. Lang)
""")
    presentation_url = sys.argv[1].strip()
    _, output_filename = splitString(presentation_url, "/", -1)
    domain, _ = splitString(presentation_url, "/", 3)

    base_url = f"{domain}/presentation/{output_filename}/"
    
    #dirty directories that we need to wash
    temp_dirs = [MERGED_DIR, HTML_DIR] 

    try:
        #data grabber 
        svg_data = urlopen(base_url + "shapes.svg").read().decode("utf-8")
        data = json.loads(urlopen(base_url + "tldraw.json").read().decode("utf-8"))
    except Exception as e:
        print(f"[!] Error fetching presentation data: {e}")
        cleanup_temp_dirs(temp_dirs)
        sys.exit(1)

    # makes the important dirs if not already
    for d in [MERGED_DIR, HTML_DIR, PDF_DIR]:
        os.makedirs(d, exist_ok=True)

    images = parse_shapes_svg(svg_data)
    
    merged_files = []
    
    #concurrent processing because otherwise its slow af
    print(f"[*] Starting concurrent processing of {len(images)} slides...")
    MAX_WORKERS = 10 # adjust THIS based on CPU cores and network speed 
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        future_to_slide = {
            executor.submit(process_slide, idx, slide_path, data, base_url): idx
            for idx, (_, slide_path) in enumerate(images, start=1)
        }
        for future in concurrent.futures.as_completed(future_to_slide):
            result = future.result()
            if result:
                merged_files.append(result)
            
    print("[*] All slides processed concurrently.")

    #pdf generator stuff
    
    #COLLECT MY PAGES sequentially 
    svg_files = sorted(
        [os.path.basename(f) for f in merged_files],
        key=lambda x: int(x.split("_")[1].split(".")[0])
    )

    html_pages = []
    for fname in svg_files:
        with open(os.path.join(MERGED_DIR, fname), "r", encoding="utf-8") as f:
            html_pages.append(f'<div style="page-break-after: always;">{f.read()}</div>')

    html_content = f"""
    <html><head><style>
    @page {{ size: {TARGET_WIDTH}px {TARGET_HEIGHT}px;
    margin: 0; }}
    body {{ margin: 0;
    }}
    </style></head><body>
    {''.join(html_pages)}
    </body></html>
    """

    html_out, pdf_out = os.path.join(HTML_DIR, f"{output_filename}.html"), os.path.join(PDF_DIR, f"{output_filename}.pdf")
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[+] HTML saved -> {html_out}")

    try:
        HTML(string=html_content).write_pdf(pdf_out)

        #DO NOT EXIT UNTIL A PDF EXISTS!!!
        with open(pdf_out, "rb") as f:
            f.read(1)

        print(f"[+] PDF saved -> {pdf_out}")

    except Exception as e:
        print(f"[!] Error generating PDF: {e}")
    finally:
        # more tmp cleanup
        cleanup_temp_dirs(temp_dirs)


if __name__ == "__main__":
    main()
