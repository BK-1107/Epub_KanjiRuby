import os
import shutil
import zipfile
import argparse

# Epub解压程序

def extract_epub(epub_path, extract_dir):
    """
    Extracts all files from an EPUB file into a directory.
    """
    if not os.path.exists(epub_path):
        print(f"Error: EPUB file not found: {epub_path}")
        return False
    
    # If target directory exists, delete it first to ensure a clean extraction
    if os.path.exists(extract_dir):
        print(f"Target directory '{extract_dir}' already exists. Deleting it to ensure clean extraction...")
        shutil.rmtree(extract_dir)
        
    os.makedirs(extract_dir, exist_ok=True)
    
    print(f"Extracting '{epub_path}' to '{extract_dir}'...")
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print("Extraction completed successfully.")
    return True

def pack_epub(src_dir, output_epub_path):
    """
    Packs a directory into an EPUB file, ensuring compliance with the EPUB standard:
    1. 'mimetype' file must be written first.
    2. 'mimetype' must be uncompressed (zipfile.ZIP_STORED).
    3. Directory separators must be forward slashes '/'.
    """
    if not os.path.exists(src_dir):
        print(f"Error: Source directory not found: {src_dir}")
        return False
        
    mimetype_file = os.path.join(src_dir, 'mimetype')
    if not os.path.exists(mimetype_file):
        print("Warning: 'mimetype' file not found in source directory. Creating a default one.")
        
    print(f"Packing '{src_dir}' into '{output_epub_path}'...")
    
    # Create the zip file
    with zipfile.ZipFile(output_epub_path, 'w') as zip_file:
        # 1. Write the mimetype file first with ZIP_STORED (no compression)
        if os.path.exists(mimetype_file):
            zip_file.write(mimetype_file, 'mimetype', compress_type=zipfile.ZIP_STORED)
        else:
            zip_file.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
            
        # 2. Walk and write other files
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, src_dir)
                
                # Convert backslashes (Windows) to forward slashes (standard ZIP format)
                zip_rel_path = rel_path.replace(os.path.sep, '/')
                
                # Skip mimetype as we wrote it first
                if zip_rel_path == 'mimetype':
                    continue
                    
                # Write with DEFLATE compression
                zip_file.write(full_path, zip_rel_path, compress_type=zipfile.ZIP_DEFLATED)
                
    print(f"Repacking completed successfully! Saved as '{output_epub_path}'.")
    return True

