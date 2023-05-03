import geemap
import ee
ee.Initialize()

class LandsatCollection:
    def __init__(self, start_date=None, end_date=None, tile_row=None, tile_path=None, cloud_percentage_threshold=None, collection=None):
        if collection is None and (start_date is None or end_date is None or tile_row is None or tile_path is None or cloud_percentage_threshold is None):
            raise ValueError("Either provide all required fields (start_date, end_date, tile_row, tile_path, cloud_percentage_threshold) or provide a collection.")
        if collection is None:
            self.start_date = start_date
            self.end_date = end_date
            self.tile_row = tile_row
            self.tile_path = tile_path
            self.cloud_percentage_threshold = cloud_percentage_threshold

            # Filter the collection
            self.collection = self.get_filtered_collection()
        else:
            self.collection = collection

        self.dates_list = self.list_of_dates()
        self.ndwi_threshold = -1
        self.ndvi_threshold = -1
        self.halite_threshold = -1
        self.gypsum_threshold = -1
        self.masked_clouds_collection = self.masked_clouds_collection()

        # Check if the required bands are available
        first_image = self.collection.first()
        available_bands = first_image.bandNames()

        if available_bands.contains('SR_B3') and available_bands.contains('SR_B5'):
            self.ndwi = self.ndwi_collection(self.ndwi_threshold)
        else:
            self.ndwi = None
            raise ValueError("Insufficient Bands for ndwi calculation")
        
        if available_bands.contains('SR_B4') and available_bands.contains('SR_B5'):
            self.ndvi = self.ndvi_collection(self.ndvi_threshold)
        else:
            self.ndvi = None
            raise ValueError("Insufficient Bands for ndwi calculation")

        if available_bands.contains('SR_B4') and available_bands.contains('SR_B6'):
            self.halite = self.halite_collection(self.halite_threshold)
        else:
            self.halite = None
            raise ValueError("Insufficient Bands for halite calculation")

        if available_bands.contains('SR_B6') and available_bands.contains('SR_B7'):
            self.gypsum = self.gypsum_collection(self.gypsum_threshold)
        else:
            self.gypsum = None
            raise ValueError("Insufficient Bands for gypsum calculation")

        if available_bands.contains('ST_ATRAN') and available_bands.contains('ST_EMIS') and available_bands.contains('ST_DRAD') and available_bands.contains('ST_TRAD') and available_bands.contains('ST_URAD') :
            self.LST = self.surface_temperature_collection()
        else:
            self.LST = None
            raise ValueError("Insufficient Bands for temperature calculation")



    @staticmethod
    def image_dater(image):
        date = ee.Number(image.date().format('YYYY-MM-dd'))
        return image.set({'Date_Filter': date})
    
    @staticmethod
    def landsat5bandrename(img):
        return img.select('SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'QA_PIXEL').rename('SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'QA_PIXEL')
    
    @staticmethod
    def landsat_ndwi_fn(image, threshold):
        ndwi_calc = image.normalizedDifference(['SR_B3', 'SR_B5']) #green-NIR / green+NIR -- full NDWI image
        water = ndwi_calc.updateMask(ndwi_calc.gte(threshold)).rename('ndwi').copyProperties(image) 
        return water

    @staticmethod
    def landsat_ndvi_fn(image, threshold):
        ndvi_calc = image.normalizedDifference(['SR_B5', 'SR_B4']) #NIR-RED/NIR+RED -- full NDVI image
        vegetation = ndvi_calc.updateMask(ndvi_calc.gte(threshold)).rename('ndvi').copyProperties(image) # subsets the image to just water pixels, 0.2 threshold for datasets
        return vegetation
    
    @staticmethod
    def landsat_halite_fn(image, threshold):
        halite_index = image.normalizedDifference(['SR_B4', 'SR_B6'])
        halite = halite_index.updateMask(halite_index.gte(threshold)).rename('halite').copyProperties(image)
        return halite 
      
    @staticmethod
    def landsat_gypsum_fn(image, threshold):
        gypsum_index = image.normalizedDifference(['SR_B6', 'SR_B7'])
        gypsum = gypsum_index.updateMask(gypsum_index.gte(threshold)).rename('gypsum').copyProperties(image)
        return gypsum
    
    @staticmethod
    def MaskWaterLandsat(image):
        WaterBitMask = ee.Number(2).pow(7).int()
        qa = image.select('QA_PIXEL')
        water_extract = qa.bitwiseAnd(WaterBitMask).eq(0)
        masked_image = image.updateMask(water_extract).copyProperties(image)
        return masked_image

    @staticmethod
    def maskL8clouds(image):
        cloudBitMask = ee.Number(2).pow(3).int()
        CirrusBitMask = ee.Number(2).pow(2).int()
        qa = image.select('QA_PIXEL')
        cloud_mask = qa.bitwiseAnd(cloudBitMask).eq(0)
        cirrus_mask = qa.bitwiseAnd(CirrusBitMask).eq(0)
        return image.updateMask(cloud_mask).updateMask(cirrus_mask)
    
    @staticmethod
    def temperature_bands(img):
        #date = ee.Number(img.date().format('YYYY-MM-dd'))
        scale1 = ['ST_ATRAN', 'ST_EMIS']
        scale2 = ['ST_DRAD', 'ST_TRAD', 'ST_URAD']
        scale1_names = ['transmittance', 'emissivity']
        scale2_names = ['downwelling', 'B10_radiance', 'upwelling']
        scale1_bands = img.select(scale1).multiply(0.0001).rename(scale1_names) #Scaled to new L8 collection
        scale2_bands = img.select(scale2).multiply(0.001).rename(scale2_names) #Scaled to new L8 collection
        return img.addBands(scale1_bands).addBands(scale2_bands).copyProperties(img)
    
    @staticmethod
    def landsat_LST(image):
        # Based on Sekertekin, A., & Bonafoni, S. (2020) https://doi.org/10.3390/rs12020294
        
        k1 = 774.89
        k2 = 1321.08
        LST = image.expression(
            '(k2/log((k1/((B10_rad - upwelling - transmittance*(1 - emissivity)*downwelling)/(transmittance*emissivity)))+1)) - 273.15',
            {'k1': k1,
            'k2': k2,
            'B10_rad': image.select('B10_radiance'),
            'upwelling': image.select('upwelling'),
            'transmittance': image.select('transmittance'),
            'emissivity': image.select('emissivity'),
            'downwelling': image.select('downwelling')}).rename('LST')
        return image.addBands(LST).copyProperties(image) #.set({'Date_Filter': date}) #Outputs temperature in C
    
    @staticmethod
    def PixelAreaSum(image, band_name, geometry, threshold=-1, scale=30, maxPixels=1e12):
        # band_name = image.getInfo()['bands'][0]['id']
        area_image = ee.Image.pixelArea()
        mask = image.select(band_name).gte(threshold)
        final = image.addBands(area_image)
        stats = final.select('area').updateMask(mask).rename(band_name).reduceRegion(
            reducer = ee.Reducer.sum(),
            geometry= geometry,
            scale=scale,
            maxPixels = maxPixels)
        return image.set(band_name, stats.get(band_name))

    @staticmethod
    def dNDWIPixelAreaSum(image, geometry, band_name='ndwi', scale=30, maxPixels=1e12):
        def OtsuThreshold(histogram):
            counts = ee.Array(ee.Dictionary(histogram).get('histogram'))
            means = ee.Array(ee.Dictionary(histogram).get('bucketMeans'))
            size = means.length().get([0])
            total = counts.reduce(ee.Reducer.sum(), [0]).get([0])
            sum = means.multiply(counts).reduce(ee.Reducer.sum(), [0]).get([0])
            mean = sum.divide(total)
            indices = ee.List.sequence(1, size)

            def func_xxx(i):
                aCounts = counts.slice(0, 0, i)
                aCount = aCounts.reduce(ee.Reducer.sum(), [0]).get([0])
                aMeans = means.slice(0, 0, i)
                aMean = (
                    aMeans.multiply(aCounts)
                    .reduce(ee.Reducer.sum(), [0])
                    .get([0])
                    .divide(aCount)
                )
                bCount = total.subtract(aCount)
                bMean = sum.subtract(aCount.multiply(aMean)).divide(bCount)
                return aCount.multiply(aMean.subtract(mean).pow(2)).add(
                    bCount.multiply(bMean.subtract(mean).pow(2)))

            bss = indices.map(func_xxx)
            return means.sort(bss).get([-1])
        # band_name = image.getInfo()['bands'][0]['id']
        area_image = ee.Image.pixelArea()
        histogram = image.select(band_name).reduceRegion(
            reducer = ee.Reducer.histogram(255, 2),
            geometry = geometry.geometry().buffer(6000),
            scale = scale,
            bestEffort= True,)
        threshold = OtsuThreshold(histogram.get(band_name)).add(0.15) #was standard for last export #.add(0.15) removing threshold offset to ensure all water pixels are included for cyanobacteria detection
        mask = image.select(band_name).gte(threshold)
        final = image.addBands(area_image)
        stats = final.select('area').updateMask(mask).rename(band_name).reduceRegion(
            reducer = ee.Reducer.sum(),
            geometry= geometry,
            scale=scale,
            maxPixels = maxPixels)
        return image.set(band_name, stats.get(band_name))

    def get_filtered_collection(self):
        landsat8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        landsat9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        landsat5 = ee.ImageCollection("LANDSAT/LT05/C02/T1_L2").map(LandsatCollection.landsat5bandrename)  # Replace with the correct Landsat 5 collection ID
        filtered_collection = landsat8.merge(landsat9).merge(landsat5).filterDate(self.start_date, self.end_date).filter(ee.Filter.And(ee.Filter.eq('WRS_PATH', self.tile_path),
                                ee.Filter.eq('WRS_ROW', self.tile_row))).filter(ee.Filter.lte('CLOUD_COVER', self.cloud_percentage_threshold)).map(LandsatCollection.image_dater).sort('Date_Filter')
        return filtered_collection
    
    def ndwi_collection(self, threshold):
        col = self.collection.map(lambda image: LandsatCollection.landsat_ndwi_fn(image, threshold=self.ndwi_threshold))
        return LandsatSubCollection(col, self.dates_list)

    
    def ndvi_collection(self, threshold):
        col = self.collection.map(lambda image: LandsatCollection.landsat_ndvi_fn(image, threshold=self.ndvi_threshold))
        return LandsatSubCollection(col, self.dates_list)

    def halite_collection(self, threshold):
        col = self.collection.map(lambda image: LandsatCollection.landsat_halite_fn(image, threshold=self.halite_threshold))
        return LandsatSubCollection(col, self.dates_list)

    def gypsum_collection(self, threshold):
        col = self.collection.map(lambda image: LandsatCollection.landsat_gypsum_fn(image, threshold=self.gypsum_threshold))
        return LandsatSubCollection(col, self.dates_list)

    def masked_water_collection(self):
        col = self.collection.map(LandsatCollection.MaskWaterLandsat)
        return LandsatSubCollection(col, self.dates_list)
    
    def masked_clouds_collection(self):
        col = self.collection.map(LandsatCollection.maskL8clouds)
        return LandsatSubCollection(col, self.dates_list)
    
    def surface_temperature_collection(self):
        col = self.collection.map(LandsatCollection.temperature_bands).map(LandsatCollection.landsat_LST).map(LandsatCollection.image_dater)
        return LandsatSubCollection(col, self.dates_list)
    
    def list_of_dates(self):
        dates = self.collection.aggregate_array('Date_Filter').getInfo()
        return dates
    

    def image_grab(self, img_selector):
        new_col = self.collection.filter(ee.Filter.eq('Date_Filter', self.dates_list[img_selector])) #.filter(ee.Filter.eq('Date_Filter', img_selector))
        new_col_list = new_col.toList(new_col.size())
        return ee.Image(new_col_list.get(0))

    def custom_image_grab(self, img_col, img_selector):
        new_col = img_col.filter(ee.Filter.eq('Date_Filter', self.dates_list[img_selector])) #.filter(ee.Filter.eq('Date_Filter', img_selector))
        new_col_list = new_col.toList(new_col.size())
        return ee.Image(new_col_list.get(0))
    
    def image_pick(self, img_date):
        new_col = self.collection.filter(ee.Filter.eq('Date_Filter', img_date)) #.filter(ee.Filter.eq('Date_Filter', img_selector))
        new_col_list = new_col.toList(new_col.size())
        return ee.Image(new_col_list.get(0))
    
    def CollectionStitch(self, img_col2):  # this function mosaics north and south images only if their dates match. Ignores scenes without a partner.
        image_list = []
        dates_list = self.dates_list + img_col2.dates_list
        dates_list = sorted(list(set(dates_list)))  # Get unique sorted list of dates

        for date in dates_list:
            if date in self.dates_list and date in img_col2.dates_list:
                filtered_col1 = self.image_grab(self.dates_list.index(date))
                filtered_col2 = img_col2.image_grab(img_col2.dates_list.index(date))
                merged_col = ee.ImageCollection.fromImages([filtered_col1, filtered_col2])
                mosaic = merged_col.mosaic().copyProperties(filtered_col1).set('system:time_start', filtered_col1.get('system:time_start'))  # new collection images contain all image properties of the northern landsat image
                image_list.append(mosaic)
            else:
                None  # If the condition isn't met, do nothing and keep going through the list
        new_col = ee.ImageCollection.fromImages(image_list)
        return LandsatCollection(collection=new_col)
    
