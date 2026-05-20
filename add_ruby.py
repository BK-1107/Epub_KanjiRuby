# -*- coding: utf-8 -*-
import os
import sys
import argparse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, NavigableString
from fugashi import Tagger



def to_hiragana(katakana):
    """
    Converts a Katakana string to Hiragana.
    """
    res = []
    for char in katakana:
        code = ord(char)
        # Katakana block: 0x30A1 - 0x30F6
        if 0x30A1 <= code <= 0x30F6:
            res.append(chr(code - 0x60))
        else:
            res.append(char)
    return "".join(res)

def is_kanji(char):
    """
    Checks if a character is a Japanese Kanji.
    """
    return 0x4E00 <= ord(char) <= 0x9FFF

def align(surface, reading):
    """
    Advanced alignment algorithm using memoized DP search.
    Matches surface characters to segments of reading.
    """
    surf_h = to_hiragana(surface)
    read_h = to_hiragana(reading)
    
    memo = {}
    
    def search(s_idx, r_idx):
        state = (s_idx, r_idx)
        if state in memo:
            return memo[state]
            
        # Base cases
        if s_idx == len(surface) and r_idx == len(read_h):
            return []
        if s_idx == len(surface) or r_idx == len(read_h):
            return None
            
        s_char = surface[s_idx]
        s_char_h = surf_h[s_idx]
        
        # If surface char is not Kanji (e.g. Hiragana, Katakana, punctuation, etc.)
        if not is_kanji(s_char):
            r_char_h = read_h[r_idx]
            if s_char_h == r_char_h:
                rest = search(s_idx + 1, r_idx + 1)
                if rest is not None:
                    res = [('kana', s_char, r_char_h)] + rest
                    memo[state] = res
                    return res
            memo[state] = None
            return None
            
        # If surface char is Kanji, try matching against substrings of reading
        for length in range(1, len(read_h) - r_idx + 1):
            r_part = read_h[r_idx : r_idx + length]
            rest = search(s_idx + 1, r_idx + length)
            if rest is not None:
                res = [('kanji', s_char, r_part)] + rest
                memo[state] = res
                return res
                
        memo[state] = None
        return None

    return search(0, 0)

def fallback_align(surface, reading):
    """
    Fallback alignment using simple prefix-suffix okurigana stripping.
    Used if DP alignment fails.
    """
    surf_h = to_hiragana(surface)
    read_h = to_hiragana(reading)
    
    # 1. Match prefix kana
    prefix_len = 0
    while (prefix_len < len(surface) and 
           prefix_len < len(read_h) and 
           not is_kanji(surface[prefix_len]) and 
           to_hiragana(surface[prefix_len]) == read_h[prefix_len]):
        prefix_len += 1
        
    # 2. Match suffix kana
    suffix_len = 0
    while (suffix_len < len(surface) - prefix_len and 
           suffix_len < len(read_h) - prefix_len and 
           not is_kanji(surface[len(surface) - 1 - suffix_len]) and 
           to_hiragana(surface[len(surface) - 1 - suffix_len]) == read_h[len(read_h) - 1 - suffix_len]):
        suffix_len += 1
        
    mid_surf = surface[prefix_len : len(surface) - suffix_len]
    mid_read = read_h[prefix_len : len(read_h) - suffix_len]
    
    if mid_surf and all(is_kanji(c) for c in mid_surf) and mid_read:
        parts = []
        if prefix_len > 0:
            parts.append(('kana', surface[:prefix_len], read_h[:prefix_len]))
        parts.append(('kanji', mid_surf, mid_read))
        if suffix_len > 0:
            parts.append(('kana', surface[len(surface)-suffix_len:], read_h[len(read_h)-suffix_len:]))
        return parts
        
    return None

def merge_alignment(alignment):
    """
    Merges consecutive kanji or kana elements together to generate clean ruby segments.
    """
    if not alignment:
        return []
    merged = []
    current_type = None
    current_surf = []
    current_read = []
    
    for item_type, surf, read in alignment:
        if item_type == 'kanji':
            if current_type == 'kanji':
                current_surf.append(surf)
                current_read.append(read)
            else:
                if current_type is not None:
                    merged.append((current_type, "".join(current_surf), "".join(current_read)))
                current_type = 'kanji'
                current_surf = [surf]
                current_read = [read]
        else: # item_type == 'kana'
            if current_type == 'kana':
                current_surf.append(surf)
                current_read.append(read)
            else:
                if current_type is not None:
                    merged.append((current_type, "".join(current_surf), "".join(current_read)))
                current_type = 'kana'
                current_surf = [surf]
                current_read = [read]
                
    if current_type is not None:
        merged.append((current_type, "".join(current_surf), "".join(current_read)))
        
    return merged

