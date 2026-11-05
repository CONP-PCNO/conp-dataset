#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import urllib.request
from typing import List, Dict, Any

# File extensions that must be stored as regular files (not annexed)
TEXT_EXTENSIONS = {'.csv', '.json', '.md', '.txt', '.py', '.yml', '.yaml', '.tsv', '.jsonld', '.html'}
TEXT_FILENAMES = {'README', 'LICENSE', 'CHANGES', 'AUTHORS', 'MANIFEST', 'DESCRIPTION'}

def is_text_file(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    base = os.path.basename(filename).upper()
    return ext in TEXT_EXTENSIONS or base in TEXT_FILENAMES

def run(cmd: list[str], cwd: str | None = None):
    subprocess.run(cmd, cwd=cwd, check=True)

def clean_title(title: str) -> str:
    """Sanitize the title: cap at 80 chars and strip shell-unsafe characters"""
    clean = title.replace('&', 'and')
    clean = re.sub(r'[<>:"/\\|?*(),]', '_', clean)
    clean = re.sub(r'\s+', '_', clean)
    clean = re.sub(r'_+', '_', clean)
    clean = clean.strip('_')
    if len(clean) > 80:
        clean = clean[:80].strip('_')
    return clean

def html_to_text(value: str) -> str:
    if not value: return ""
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def natural_size(num_bytes: int) -> tuple[float, str]:
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB"]
    size = float(num_bytes)
    unit = units[0]
    for u in units:
        unit = u
        if size < 1024:
            break
        size /= 1024
    return (round(size, 2), unit)

def download_file_to_disk(url: str, dest_path: str, token: str | None = None):
    """Download a file straight to the local disk"""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=300) as response, open(dest_path, "wb") as out_file:
        out_file.write(response.read())

def configure_git_attributes(dataset_dir: str):
    """Configure .gitattributes so text files stay out of the annex"""
    attr_path = os.path.join(dataset_dir, ".gitattributes")
    # Use the "nothing" syntax to repair the earlier parse error
    patterns = [
        "README.md annex.largefiles=nothing",
        "DATS.json annex.largefiles=nothing",
        ".conp-zenodo-crawler.json annex.largefiles=nothing",
        "*.csv annex.largefiles=nothing",
        "*.json annex.largefiles=nothing",
        "*.txt annex.largefiles=nothing",
        ".gitattributes annex.largefiles=nothing"
    ]
    with open(attr_path, "w") as f:
        f.write("\n".join(patterns) + "\n")
    run(["git", "add", ".gitattributes"], cwd=dataset_dir)

def generate_readme(record: dict, total_size: float, size_unit: str) -> str:
    metadata = record.get("metadata", {})
    return f"""# {metadata.get('title')}

## Description
{html_to_text(metadata.get('description', 'No description provided.'))}

## Metadata
- **Zenodo Record ID**: {record.get('id')}
- **DOI**: {metadata.get('doi', 'N/A')}
- **Total Size**: {total_size} {size_unit}
- **Keywords**: {", ".join(metadata.get('keywords', []))}

---
*Automatically imported via CONP-Zenodo-Crawler*
"""

