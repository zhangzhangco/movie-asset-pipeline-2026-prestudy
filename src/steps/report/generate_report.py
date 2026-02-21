import os
import argparse
import json
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
            --bg-color: #0b0f19;
            --card-bg: #151b2b;
            --card-border: #1e293b;
            --text-primary: #e2e8f0;
            --text-secondary: #94a3b8;
            --accent: #6366f1;
            --accent-hover: #4f46e5;
            --success: #10b981;
            --success-bg: rgba(16, 185, 129, 0.1);
            --danger: #ef4444;
            --danger-bg: rgba(239, 68, 68, 0.1);
            --warning: #f59e0b;
        }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 3rem;
            line-height: 1.6;
        }}
        h1, h2, h3 {{ font-weight: 600; letter-spacing: -0.025em; }}
        .header {{
            margin-bottom: 3rem;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .header h1 {{ margin: 0; font-size: 2.25rem; color: #fff; }}
        .header .meta {{ color: var(--text-secondary); font-size: 0.875rem; font-family: monospace; text-align: right; }}
        .section {{ margin-bottom: 4rem; }}
        .section-title {{
            font-size: 1.125rem;
            margin-bottom: 1.5rem;
            color: var(--text-primary);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            display: flex;
            align-items: center;
        }}
        .section-title::before {{
            content: '';
            display: inline-block;
            width: 12px;
            height: 12px;
            background: var(--accent);
            border-radius: 2px;
            margin-right: 0.75rem;
        }}
        .context-grid {{ display: grid; gap: 2rem; grid-template-columns: 2fr 1fr; }}
        .context-card {{
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 0.75rem;
            border: 1px solid var(--card-border);
        }}
        .context-card img {{ width: 100%; border-radius: 0.5rem; display: block; }}
        .context-card h3 {{ margin-top: 0; margin-bottom: 1rem; font-size: 1rem; color: var(--text-primary); }}
        .probe-swatch {{
            height: 80px;
            width: 100%;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);
        }}
        .json-dump {{
            background: #000;
            padding: 1rem;
            border-radius: 0.5rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: #818cf8;
            overflow-x: auto;
            border: 1px solid var(--card-border);
        }}
        .grid {{ display: grid; gap: 2rem; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); }}
        .asset-card {{
            background: var(--card-bg);
            border-radius: 1rem;
            border: 1px solid var(--card-border);
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            display: flex;
            flex-direction: column;
        }}
        .card-header {{
            padding: 1.25rem;
            border-bottom: 1px solid var(--card-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .card-header .id {{ font-family: 'JetBrains Mono', monospace; font-size: 0.875rem; font-weight: 500; color: #fff; }}
        .badge {{
            font-size: 0.7rem;
            font-weight: 600;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .badge.success {{ background: var(--success-bg); color: var(--success); border: 1px solid rgba(16,185,129,0.2); }}
        .badge.failed {{ background: var(--danger-bg); color: var(--danger); border: 1px solid rgba(239,68,68,0.2); }}
        .badge.warning {{ background: rgba(245,158,11,0.1); color: var(--warning); border: 1px solid rgba(245,158,11,0.2); }}
        .card-images {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1px;
            background: var(--card-border);
        }}
        .card-images > div {{ background: var(--card-bg); padding: 1rem; text-align: center; }}
        .card-images img {{
            width: 100%;
            aspect-ratio: 1/1;
            object-fit: contain;
            border-radius: 0.25rem;
            background: #000;
            margin-bottom: 0.5rem;
        }}
        .image-label {{ font-size: 0.7rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; }}
        .card-meta {{ padding: 1.25rem; flex-grow: 1; }}
        .meta-list {{ list-style: none; padding: 0; margin: 0; }}
        .meta-list li {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            font-size: 0.875rem;
        }}
        .meta-list li:last-child {{ border-bottom: none; }}
        .meta-label {{ color: var(--text-secondary); }}
        .meta-value {{ color: var(--text-primary); font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; }}
        .btn {{
            display: block;
            text-align: center;
            background: var(--accent);
            color: white;
            text-decoration: none;
            padding: 0.875rem;
            font-size: 0.875rem;
            font-weight: 500;
            letter-spacing: 0.025em;
            transition: all 0.2s;
        }}
        .btn:hover {{ background: var(--accent-hover); }}
        .import-check {{
            margin-top: 1rem;
            padding: 0.75rem;
            background: rgba(0,0,0,0.2);
            border-radius: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.875rem;
            border: 1px solid var(--card-border);
        }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>Asset Acquisition Report</h1>
            <div style="color: var(--accent); margin-top: 0.5rem;">Pipeline Pre-Study 2026</div>
        </div>
        <div class="meta">
            SESSION_ID: {session_id}<br>
            TIMESTAMP: {gen_date}
        </div>
    </div>

    <div class="section">
        <div class="section-title">Contextual Layer</div>
        <div class="context-grid">
            <div class="context-card">
                <h3>Source Plate</h3>
                <img src="{input_image_rel}" alt="Input Image">
            </div>
            <div class="context-card">
                <h3>Global Lighting Probe</h3>
                <div class="probe-swatch" style="background-color: rgb({amb_r},{amb_g},{amb_b});"></div>
                <div class="json-dump">{light_json}</div>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Digital Heritage Assets</div>
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
                    <span class="badge {status_class}">{status_text}</span>
                </div>

                <div class="card-images">
                    <div>
                        <img src="{preview_path}" alt="Evidence Preview">
                        <div class="image-label">Logic Evidence</div>
                    </div>
                    <div>
                        <img src="{relit_path}" alt="Relit Asset">
                        <div class="image-label">Processed Node</div>
                    </div>
                </div>

                <div class="card-meta">
                    <ul class="meta-list">
                        <li>
                            <span class="meta-label">Domain</span>
                            <span class="meta-value">{asset_type} / {backend}</span>
                        </li>
                        <li>
                            <span class="meta-label">Asset Format</span>
                            <span class="meta-value">{asset_format}</span>
                        </li>
                    </ul>

                    <div class="import-check">
                        <span style="color: var(--text-secondary)">DCC Validation</span>
                        {import_badge}
                    </div>
                </div>

                <a href="{download_path}" class="btn" {btn_attrs}>DOWNLOAD ARTIFACT</a>
            </div>
"""


def _to_rel(output_dir, path):
    if not path:
        return "#"
    candidate = path if os.path.isabs(path) else os.path.join(output_dir, path)
    if not os.path.exists(candidate):
        return "#"
    return os.path.relpath(candidate, output_dir)


def _pick_output(outputs, names):
    for output in outputs:
        base = os.path.basename(output)
        if base in names:
            return output
    return None


def _pick_by_ext(outputs, exts):
    for output in outputs:
        if any(output.endswith(ext) for ext in exts):
            return output
    return None


def generate_report(output_dir):
    session_id = os.path.basename(output_dir)

    light_path = os.path.join(output_dir, "lighting_probe.json")
    amb_r, amb_g, amb_b = 128, 128, 128
    light_json_str = "{}"
    if os.path.exists(light_path):
        with open(light_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            light_json_str = json.dumps(data, indent=2)
            amb = data.get("ambient_light", {})
            amb_r = int(amb.get("r", 1.0) * 255)
            amb_g = int(amb.get("g", 1.0) * 255)
            amb_b = int(amb.get("b", 1.0) * 255)

    manifest_path = os.path.join(output_dir, "manifest.json")
    manifest_data = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

    asset_cards = ""
    for asset_info in manifest_data.get("assets", []):
        if asset_info.get("asset_type") == "scene":
            continue

        outputs = asset_info.get("outputs", [])
        status = asset_info.get("status", "unknown")
        asset_type = asset_info.get("asset_type", "prop")
        backend = asset_info.get("backend_selected", "unknown")
        import_valid = asset_info.get("import_valid", "N/A")

        preview_abs = _pick_output(outputs, {"preview.png"})
        relit_abs = _pick_by_ext(outputs, {"_relit.png", ".png"})
        mesh_abs = _pick_output(outputs, {"mesh.glb", "mesh.obj", "splat.ply"})

        rel_preview = _to_rel(output_dir, preview_abs)
        rel_relit = _to_rel(output_dir, relit_abs)
        rel_mesh = _to_rel(output_dir, mesh_abs)

        if status == "success":
            status_class = "success"
            status_text = "Standardized"
        elif status == "failed":
            status_class = "failed"
            status_text = "Failed"
        else:
            status_class = "warning"
            status_text = status.upper()

        if import_valid is True:
            import_badge = '<span class="badge success">PASSED</span>'
        elif import_valid is False:
            import_badge = '<span class="badge failed">FAILED</span>'
        else:
            import_badge = '<span class="badge warning">SKIPPED</span>'

        asset_format = os.path.splitext(mesh_abs)[1] if mesh_abs else "N/A"
        btn_attrs = "disabled style='background:#334155;cursor:not-allowed'" if rel_mesh == "#" else ""

        asset_cards += CARD_TEMPLATE.format(
            asset_id=asset_info.get("asset_id", "unknown"),
            status_class=status_class,
            status_text=status_text,
            preview_path=rel_preview,
            relit_path=rel_relit,
            asset_type=asset_type.upper(),
            backend=backend.upper(),
            asset_format=asset_format,
            import_badge=import_badge,
            download_path=rel_mesh,
            btn_attrs=btn_attrs,
        )

    if not asset_cards:
        asset_cards = "<p style='color:#64748b; font-style:italic;'>No assets harvested in this session.</p>"

    html_content = HTML_TEMPLATE.format(
        session_id=session_id,
        gen_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        input_image_rel="source_image.png",
        amb_r=amb_r,
        amb_g=amb_g,
        amb_b=amb_b,
        light_json=light_json_str,
        asset_cards=asset_cards,
    )

    report_path = os.path.join(output_dir, "report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ Report generated: {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_root", required=True, help="Path to specific session output dir")
    parser.add_argument("--input_image", help="Original input image path (optional)")
    args = parser.parse_args()

    generate_report(args.output_root)

    if args.input_image and os.path.exists(args.input_image):
        import shutil
        dest = os.path.join(args.output_root, "source_image.png")
        shutil.copy2(args.input_image, dest)
