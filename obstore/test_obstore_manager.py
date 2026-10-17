from obstore_manager import ObstoreManager


SAMPLE_FILES = [
    "auckland/auckland_2010_0.075m/rgb/2193/BA32_1000_3108.tiff",
    "auckland/auckland_2010_0.075m/rgb/2193/BA32_1000_3109.tiff",
    "50280-nz-geographic-names-topo-150k/.kart/hooks/pre-applypatch.sample",
    "50280-nz-geographic-names-topo-150k/.kart/hooks/pre-commit.sample",
]


def test_filter_files_by_extension_returns_only_matching_files():
    manager = ObstoreManager(bucket="dataset")

    result = manager.filter_files_by_extension(SAMPLE_FILES, ".tiff")

    assert result == [
        "auckland/auckland_2010_0.075m/rgb/2193/BA32_1000_3108.tiff",
        "auckland/auckland_2010_0.075m/rgb/2193/BA32_1000_3109.tiff",
    ]


def test_filter_files_by_extension_can_prefix_bucket_path():
    manager = ObstoreManager(bucket="dataset")

    result = manager.filter_files_by_extension(SAMPLE_FILES, ".sample", apply_base_folder=True)

    assert result == [
        "dataset/50280-nz-geographic-names-topo-150k/.kart/hooks/pre-applypatch.sample",
        "dataset/50280-nz-geographic-names-topo-150k/.kart/hooks/pre-commit.sample",
    ]


def test_filter_paths_by_keywords_matches_any_keyword_in_flat_list():
    manager = ObstoreManager(bucket="dataset")

    result = manager.filter_paths_by_keywords(SAMPLE_FILES, ["auckland", "50280"])

    assert result == SAMPLE_FILES


def test_filter_paths_by_keywords_supports_keyword_groups():
    manager = ObstoreManager(bucket="dataset")

    result = manager.filter_paths_by_keywords(
        SAMPLE_FILES,
        [["auckland", "3109"], ["50280", "pre-commit"]],
    )

    assert result == [
        "auckland/auckland_2010_0.075m/rgb/2193/BA32_1000_3109.tiff",
        "50280-nz-geographic-names-topo-150k/.kart/hooks/pre-commit.sample",
    ]