def generate_dats_json(record: dict, total_size: float, size_unit: str, file_count: int) -> dict:
    metadata = record.get("metadata", {})
    return {
        "title": metadata.get("title"),
        "description": html_to_text(metadata.get("description")),
        "creators": [{"name": c.get("name")} for c in metadata.get("creators", [])],
        "version": metadata.get("version", "1.0.0"),
        "types": [{"information": {"value": "dataset"}}],
        "licenses": [{"name": metadata.get("license", "None")}],
        "keywords": [{"value": k} for k in metadata.get("keywords", [])] if metadata.get("keywords") else [{"value": "N/A"}],
        "distributions": [{
            "size": total_size,
            "unit": {"value": size_unit},
            "access": {"landingPage": f"https://zenodo.org/record/{record.get('id')}"},
            "formats": ["N/A"]
        }],
        "extraProperties": [
            {"category": "source", "values": [{"value": "zenodo"}]},
            {"category": "zenodo_record_id", "values": [{"value": str(record.get('id'))}]},
            {"category": "files", "values": [{"value": str(file_count)}]},
            {"category": "subjects", "values": [{"value": "N/A"}]},
            {"category": "CONP_status", "values": [{"value": "CONP"}]}
        ]
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True)
    parser.add_argument("--basedir", default=".")
    parser.add_argument("--zenodo-token")
    args = parser.parse_args()

    record_id = args.record.split("/")[-1]
    token = args.zenodo_token or os.getenv("ZENODO_TOKEN") or os.getenv("DATALAD_ZENODO_token")

    print(f"📥 Fetching Zenodo record {record_id}...")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(f"https://zenodo.org/api/records/{record_id}", headers=headers)
    with urllib.request.urlopen(req) as r:
        record = json.loads(r.read().decode())
    
    title = record.get("metadata", {}).get("title", f"Record_{record_id}")
    folder_name = clean_title(title)
    dataset_dir = os.path.abspath(os.path.join(args.basedir, "projects", folder_name))
    print(f"📂 Preparing directory: {dataset_dir}")
    os.makedirs(dataset_dir, exist_ok=True)

    print("🚀 Initializing DataLad (if needed)...")
    if not os.path.exists(os.path.join(dataset_dir, ".datalad")):
        run(["datalad", "create", "--force", "."], cwd=dataset_dir)
    else:
        print("✅ Directory is already a DataLad dataset, skipping creation.")
    configure_git_attributes(dataset_dir)

    files = record.get("files", [])
    total_bytes = sum([int(f.get("size", 0)) for f in files])
    total_size, size_unit = natural_size(total_bytes)

    # Track whether the metadata file has been handled yet
    has_readme = False
    has_dats = False

    print(f"🔗 Processing {len(files)} files...")
    for f_item in files:
        name = f_item["key"]
        url = f_item["links"]["self"]
        ext = os.path.splitext(name)[1].lower()
        dest = os.path.join(dataset_dir, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        if name.lower() == "readme.md": has_readme = True
        if name.lower() == "dats.json": has_dats = True

        if is_text_file(name):
            print(f"   📄 [TEXT] Downloading: {name}")
            # Fix: if the file already exists (possibly an annex symlink), remove it first, otherwise open() raises
            if os.path.lexists(dest):
                os.remove(dest)
            download_file_to_disk(url, dest, token)
            run(["git", "add", name], cwd=dataset_dir)
        else:
            print(f"   📦 [LARGE] Adding Link: {name}")
            run(["git", "annex", "addurl", url, "--fast", "--relaxed", "--file", name], cwd=dataset_dir)

    # --- Auto-generate the missing standard files ---
    if not has_readme:
        print("📝 Generating standard README.md...")
        with open(os.path.join(dataset_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(generate_readme(record, total_size, size_unit))
        run(["git", "add", "README.md"], cwd=dataset_dir)

    # --- Handle DATS.json (smart merge) ---
    dats_path = os.path.join(dataset_dir, "DATS.json")
    # First build a complete template to use as the reference
    perfect_dats = generate_dats_json(record, total_size, size_unit, len(files))
    
    if os.path.exists(dats_path):
        print("📝 Existing DATS.json found, merging metadata...")
        try:
            with open(dats_path, 'r', encoding="utf-8") as f:
                final_dats = json.load(f)
            
            # 1. Dynamic field: Version
            metadata = record.get("metadata", {})
            final_dats["version"] = metadata.get("version") or record.get("updated", perfect_dats.get("version", final_dats.get("version")))
            
            # 2. Dynamic field: Distributions (deep merge, only size/unit are updated)
            if "distributions" in final_dats and isinstance(final_dats["distributions"], list) and len(final_dats["distributions"]) > 0:
                # Assume the first entry is the main distribution
                main_dist = final_dats["distributions"][0]
                # Deep merge: make sure the required fields (size, unit, formats, access) exist
                if "distributions" in perfect_dats and len(perfect_dats["distributions"]) > 0:
                    template_dist = perfect_dats["distributions"][0]
                    main_dist["size"] = template_dist["size"]
                    main_dist["unit"] = template_dist["unit"]
                    
                    # Fill in required field: formats (enforced by the validator)
                    if "formats" not in main_dist or not main_dist["formats"]:
                        main_dist["formats"] = template_dist.get("formats", ["DataLad"])
                    
                    # Fill in required field: access
                    if "access" not in main_dist:
                        main_dist["access"] = template_dist.get("access", {})
                    elif "landingPage" not in main_dist["access"]:
                        main_dist["access"]["landingPage"] = template_dist.get("access", {}).get("landingPage", "")
                # Keep every other entry from main_dist (authorizations, etc.)
            else:
                final_dats["distributions"] = perfect_dats.get("distributions", [])
                
            # 3. Dynamic field: Dates (only set/add date modified)
            now_str = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            mod_date_val = record.get("updated", now_str)
            if "dates" in final_dats and isinstance(final_dats["dates"], list):
                found_mod = False
                for d in final_dats["dates"]:
                    if d.get("type", {}).get("value") == "date modified":
                        d["date"] = mod_date_val
                        found_mod = True
                if not found_mod:
                    final_dats["dates"].append({
                        "date": mod_date_val,
                        "type": {"value": "date modified"}
                    })
            else:
                final_dats["dates"] = perfect_dats.get("dates", [])

            # 4. Incremental fill: copy a top-level key from the template only when it is missing entirely
            for key, val in perfect_dats.items():
                if key not in final_dats:
                    final_dats[key] = val
                elif key == "extraProperties":
                    # Fill extraProperties incrementally too (add only, never remove)
                    existing_props = final_dats.get("extraProperties", [])
                    existing_cats = {p.get("category") for p in existing_props if "category" in p}
                    for p in perfect_dats.get("extraProperties", []):
                        if p.get("category") not in existing_cats:
                            existing_props.append(p)
                    final_dats["extraProperties"] = existing_props
                elif key == "creators":
                    # Placeholder guard: if the template says Multiple Contributors but the old file has real authors, keep the old ones
                    old_creators = final_dats.get("creators", [])
                    new_creators = perfect_dats.get("creators", [])
                    # The Zenodo template sometimes contains "N/A" or an empty list
                    placeholder_names = ["Multiple Contributors", "N/A", "unknown", ""]
                    is_new_placeholder = len(new_creators) > 0 and new_creators[0].get("name") in placeholder_names
                    has_old_real_name = len(old_creators) > 0 and old_creators[0].get("name") not in placeholder_names
                    
                    if is_new_placeholder and has_old_real_name:
                        print("🛡️  Preserving manually curated creators list...")
                        # Leave final_dats["creators"] untouched
                    else:
                        final_dats["creators"] = new_creators

            # 5. Hard lock: keywords, licenses, description, title, etc.
            # Never modify the value of any key already present in final_dats
            
            # Strong patch: fix the types validation (must be an information -> value structure)
            correct_types = perfect_dats.get("types", [{"information": {"value": "dataset"}}])
            if "types" in final_dats:
                old_types = final_dats["types"]
                # Check that it uses the standard list form and contains the information key
                is_valid = isinstance(old_types, list) and len(old_types) > 0 and isinstance(old_types[0], dict) and "information" in old_types[0]
                if not is_valid:
                    print("🔧 Repairing 'types' field for schema compliance...")
                    final_dats["types"] = correct_types
            else:
                final_dats["types"] = correct_types
                
        except Exception as e:
            print(f"⚠️  Error in ultimate strict merge ({e}), falling back to template.")
            final_dats = perfect_dats
    else:
        print("📝 Creating new DATS.json from scratch...")
        final_dats = perfect_dats

    # Force the file back out (unlink first in case a symlink locks it)
    if os.path.lexists(dats_path):
        os.remove(dats_path)
    with open(dats_path, "w", encoding="utf-8") as f:
        json.dump(final_dats, f, indent=4, ensure_ascii=False)
    run(["git", "add", "DATS.json"], cwd=dataset_dir)

    # Generate the crawler record file
    metadata = record.get("metadata", {})
    tracker = {
        "record_id": record_id,
        "concept_id": metadata.get("conceptrecid"),
        "title": metadata.get("title", ""),
        "version": metadata.get("version") or record.get("updated", ""),
        "import_date": dt.datetime.now().isoformat(),
    }
    with open(os.path.join(dataset_dir, ".conp-zenodo-crawler.json"), "w") as f:
        json.dump(tracker, f, indent=4)
    run(["git", "add", ".conp-zenodo-crawler.json"], cwd=dataset_dir)

    print("💾 Saving dataset state...")
    run(["datalad", "save", "-m", f"Import Zenodo {record_id} with standardized metadata and mixed storage"], cwd=dataset_dir)
    print(f"\n✅ Success! Dataset ready at {dataset_dir}")

if __name__ == "__main__":
    main()