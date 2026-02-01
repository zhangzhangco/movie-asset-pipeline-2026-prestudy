
import os
import time
import argparse
from pathlib import Path
from gradio_client import Client, handle_file

def run_trellis_api(image_path, output_dir):
    """
    Call TRELLIS HuggingFace Space API to generate 3D model.
    """
    print(f"Initializing Client for 'trellis-community/TRELLIS'...")
    try:
        client = Client("trellis-community/TRELLIS") # Public space usually doesn't need token
    except Exception as e:
        print(f"Error connecting to Space: {e}")
        return

    img_path = str(Path(image_path).absolute())
    if not os.path.exists(img_path):
        print(f"Error: Image not found at {img_path}")
        return

    print(f"Uploading image: {img_path}")
    print("Sending request to API (this may take 1-2 minutes depending on queue)...")
    
    start_time = time.time()
    
    # Based on typical TRELLIS demo API structure:
    # It usually takes an image and some parameters.
    # We'll try the standard flow.
    try:
        # Note: The API endpoints might change. This is a best-guess based on standard Gradio API structure for this space.
        # Usually user calls the prediction function.
        # Let's inspect the API first if this fails, but usually 'predict' works or checking `client.view_api()` could help.
        # For now we assume a standard image-to-3d fn.
        
        # Looking at recent TRELLIS spaces, prompt structure is:
        # Image -> [preprocess] -> [generate] -> [assets]
        
        # We'll try the main predict endpoint. Use api_name explicitly if known, otherwise letting client guess is risky.
        # Let's try to verify API first? No, just run it. The user wants results.
        
        # NOTE: Updated to match TRELLIS.2 or TRELLIS demo common parameters
        # Input 0: Image
        # Input 1: Seed (int)
        # Input 2: SS Guidance (float)
        # Input 3: SLAT Guidance (float)
        
        # Updated based on view_api() output
        # /image_to_3d takes: image, multiimage_input, seed, ...
        # Returns: video, model_3d, download_btn
        
        print("Calling /generate_and_extract_glb with positional args...")
        # Order: image, multiimages, seed, ss_guidance_strength, ss_sampling_steps, 
        # slat_guidance_strength, slat_sampling_steps, multiimage_algo, mesh_simplify, texture_size
        
        result = client.predict(
                handle_file(img_path), # 0: image
                [],                    # 1: multiimages
                0,                     # 2: seed
                7.5,                   # 3: ss_guidance
                12,                    # 4: ss_steps
                3.0,                   # 5: slat_guidance
                12,                    # 6: slat_steps
                "stochastic",          # 7: algo
                0.95,                  # 8: simplify
                1024,                  # 9: texture
                api_name="/generate_and_extract_glb" 
        )
        
        print("/image_to_3d returned!")
        # result is likely [video_path, model_path, glb_path]
        
        # Try to extract gaussian if possible
        try:
             print("Attempting to extract gaussian via /extract_gaussian...")
             # Note: This might fail if state is not preserved, but worth a try.
             res_gs = client.predict(api_name="/extract_gaussian")
             # Returns: (extracted_glbgaussian, download_gaussian)
             if isinstance(res_gs, (list, tuple)) and len(res_gs) > 1:
                 result = list(result) + [res_gs[1]] # Append gaussian path
                 print("Gaussian extraction successful!")
        except Exception as e:
             print(f"Gaussian extraction skipped/failed: {e}")

        
        print("API returned successfully!")
        print(f"Time taken: {time.time() - start_time:.1f}s")
        print(f"Result: {result}")

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        if isinstance(result, (list, tuple)):
            for i, item in enumerate(result):
                if isinstance(item, str) and os.path.exists(item):
                    ext = Path(item).suffix
                    dest = out_path / f"{Path(image_path).stem}_output_{i}{ext}"
                    import shutil
                    shutil.copy2(item, dest)
                    print(f"Saved: {dest}")
        elif isinstance(result, str) and os.path.exists(result):
             # Single file
             ext = Path(result).suffix
             dest = out_path / f"{Path(image_path).stem}{ext}"
             import shutil
             shutil.copy2(result, dest)
             print(f"Saved: {dest}")

    except Exception as e:
        print(f"API Call Failed: {e}")
        print("\nAttempting to list API endpoints for debugging:")
        try:
            client.view_api()
        except:
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", type=str, required=True, help="Input image path")
    parser.add_argument("--output", "-o", type=str, default="outputs/trellis_api", help="Output directory")
    args = parser.parse_args()
    
    run_trellis_api(args.input, args.output)
