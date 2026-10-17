## ObstoreManager

`obstore_manager.py` provides a small helper class for listing and filtering paths from either a local directory or an S3 bucket.

### Supported backends

- Local filesystem via `LocalStore`
- Public S3 via `S3Store` with signature skipping enabled
- Private S3 via `S3Store` with access key, secret key, and optional session token

### Main methods

- `list_local_filesystem(prefix="")`: list files from a local directory rooted at `bucket`
- `list_s3_public(prefix="")`: list files from a public S3 bucket
- `list_s3_private(prefix)`: list files from a private S3 bucket
- `filter_files_by_extension(files, extension, apply_base_folder=False)`: keep only paths that end with a given extension
- `filter_paths_by_keywords(files, keywords, apply_base_folder=False)`: keep only paths containing keyword matches

### Example

```python
from obstore_manager import ObstoreManager

manager = ObstoreManager(bucket="/data/topo50")

files, items = manager.list_local_filesystem()
filtered_tiffs = manager.filter_files_by_extension(files, ".tiff")
filtered_paths = manager.filter_paths_by_keywords(files, ["auckland", "3109"])
```

For private S3 access, pass `bucket`, `region`, `access_key`, `secret_key`, and optionally `session_token` when creating the manager.
