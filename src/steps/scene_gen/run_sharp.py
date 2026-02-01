from sharp.cli.predict import predict_cli
import sys

# Environment Guard
try:
    import sharp
except ImportError:
    print("❌ ERROR: Please run this script in the 'sharp' conda environment.")
    print("   Run: conda activate sharp")
    sys.exit(1)
if __name__ == '__main__':
    predict_cli()