class LandsatSubCollection(LandsatCollection):
    def __init__(self, collection, dates_list):
        self.collection = collection
        self.dates_list = dates_list

    def get_filtered_collection(self):
        return self.collection
    
class Sentinel2Collection:
    def __init__(self, start_date=None, end_date=None, tile=None, cloud_percentage_threshold=None, nodata_threshold=None, collection=None):
        if collection is None and (start_date is None or end_date is None or tile is None or cloud_percentage_threshold is None or nodata_threshold is None):
            raise ValueError("Either provide all required fields (start_date, end_date, tile_row, tile_path, cloud_percentage_threshold) or provide a collection.")
        if collection is None:
            self.start_date = start_date
            self.end_date = end_date
            self.tile = tile
            self.cloud_percentage_threshold = cloud_percentage_threshold
            self.nodata_threshold = nodata_threshold

            # Filter the collection
            self.collection = self.get_filtered_collection()
        else:
            self.collection = collection

        self.dates_list = self.list_of_dates()
        self.ndwi_threshold = -1
        self.ndvi_threshold = -1
        self.halite_threshold = -1
        self.gypsum_threshold = -1
        self.masked_clouds_collection = self.masked_clouds_collection()

        # Check if the required bands are available
        first_image = self.collection.first()
        available_bands = first_image.bandNames()

        if available_bands.contains('B3') and available_bands.contains('B8'):
            self.ndwi = self.ndwi_collection(self.ndwi_threshold)
        else:
            self.ndwi = None
            raise ValueError("Insufficient Bands for ndwi calculation")
        
        if available_bands.contains('B4') and available_bands.contains('B8'):
            self.ndvi = self.ndvi_collection(self.ndvi_threshold)
        else:
            self.ndvi = None
            raise ValueError("Insufficient Bands for ndvi calculation")

        if available_bands.contains('B4') and available_bands.contains('B11'):
            self.halite = self.halite_collection(self.halite_threshold)
        else:
            self.halite = None
            raise ValueError("Insufficient Bands for halite calculation")

        if available_bands.contains('SR_B6') and available_bands.contains('SR_B7'):
            self.gypsum = self.gypsum_collection(self.gypsum_threshold)
        else:
            self.gypsum = None
            raise ValueError("Insufficient Bands for gypsum calculation")

    @staticmethod
    def image_dater(image):
        date = ee.Number(image.date().format('YYYY-MM-dd'))
        return image.set({'Date_Filter': date})
    
    
    @staticmethod
    def sentinel_ndwi_fn(image, threshold):
        ndwi_calc = image.normalizedDifference(['B3', 'B8']) #green-NIR / green+NIR -- full NDWI image
        water = ndwi_calc.updateMask(ndwi_calc.gte(threshold)).rename('ndwi').copyProperties(image) 
        return water

    @staticmethod
    def sentinel_ndvi_fn(image, threshold):
        ndvi_calc = image.normalizedDifference(['B8', 'B4']) #NIR-RED/NIR+RED -- full NDVI image
        vegetation = ndvi_calc.updateMask(ndvi_calc.gte(threshold)).rename('ndvi').copyProperties(image) # subsets the image to just water pixels, 0.2 threshold for datasets
        return vegetation

    @staticmethod
    def sentinel_halite_fn(image, threshold):
        halite_index = image.normalizedDifference(['B4', 'B11'])
        halite = halite_index.updateMask(halite_index.gte(threshold)).rename('halite').copyProperties(image)
        return halite

    @staticmethod
    def sentinel_gypsum_fn(image, threshold):
        gypsum_index = image.normalizedDifference(['B11', 'B12'])
        gypsum = gypsum_index.updateMask(gypsum_index.gte(threshold)).rename('gypsum').copyProperties(image)
        return gypsum
    
    @staticmethod
    def MaskCloudsS2(image):
        SCL = image.select('SCL')
        CloudMask = SCL.neq(9)
        return image.updateMask(CloudMask).copyProperties(image)
    
    @staticmethod
    def MaskWaterS2(image):
        SCL = image.select('SCL')
        WaterMask = SCL.neq(6)
        return image.updateMask(WaterMask).copyProperties(image)
    
    @staticmethod
    def PixelAreaSum(image, band_name, geometry, threshold=-1, scale=10, maxPixels=1e12):
        # band_name = image.getInfo()['bands'][0]['id']
        area_image = ee.Image.pixelArea()
        mask = image.select(band_name).gte(threshold)
        final = image.addBands(area_image)
        stats = final.select('area').updateMask(mask).rename(band_name).reduceRegion(
            reducer = ee.Reducer.sum(),
            geometry= geometry,
            scale=scale,
            maxPixels = maxPixels)
        return image.set(band_name, stats.get(band_name)) #calculates and returns summed pixel area as image property titled the same as the band name of the band used for calculation
    
    def get_filtered_collection(self):
        sentinel2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        filtered_collection = sentinel2.filterDate(self.start_date, self.end_date).filter(ee.Filter.inList('MGRS_TILE', [self.tile])).filter(ee.Filter.lte('NODATA_PIXEL_PERCENTAGE', self.nodata_threshold)) \
                                                        .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', self.cloud_percentage_threshold)).map(Sentinel2Collection.image_dater).sort('Date_Filter')
        return filtered_collection

    def ndwi_collection(self, threshold):
        col =  self.collection.map(lambda image: Sentinel2Collection.sentinel_ndwi_fn(image, threshold=self.ndwi_threshold))
        return Sentinel2SubCollection(col, self.dates_list)
    
    def ndvi_collection(self, threshold):
        col = self.collection.map(lambda image: Sentinel2Collection.sentinel_ndvi_fn(image, threshold=self.ndvi_threshold))
        return Sentinel2SubCollection(col, self.dates_list)

    def halite_collection(self, threshold):
        col = self.collection.map(lambda image: Sentinel2Collection.sentinel_halite_fn(image, threshold=self.halite_threshold))
        return Sentinel2SubCollection(col, self.dates_list)

    def gypsum_collection(self, threshold):
        col = self.collection.map(lambda image: Sentinel2Collection.sentinel_gypsum_fn(image, threshold=self.gypsum_threshold))
        return Sentinel2SubCollection(col, self.dates_list)

    def masked_water_collection(self):
        col = self.collection.map(Sentinel2Collection.MaskWaterS2)
        return Sentinel2SubCollection(col, self.dates_list)
    
    def masked_clouds_collection(self):
        col = self.collection.map(Sentinel2Collection.MaskCloudsS2)
        return Sentinel2SubCollection(col, self.dates_list)
    
    def list_of_dates(self):
        dates = self.collection.aggregate_array('Date_Filter').getInfo()
        return dates
    
    def image_grab(self, img_selector):
        new_col = self.collection.filter(ee.Filter.eq('Date_Filter', self.dates_list[img_selector])) 
        new_col_list = new_col.toList(new_col.size())
        return ee.Image(new_col_list.get(0))

    def custom_image_grab(self, img_col, img_selector):
        new_col = img_col.filter(ee.Filter.eq('Date_Filter', self.dates_list[img_selector])) 
        new_col_list = new_col.toList(new_col.size())
        return ee.Image(new_col_list.get(0))
    
    def image_pick(self, img_date):
        new_col = self.collection.filter(ee.Filter.eq('Date_Filter', img_date)) #.filter(ee.Filter.eq('Date_Filter', img_selector))
        new_col_list = new_col.toList(new_col.size())
        return ee.Image(new_col_list.get(0))
    
    def CollectionStitch(self, img_col2):  # this function mosaics north and south images only if their dates match. Ignores scenes without a partner.
        image_list = []
        dates_list = self.dates_list + img_col2.dates_list
        dates_list = sorted(list(set(dates_list)))  # Get unique sorted list of dates

        for date in dates_list:
            if date in self.dates_list and date in img_col2.dates_list:
                filtered_col1 = self.image_grab(self.dates_list.index(date))
                filtered_col2 = img_col2.image_grab(img_col2.dates_list.index(date))
                merged_col = ee.ImageCollection.fromImages([filtered_col1, filtered_col2])
                mosaic = merged_col.mosaic().copyProperties(filtered_col1).set('system:time_start', filtered_col1.get('system:time_start'))  # new collection images contain all image properties of the northern landsat image
                image_list.append(mosaic)
            else:
                None  # If the condition isn't met, do nothing and keep going through the list
        new_col = ee.ImageCollection.fromImages(image_list)
        return Sentinel2Collection(collection=new_col)

