import os
import setup_gdal_env  # Configure GDAL environment
import numpy as np
import rasterio
import cv2
from skimage.transform import resize
from shapely.geometry import *
from scipy.ndimage import binary_closing
from osgeo import gdal

from scipy.ndimage import convolve



class NDVIProcessor:
    """
    A comprehensive processor for analyzing multispectral imagery and extracting vegetation,
    water, and urban features using various spectral indices and height information.
    
    This class provides functionality to:
    - Process RGBI (Red, Green, Blue, Infrared) imagery
    - Calculate vegetation indices (NDVI, NDWI)
    - Perform height-based classification using DSM/DEM data
    - Extract vegetation, water, and urban features
    - Generate classification masks and export results
    
    The processor supports both height-aware and height-independent classification,
    with optional debug outputs for intermediate processing steps.
    
    Attributes:
        use_height (bool): Whether to incorporate height information from DSM/DEM data
        in_debug_mode (bool): Whether to save intermediate processing outputs for debugging
    
    Example:
        >>> processor = NDVIProcessor()
        >>> processor.set_height_usage(True)
        >>> processor.set_debug_mode(True)
        >>> rgbi, dsm, dtm, transform = processor.read_raster_datasets(
        ...     rgbi_path, dsm_path, dem_path
        ... )
        >>> processor.process_vegetation(
        ...     rgbi, transform, dsm, dtm, output_path, height_tolerance=3.5
        ... )
    """
    def __init__(self):
        """
        Initialize the NDVIProcessor with default settings.
        
        The processor is initialized with height usage enabled and debug mode disabled.
        These settings can be modified using the respective setter methods.
        """
        self.use_height = True
        self.in_debug_mode = False

    def set_height_usage(self, use_height: bool):
        """
        Sets whether to use height information in vegetation classification.

        Args:
            use_height (bool): If True, height information will be used; otherwise, it will not.
        """
        self.use_height = use_height

    def set_debug_mode(self, debug_mode: bool):
        """
        Sets the debug mode for the processor.

        Args:
            debug_mode (bool): If True, debug mode is enabled; otherwise, it is disabled.
        """
        self.in_debug_mode = debug_mode

    def read_raster_datasets(self, rgbi_path: str, dsm_path: str, dem_path: str, resize_rgbi_base: bool = True
    ) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None, rasterio.Affine]:
        """
        Reads RGBI, DSM, and DTM raster files, crops DSM and DTM to RGBI bounds, 
        resizes DSM and DTM to match RGBI shape, and returns the arrays and transform.

        Args:
            rgbi_path (str): Path to the RGBI raster file.
            dsm_path (str): Path to the DSM raster file.
            dem_path (str): Path to the DEM raster file.

        Returns:
            tuple: (rgbi, dsm, dem, transform)
                rgbi (np.ndarray): RGBI image array.
                dsm (np.ndarray): DSM array resized to match RGBI.
                dem (np.ndarray): DEM array resized to match RGBI.
                transform (rasterio.Affine): Affine transform for the rasters.
        """
        print("Reading raster datasets...")
        rgbi, transform, bounds = self.read_rgbi(rgbi_path)
        if self.use_height:
            dsm = self.read_dsm(dsm_path, bounds)
            # Check the DSM, DEM are the same cell size 
            if resize_rgbi_base:
                dsm = resize(dsm, rgbi[:1,:,:].shape)
            else:
                rgbi = resize(rgbi, dsm.shape, preserve_range=True)


            dtm, _ = self.read_dem(dem_path, bounds)
            if resize_rgbi_base:
                dtm = resize(dtm, rgbi[:1,:,:].shape)
            else:   #rework this
                rgbi = resize(rgbi, dtm.shape, preserve_range=True)
        else:
            dsm = None
            dtm = None
        return rgbi, dsm, dtm, transform

    def read_rgbi(self, rgbi_path: str) -> tuple[np.ndarray, rasterio.Affine, tuple]:
        """
        Reads an RGBI raster file and returns the image array, affine transform, and bounds.

        Args:
            rgbi_path (str): Path to the RGBI raster file.

        Returns:
            tuple: (rgbi, rgbi_transform, rgbi_bounds)
                rgbi (np.ndarray): The RGBI image array.
                rgbi_transform (rasterio.Affine): Affine transform for the raster.
                rgbi_bounds (tuple): Bounding box of the raster (left, bottom, right, top).
        """
        with rasterio.open(rgbi_path, "r") as rgbi_f:
            print(rgbi_f.crs)
            rgbi_transform = rgbi_f.transform
            rgbi_bounds = rgbi_f.bounds
            rgbi = rgbi_f.read().astype(np.float32)
        return rgbi, rgbi_transform, rgbi_bounds

    def read_dsm(self, dsm_path: str, bounds: tuple = None) -> np.ndarray:
        """
        Reads a DSM raster file, crops it to the given bounds, and returns the array.

        Args:
            dsm_path (str): Path to the DSM raster file.
            bounds (tuple): Bounding box to crop (left, bottom, right, top).

        Returns:
            np.ndarray: Cropped DSM array.
        """
        if bounds is None:
            dsm = rasterio.open(dsm_path).read().astype(np.float32)
        else:
            with rasterio.open(dsm_path, "r") as dsm_f:
                dsm = dsm_f.read(
                    window=rasterio.windows.from_bounds(*bounds, transform=dsm_f.transform)
                ).astype(np.float32)
        return dsm

    def read_dem(self, dem_path: str, bounds: tuple = None) -> np.ndarray:
        """
        Reads a DTM raster file, crops it to the given bounds, and returns the array.

        Args:
            dem_path (str): Path to the DEM raster file.
            bounds (tuple): Bounding box to crop (left, bottom, right, top).

        Returns:
            np.ndarray: Cropped DEM array.
        """
        transform = None
        if bounds is None:
            with rasterio.open(dem_path, "r") as dem_f:
                dem = dem_f.read().astype(np.float32)
                transform = dem_f.transform
        else:
            with rasterio.open(dem_path, "r") as dem_f:
                dem = dem_f.read(
                    window=rasterio.windows.from_bounds(*bounds, transform=dem_f.transform)
                ).astype(np.float32)
        return dem, transform

    def calculate_ndsm(self, dsm: np.ndarray, dem: np.ndarray) -> np.ndarray:
        """
        Calculates the normalized Digital Surface Model (nDSM) by subtracting DEM from DSM.

        Args:
            dsm (np.ndarray): DSM array.
            dem (np.ndarray): DEM array.

        Returns:
            np.ndarray: nDSM array with negative values set to 0.
        """
        ndsm = (dsm[0] - dem[0])
        # Set negative values to 0. Possible if the DEM is higher than the DSM.
        # TODO: May want to use local value to get average
        ndsm[ndsm < 0] = 0  
        return ndsm

    def calculate_slope(self, dem, out_path, transform):
        """
        Calculates the slope of the DEM and saves it to the specified output path.

        Args:
            dem (np.ndarray): The DEM array.
            out_path (str): The path to save the slope raster.
        """

        cellsize_x = transform.a
        cellsize_y = -transform.e  # usually negative

        # Horn's method kernels
        kernel_x = np.array([[-1, 0, 1],
                            [-2, 0, 2],
                            [-1, 0, 1]]) / (8 * cellsize_x)

        kernel_y = np.array([[ 1,  2,  1],
                            [ 0,  0,  0],
                            [-1, -2, -1]]) / (8 * cellsize_y)

        # Compute gradients
        dzdx = convolve(dem, kernel_x, mode='nearest')
        dzdy = convolve(dem, kernel_y, mode='nearest')

        # Compute slope in degrees
        slope_rad = np.arctan(np.sqrt(dzdx**2 + dzdy**2))
        slope_deg = np.degrees(slope_rad)




        x_grad, y_grad = np.gradient(dem)
        slope = np.sqrt(x_grad**2 + y_grad**2)

        # Classify slope
        threshold = 5  # degrees
        flat = slope < threshold
        sloped = slope >= threshold
        classification = np.where(flat, 0, 1)

        # Save the slope raster
        with rasterio.open(out_path, 'w', driver='GTiff', height=classification.shape[0],
                           width=classification.shape[1], count=1, dtype=np.float32,
                           transform=dem.transform) as dst:
            dst.write(classification, 1)


    def process_slope(self, input_dem_path, output_slope_path, slope_format='degrees'):
        """
        Process a DEM to calculate slope using GDAL's DEMProcessing functionality.
        
        This method uses GDAL's built-in slope calculation algorithm to generate
        slope rasters from digital elevation models. The output format can be
        specified as degrees, percent, or rise over run.
        
        Args:
            input_dem_path (str): Path to the input DEM raster file
            output_slope_path (str): Path where the output slope raster will be saved
            slope_format (str, optional): Output format - 'degrees', 'percent', or 'rise_run'.
                                        Defaults to 'degrees'.
        
        Returns:
            None
            
        Raises:
            Exception: If DEM file cannot be opened or processing fails
        """

        try:
            # Open the input DEM dataset
            dem_ds = gdal.Open(input_dem_path)
            if dem_ds is None:
                print(f"Error: Could not open DEM file: {input_dem_path}")
                return

            # Define options for DEMProcessing
            options = ['slope']
            if slope_format == 'percent':
                options.append('-p')
            elif slope_format == 'rise_run':
                options.append('-s')

            # Perform the DEM processing to calculate slope
            gdal.DEMProcessing(output_slope_path, dem_ds, 'slope', options=options)

            print(f"Slope calculated and saved to: {output_slope_path}")

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # Close the dataset (important for releasing file locks)
            if 'dem_ds' in locals() and dem_ds is not None:
                dem_ds = None




    def process_general(self, rgbi, transform, dsm, dem, output_path, 
                        height_tolerance=3.5, max_height=None, 
                        greater_than=True, index_value=0.3,
                        mode='ndvi'):
        """
        General processing method for extracting features using spectral indices and height data.
        
        This flexible method can process either NDVI or NDWI indices and apply height-based
        filtering to extract specific features. Supports both vegetation and water extraction
        depending on the mode and threshold settings.
        
        Args:
            rgbi (np.ndarray): Multi-band image array (Red, Green, Blue, Infrared)
            transform (rasterio.Affine): Affine transformation for georeferencing
            dsm (np.ndarray): Digital Surface Model array
            dem (np.ndarray): Digital Elevation Model array
            output_path (str): Path to save the output classification raster
            height_tolerance (float, optional): Minimum height above ground for classification.
                                              Defaults to 3.5 meters.
            max_height (float, optional): Maximum height for classification. Defaults to None.
            greater_than (bool, optional): Whether to use greater than (>) or less than (<)
                                         comparison for index threshold. Defaults to True.
            index_value (float, optional): Threshold value for spectral index classification.
                                         Defaults to 0.3.
            mode (str, optional): Spectral index mode - 'ndvi' or 'ndwi'. Defaults to 'ndvi'.
        
        Returns:
            None
        """
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        print("Processing indexes...")
        if mode == 'ndvi':
            ndvi = self.calculate_ndvi(rgbi)
        elif mode == 'ndwi':
            ndvi = self.calculate_ndwi(rgbi)

        if self.in_debug_mode:
            temp_path = output_path.replace('.tif', f'_{mode}.tif')
            with rasterio.open(temp_path, 'w', driver='GTiff', height=ndvi.shape[0],
                                width=ndvi.shape[1], count=1, dtype=np.float32,
                                transform=transform) as dst:
                dst.write(ndvi, 1)

        if self.use_height:
            print("Processing ndsm...")
            ndsm = self.calculate_ndsm(dsm, dem)
            if self.in_debug_mode:
                temp_path = output_path.replace('.tif', '_ndsm.tif')
                with rasterio.open(temp_path, 'w', driver='GTiff', height=ndsm.shape[0],
                                    width=ndsm.shape[1], count=1, dtype=np.float32,
                                    transform=transform) as dst:
                    dst.write(ndsm, 1)

        print("Processing classification...")
        classified_data = self.classify(ndvi, greater_than=greater_than, ndvi_value=index_value)
        if self.in_debug_mode:
            temp_path = output_path.replace('.tif', '_classified.tif')
            with rasterio.open(temp_path, 'w', driver='GTiff', height=classified_data.shape[0],
                                width=classified_data.shape[1], count=1, dtype=np.float32,
                                transform=transform) as dst:
                dst.write(classified_data.astype(np.float32), 1)

        if self.use_height:
            print("Processing height...")
            heighted_data = self.select_by_height(classified_data, ndsm, height_tolerance, max_height)
            heighted_data = np.where(heighted_data, 1, 0)
        else:
            heighted_data = classified_data
            
        with rasterio.open(output_path, 'w', driver='GTiff', height=heighted_data.shape[0],
                            width=heighted_data.shape[1], count=1, dtype=np.float32,
                            transform=transform) as dst:
            dst.write(heighted_data, 1)
        
        print(output_path, "created")

    def export_image(self, image, output_path, transform):
        """
        Export a multi-band image array to a GeoTIFF file.
        
        Args:
            image (np.ndarray): Multi-band image array to export
            output_path (str): Path to save the output GeoTIFF file
            transform (rasterio.Affine): Affine transformation for georeferencing
        
        Returns:
            None
        """
        with rasterio.open(output_path, 'w', driver='GTiff', height=image.shape[0],
                           width=image.shape[1], count=3, dtype=np.float32,
                           transform=transform) as dst:
            dst.write(image, 3)

    def process_vegetation(self, rgbi, transform, dsm, dem, output_path, height_tolerance=3.5, max_height=None):
        """
        Classifies vegetation over a set height from image and exports a raster mask.

        This method processes multi-band imagery (RGBI), a digital surface model (DSM), and a digital elevation model (DEM)
        to compute the NDVI (Normalized Difference Vegetation Index) and nDSM (normalized Digital Surface Model).
        It then classifies vegetation and identifies egetation based on a height threshold, exporting the result as a GeoTIFF raster.

        Args:
            rgbi (np.ndarray): Multi-band image array containing Red, Green, Blue, and Infrared channels.
            transform (Affine): Affine transformation for georeferencing the output raster.
            dsm (np.ndarray): Digital Surface Model array representing surface elevations.
            dem (np.ndarray): Digital Elevation Model array representing ground elevations.
            output_path (str): File path to save the output raster.
            height_tolerance (float, optional): Minimum height (in meters) above ground to classify as features. Defaults to 3.5.

        Returns:
            None

        """
        
        ndvi = self.calculate_ndvi(rgbi)
        if self.in_debug_mode:
            temp_path = output_path.replace('.tif', '_ndvi.tif')
            with rasterio.open(temp_path, 'w', driver='GTiff', height=ndvi.shape[0],
                                width=ndvi.shape[1], count=1, dtype=np.float32,
                                transform=transform) as dst:
                dst.write(ndvi, 1)

        
        ndsm = self.calculate_ndsm(dsm, dem)
        if self.in_debug_mode:
            temp_path = output_path.replace('.tif', '_ndsm.tif')
            with rasterio.open(temp_path, 'w', driver='GTiff', height=ndsm.shape[0],
                                width=ndsm.shape[1], count=1, dtype=np.float32,
                                transform=transform) as dst:
                dst.write(ndsm, 1)


        vegetation = self.classify_vegetation(ndvi)
        heighted_vegetation = self.select_by_height(vegetation, ndsm, height_tolerance, max_height)
        heighted_vegetation = np.where(heighted_vegetation, 1, 0)
        with rasterio.open(output_path, 'w', driver='GTiff', height=heighted_vegetation.shape[0],
                            width=heighted_vegetation.shape[1], count=1, dtype=np.float32,
                            transform=transform) as dst:
            dst.write(heighted_vegetation, 1)
        
        print(output_path, "created")
        #filler = RasterHoleFiller(r"C:\Data\imagery_rgbi_woolpert\PRJ47237_Tauranga\Vegetation\method2a\RGBI_BD37_2025_1000_2619_vegetation_3.5m.tif")
        #filler.fill_holes()
        #filler.close()
        #filler.trim_edges()

        
        return


    def calculate_ndvi(self, rgbi):
        """
        Calculates the Normalized Difference Vegetation Index (NDVI) from an RGBA image array.

        NDVI is a widely used vegetation index that quantifies vegetation health by comparing the near-infrared (NIR) and red bands of an image. The formula used is:
            NDVI = (NIR - Red) / (NIR + Red)

        Parameters:
            rgbi (numpy.ndarray): A 4-channel image array (Red, Green, Blue, Infrared), where
                rgbi[0] corresponds to the Red channel,
                rgbi[3] corresponds to the Near-Infrared (NIR) channel.

        Returns:
            numpy.ndarray: The computed NDVI values as a float array.

        References:
            - Tucker, C.J. (1979). "Red and photographic infrared linear combinations for monitoring vegetation." Remote Sensing of Environment, 8(2), 127-150.
            - [NDVI on Wikipedia](https://en.wikipedia.org/wiki/Normalized_difference_vegetation_index)
            - [USGS NDVI Explanation](https://www.usgs.gov/core-science-systems/nli/landsat/landsat-normalized-difference-vegetation-index)
        """
        ndvi = (rgbi[3] - rgbi[0]) / (rgbi[3] + rgbi[0])
        return ndvi
    
    def calculate_ndwi(self, rgbi):
        """
        Calculates the Normalized Difference Water Index (NDWI) from an RGBA image array.

        NDWI is used to monitor water content in vegetation and surface water bodies. The formula used is:
            NDWI = (Green - NIR) / (Green + NIR)

        Parameters:
            rgbi (numpy.ndarray): A 4-channel image array (Red, Green, Blue, Infrared), where
                rgbi[1] corresponds to the Green channel,
                rgbi[3] corresponds to the Near-Infrared (NIR) channel.

        Returns:
            numpy.ndarray: The computed NDWI values as a float array.
        """
        ndwi = (rgbi[1] - rgbi[3]) / (rgbi[1] + rgbi[3])
        return ndwi
    
    def calculate_brightness_index(self, rgbi):
        """
        Calculate the Brightness Index (BI) from an RGBI image array.
        
        The Brightness Index is calculated as the square root of the sum of squared
        RGB values, providing a measure of overall pixel brightness.
        Formula: BI = sqrt(Red² + Green² + Blue²)
        
        Args:
            rgbi (np.ndarray): A 4-channel image array (Red, Green, Blue, Infrared)
        
        Returns:
            np.ndarray: The computed Brightness Index values as a float array
        """
        
        RED = rgbi[0]
        GREEN = rgbi[1]
        BLUE = rgbi[2]

        # Calculate Brightness Index
        BI = np.sqrt(RED**2 + GREEN**2 + BLUE**2)
        return BI

    def calculate_urban_index(self, ndvi, bi):
        """
        Calculates the Urban Index (UI) from NDVI and Brightness Index (BI) arrays.

        The Urban Index is a simple metric to identify urban areas based on their
        vegetation and brightness characteristics. The formula used is:
            UI=BIx(1-NDVI)

        Parameters:
            ndvi (np.ndarray): Input NDVI array.
            bi (np.ndarray): Input Brightness Index array.

        Returns:
            np.ndarray: The computed Urban Index values as a float array.
        """

        ui = bi * (1 - ndvi)

        return ui

    def calculate_urban_threshold(self, ndvi, bi):
        """
        Calculates the Urban Threshold based on NDVI and Brightness Index (BI) values.

        Args:
            ndvi (np.ndarray): Input NDVI array.
            bi (np.ndarray): Input Brightness Index array.

        Returns:
            np.ndarray: Boolean array where True indicates urban presence.
        """
        # Apply thresholds
        ndvi_threshold = 0.2
        bi_threshold = 1.0
        threshold = (ndvi < ndvi_threshold) & (bi > bi_threshold)
        return threshold.astype(np.uint8)


    def classify_vegetation(self, ndvi):
        """
        Classifies vegetation presence in an NDVI (Normalized Difference Vegetation Index) array based on a computed threshold.

        This method replaces NaN values in the input NDVI array with -1, set a vegetation identification value 0.3, 
        and then classifies each pixel as vegetation or non-vegetation by comparing the NDVI value to the identification value.

        Args:
            ndvi (np.ndarray): Input NDVI array, where higher values typically indicate denser vegetation.

        Returns:
            tuple:
                veg (np.ndarray): Boolean array where True indicates vegetation presence.

        References:
            - [Normalized Difference Vegetation Index (NDVI) - USGS](https://www.usgs.gov/landsat-missions/landsat-normalized-difference-vegetation-index)
            - [Remote Sensing of Environment: NDVI](https://www.sciencedirect.com/topics/earth-and-planetary-sciences/normalized-difference-vegetation-index)
        
        NDVI value ranges:
        - Healthy vegetation: 0.5 to 0.8+
        - Moderate vegetation: 0.3 to 0.5
        - Sparse vegetation: 0.2 to 0.3
        """
        is_vegetation = 0.35
        vegetation = ndvi > is_vegetation
        return vegetation

    def classify(self, ndvi, greater_than: bool, ndvi_value: float) -> np.ndarray:
        """
        Classifies vegetation presence in an NDVI (Normalized Difference Vegetation Index) array based on a computed threshold.

        This method replaces NaN values in the input NDVI array with -1, set a vegetation identification value 0.3, 
        and then classifies each pixel as vegetation or non-vegetation by comparing the NDVI value to the identification value.

        Args:
            ndvi (np.ndarray): Input NDVI array, where higher values typically indicate denser vegetation.

        Returns:
            tuple:
                veg (np.ndarray): Boolean array where True indicates vegetation presence.

        References:
            - [Normalized Difference Vegetation Index (NDVI) - USGS](https://www.usgs.gov/landsat-missions/landsat-normalized-difference-vegetation-index)
            - [Remote Sensing of Environment: NDVI](https://www.sciencedirect.com/topics/earth-and-planetary-sciences/normalized-difference-vegetation-index)
        
        NDVI value ranges:
        - Healthy vegetation: 0.5 to 0.8+
        - Moderate vegetation: 0.3 to 0.5
        - Sparse vegetation: 0.2 to 0.3
        - Urban / Water: <0.1 or negative
        """
        if greater_than:
            vegetation = ndvi > ndvi_value
        else:
            vegetation = ndvi < ndvi_value
        return vegetation

    def convert_to_hsv(self, rgbi: np.ndarray) -> np.ndarray:
        """
        Converts an RGBI image array to HSV (Hue, Saturation, Value) using OpenCV.

        Only the RGB channels are used for HSV conversion; the infrared band is ignored.

        Args:
            rgbi (np.ndarray): A 4-channel image array (Red, Green, Blue, Infrared).

        Returns:
            np.ndarray: HSV image array (shape: H x W x 3).
        """
        # Rearrange to H x W x 3 for OpenCV (RGB only)
        rgb = np.stack([rgbi[0], rgbi[1], rgbi[2]], axis=-1)
        rgb = rgb.astype(np.uint8) if rgb.max() > 1 else (rgb * 255).astype(np.uint8)
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        return hsv

    def select_by_height(self, data, ndsm, height_threshold, max_height=None):
        """
        Classifies height of vegetation based on vegetation mask and normalized digital surface model (nDSM) data.

        This function takes a binary vegetation and a nDSM array, then identifies pixels by applying a height threshold.
        Morphological closing is used to remove small holes and connect adjacent pixels.

        Args:
            vegetation (np.ndarray): A binary or boolean vegetation mask array (expected shape: (1, H, W) or (H, W)).
            ndsm (np.ndarray): Normalized Digital Surface Model array of the same shape as vegetation, representing height values.
            height_threshold (float): Height threshold in the same units as ndsm; pixels above this value are considered high vegetation.

        Returns:
            np.ndarray: A binary array of the same shape as vegetation, where high vegetation pixels are marked as 1 and others as 0.

        References:
            - [Scikit-image: Morphological operations](https://scikit-image.org/docs/stable/auto_examples/numpy_operations/plot_binary_closing.html)
            - [Remote Sensing of Environment: NDVI and nDSM for vegetation classification](https://www.sciencedirect.com/science/article/pii/S0034425717303766)
        """
        if max_height is not None:
            height_vegetation = data & (ndsm >= height_threshold) & (ndsm <= max_height)
        else:
            height_vegetation = data & (ndsm >= height_threshold)

        height_vegetation = binary_closing(height_vegetation, structure=np.ones((3, 3))).astype(height_vegetation.dtype)
        return height_vegetation
    
    def fill_holes(self, heighted_vegetation):
        """
        Fill holes in a binary vegetation mask using GDAL's FillNodata function.
        
        This method uses GDAL's interpolation algorithm to fill small gaps and holes
        in vegetation classification results, which is more effective than simple
        morphological operations for larger gaps.
        
        Args:
            heighted_vegetation (np.ndarray): Binary vegetation mask with holes to fill
        
        Returns:
            gdal.Band: GDAL raster band object with filled holes
            
        Note:
            The method uses a maximum search distance of 10 pixels and 1 smoothing
            iteration. Adjust these parameters based on the size of holes to fill.
        """

        nodata_value = 0 
        mask_array = (heighted_vegetation != nodata_value).astype(np.uint8)

        # Create an in-memory raster mask using GDAL MEM driver
        mem_driver = gdal.GetDriverByName('MEM')
        mask_ds = mem_driver.Create('', heighted_vegetation.shape[1], heighted_vegetation.shape[0], 1, gdal.GDT_Byte)
        mask_ds.GetRasterBand(1).WriteArray(mask_array)
        mask_band = mask_ds.GetRasterBand(1)

        # Convert the numpy array to a GDAL raster band
        band_driver = gdal.GetDriverByName('MEM')
        band_ds = band_driver.Create('', heighted_vegetation.shape[1], heighted_vegetation.shape[0], 1, gdal.GDT_Float32)
        band_ds.GetRasterBand(1).WriteArray(heighted_vegetation)
        band = band_ds.GetRasterBand(1)

        # Using gdal method as it work better than binary_closing - Fill nodata values
        gdal.FillNodata(band, mask_band, maxSearchDist=10, smoothingIterations=1, options=[])
        return band

    