
import cv2
import numpy as np
import argparse
import os
import subprocess
import json
import uuid
import datetime

def harvest_prop_grabcut(image_path, output_dir, rect_ratio=0.6, roi_hint=None, disable_skin_rejection=False):
    """
    Simulate automated harvesting using GrabCut.
    In production, this would be replaced by Segment Anything Model (SAM2).
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read {image_path}")
    
    h, w = img.shape[:2]
    
    # Create mask directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load Face Detector (Haar Cascade)
    # Using relative path to cv2 data if possible, or simple fallback
    face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(face_cascade_path)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    if roi_hint:
        try:
            rect = tuple(map(int, roi_hint.split(',')))
            print(f"🎯 使用用户提供的 ROI Hint: {rect}")
        except Exception as e:
            print(f"⚠️ ROI Hint 解析失败 {roi_hint}，回退到自动推断: {e}")
            rect = None
    else:
        rect = None

    if rect is None:
        if len(faces) > 0:
            # --- NEW LOGIC: Capture ALL characters + Context ---
            print(f"👀 Detected {len(faces)} faces. Calculating Group ROI...")
            
            # 1. Find bounding box of ALL faces
            min_x = min(f[0] for f in faces)
            min_y = min(f[1] for f in faces)
            max_x = max(f[0] + f[2] for f in faces)
            max_y = max(f[1] + f[3] for f in faces)
            
            group_w = max_x - min_x
            group_h = max_y - min_y
            
            # 2. Expand ROI to include bodies and environment (Car)
            # Expand width by 100% (50% each side)
            pad_x = int(group_w * 0.8) 
            rx = max(0, min_x - pad_x)
            rw = min(w - rx, group_w + 2 * pad_x)
            
            # Expand height: Top slightly, Bottom all the way
            pad_top = int(group_h * 0.5)
            ry = max(0, min_y - pad_top)
            rh = min(h - ry, h - ry - 20) # Go to almost bottom
            
            rect = (rx, ry, rw, rh)
        else:
            # Fallback: Widen ROI to 90% height, 80% width
            print("👀 No face detected. Using Full-Body Center ROI.")
            rw, rh = int(w * 0.8), int(h * 0.9)
            rx, ry = (w - rw) // 2, (h - rh) // 2
            rect = (rx, ry, rw, rh)

    print(f"Applying Intelligent Extraction (GrabCut) on ROI: {rect}...")
    
    # === Evidence Preview ===
    preview_img = img.copy()
    cv2.rectangle(preview_img, (rect[0], rect[1]), (rect[0]+rect[2], rect[1]+rect[3]), (0, 255, 0), 2)
    for (fx, fy, fw, fh) in faces:
        cv2.rectangle(preview_img, (fx, fy), (fx+fw, fy+fh), (255, 0, 0), 2)
    preview_path = os.path.join(output_dir, "roi_preview.png")
    cv2.imwrite(preview_path, preview_img)
    print(f"📸 Saved Evidence Preview (ROI): {preview_path}")
    
    mask = np.zeros(img.shape[:2], np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    
    # Initial pass with bounding rect
    cv2.grabCut(img, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
    
    # 🛑 NEW FEATURE: Remove Hands (Skin Color Rejection)
    if not disable_skin_rejection:
        print("🖐 防粘连机制：执行肤色检测以剔除手部遮挡...")
        img_ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
        # Generic skin tone ranges in YCrCb
        lower_skin = np.array([0, 133, 77], dtype=np.uint8)
        upper_skin = np.array([255, 173, 127], dtype=np.uint8)
        skin_mask_raw = cv2.inRange(img_ycrcb, lower_skin, upper_skin)
        
        # Filter skin mask to only apply within the BBOX and foreground to avoid false positives in BG
        fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype('uint8')
        skin_in_fg = cv2.bitwise_and(skin_mask_raw, skin_mask_raw, mask=fg_mask)
        
        # Force localized skin pixels into "Sure Background"
        if cv2.countNonZero(skin_in_fg) > 0:
            mask[skin_in_fg == 255] = cv2.GC_BGD
            print(f"   -> 剔除疑似手部/肤色像素: {cv2.countNonZero(skin_in_fg)} pixels")
            # Run second pass GrabCut with the modified mask
            cv2.grabCut(img, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_MASK)
    else:
        print("⏭️ 防粘连机制已关闭，跳过手部/肤色像素检测...")
    
    # Mask: 0/2 is BG, 1/3 is FG
    mask2 = np.where((mask==2)|(mask==0), 0, 1).astype('uint8')
    
    # Create RGBA
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img_rgba = np.dstack((img_rgb, mask2 * 255))
    
    # --- NEW FEATURE: Instance Splitting ---
    # Check if we have multiple disconnected objects (e.g. 2 cars)
    contours, _ = cv2.findContours(mask2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    saved_assets = []
    
    # Filter small noise
    valid_contours = [c for c in contours if cv2.contourArea(c) > (w * h * 0.05)]
    
    # 模拟判断是否有人的信号
    has_person_signal = len(faces) > 0
    
    if len(valid_contours) > 1:
        print(f"✂️  Auto-Split: Detected {len(valid_contours)} separate objects. Splitting...")
        
        for i, cnt in enumerate(valid_contours):
            x, y, w_c, h_c = cv2.boundingRect(cnt)
            # Add padding
            pad = 20
            x = max(0, x - pad)
            y = max(0, y - pad)
            w_c = min(img.shape[1] - x, w_c + 2*pad)
            h_c = min(img.shape[0] - y, h_c + 2*pad)
            
            # Crop RGBA
            # We need to construct RGBA for this specific contour only? 
            # Ideally yes, but masking strictly is hard efficiently here. 
            # Simple approach: Crop the already masked RGBA image to this bbox.
            # (Pixels outside contour but inside bbox will remain visible if they belong to other objects? 
            #  No, because they are spatially separated. Bbox might overlap slightly but usually okay for demo.)
            
            # Better: Create a sub-mask for this contour to be clean
            sub_mask = np.zeros_like(mask2)
            cv2.drawContours(sub_mask, [cnt], -1, 1, thickness=cv2.FILLED)
            
            # Combine original RGB with this Sub-Mask
            sub_rgba = np.dstack((img_rgb, sub_mask * 255))
            
            # Crop
            final_crop = sub_rgba[y:y+h_c, x:x+w_c]
            
            asset_id = f"prop_{datetime.datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:4]}_part{i+1}"
            out_path = os.path.join(output_dir, f"{asset_id}.png")
            cv2.imwrite(out_path, cv2.cvtColor(final_crop, cv2.COLOR_RGBA2BGRA))
            print(f"   -> Saved Part {i+1}: {out_path}")
            
            # Generate Signals
            area_ratio = round(cv2.contourArea(cnt) / (w * h), 3)
            saved_assets.append({
                "path": out_path,
                "id": asset_id,
                "signals": {
                    "area_ratio": area_ratio,
                    "has_person": has_person_signal,
                    "num_instances": len(valid_contours),
                    "preview": preview_path
                }
            })
            
    else:
        # Fallback to single object logic (bounding rect of all mask)
        coords = cv2.findNonZero(mask2)
        x, y, w_b, h_b = cv2.boundingRect(coords)
        pad = 20
        x = max(0, x - pad)
        y = max(0, y - pad)
        w_b = min(img.shape[1] - x, w_b + 2*pad)
        h_b = min(img.shape[0] - y, h_b + 2*pad)
        
        cropped_rgba = img_rgba[y:y+h_b, x:x+w_b]
        
        asset_id = f"prop_{datetime.datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:4]}"
        out_path = os.path.join(output_dir, f"{asset_id}.png")
        cv2.imwrite(out_path, cv2.cvtColor(cropped_rgba, cv2.COLOR_RGBA2BGRA))
        print(f"Harvested Asset: {out_path}")
        
        # Determine Area
        area = cv2.countNonZero(mask2)
        saved_assets.append({
            "path": out_path,
            "id": asset_id,
            "signals": {
                "area_ratio": round(area / (w * h), 3),
                "has_person": has_person_signal,
                "num_instances": 1,
                "preview": preview_path
            }
        })

    return saved_assets

def analyze_articulation(image_path, mask_rect):
    """
    Simulate AI Structural Inference.
    In a real National Platform pipeline, this would call a Vision-Language Model (VLM)
    or a Part-Segmentation Model to identify moving parts.
    
    For the Phase 8 Demo, we simulate this by detecting circular shapes (wheels) 
    or simply hardcoding for specific demo assets.
    """
    print(f"🧠 [AI Decomposition] Analyzing structural potential for {os.path.basename(image_path)}...")
    
    # Mock Inference logic for "The Carriage" or "The Door"
    # If we detect a circle, we assume it's a wheel -> Revolute Joint.
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
        
    # Hough Circle Transform to find "Wheels"
    circles = cv2.HoughCircles(img, cv2.HOUGH_GRADIENT, dp=1.2, minDist=30,
                               param1=50, param2=30, minRadius=10, maxRadius=int(min(img.shape)*0.4))
    
    if circles is not None:
        print(f"   -> Detected {len(circles[0])} circular structures (Potential Wheels).")
        return {
            "type": "articulated",
            "joint": "revolute",
            "part_name": "wheel_01",
            "confidence": 0.85
        }
    
    # Default for non-circular: assume static or check for simple hinge
    return {
        "type": "static",
        "confidence": 0.99
    }

def apply_relighting(prop_image_path, lighting_json_path):
    """
    Simulate relighting by multiplying existing pixels with scene ambient color.
    This is a naive approximation. Real pipeline uses PBR texture baking.
    """
    if not os.path.exists(lighting_json_path):
        print(f"No lighting probe found at {lighting_json_path}, skipping relighting.")
        return prop_image_path
        
    with open(lighting_json_path, 'r') as f:
        light_data = json.load(f)
    
    ambient = light_data.get("ambient_light", {"r":1,"g":1,"b":1})
    color_scale = [ambient['b'], ambient['g'], ambient['r']] # BGR for OpenCV
    
    img = cv2.imread(prop_image_path, cv2.IMREAD_UNCHANGED)
    # Multiply RGB distinct from Alpha
    rgb = img[:, :, :3].astype(float)
    alpha = img[:, :, 3]
    
    # Apply ambient tint (Re-lighting)
    # We mix original color with ambient tint. 
    # Let's say we tint it 30% towards ambient.
    rgb = rgb * np.array(color_scale) * 1.2 # Boost slightly because ambient is dark
    
    # Clip
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    
    # Merge
    relighted = np.dstack((rgb, alpha))
    
    new_path = prop_image_path.replace(".png", "_relit.png")
    cv2.imwrite(new_path, relighted)
    print(f"Relighted asset saved to {new_path} using ambient {color_scale}")
    return new_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output_dir", default="outputs/harvested_props")
    parser.add_argument("--lighting_probe", help="Path to lighting_probe.json")
    parser.add_argument("--roi_hint", type=str, help="Hint string in format 'x,y,w,h' to override automatic extraction.", default=None)
    parser.add_argument("--disable_skin_rejection", action="store_true", help="Disable the skin color rejection mechanism (useful for animals or distinct backgrounds)")
    args = parser.parse_args()
    
    # 1. Extraction
    saved_assets = harvest_prop_grabcut(args.input, args.output_dir, roi_hint=args.roi_hint, disable_skin_rejection=args.disable_skin_rejection)
    
    # Create valid manifest list
    manifest_list = []

    for asset_dict in saved_assets:
        prop_path = asset_dict["path"]
        asset_id = asset_dict["id"]
        signals = asset_dict.get("signals", {})
        
        # 2. Relighting (Color Consistency)
        final_prop_path = prop_path
        if args.lighting_probe:
            final_prop_path = apply_relighting(prop_path, args.lighting_probe)
        
        # 3. Intelligent Analysis (New Phase 8 Feature)
        articulation_data = analyze_articulation(final_prop_path, None)
        
        # Add to manifest
        manifest_list.append({
            "id": asset_id,
            "path": final_prop_path,
            "raw_path": prop_path,
            "articulation": articulation_data,  # <--- The Key "Dynamic" Data
            "signals": signals                  # <--- Pipeline Routing Signals
        })
        
        # Create Individual GBT Metadata (Legacy support)
        meta = {
            "id": asset_id,
            "source_image": args.input,
            "extraction_method": "Auto-GrabCut + AI Decomposition",
            "lighting_applied": True if args.lighting_probe else False,
            "type": "Hero Asset",
            "structure": articulation_data
        }
        with open(os.path.join(args.output_dir, f"{asset_id}.json"), 'w') as f:
            json.dump(meta, f, indent=4)
            
    # Write Master Manifest for Pipeline Runner
    manifest_path = os.path.join(args.output_dir, "harvest_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest_list, f, indent=4)
    print(f"✅ Manifest written to {manifest_path}")

