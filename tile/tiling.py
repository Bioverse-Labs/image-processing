import os
import gdal
import cv2
import logging
import shapefile
import numpy as np
import geopandas as gp
import glob
import settings

from shapely.geometry import Polygon
from PIL import Image, ImageDraw

logging.getLogger('shapely.geos').setLevel(logging.CRITICAL)


class Tiling:
    """ Command-line routine to tile images and shapefiles according to desired width and heights """

    def __init__(self):
        pass

    def unify_color(self, path_input_image, desired_colors):
        """
        :param path_input_image:
        :param desired_colors:
        :return:
        """
        if not os.path.isfile(path_input_image):
            logging.warning(">>>> {} not a file!".format(path_input_image))
            return

        dirname = os.path.dirname(path_input_image)
        filename = os.path.basename(path_input_image)
        output = os.path.join(dirname, filename + "_unified.png")

        if os.path.isfile(path_input_image):
            logging.info(">> Unifying facade color classes...")
            image = cv2.imread(path_input_image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            rows, cols, bands = image.shape
            im = np.zeros((rows, cols, bands), dtype=np.uint8)

            for i in range(rows):
                for j in range(cols):
                    color = image[i, j]
                    color = map(int, color)

                    if (color == [85, 255, 170]) or (color == [170, 255, 85]):
                        color_code = desired_colors[4]
                    elif (color == [0, 85, 255]) or (color == [255, 255, 0]):
                        color_code = desired_colors[5]
                    elif (color == [0, 170, 255]) or (color == [170, 0, 0]):
                        color_code = desired_colors[6]
                    else:
                        color_code = desired_colors[3]

                    im[i][j] = color_code
        else:
            logging.info(">>>> {} is not a valid file. Check and try again!".format(path_input_image))

        cv2.imwrite(output, cv2.cvtColor(im, cv2.COLOR_RGB2BGR))
        logging.info("Annotated image with unified classes saved as {}".format(output))

    # TODO: refactor
    def slice_array(self, array, positions):
        """
        :param array:
        :param positions:
        :return:
        """
        new_arrays = []
        positions.append(len(array) - 1)

        for i in range(len(positions) - 1):
            new_arrays.append(array[positions[i]:positions[i + 1]])

        return new_arrays

    def shp2png(self, raster_folder, shapefile_folder, output_folder, width, height, classes):
        """
        Source: https://github.com/GeospatialPython/geospatialpython/blob/master/shp2img.py
        Example of classes variable:
        classes = {
                "def": [255, 255, 0],
                "water": [102, 204, 255],
                "cloud": [255, 255, 255],
                "shadow": [128, 128, 128]
            }
        :param raster_folder:
        :param shapefile_folder:
        :param output_folder:
        :param width:
        :param height:
        :param classes:
        :return:
        """
        files = os.listdir(shapefile_folder)
        shp_list = [file for file in files if file.endswith(settings.VALID_VECTOR_EXTENSION)]

        for shape in shp_list:
            name, file_extension = os.path.splitext(shape)
            shape_path = os.path.join(shapefile_folder, shape)
            output = os.path.join(output_folder, name + ".png")
            raster = os.path.join(raster_folder, name + ".TIF")

            if os.path.isfile(raster):
                tile = gdal.Open(raster)
                gt = tile.GetGeoTransform()
                cols_tile = tile.RasterXSize
                rows_tile = tile.RasterYSize
                ext = self.get_extent(gt, cols_tile, rows_tile)
            else:
                continue

            if os.path.isfile(shape_path):
                # TODO: try to predict the encoding - hard-coded
                r = shapefile.Reader(shape_path, encoding='ISO8859-1')
                if not r:
                    logging.info('>>>> Error: could not open the shapefile')
                    continue
            else:
                logging.info('>>>> Error: could not open the shapefile')
                continue

            x_dist = ext[3][0] - ext[1][0]
            y_dist = ext[3][1] - ext[1][1]
            x_ratio = width / x_dist
            y_ratio = height / y_dist

            shapes = r.shapes()
            records = r.records()

            img = Image.new("RGB", (width, height), "black")
            draw = ImageDraw.Draw(img)

            for i, record in enumerate(records):
                if record[1] in classes:
                    parts = shapes[i].parts
                    pixels = []
                    for x, y in shapes[i].points:
                        px = int(width - ((ext[3][0] - x) * x_ratio))
                        py = int((ext[3][1] - y) * y_ratio)
                        pixels.append((px, py))

                    if len(parts) > 1:
                        polygons_parts = self.slice_array(pixels, parts)
                        for k in range(len(polygons_parts)):
                            draw.polygon(polygons_parts[k], outline=None,
                                         fill="rgb(" + str(classes[record[1]][0]) + ", " + str(
                                             classes[record[1]][1]) + ", " + str(classes[record[1]][2]) + ")")
                    else:
                        draw.polygon(pixels, outline=None, fill="rgb(" + str(classes[record[1]][0]) + ", " + str(
                            classes[record[1]][1]) + ", " + str(classes[record[1]][2]) + ")")
            img.save(output)

    def get_extent(self, gt, cols, rows):
        """
        Source: https://gis.stackexchange.com/questions/57834/how-to-get-raster-corner-coordinates-using-python-gdal-bindings
        :param gt:
        :param cols:
        :param rows:
        :return:
        """
        ext = []
        x_arr = [0, cols]
        y_arr = [0, rows]

        for px in x_arr:
            for py in y_arr:
                x = gt[0] + (px * gt[1]) + (py * gt[2])
                y = gt[3] + (px * gt[4]) + (py * gt[5])
                ext.append([x, y])
            y_arr.reverse()
        return ext

    def tiling_raster(self, image, output_folder, width, height):
        """
        :param image:
        :param output_folder:
        :param width:
        :param height:
        :return:
        """
        if os.path.isfile(image) and image.endswith(settings.VALID_RASTER_EXTENSION):
            filename = os.path.basename(image)
            name, file_extension = os.path.splitext(filename)
            ds = gdal.Open(image)

            if ds is None:
                logging.warning(">>>>>> Could not open image file {}. Skipped!".format(image))

            stats = [ds.GetRasterBand(i + 1).GetStatistics(True, True) for i in range(ds.RasterCount)]
            vmin, vmax, vmean, vstd = zip(*stats)

            rows = ds.RasterXSize
            cols = ds.RasterYSize
            tiles_cols = cols / width
            tiles_rows = rows / height
            logging.info(">>>> Tiling image {}. {} x {} pixels. Estimated {} tiles of {} x {}..."
                         .format(image, rows, cols, round(tiles_cols * tiles_rows), width, height))

            gdal.UseExceptions()
            for i in range(0, rows, width):
                for j in range(0, cols, height):
                    try:
                        output = os.path.join(output_folder, name + "_" + str(i) + "_" + str(j) + file_extension)
                        gdal.Translate(output, ds, format='GTIFF', srcWin=[i, j, width, height],
                                       outputType=gdal.GDT_UInt16, scaleParams=[[list(zip(*[vmin, vmax]))]],
                                       options=['-epo', '-eco', '-b', '5', '-b', '3', '-b', '2'])

                    except RuntimeError:
                        continue

    def tiling_vector(self, image_tiles_folder, shp_reference, output_folder):
        """
        :param image_tiles_folder:
        :param shp_reference:
        :param output_folder:
        :return:
        """
        if not os.path.isdir(image_tiles_folder):
            logging.warning(">>>> {} is not a folder!".format(image_tiles_folder))
            return

        if not os.path.isfile(shp_reference):
            logging.warning(">>>> {} is not a file!".format(shp_reference))
            return

        filename = os.path.basename(shp_reference)
        name, file_extension = os.path.splitext(filename)

        if file_extension.lower() not in settings.VALID_VECTOR_EXTENSION:
            logging.warning(">>>> {} not a valid extension for a vector!".format(file_extension))
            return

        logging.info(">> Tiling vector {} respecting to the tiles extends".format(shp_reference))

        list_correspondent_raster = glob.glob(os.path.join(image_tiles_folder, name + '*'))
        for image in list_correspondent_raster:
            filename = os.path.basename(image)
            name, ext = os.path.splitext(filename)

            if ext.lower() not in settings.VALID_RASTER_EXTENSION:
                logging.warning(">>>> {} not a valid extension for a raster!".format(ext))
                continue

            complete_path = os.path.join(image_tiles_folder, image)
            tile = gdal.Open(complete_path)

            gt = tile.GetGeoTransform()
            cols_tile = tile.RasterXSize
            rows_tile = tile.RasterYSize
            ext = self.get_extent(gt, cols_tile, rows_tile)

            bounds = Polygon(ext)
            baseshp = gp.read_file(shp_reference)

            # TODO: define shapefile crs from image crs
            # srs = osr.SpatialReference()
            # srs.ImportFromWkt(tile.GetProjection())
            baseshp = baseshp.to_crs('epsg:32722')

            ids = []
            classes = []
            polygons_intersecting = []
            for i in range(len(baseshp)):
                p1 = baseshp['geometry'][i]
                p2 = bounds

                if p1.is_valid is False:
                    p1 = p1.buffer(0)

                if not p1.intersection(p2).is_empty:
                    ids.append(i)
                    classes.append(baseshp[settings.CLASS_NAME][i])
                    polygons_intersecting.append(p1.intersection(p2))

            if len(polygons_intersecting) != 0:
                gdf = gp.GeoDataFrame()
                gdf.crs = baseshp.crs
                gdf['id'] = ids
                gdf['class'] = classes
                gdf['geometry'] = polygons_intersecting

                output = os.path.join(output_folder, name + ".shp")
                gdf.to_file(output, driver='ESRI Shapefile')
            else:
                os.remove(complete_path)

