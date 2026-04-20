import os
import time
from datetime import datetime
from osgeo import gdal

gdal.SetConfigOption('AWS_REGION', 'ap-southeast-2')
gdal.SetConfigOption('AWS_NO_SIGN_REQUEST', 'YES')
gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'YES')

# Ensure output directory exists
output_dir = "c:\\data\\imagery"
os.makedirs(output_dir, exist_ok=True)

print(f"Starting download at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
start_time = time.time()

# Define source and destination
source_url = "/vsis3/nz-imagery/wellington/wellington_2025_0.2m/rgbnir/2193/BM36_5000_1010.tiff"
destination_file = os.path.join(output_dir, "BM36_5000_1010_RGBI.tiff")

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