def update_css_rules(css_file_path):
    """
    Appends the custom writing-mode targeted ruby rules to the CSS file.
    """
    if not os.path.exists(css_file_path):
        return
        
    with open(css_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    header = "/* =============================================================\\n * Ruby Annotations Compatibility Styles\\n * ============================================================= */"
    
    if "Ruby Annotations Compatibility Styles" in content:
        # Avoid double-injection, strip previous injection if exists
        parts = content.split("/* =============================================================")
        base_content = parts[0]
    else:
        base_content = content + "\n\n"

    new_styles = """/* =============================================================
 * Ruby Annotations Compatibility Styles
 * ============================================================= */
/* Horizontal Layout: use inline-table fallback to position rt above ruby base */
.hltr ruby {
  display: inline-table !important;
  text-indent: 0 !important;
  border-collapse: collapse !important;
  text-align: center !important;
  vertical-align: bottom !important;
  line-height: 1 !important;
  margin: 0 0.1em !important;
  padding: 0 !important;
  width: auto !important;
}

.hltr rt {
  display: table-header-group !important;
  font-size: 0.55em !important;
  line-height: 1.15 !important;
  text-align: center !important;
  margin: 0 !important;
  padding: 0 !important;
  letter-spacing: 0 !important;
}

/* Vertical Layout: let the reader's native vertical engine handle it perfectly */
.vrtl ruby {
  display: ruby !important;
  ruby-position: over !important;
  -webkit-ruby-position: over !important;
  -epub-ruby-position: over !important;
}

.vrtl rt {
  display: ruby-text !important;
  font-size: 0.55em !important;
  line-height: 1.15 !important;
  ruby-position: over !important;
  -webkit-ruby-position: over !important;
  -epub-ruby-position: over !important;
}
"""
    final_content = base_content.rstrip() + "\n\n" + new_styles
    with open(css_file_path, "w", encoding="utf-8") as f:
        f.write(final_content)
    print(f"CSS rules successfully updated: {css_file_path}")

def clean_css_empty_rules(css_file_path):
    """
    Cleans up empty CSS rulesets to avoid e-reader rendering/linter errors.
    """
    import re
    if not os.path.exists(css_file_path):
        return
        
    with open(css_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r'[^{}]*\{\s*\}')
    old_text = content
    while True:
        new_text = pattern.sub('', old_text)
        if new_text == old_text:
            break
        old_text = new_text

    cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', new_text)
    
    with open(css_file_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)
    print(f"Successfully cleaned empty rulesets in: {css_file_path}")

def batch_process_repository(add_rp=False, include_nav=False):
    """
    Scans the 'repository' folder for EPUB files, extracts them, injects CSS,
    annotates Kanji, repacks them, and saves the output to the root directory.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.join(script_dir, 'repository')
    if not os.path.exists(repo_dir):
        print(f"Creating '{repo_dir}' directory at {os.path.abspath(repo_dir)}...")
        os.makedirs(repo_dir, exist_ok=True)
        print("Please place your EPUB files in the 'repository' directory and run the command again.")
        return
        
    epub_files = [f for f in os.listdir(repo_dir) if f.lower().endswith('.epub')]
    if not epub_files:
        print(f"No EPUB files found in the '{repo_dir}' folder.")
        return
        
    print(f"Found {len(epub_files)} EPUB file(s) in '{repo_dir}' to process.")
    
    output_dir = script_dir
    
    for epub_name in epub_files:
        epub_path = os.path.join(repo_dir, epub_name)
        base_name_without_ext = os.path.splitext(epub_name)[0]
        temp_extract_dir = os.path.join(script_dir, f"temp_extracted_{base_name_without_ext}")
        output_epub_path = os.path.join(output_dir, epub_name)
        
        print("\n" + "="*60)
        print(f"Starting batch process for: {epub_name}")
        print("="*60)
        
        # 1. Extract
        if not extract_epub(epub_path, temp_extract_dir):
            print(f"Skipping {epub_name} due to extraction error.")
            continue
            
        # 2. Inject CSS and clean empty rules in all CSS files
        css_files = []
        for root, _, files in os.walk(temp_extract_dir):
            for file in files:
                if file.lower().endswith('.css'):
                    css_files.append(os.path.join(root, file))
                    
        for css_file in css_files:
            update_css_rules(css_file)
            clean_css_empty_rules(css_file)
            
        # 3. Add Kanji annotation
        from add_ruby import run_ruby_annotation
        print(f"Running Kanji annotations on {epub_name}...")
        try:
            run_ruby_annotation(temp_extract_dir, add_rp=add_rp, include_nav=include_nav)
        except Exception as e:
            print(f"Error during annotation of {epub_name}: {e}")
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            continue
            
        # 4. Pack back into root folder
        if not pack_epub(temp_extract_dir, output_epub_path):
            print(f"Error packing EPUB for {epub_name}")
        else:
            print(f"Successfully processed and saved: {output_epub_path}")
            
        # 5. Clean up temporary directory
        if os.path.exists(temp_extract_dir):
            print(f"Cleaning up temporary directory '{temp_extract_dir}'...")
            shutil.rmtree(temp_extract_dir)
            
    print("\nBatch processing completed successfully!")

def main():
    parser = argparse.ArgumentParser(description="EPUB Extraction and Repacking Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract EPUB file to a directory")
    extract_parser.add_argument("epub_file", help="Path to the .epub file")
    extract_parser.add_argument("extract_dir", nargs="?", default="extracted_epub", help="Directory to extract to (default: extracted_epub)")
    
    # Pack command
    pack_parser = subparsers.add_parser("pack", help="Pack a directory back into an EPUB file")
    pack_parser.add_argument("src_dir", help="Directory containing extracted EPUB content")
    pack_parser.add_argument("output_epub", help="Output path for the new .epub file")
    
    # Ruby command
    ruby_parser = subparsers.add_parser("ruby", help="Add ruby annotations to Kanji in the extracted EPUB content")
    ruby_parser.add_argument("src_dir", help="Directory containing extracted EPUB content")
    ruby_parser.add_argument("--rp", action="store_true", help="Add <rp> fallback tags for old e-readers")
    ruby_parser.add_argument("--include-nav", action="store_true", help="Process navigation and cover pages as well")
    
    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Batch process EPUB files in the 'repository' directory")
    batch_parser.add_argument("--rp", action="store_true", help="Add <rp> fallback tags for old e-readers")
    batch_parser.add_argument("--include-nav", action="store_true", help="Process navigation and cover pages as well")
    
    args = parser.parse_args()
    
    if args.command == "extract":
        extract_epub(args.epub_file, args.extract_dir)
    elif args.command == "pack":
        pack_epub(args.src_dir, args.output_epub)
    elif args.command == "ruby":
        from add_ruby import run_ruby_annotation
        run_ruby_annotation(args.src_dir, args.rp, args.include_nav)
    elif args.command == "batch":
        batch_process_repository(args.rp, args.include_nav)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
