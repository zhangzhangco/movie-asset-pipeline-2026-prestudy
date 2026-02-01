import os
import argparse
import json
import glob
from datetime import datetime

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Asset Acquisition Report</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent: #3b82f6;
            --success: #10b981;
        }}
        body {{
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 2rem;
        }}
        .header {{
            margin-bottom: 2rem;
            border-bottom: 1px solid #334155;
            padding-bottom: 1rem;
        }}
        .header h1 {{ margin: 0; font-size: 2rem; font-weight: 700; color: var(--text-primary); }}
        .header .meta {{ color: var(--text-secondary); margin-top: 0.5rem; font-size: 0.9rem; }}
        
        .section {{ margin-bottom: 3rem; }}
        .section-title {{ 
            font-size: 1.25rem; 
            font-weight: 600; 
            margin-bottom: 1rem; 
            color: var(--accent); 
            text-transform: uppercase; 
            letter-spacing: 0.05em;
        }}

        /* Layout */
        .grid {{ display: grid; gap: 1.5rem; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }}
        
        /* Scene Context */
        .scene-container {{ display: flex; flex-wrap: wrap; gap: 2rem; }}
        .scene-item {{ flex: 1; min-width: 300px; background: var(--card-bg); padding: 1rem; border-radius: 0.75rem; }}
        .scene-item img {{ width: 100%; border-radius: 0.5rem; display: block; }}
        .scene-item h3 {{ margin-top: 0; font-size: 1rem; color: var(--text-secondary); }}
        
        /* Lighting Probe */
        .probe-swatch {{ 
            height: 100px; 
            width: 100%; 
            border-radius: 0.5rem; 
            margin-bottom: 1rem; 
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .json-dump {{ 
            background: #0b1120; 
            padding: 0.75rem; 
            border-radius: 0.5rem; 
            font-family: monospace; 
            font-size: 0.8rem; 
            color: #22d3ee; 
            overflow-x: auto;
        }}

        /* Asset Cards */
        .asset-card {{ 
            background: var(--card-bg); 
            border-radius: 0.75rem; 
            overflow: hidden; 
            border: 1px solid #334155;
            transition: transform 0.2s;
        }}
        .asset-card:hover {{ transform: translateY(-2px); border-color: var(--accent); }}
        
        .card-header {{ padding: 1rem; background: rgba(0,0,0,0.2); display: flex; justify-content: space-between; align-items: center; }}
        .card-header .id {{ font-family: monospace; font-size: 0.85rem; color: var(--accent); }}
        .card-header .status {{ font-size: 0.7rem; background: rgba(16, 185, 129, 0.2); color: var(--success); padding: 0.2rem 0.6rem; border-radius: 1rem; }}
        
        .card-body {{ padding: 1rem; }}
        .image-row {{ display: flex; gap: 0.5rem; margin-bottom: 1rem; }}
        .image-row div {{ flex: 1; }}
        .image-row img {{ width: 100%; border-radius: 0.4rem; aspect-ratio: 1/1; object-fit: contain; background: #000; }}
        .image-label {{ font-size: 0.7rem; color: var(--text-secondary); text-align: center; margin-top: 0.3rem; }}
        
        .meta-row {{ display: flex; justify-content: space-between; font-size: 0.8rem; border-top: 1px solid #334155; padding-top: 0.8rem; }}
        .meta-item {{ color: var(--text-secondary); }}
        .meta-val {{ color: var(--text-primary); font-weight: 600; }}

        .btn {{ 
            display: block; 
            text-align: center; 
            background: var(--accent); 
            color: white; 
            text-decoration: none; 
            padding: 0.75rem; 
            border-radius: 0.5rem; 
            margin-top: 1rem; 
            font-size: 0.9rem;
            font-weight: 500;
        }}
        .btn:hover {{ filter: brightness(1.1); }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📦 Asset Acquisition Report</h1>
        <div class="meta">
            Session ID: {session_id} <br>
            Generated: {gen_date}
        </div>
    </div>

    <div class="section">
        <div class="section-title">1. Scene Context (Scene Layer)</div>
        <div class="scene-container">
            <div class="scene-item">
                <h3>Original Input</h3>
                <img src="{input_image_rel}" alt="Input Image">
            </div>
            <div class="scene-item">
                <h3>Environmental Lighting Probe</h3>
                <div class="probe-swatch" style="background-color: rgb({amb_r},{amb_g},{amb_b});"></div>
                <div class="json-dump">{light_json}</div>
                <p style="font-size: 0.8rem; color: #94a3b8; margin-top:0.5rem;">
                    * This ambient color is extracted from the scene and applied to hero assets for integration.
                </p>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">2. Hero Assets Gallery (Foreground Layer)</div>
        <div class="grid">
            {asset_cards}
        </div>
    </div>

</body>
</html>
"""

CARD_TEMPLATE = """
            <div class="asset-card">
                <div class="card-header">
                    <span class="id">{asset_id}</span>
                    <span class="status">READY</span>
                </div>
                <div class="card-body">
                    <div class="image-row">
                        <div>
                            <img src="{crop_path}" alt="Raw Crop">
                            <div class="image-label">Raw Harvest</div>
                        </div>
                        <div>
                            <img src="{relit_path}" alt="Relit Asset">
                            <div class="image-label">Relit (Input)</div>
                        </div>
                    </div>
                    
                    <div class="meta-row">
                        <div class="meta-item">Type<br><span class="meta-val">Character/Prop</span></div>
                        <div class="meta-item">Format<br><span class="meta-val">3DGS (.ply)</span></div>
                        <div class="meta-item">ROI Size<br><span class="meta-val">{roi_size}</span></div>
                    </div>

                    <a href="{ply_path}" class="btn">⬇️ Download 3D Asset</a>
                </div>
            </div>
"""

def generate_report(output_dir):
    session_id = os.path.basename(output_dir)
    
    # 1. Find Input Image (Heuristic: usually passed as argument, but we can look for copied version if implemented)
    # For now, we assume script is run inside the pipeline or we rely on relative paths.
    # We'll try to find metadata json if available, else look for inputs.
    
    # Find Lighting Probe
    light_path = os.path.join(output_dir, "lighting_probe.json")
    amb_r, amb_g, amb_b = 128, 128, 128
    light_json_str = "{}"
    if os.path.exists(light_path):
        with open(light_path, 'r') as f:
            data = json.load(f)
            light_json_str = json.dumps(data, indent=2)
            amb = data.get("ambient_light", {})
            amb_r = int(amb.get("r", 1.0) * 255)
            amb_g = int(amb.get("g", 1.0) * 255)
            amb_b = int(amb.get("b", 1.0) * 255)

    # 2. Find Hero Assets
    props_dir = os.path.join(output_dir, "props")
    props_3d_dir = os.path.join(output_dir, "props_3d")
    
    asset_cards = ""
    
    if os.path.exists(props_dir):
        # Find relit images as primary keys
        relit_imgs = glob.glob(os.path.join(props_dir, "*_relit.png"))
        
        for relit_img in relit_imgs:
            base_name = os.path.basename(relit_img).replace("_relit.png", "")
            raw_img = os.path.join(props_dir, f"{base_name}.png")
            ply_file = os.path.join(props_3d_dir, f"{base_name}.ply") # Note: ply might keep _relit suffix or not depending on pipeline
            
            # Check for PLY with or without _relit suffix
            if not os.path.exists(ply_file):
                 ply_file_relit = os.path.join(props_3d_dir, f"{base_name}_relit.ply")
                 if os.path.exists(ply_file_relit):
                     ply_file = ply_file_relit
            
            # Paths relative to report.html
            rel_crop = os.path.relpath(raw_img, output_dir)
            rel_relit = os.path.relpath(relit_img, output_dir)
            rel_ply = os.path.relpath(ply_file, output_dir) if os.path.exists(ply_file) else "#"
            
            # Get Image Dimensions for ROI size
            roi_size = "N/A"
            try:
                # We won't import cv2 just for this to keep it light, unless needed.
                # Let's just say "Variable" or check file size.
                roi_size = f"{os.path.getsize(relit_img) // 1024} KB" 
            except:
                pass

            asset_cards += CARD_TEMPLATE.format(
                asset_id=base_name,
                crop_path=rel_crop,
                relit_path=rel_relit,
                ply_path=rel_ply,
                roi_size=roi_size
            )

    if not asset_cards:
        asset_cards = "<p style='color:#64748b; font-style:italic;'>No assets harvested in this session.</p>"

    # Input image placeholder (Needs to be passed or inferred)
    # We will accept an argument for input image path and try to copy it or link it.
    input_image_rel = "../input.png" # Placeholder

    html_content = HTML_TEMPLATE.format(
        session_id=session_id,
        gen_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        input_image_rel=input_image_rel,
        amb_r=amb_r, amb_g=amb_g, amb_b=amb_b,
        light_json=light_json_str,
        asset_cards=asset_cards
    )
    
    report_path = os.path.join(output_dir, "report.html")
    with open(report_path, 'w') as f:
        f.write(html_content)
    
    print(f"✅ Report generated: {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_root", required=True, help="Path to specific session output dir")
    parser.add_argument("--input_image", help="Original input image path (optional)")
    args = parser.parse_args()
    
    # Generate
    generate_report(args.output_root)
    
    # If input image provided, copy/link it for viewing?
    # For HTML portability, relative links are best. 
    # But input image is outside. We might need to copy it into output_dir just for display.
    if args.input_image and os.path.exists(args.input_image):
        import shutil
        dest = os.path.join(args.output_root, "source_image.png")
        shutil.copy2(args.input_image, dest)
        # We need to update the HTML to point to this new local copy
        # Quick hack: Read it back and replace
        with open(os.path.join(args.output_root, "report.html"), 'r') as f:
            content = f.read()
        content = content.replace('src="../input.png"', 'src="source_image.png"')
        with open(os.path.join(args.output_root, "report.html"), 'w') as f:
            f.write(content)