def align_word(surface, reading):
    """
    Aligns a surface word with its reading, returning a merged list of segments.
    """
    # If no Kanji, return as-is
    if not any(is_kanji(c) for c in surface):
        return [('kana', surface, surface)]
        
    if not reading or reading == '*':
        return [('kana', surface, surface)]
        
    reading_h = to_hiragana(reading)
    
    # Try DP alignment
    alignment = align(surface, reading_h)
    if alignment:
        return merge_alignment(alignment)
        
    # Try fallback alignment
    fallback = fallback_align(surface, reading_h)
    if fallback:
        return merge_alignment(fallback)
        
    # Fallback to returning original surface without annotation if all alignments fail
    return [('kana', surface, surface)]

def should_annotate(surface):
    """
    Determines if a word should be annotated with Ruby (if it contains any Kanji).
    """
    return any(is_kanji(c) for c in surface)

def annotate_text(text, tagger, add_rp, soup):
    """
    Tokenizes a block of text, aligns words, and returns a list of BS4 nodes
    (NavigableStrings and <ruby> tags) while preserving whitespace and symbols.
    """
    tokens = list(tagger(text))
    
    # Quick optimization: check if there's any Kanji needing annotation first
    any_change = False
    for token in tokens:
        surf = token.surface
        reading = token.feature.kana
        if should_annotate(surf) and reading and reading != '*':
            alignment = align_word(surf, reading)
            if any(t == 'kanji' for t, s, r in alignment):
                any_change = True
                break
                
    if not any_change:
        return None
        
    new_nodes = []
    i = 0
    t_idx = 0
    
    while i < len(text):
        # 1. Consume all whitespaces first, preserving them exactly
        ws = []
        while i < len(text) and text[i].isspace():
            ws.append(text[i])
            i += 1
        if ws:
            new_nodes.append(NavigableString("".join(ws)))
            continue
            
        # 2. Process token alignment
        if t_idx < len(tokens):
            token = tokens[t_idx]
            surf = token.surface
            
            # Skip whitespace tokens in MeCab since we handled them in step 1
            if surf.isspace():
                t_idx += 1
                continue
                
            # If the current substring matches MeCab token surface
            if text[i : i + len(surf)] == surf:
                reading = token.feature.kana
                
                if should_annotate(surf) and reading and reading != '*':
                    alignment = align_word(surf, reading)
                    for item_type, s_part, r_part in alignment:
                        if item_type == 'kanji':
                            ruby_tag = soup.new_tag('ruby')
                            ruby_tag.append(NavigableString(s_part))
                            
                            if add_rp:
                                rp_open = soup.new_tag('rp')
                                rp_open.append(NavigableString('（'))
                                ruby_tag.append(rp_open)
                                
                            rt_tag = soup.new_tag('rt')
                            rt_tag.append(NavigableString(r_part))
                            ruby_tag.append(rt_tag)
                            
                            if add_rp:
                                rp_close = soup.new_tag('rp')
                                rp_close.append(NavigableString('）'))
                                ruby_tag.append(rp_close)
                                
                            new_nodes.append(ruby_tag)
                        else:
                            new_nodes.append(NavigableString(s_part))
                else:
                    new_nodes.append(NavigableString(surf))
                    
                i += len(surf)
                t_idx += 1
            else:
                # If there is a mismatch (e.g. skipped punctuation), copy 1 char and advance
                new_nodes.append(NavigableString(text[i]))
                i += 1
        else:
            # Copy all remaining text
            new_nodes.append(NavigableString(text[i:]))
            break
            
    return new_nodes

def split_ruby_tags(soup):
    """
    Splits multi-rt ruby tags (e.g. <ruby>A<rt>a</rt>B<rt>b</rt></ruby>) into
    individual single-rt ruby tags (<ruby>A<rt>a</rt></ruby><ruby>B<rt>b</rt></ruby>).
    This ensures CSS Flexbox hacks layout correctly without text overlap on readers
    that lack native ruby support.
    """
    modified = False
    for ruby in list(soup.find_all('ruby')):
        children = list(ruby.contents)
        rt_count = sum(1 for c in children if getattr(c, 'name', None) == 'rt')
        if rt_count <= 1:
            continue
            
        new_rubies = []
        current_base = []
        
        for child in children:
            if getattr(child, 'name', None) == 'rt':
                new_ruby = soup.new_tag('ruby')
                for b in current_base:
                    new_ruby.append(b)
                new_ruby.append(child)
                new_rubies.append(new_ruby)
                current_base = []
            elif getattr(child, 'name', None) == 'rp':
                continue
            else:
                current_base.append(child)
                
        if current_base:
            new_rubies.extend(current_base)
            
        for new_el in new_rubies:
            ruby.insert_before(new_el)
        ruby.extract()
        modified = True
        
    return modified