class Sentinel2SubCollection(Sentinel2Collection):
    def __init__(self, collection, dates_list):
        self.collection = collection
        self.dates_list = dates_list

    def get_filtered_collection(self):
        return self.collection

def CollectionStitch(img_col1, img_col2, copy_properties_from=1):  # this function mosaics north and south images only if their dates match. Ignores scenes without a partner.
    image_list = []
    dates_list = img_col1.dates_list + img_col2.dates_list
    dates_list = sorted(list(set(dates_list)))  # Get unique sorted list of dates

    for date in dates_list:
        if date in img_col1.dates_list and date in img_col2.dates_list:
            filtered_col1 = img_col1.image_grab(img_col1.dates_list.index(date))
            filtered_col2 = img_col2.image_grab(img_col2.dates_list.index(date))
            merged_col = ee.ImageCollection.fromImages([filtered_col1, filtered_col2])
            if copy_properties_from == 1:
                mosaic = merged_col.mosaic().copyProperties(filtered_col1)  # new collection images contain all image properties of the northern landsat image
            elif copy_properties_from == 2:
                mosaic = merged_col.mosaic().copyProperties(filtered_col2)  # new collection images contain all image properties of the southern landsat image
            else:
                raise ValueError("Invalid value for 'copy_properties_from'. Must be 1 or 2.")  # new collection images contain all image properties of the northern landsat image
            image_list.append(mosaic)
        else:
            None  # If the condition isn't met, do nothing and keep going through the list
    new_col = ee.ImageCollection.fromImages(image_list)
    return new_col