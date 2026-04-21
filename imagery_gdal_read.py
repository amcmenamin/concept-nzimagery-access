import setup_gdal_env  # Configure GDAL environment
from osgeo import gdal
import os
import time
from datetime import datetime

# =============================================================================
# CONFIGURATION: Choose PUBLIC or PRIVATE S3 access
# =============================================================================

# Option 1: PUBLIC S3 bucket access (LINZ datasets)
# Configure GDAL for AWS S3 public bucket access
gdal.SetConfigOption('AWS_REGION', 'ap-southeast-2')
gdal.SetConfigOption('AWS_NO_SIGN_REQUEST', 'YES')
gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'YES')

# Option 2: PRIVATE S3 bucket access (requires credentials)
# Uncomment and configure the following for private S3 access:
"""
# Method A: Using AWS credentials directly
gdal.SetConfigOption('AWS_ACCESS_KEY_ID', 'your_access_key_here')
gdal.SetConfigOption('AWS_SECRET_ACCESS_KEY', 'your_secret_key_here') 
gdal.SetConfigOption('AWS_REGION', 'your-region')  # e.g., 'ap-southeast-2'
# gdal.SetConfigOption('AWS_SESSION_TOKEN', 'your_token_if_using_sts')  # Optional for STS

# Method B: Using AWS profile (reads from ~/.aws/credentials)
gdal.SetConfigOption('AWS_PROFILE', 'your_profile_name')  # e.g., 'default'
gdal.SetConfigOption('AWS_REGION', 'your-region')

# Method C: Using environment variables (set these before running script):
# export AWS_ACCESS_KEY_ID=your_access_key
# export AWS_SECRET_ACCESS_KEY=your_secret_key  
# export AWS_DEFAULT_REGION=your_region
# No additional gdal.SetConfigOption calls needed - GDAL reads from environment

# Additional private S3 options:
gdal.SetConfigOption('AWS_REQUEST_PAYER', 'requester')  # If bucket requires requester pays
gdal.SetConfigOption('AWS_S3_ENDPOINT', 'custom-endpoint.com')  # For non-AWS S3-compatible services
gdal.SetConfigOption('AWS_HTTPS', 'NO')  # Use HTTP instead of HTTPS (not recommended)
gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'YES')  # Performance optimization
"""

# =============================================================================

# Ensure output directory exists
output_dir = "c:\\data\\imagery"
os.makedirs(output_dir, exist_ok=True)

print(f"Starting download at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
start_time = time.time()

# Define source and destination
source_url = "/vsis3/nz-imagery/taranaki/taranaki_2022-2023_0.1m/rgb/2193/BH28_500_095032.tiff"
destination_file = "c:\\data\\imagery\\image.tiff"

# =============================================================================
# METADATA PRESERVATION: Read source properties and preserve them
# =============================================================================

print("🔍 Reading source metadata...")
src = gdal.Open(source_url)
if src is None:
    print("❌ Failed to open source file")
    exit(1)

# Read IMAGE_STRUCTURE metadata to preserve compression and tiling
img_md = src.GetMetadata("IMAGE_STRUCTURE")
creation_opts = []

# Preserve compression if present
if "COMPRESSION" in img_md:
    compression = img_md["COMPRESSION"]
    creation_opts.append(f"COMPRESS={compression}")
    print(f"📦 Preserving compression: {compression}")

# Preserve tiling if present
if img_md.get("TILED") == "YES":
    creation_opts.append("TILED=YES")
    print("🔳 Preserving tiled structure")

# Preserve interleaving if pixel interleaved
if img_md.get("INTERLEAVE") == "PIXEL":
    creation_opts.append("INTERLEAVE=PIXEL")
    print("🎨 Preserving pixel interleaving")

# Show what creation options will be used
if creation_opts:
    print(f"⚙️  Using creation options: {creation_opts}")
else:
    print("📋 No special creation options needed")

# Download S3 file to local file with preserved metadata
# For private buckets, change the source URL to your private bucket:
# "/vsis3/your-private-bucket/path/to/file.tiff"

print("Downloading with metadata preservation...")
result = gdal.Translate(
    destination_file,  # destination (local file)
    src,               # source (opened dataset)
    creationOptions=creation_opts
)

end_time = time.time()
duration = end_time - start_time

print(f"Finished download at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Download duration: {duration:.2f} seconds")

if result:
    # Calculate file size and speed
    file_size = os.path.getsize(destination_file) if os.path.exists(destination_file) else 0
    file_size_mb = file_size / (1024 * 1024)
    
    print("✅ File downloaded successfully!")
    print(f"📄 File: {destination_file}")
    print(f"📊 Size: {file_size_mb:.2f} MB")
    if duration > 0:
        print(f"🚀 Speed: {file_size_mb/duration:.2f} MB/s")
    
    # Show preserved metadata
    if creation_opts:
        print(f"🔧 Preserved metadata: {', '.join(creation_opts)}")
else:
    print("❌ Failed to download file")

# Close the source dataset
src = None


# =============================================================================
# PRIVATE S3 AUTHENTICATION EXAMPLES
# =============================================================================

# Example 1: Direct credentials (not recommended for production)
"""
gdal.SetConfigOption('AWS_ACCESS_KEY_ID', 'AKIAIOSFODNN7EXAMPLE')
gdal.SetConfigOption('AWS_SECRET_ACCESS_KEY', 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY')
gdal.SetConfigOption('AWS_REGION', 'us-west-2')
"""

# Example 2: Using AWS CLI profile (recommended)  
"""
# First run: aws configure --profile myprofile
gdal.SetConfigOption('AWS_PROFILE', 'myprofile')
gdal.SetConfigOption('AWS_REGION', 'us-west-2')
"""

# Example 3: Environment variables (good for containers/CI)
"""
# Set these environment variables:
# export AWS_ACCESS_KEY_ID=your_key
# export AWS_SECRET_ACCESS_KEY=your_secret  
# export AWS_DEFAULT_REGION=us-west-2
# Then no additional GDAL config needed
"""

# Example 4: IAM roles (for EC2 instances)
"""
# No credentials needed - GDAL automatically uses EC2 instance role
gdal.SetConfigOption('AWS_REGION', 'us-west-2')
"""

# Example 5: For private bucket download with metadata preservation
"""
source_url = "/vsis3/my-private-bucket/folder/file.tiff"
src = gdal.Open(source_url)
img_md = src.GetMetadata("IMAGE_STRUCTURE")

creation_opts = []
if "COMPRESSION" in img_md:
    creation_opts.append(f"COMPRESS={img_md['COMPRESSION']}")
if img_md.get("TILED") == "YES":
    creation_opts.append("TILED=YES")

result = gdal.Translate(
    "c:\\data\\imagery\\private_image.tiff",
    src,
    creationOptions=creation_opts
)
"""

# Example 6: Advanced metadata preservation
"""
# Custom creation options for different scenarios
custom_opts = [
    "COMPRESS=LZW",     # Force LZW compression
    "TILED=YES",        # Force tiling
    "PREDICTOR=2",      # Add predictor for better compression
    "BLOCKXSIZE=512",   # Custom tile size
    "BLOCKYSIZE=512"
]

result = gdal.Translate(
    "c:\\data\\imagery\\custom_format.tiff",
    src,
    creationOptions=custom_opts
)
"""