def process_xhtml_file(file_path, tagger, add_rp=False):
    """
    Parses an XHTML file, modifies its body text nodes, validates XML well-formedness,
    and writes the results back.
    """
    print(f"Processing: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    soup = BeautifulSoup(content, 'xml')
    body = soup.find('body')
    if not body:
        print(f"Skipping {file_path}: No <body> tag found.")
        return False
        
    # Traverse DOM recursively to locate raw text nodes
    text_nodes = []
    
    def collect_text_nodes(element):
        # DO NOT process tags that represent existing ruby markup or styles/scripts
        if element.name in ('ruby', 'rt', 'rp', 'script', 'style', 'head', 'title'):
            return
            
        for child in list(element.children):
            if isinstance(child, NavigableString):
                # Ignore purely whitespace text nodes
                if child.strip():
                    text_nodes.append(child)
            elif child.name:
                collect_text_nodes(child)
                
    collect_text_nodes(body)
    
    # Annotate each text node in-place
    modified_count = 0
    for node in text_nodes:
        if not node.parent:
            continue
            
        annotated_nodes = annotate_text(node.string, tagger, add_rp, soup)
        if annotated_nodes:
            # Insert the new nodes before the original node, then extract the original
            for new_node in annotated_nodes:
                node.insert_before(new_node)
            node.extract()
            modified_count += 1
            
    # Also split any multi-rt ruby tags (original and new) to ensure universal compatibility
    if split_ruby_tags(soup):
        modified_count += 1
        
    if modified_count == 0:
        print(f"No changes made to {file_path}")
        return False
        
    # Standardize XML output
    output_xml = soup.decode(formatter="minimal")
    
    # XML well-formedness validation
    try:
        ET.fromstring(output_xml.encode('utf-8'))
    except ET.ParseError as e:
        print(f"Error: Generated XML for {file_path} is malformed! Details: {e}")
        # Write to a debug file for investigation instead of overwriting the original
        debug_path = file_path + ".debug.xhtml"
        with open(debug_path, "w", encoding="utf-8") as df:
            df.write(output_xml)
        print(f"Malformed XML written to {debug_path} for debugging. Aborting file overwrite.")
        return False
        
    # Overwrite the original file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(output_xml)
        
    print(f"Successfully processed {file_path} ({modified_count} text blocks annotated)")
    return True

def run_ruby_annotation(extracted_dir, add_rp=False, include_nav=False):
    """
    Runs the ruby annotation on the target XHTML files in the extracted EPUB directory.
    """
    tagger = Tagger()
    
    # Search for files under OEBPS/Text
    text_dir = os.path.join(extracted_dir, 'OEBPS', 'Text')
    if not os.path.exists(text_dir):
        print(f"Error: Text directory not found: {text_dir}")
        return False
        
    xhtml_files = []
    for file in os.listdir(text_dir):
        if file.endswith('.xhtml') or file.endswith('.html'):
            # Filter targeted files
            if not include_nav:
                # Exclude standard navigation/meta files
                basename = file.lower()
                if any(x in basename for x in ('nav', 'toc', 'cover', 'title', 'copyright', 'colophon', 'license')):
                    continue
            xhtml_files.append(os.path.join(text_dir, file))
            
    print(f"Found {len(xhtml_files)} target files to process.")
    
    success_count = 0
    for file_path in sorted(xhtml_files):
        try:
            if process_xhtml_file(file_path, tagger, add_rp):
                success_count += 1
        except Exception as e:
            print(f"Exception raised while processing {file_path}: {e}")
            
    print(f"Finished processing! Successfully modified {success_count} files.")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Japanese EPUB Kanji Ruby Annotator")
    parser.add_argument("extracted_dir", help="Path to the extracted EPUB directory")
    parser.add_argument("--rp", action="store_true", help="Add <rp> fallback tags for old e-readers")
    parser.add_argument("--include-nav", action="store_true", help="Process navigation and cover XHTML files")
    
    args = parser.parse_args()
    
    run_ruby_annotation(args.extracted_dir, args.rp, args.include_nav)
