use reqwest::blocking::get;
use std::fs;
use std::io;
use std::path::Path;

fn extract_id_from_url(url: &str) -> Option<&str> {
    let segments: Vec<&str> = url.split('/').collect();
    segments.last().map(|s| *s)
}

fn extract_domain_from_url(url: &str) -> Option<&str> {
    let segments: Vec<&str> = url.split('/').collect();
    segments.get(2).map(|s| *s)
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut presentation_url = String::new();
    let mut output_filename = String::new();

    println!("Enter the BBB presentation URL:");
    io::stdin().read_line(&mut presentation_url)?;
    println!("Enter the output file name (without extension):");
    io::stdin().read_line(&mut output_filename)?;

    let trimmed_url = presentation_url.trim();

    if let (Some(presentation_id), Some(domain_name)) = (
        extract_id_from_url(trimmed_url),
        extract_domain_from_url(trimmed_url),
    ) {
        let svg_url = format!(
            "https://{}/presentation/{}/shapes.svg",
            domain_name, presentation_id
        );
        let svg_response = get(&svg_url)?.text()?;
        let svg_file_name = Path::new(&svg_url).file_name().unwrap().to_str().unwrap();
        let base_svg_url = svg_url.replace(svg_file_name, "");

        let modified_svg_content = svg_response
            .replace("<image", r#"<svg viewBox="0 0 1600 976"> <image"#)
            .replace("presentation/", &format!("{}presentation/", base_svg_url))
            .replace("visibility:hidden", "")
            .replace(r#"<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" id="svgfile" style="position:absolute;height:600px;width:800px" version="1.1" viewBox="0 0 800 600">"#, "")
            .replace("display=\"none\"", "");

        let mut svg_parts: Vec<&str> = modified_svg_content.split("<svg").collect();
        let initial_svg = svg_parts.remove(0);
        let combined_svg = svg_parts.join("</svg> <svg");

        let final_html_content = format!(
            "<html>\n<body>\n{}<svg{}\n</body>\n</html>",
            initial_svg, combined_svg
        );

        let output_file_path = format!("{}.html", output_filename.trim());
        fs::write(output_file_path, final_html_content)?;
    }

    Ok(())
}
