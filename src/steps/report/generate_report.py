import os
import argparse
import json
from datetime import datetime

# Author: zhangxin
# Description: 电影资产化管线可视化报告生成脚本。
# 功能：读取 manifest.json 和资产目录，生成包含处理逻辑、决策原因及专家建议的中文 HTML 报告。
# 输入：管线输出根目录
# 输出：report.html

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D 资产化处理报告 - Pipeline 2026</title>
    <style>
        :root {{
            --bg-color: #0b111a;
            --card-bg: #151c2c;
            --card-border: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.3);
            --success: #10b981;
            --success-bg: rgba(16, 185, 129, 0.1);
            --danger: #ef4444;
            --danger-bg: rgba(239, 68, 68, 0.1);
            --warning: #f59e0b;
            --info: #3b82f6;
        }}
        body {{
            font-family: 'PingFang SC', 'Microsoft YaHei', -apple-system, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 2rem 4rem;
            line-height: 1.6;
        }}
        h1, h2, h3 {{ font-weight: 600; letter-spacing: -0.01em; margin-bottom: 0.5rem; }}
        .header {{
            margin-bottom: 3rem;
            border-bottom: 2px solid var(--accent);
            padding-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ margin: 0; font-size: 2.5rem; background: linear-gradient(90deg, #fff, var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .header .meta {{ color: var(--text-secondary); font-size: 0.9rem; font-family: 'JetBrains Mono', monospace; text-align: right; }}
        
        .section {{ margin-bottom: 4rem; }}
        .section-title {{
            font-size: 1.4rem;
            margin-bottom: 1.5rem;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            border-left: 4px solid var(--accent);
            padding-left: 1rem;
        }}
        
        .context-grid {{ display: grid; gap: 2rem; grid-template-columns: 1.5fr 1fr; }}
        .context-card {{
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 1rem;
            border: 1px solid var(--card-border);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
        }}
        .context-card img {{ width: 100%; border-radius: 0.5rem; display: block; filter: brightness(0.9); transition: 0.3s; }}
        .context-card img:hover {{ filter: brightness(1.1); transform: scale(1.01); }}
        .context-card h3 {{ margin-top: 0; margin-bottom: 1rem; font-size: 1.1rem; color: var(--accent); }}
        
        .grid {{ display: grid; gap: 2.5rem; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); }}
        .asset-card {{
            background: var(--card-bg);
            border-radius: 1.25rem;
            border: 1px solid var(--card-border);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .asset-card:hover {{ transform: translateY(-5px); border-color: var(--accent); box-shadow: 0 0 20px var(--accent-glow); }}
        
        .card-header {{
            padding: 1.25rem 1.5rem;
            background: rgba(255, 255, 255, 0.03);
            border-bottom: 1px solid var(--card-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .card-header .id {{ font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 600; color: var(--accent); }}
        
        .badge {{
            font-size: 0.75rem;
            font-weight: bold;
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            text-transform: uppercase;
        }}
        .badge.success {{ background: var(--success-bg); color: var(--success); border: 1px solid var(--success); }}
        .badge.failed {{ background: var(--danger-bg); color: var(--danger); border: 1px solid var(--danger); }}
        .badge.warning {{ background: rgba(245, 158, 11, 0.1); color: var(--warning); border: 1px solid var(--warning); }}

        .card-content {{ display: flex; flex-direction: column; gap: 1rem; padding: 1.5rem; }}
        
        .image-compare {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }}
        .image-box {{ text-align: center; }}
        .image-box img {{ width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 0.5rem; background: #000; border: 1px solid #334155; }}
        .image-label {{ font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.5rem; }}

        .analysis-box {{
            background: rgba(0, 0, 0, 0.25);
            padding: 1rem;
            border-radius: 0.75rem;
            border-left: 3px solid var(--info);
            font-size: 0.9rem;
        }}
        .analysis-box h4 {{ margin: 0 0 0.5rem 0; color: var(--info); font-size: 0.95rem; }}
        .analysis-item {{ margin-bottom: 0.4rem; display: flex; }}
        .analysis-label {{ color: var(--text-secondary); min-width: 80px; flex-shrink: 0; }}
        .analysis-value {{ color: var(--text-primary); }}

        .advice-box {{
            background: rgba(16, 185, 129, 0.05);
            padding: 0.8rem 1rem;
            border-radius: 0.75rem;
            border: 1px dashed var(--success);
            font-size: 0.85rem;
            color: var(--text-primary);
        }}
        .advice-box strong {{ color: var(--success); margin-right: 0.5rem; }}

        .metadata-line {{
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            padding: 0.4rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .metadata-line:last-child {{ border-bottom: none; }}
        
        .btn {{
            display: block;
            text-align: center;
            background: var(--accent);
            color: white;
            padding: 1rem;
            text-decoration: none;
            font-weight: 600;
            transition: 0.2s;
        }}
        .btn:hover {{ background: #4f46e5; filter: brightness(1.1); }}
        
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>电影资产化技术报告</h1>
            <div style="color: var(--accent); margin-top: 0.5rem; font-weight: 500;">Hybrid 3D Acquisition Pipeline | Pre-Study 2026</div>
        </div>
        <div class="meta">
            会话 ID: {session_id}<br>
            生成时间: {gen_date}
        </div>
    </div>

    <div class="section">
        <div class="section-title">场景环境上下文 (Contextual Layer)</div>
        <div class="context-grid">
            <div class="context-card">
                <h3>原始扫描帧 (Source Plate)</h3>
                <img src="{input_image_rel}" alt="Input Image">
            </div>
            <div class="context-card" style="display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <h3>全局光照探针 (Lighting Probe)</h3>
                    <div style="height: 100px; width: 100%; border-radius: 0.6rem; background: rgb({amb_r},{amb_g},{amb_b}); box-shadow: inset 0 2px 10px rgba(0,0,0,0.5); margin-bottom: 1rem;"></div>
                    <pre style="background: #000; padding: 1rem; border-radius: 0.5rem; font-size: 0.75rem; color: #818cf8; overflow: auto;">{light_json}</pre>
                </div>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">数字化文化遗产资产 (Digital Assets)</div>
        <div class="grid">
            {asset_cards}
        </div>
    </div>
    
    <div style="margin-top: 4rem; text-align: center; color: var(--text-secondary); font-size: 0.8rem; border-top: 1px solid var(--card-border); padding-top: 2rem;">
        &copy; 2026 Movie Assetization Pipeline Project. Author: zhangxin. 严格遵循 GB/T 36369 标准。
    </div>
</body>
</html>
"""

ASSET_CARD_TEMPLATE = """
            <div class="asset-card">
                <div class="card-header">
                    <span class="id">{asset_id}</span>
                    <span class="badge {status_class}">{status_text}</span>
                </div>
                
                <div class="card-content">
                    <div class="image-compare">
                        <div class="image-box">
                            <img src="{preview_path}" alt="Logic Evidence">
                            <div class="image-label">逻辑证据 (Mask/Depth)</div>
                        </div>
                        <div class="image-box">
                            <img src="{relit_path}" alt="Processed Node">
                            <div class="image-label">重光照处理帧</div>
                        </div>
                    </div>

                    <div class="analysis-box">
                        <h4>🔍 管线自动分析</h4>
                        <div class="analysis-item">
                            <span class="analysis-label">处理内容:</span>
                            <span class="analysis-value">执行 {backend} 算法进行 3D 几何建模与纹理映射。</span>
                        </div>
                        <div class="analysis-item">
                            <span class="analysis-label">决策分支:</span>
                            <span class="analysis-value">{decision_reason}</span>
                        </div>
                        <div class="analysis-item">
                            <span class="analysis-label">执行结果:</span>
                            <span class="analysis-value">{execution_result}</span>
                        </div>
                    </div>

                    <div class="advice-box">
                        <strong>🛠️ 专家建议:</strong> {advice_text}
                    </div>

                    <div style="margin-top: 0.5rem;">
                        <div class="metadata-line">
                            <span style="color:var(--text-secondary)">资产分类</span>
                            <span>{asset_type}</span>
                        </div>
                        <div class="metadata-line">
                            <span style="color:var(--text-secondary)">DCC 校验 (Blender)</span>
                            <span>{dcc_status}</span>
                        </div>
                        <div class="metadata-line">
                            <span style="color:var(--text-secondary)">存储格式</span>
                            <span>{asset_format}</span>
                        </div>
                    </div>
                </div>

                <a href="{download_path}" class="btn" {btn_attrs}>下载原始 3D 成果 (ARTIFACT)</a>
            </div>
"""

def _to_rel(output_dir, path):
    if not path: return "#"
    candidate = path if os.path.isabs(path) else os.path.join(output_dir, path)
    if not os.path.exists(candidate): return "#"
    return os.path.relpath(candidate, output_dir)

def _get_decision_reason(asset_info):
    signals = asset_info.get("signals", {})
    params = asset_info.get("parameters_snapshot", {})
    logic = params.get("logic", {})
    
    if logic.get("asset_type") == "human":
        return "检测到人体特征信号（Face/Pose），自动进入人体高精建模流程。"
    
    has_mask = signals.get("has_mask", False)
    num_instances = signals.get("num_instances", 1)
    area_ratio = signals.get("area_ratio", 0)
    
    if num_instances > 1 or area_ratio < 0.3:
        return f"检测到多目标（{num_instances}个）或低占比分布，选择轻量化多目标建模方案。"
    
    if has_mask:
        return "检测到显著实例掩码，判定为独立道具，执行高保真单体生成。"
        
    return "未发现显著单体特征，默认作为场景静态组件进行通用重建。"

def _get_execution_result(asset_info):
    status = asset_info.get("status", "unknown")
    import_check = asset_info.get("import_check", {})
    
    if status == "success":
        res = "管线执行成功。"
        if import_check.get("import_ok"):
            res += " DCC 导入校验通过，几何拓扑正常。"
        return res
    if status == "failed":
        return f"执行中断。错误信息: {asset_info.get('error_message', '未知错误')}。"
    return "状态未知。"

def _get_advice(asset_info):
    status = asset_info.get("status", "unknown")
    import_check = asset_info.get("import_check", {})
    
    if status == "success":
        if import_check.get("import_ok"):
            return "资产质量达标，建议导入 Maya/Houdini 进行材质细化与绑定。"
        else:
            return "生成成功但 DCC 校验存疑，建议检查模型法线或是否存在重叠面。"
    
    if status == "failed":
        return "请检查输入切片的分辨率和遮罩完整性，或尝试切换生成后端（如从 TRELLIS 切换到 SAM3D）。"
    
    return "继续观察管线后续步骤。"

def generate_report(output_dir):
    session_id = os.path.basename(output_dir)
    manifest_path = os.path.join(output_dir, "manifest.json")
    
    if not os.path.exists(manifest_path):
        print(f"❌ Error: manifest.json not found in {output_dir}")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # Lighting
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

    asset_cards = ""
    for asset_info in manifest_data.get("assets", []):
        if asset_info.get("asset_type") == "scene": continue
        
        asset_id = asset_info.get("asset_id", "unknown")
        outputs = asset_info.get("outputs", [])
        status = asset_info.get("status", "unknown")
        import_check = asset_info.get("import_check", {})
        
        # Paths
        preview_abs = next((o for o in outputs if "preview.png" in o), None)
        relit_abs = next((o for o in outputs if "_relit.png" in o or "color.png" in o), None)
        mesh_abs = next((o for o in outputs if o.endswith(".glb") or o.endswith(".ply") or o.endswith(".obj")), None)
        
        rel_preview = _to_rel(output_dir, preview_abs)
        rel_relit = _to_rel(output_dir, relit_abs)
        rel_mesh = _to_rel(output_dir, mesh_abs)
        
        # Status labels
        status_class = "success" if status == "success" else "failed" if status == "failed" else "warning"
        status_text = "成功 (Standardized)" if status == "success" else "失败 (Failed)" if status == "failed" else "处理中"
        
        dcc_ok = import_check.get("import_ok")
        if dcc_ok is True: dcc_status = '<span style="color:var(--success)">✅ 通过</span>'
        elif dcc_ok is False: dcc_status = '<span style="color:var(--danger)">❌ 失败</span>'
        else: dcc_status = "未校验"

        asset_cards += ASSET_CARD_TEMPLATE.format(
            asset_id=asset_id,
            status_class=status_class,
            status_text=status_text,
            preview_path=rel_preview,
            relit_path=rel_relit,
            backend=asset_info.get("backend_selected", "AUTO").upper(),
            decision_reason=_get_decision_reason(asset_info),
            execution_result=_get_execution_result(asset_info),
            advice_text=_get_advice(asset_info),
            asset_type=asset_info.get("asset_type", "PROP").upper(),
            dcc_status=dcc_status,
            asset_format=os.path.splitext(mesh_abs)[1].upper() if mesh_abs else "N/A",
            download_path=rel_mesh,
            btn_attrs="disabled style='background:#334155;cursor:not-allowed'" if rel_mesh == "#" else ""
        )

    if not asset_cards:
        asset_cards = "<p style='color:#64748b; font-style:italic; padding: 2rem;'>本次会话未采集到独立资产目标。</p>"

    html_content = HTML_TEMPLATE.format(
        session_id=session_id,
        gen_date=datetime.now().strftime("%Y年%m月%d日 %H:%M:%S"),
        input_image_rel="source_image.png",
        amb_r=amb_r,
        amb_g=amb_g,
        amb_b=amb_b,
        light_json=light_json_str,
        asset_cards=asset_cards
    )

    report_path = os.path.join(output_dir, "report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ 报告已成功生成: {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_root", required=True)
    parser.add_argument("--input_image", help="Original input image path")
    args = parser.parse_args()
    
    generate_report(args.output_root)
    
    if args.input_image and os.path.exists(args.input_image):
        import shutil
        dest = os.path.join(args.output_root, "source_image.png")
        shutil.copy2(args.input_image, dest)
