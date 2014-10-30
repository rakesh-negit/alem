from settings import *
from utilfunctions import *
from apifunctions import *
import math
import logging
import gflags
import sys
import os
import shutil
from glob import glob
import arcpy
from pprint import pprint  # lint:ok
import numpy as np
from dbfpy import dbf
import csv
import time

FLAGS = gflags.FLAGS

arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension('spatial')
logging.basicConfig(format='%(asctime)s %(name)s[%(levelname)s]:%(message)s', level=logging.INFO)
defaultLogger = logging.getLogger(__name__)


class ALEMObject():

    def __init__(self, sceneId, logger=defaultLogger):
        self.next = 'configure_analysis'
        self.sceneId = sceneId

    def configure_analysis(self, logger=defaultLogger, **kwargs):
        self.string_args = {
            'scene': self.sceneId,
            'path':self.sceneId[3:6],
            'row':self.sceneId[6:9],
            'bqa_or_rad':kwargs.get('bqa_or_rad', DEFAULT_ANALYSIS['bqa_or_rad']),
            'zstat_mode':kwargs.get('zstat_mode', DEFAULT_ANALYSIS['zstat_mode']),
            'var':kwargs.get('var', DEFAULT_ANALYSIS['var'])
        }
        self.bands = {
            'bdivb':kwargs.get('bdivb',DEFAULT_ANALYSIS['bdivb']),
            'bxb':kwargs.get('bxb', DEFAULT_ANALYSIS['bxb']),
            'b':kwargs.get('b', DEFAULT_ANALYSIS['b'])
        }

        band_parameters = []
        unique_bands = []

        for [x, y] in self.bands['bdivb']:
            band_name = 'b{}divb{}'.format(x,y)
            band_folder = (BR_GRID_FOLDER + 'b{x}divb{y}').format(x=x, y=y, **self.string_args)
            band_parameters.append([band_name, band_folder])
            unique_bands.append(x)
            unique_bands.append(y)
        for [x, y] in self.bands['bxb']:
            band_name = 'b{}xb{}'.format(x,y)
            band_folder = (BR_GRID_FOLDER + 'b{x}x{y}').format(x=x, y=y, **self.string_args)
            band_parameters.append([band_name, band_folder])
            unique_bands.append(x)
            unique_bands.append(y)
        for x in self.bands['b']:
            band_name = 'b{}'.format(x)
            if self.string_args['bqa_or_rad'] == 'rad':
                band_folder = (TOA_GRID_FOLDER + 'toa_rad_b{x}').format(x=x, **self.string_args)
            else:
                band_folder = (TOA_BQA_FOLDER + 'toa_bqa_b{x}').format(x=x, **self.string_args)
            band_parameters.append([band_name, band_folder])
            unique_bands.append(x)

        self.band_parameters = band_parameters
        self.unique_bands = set(unique_bands)
        self.next = 'create_folders'
        logger.info('Configured analysis settings for {scene}'.format(**self.string_args))
        return None

    def create_folders(self, logger=defaultLogger):
        for [band_name, band_folder] in (self.band_parameters + [['all','']]):
            self.string_args['band']=band_name
            for folder in [
                TOA_GRID_FOLDER,
                BR_GRID_FOLDER,
                TEMP_GRID_FOLDER,
                BANDS_DBF_FOLDER,
                SAMPLE_DBF_FOLDER,
                R_OUTPUT_FOLDER,
                TOA_BQA_FOLDER,
                POINTS_SPLIT_FOLDER,
                TEMP_DBF_FOLDER,
                R_LEAPS_FOLDER,
                SEL_POINTS_FOLDER,
                SEL_SPLIT_FOLDER,
                SEL_TEMP_DBF_FOLDER ]:
                if not os.path.exists(folder.format(**self.string_args)):
                    os.makedirs(folder.format(**self.string_args))

        self.next = 'parse_metadata'
        logger.info('Created folders for {scene}'.format(**self.string_args))
        return None

    def parse_metadata(self, logger=defaultLogger):
        values = []
        with open((IMAGE_FOLDER + '{scene}_MTL.TXT').format(**self.string_args)) as fh:
            for line in fh:
                values.append(line)

        keys = []
        for value in values:
            if value[3] == " ":
                keys.append(value[4:-1])

        for i in range(len(keys)):
            keys[i] = keys[i].split(' = ')
            if (keys[i][1][0] != '"'):
                keys[i][1] = '"{}"'.format(keys[i][1])
            keys[i] = '='.join(keys[i])

        keys = ', '.join(keys)

        exec('self.metadata = dict({})'.format(keys))
        logger.info('Parsed metadata for {scene}.'.format(**self.string_args))
        self.next='upload_metadata'
        return None

    def upload_metadata(self, logger=defaultLogger):
        fusionTable = FusionTables()
        service = fusionTable.connect()

        query = 'SELECT Scene_Id FROM {fid}'.format(fid=ID_IMAGES)
        response = service.query().sql(sql=query).execute()
        sceneIDs = []
        response_list = convert_query_response_to_list(response)
        for row in response_list[1:]:
            sceneIDs.append(row[0])

        if sceneIDs.count(self.sceneId) == 0:
            columns = ['Scene_Id', 'Path', 'Row', 'Year', 'Month','Day','Geom']
            polygon="""<Polygon><outerBoundaryIs><coordinates> {},{},0 {},{},0 {},{},0 {},{},0 </coordinates></outerBoundaryIs></Polygon>""".format(
                self.metadata['CORNER_LR_LON_PRODUCT'],
                self.metadata['CORNER_LR_LAT_PRODUCT'],
                self.metadata['CORNER_LL_LON_PRODUCT'],
                self.metadata['CORNER_LL_LAT_PRODUCT'],
                self.metadata['CORNER_UL_LON_PRODUCT'],
                self.metadata['CORNER_UL_LAT_PRODUCT'],
                self.metadata['CORNER_UR_LON_PRODUCT'],
                self.metadata['CORNER_UR_LAT_PRODUCT']
            )
            data = [
                self.sceneId,
                self.metadata['WRS_PATH'],
                self.metadata['WRS_ROW'],
                self.metadata['DATE_ACQUIRED'][0:4],
                self.metadata['DATE_ACQUIRED'][5:7],
                self.metadata['DATE_ACQUIRED'][8:10],
                polygon
            ]

            fusionTable.insert_list(ID_IMAGES, [columns, data])
            logger.info('Uploaded metadata to fusion table for scene {scene}'.format(**self.string_args))

        else:
            logger.info('Did not upload. Scene info for {scene} already in fusion table.'.format(**self.string_args))

        self.next = 'arcgis_prepare_toa'
        return None

    def set_up_default(self, logger=defaultLogger):
        self.configure_analysis(logger=logger)
        self.create_folders(logger=logger)
        self.parse_metadata(logger=logger)
        self.upload_metadata(logger=logger)
        self.next = 'arcgis_analysis'
        return None

    def arcgis_prepare_toa(self, logger=defaultLogger):
        for i in self.unique_bands:
            band_tiff = (IMAGE_FOLDER + '{scene}_B{i}.TIF').format(i=i, **self.string_args)
            radiance_mult_band = str(float(self.metadata['REFLECTANCE_MULT_BAND_{}'.format(i)]))
            radiance_add_band = str(float(self.metadata['REFLECTANCE_ADD_BAND_{}'.format(i)]))
            times_b_rad = (TEMP_GRID_FOLDER + 'times_b{i}_rad').format(i=i, **self.string_args)
            prime_rad_b = (TEMP_GRID_FOLDER + 'prime_rad_b{i}').format(i=i, **self.string_args)
            toa_rad_b = (TOA_GRID_FOLDER + 'toa_rad_b{i}').format(i=i, **self.string_args)

            print('Processing band {}'.format(i))
            if not os.path.exists(times_b_rad):
                with open(PROCESS_FILE.format(**self.string_args), 'w') as f:
                    f.write(times_b_rad)
                arcpy.gp.Times_sa(band_tiff, radiance_mult_band, times_b_rad)
            if not os.path.exists(prime_rad_b):
                with open(PROCESS_FILE.format(**self.string_args), 'w') as f:
                    f.write(times_b_rad)
                arcpy.gp.Plus_sa(times_b_rad, radiance_add_band, prime_rad_b)
            if not os.path.exists(toa_rad_b):
                with open(PROCESS_FILE.format(**self.string_args), 'w') as f:
                        f.write(times_b_rad)
                arcpy.gp.Float_sa(prime_rad_b, toa_rad_b)

        logger.info('Prepared TOA rasters for scene {scene}'.format(**self.string_args))
        if os.path.exists(PROCESS_FILE.format(**self.string_args)):
            os.remove(PROCESS_FILE.format(**self.string_args))
        self.next = 'arcgis_prepare_bqa'
        return None

    def arcgis_prepare_bqa(self, logger=defaultLogger):
        arcpy.env.extent = 'MAXOF'
        bqa_reclass = (TEMP_GRID_FOLDER + 'bqa_reclass').format(**self.string_args)
        bqa_band_tiff = (IMAGE_FOLDER + '{scene}_BQA.TIF').format(**self.string_args)

        arcpy.gp.Reclassify_sa(bqa_band_tiff, "Value", "0 10000 1;10000 16381 NODATA;16381 24000 1;24000 70000 NODATA", bqa_reclass, "DATA")

        for i in self.unique_bands:
            toa_rad_b = (TOA_GRID_FOLDER + 'toa_rad_b{i}').format(i=i, **self.string_args)
            toa_bqa_b = (TOA_BQA_FOLDER + 'toa_bqa_b{i}').format(i=i, **self.string_args)

            print('Processing band {}'.format(i))
            if not os.path.exists(toa_bqa_b):
                with open(PROCESS_FILE.format(**self.string_args), 'w') as f:
                    f.write(toa_bqa_b)
                arcpy.gp.Times_sa(bqa_reclass, toa_rad_b, toa_bqa_b)

        logger.info('Prepared TOA times BQA rasters for scene {scene}'.format(**self.string_args))
        if os.path.exists(PROCESS_FILE.format(**self.string_args)):
            os.remove(PROCESS_FILE.format(**self.string_args))
        self.next = 'arcgis_prepare_band_ratios'
        return None

    def arcgis_prepare_band_ratios(self, logger=defaultLogger):
        for [x, y] in self.bands['bdivb']:
            output = (BR_GRID_FOLDER + 'b{x}divb{y}').format(x=x, y=y, **self.string_args)
            if self.string_args['bqa_or_rad'] == 'bqa':
                numerator_toa = (TOA_BQA_FOLDER + 'toa_bqa_b{x}').format(x=x, **self.string_args)
                denominator_toa = (TOA_BQA_FOLDER + 'toa_bqa_b{y}').format(y=y, **self.string_args)
            else:
                numerator_toa = (TOA_GRID_FOLDER + 'toa_rad_b{y}').format(x=x, **self.string_args)
                denominator_toa = (TOA_GRID_FOLDER + 'toa_rad_b{y}').format(y=y, **self.string_args)

            if not os.path.exists(output):
                with open(PROCESS_FILE.format(**self.string_args), 'w') as f:
                    f.write(output)
                arcpy.gp.Divide_sa(numerator_toa, denominator_toa, output)

        logger.info('Prepared band ratios for scene {scene}'.format(**self.string_args))
        if os.path.exists(PROCESS_FILE.format(**self.string_args)):
            os.remove(PROCESS_FILE.format(**self.string_args))
        self.next = 'arcgis_prepare_band_products'
        return None

    def arcgis_prepare_band_products(self, logger=defaultLogger):
        for [x, y] in self.bands['bxb']:
            output = (BR_GRID_FOLDER + 'b{x}x{y}').format(x=x, y=y, **self.string_args)
            if self.string_args['bqa_or_rad'] == 'bqa':
                mult_toa1 = (TOA_BQA_FOLDER + 'toa_bqa_b{x}').format(x=x, **self.string_args)
                mult_toa2 = (TOA_BQA_FOLDER + 'toa_bqa_b{y}').format(y=y, **self.string_args)
            else:
                mult_toa1 = (TOA_GRID_FOLDER + 'toa_rad_b{x}').format(x=x, **self.string_args)
                mult_toa2 = (TOA_GRID_FOLDER + 'toa_rad_b{y}').format(y=y, **self.string_args)

            if not os.path.exists(output):
                with open(PROCESS_FILE.format(**self.string_args), 'w') as f:
                    f.write(output)
                arcpy.gp.Times_sa(mult_toa1, mult_toa2, output)

        logger.info('Prepared band products for scene {scene}'.format(**self.string_args))
        if os.path.exists(PROCESS_FILE.format(**self.string_args)):
            os.remove(PROCESS_FILE.format(**self.string_args))

        return None

    def arcgis_zstat_poly_analysis(self, logger=defaultLogger):
        self.string_args['ext'] = 'dbf'

        buffer_file = (BUFFERS_FOLDER + BUFFER_FILE).format(**self.string_args)
        field1 = 'NID'

        for [band_name, band_folder] in self.band_parameters:
            self.string_args['band'] = band_name

            output_all = (BANDS_DBF_FOLDER + BANDS_FILE_ALL).format(**self.string_args)
            output_final = (BANDS_DBF_FOLDER + BANDS_FILE).format(**self.string_args)
            field2 = band_name

            if not os.path.exists(output_final) and not os.path.exists(output_final.replace('dbf','csv')):
                print('Processing band {} of scene {scene}'.format(band_name, **self.string_args))
                with open(PROCESS_FILE.format(**self.string_args), 'w') as f:
                    f.write(output_final)
                arcpy.gp.ZonalStatisticsAsTable_sa(buffer_file, field1, band_folder, output_all, "DATA", 'ALL')
                arcpy.Copy_management(output_all, output_final, "")
                arcpy.AddField_management(output_final,field2, 'DOUBLE', "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
                arcpy.CalculateField_management(output_final, field2, '[MEAN]', "VB", "")
                arcpy.DeleteField_management(output_final, "AREA;MIN;MAX;MEAN;SUM;FID_CARBBA;FID_SAMPLE;Year;Month;Day;Source;Date_freef;Latitude_s;Longitude_;SubSite;Lat_number;LAKENAME_1;LAKENAME_2;SHAPE_LENG;SHAPE_AREA;ID;GRIDCODE;AREA_1;NID_1;ID_1;GRIDCODE_1;NID_12;ZONE-CODE")
                os.remove(PROCESS_FILE.format(**self.string_args))

        #logger.info('Performed zstat poly analysis for scene {scene}'.format(**self.string_args))
        if os.path.exists(PROCESS_FILE.format(**self.string_args)):
            os.remove(PROCESS_FILE.format(**self.string_args))
        return None

    def arcgis_zstat_points_analysis(self, logger=defaultLogger):

        #arcpy.ImportToolbox("Model Functions")
        arcpy.ImportToolbox("C:\\2_ALEM_Lakes_Project\\3.Scripts_for_Analyses\\SplitLayerByAttributes\\SplitLayerByAttributes.tbx")

        #Split points into separate files
        intersectParam1 = BUFFERS_90M_FILE + ' #;' + (BUFFERS_FOLDER + BUFFER_FILE).format(**self.string_args) + ' #'
        intersectSHP = (TEMP_GRID_FOLDER + 'intersect_lakes.shp').format(**self.string_args)
        self.string_args['ext'] = 'csv'
        dbfFile2 = (SAMPLE_DBF_FOLDER + SAMPLE_PTS_FILE).format(**self.string_args)
        self.string_args['ext'] = 'dbf'

        arcpy.Buffer_analysis(SAMPLE_POINTS_FILE, BUFFERS_90M_FILE, "90 Meters", "FULL", "ROUND", "NONE", "")
        arcpy.Intersect_analysis(intersectParam1, intersectSHP, "ALL", "", "INPUT")
        arcpy.AddField_management(intersectSHP, "Zone_FID", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        arcpy.CalculateField_management(intersectSHP, "Zone_FID", "[FID]", "VB", "")
        arcpy.ExportXYv_stats(intersectSHP, "FID_output;SiteCode;Year;Month;Day;Source;Date_freef;DOC;CDOM;CHL;Zone_FID", "COMMA", dbfFile2, "NO_FIELD_NAMES")
        arcpy.gp.toolbox = "C:/2_ALEM_Lakes_Project/3.Scripts_for_Analyses/SplitLayerByAttributes/SplitLayerByAttributes.tbx";
        arcpy.gp.SplitLayerByAttributes(intersectSHP, "FID", "FID_", POINTS_SPLIT_FOLDER.format(**self.string_args))

        for [band_name, band_folder] in self.band_parameters:
            print('Processing band {}'.format(band_name))
            self.string_args['band']= band_name
            outFolder1 = (TEMP_GRID_FOLDER + 'ext_{band}').format(**self.string_args)
            outFolder2 = (TEMP_GRID_FOLDER + 'calc_{band}').format(**self.string_args)


            #Iterate through each file created when splitting points
            for iterationFile in glob(POINTS_SPLIT_FOLDER.format(**self.string_args) + '*.shp'):
                print(iterationFile)
                FID = iterationFile.split('\\')[-1].split('.')[0]
                dbfFile1 = (TEMP_DBF_FOLDER + BANDS_FILE_CALC).format(FID=FID, **self.string_args)

                arcpy.gp.ExtractByMask_sa(band_folder, iterationFile, outFolder1)
                arcpy.gp.RasterCalculator_sa("Int(\"{}\" * 0)".format(outFolder1), outFolder2)
                arcpy.BuildRasterAttributeTable_management(outFolder2, "NONE")
                arcpy.gp.ZonalStatisticsAsTable_sa(outFolder2, "VALUE", outFolder1, dbfFile1, "DATA", "ALL")

        logger.info('Performed zstat points analysis for scene {scene}'.format(**self.string_args))
        return None

    def arcgis_zstat_selected_points_analysis(self, logger=defaultLogger):

        #arcpy.ImportToolbox("Model Functions")
        arcpy.ImportToolbox("C:\\2_ALEM_Lakes_Project\\3.Scripts_for_Analyses\\SplitLayerByAttributes\\SplitLayerByAttributes.tbx")
        arcpy.gp.toolbox = "C:/2_ALEM_Lakes_Project/3.Scripts_for_Analyses/SplitLayerByAttributes/SplitLayerByAttributes.tbx"

        #Split points into separate files
        self.string_args['ext'] = 'dbf'
        intersectParam1 = SEL_BUFFERS_90M_FILE + ' #;' + (BUFFERS_FOLDER + BUFFER_FILE).format(**self.string_args) + ' #'
        intersectSHP = TEMP_GRID_FOLDER.format(**self.string_args) + 'intersect_sel_lakes.shp'
        dbfFile2 = (SEL_POINTS_FOLDER + SEL_POINTS_FILE).format(**self.string_args)

        if not os.path.exists(intersectSHP):
            arcpy.Intersect_analysis(intersectParam1, intersectSHP, "ALL", "", "INPUT")

        if not os.path.exists(dbfFile2) and not os.path.exists(dbfFile2.replace('dbf','csv')):
            arcpy.AddField_management(intersectSHP, "Zone_FID", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
            arcpy.CalculateField_management(intersectSHP, "Zone_FID", "[FID]", "VB", "")
            arcpy.ExportXYv_stats(intersectSHP, "FID;SubSite;SiteCode;Count;CDOM", "COMMA", dbfFile2, "ADD_FIELD_NAMES")

        if not os.path.exists((SEL_SPLIT_FOLDER + 'FID_00.shp').format(**self.string_args)) and not os.path.exists((SEL_SPLIT_FOLDER + 'FID_0.shp').format(**self.string_args)):
            arcpy.gp.SplitLayerByAttributes(intersectSHP, "FID", "FID_", SEL_SPLIT_FOLDER.format(**self.string_args))

        for [band_name, band_folder] in self.band_parameters:
            self.string_args['band']=band_name
            outFolder1 = (TEMP_GRID_FOLDER + 'ext_{band}').format(**self.string_args)
            outFolder2 = (TEMP_GRID_FOLDER + 'calc_{band}').format(**self.string_args)


            #Iterate through each file created when splitting points
            for iterationFile in glob((SEL_SPLIT_FOLDER + 'FID_*.shp').format(**self.string_args)):
                FID = iterationFile.split('\\')[-1].split('.')[0]
                dbfFile1 = (SEL_TEMP_DBF_FOLDER + SEL_BANDS_FILE_CALC).format(FID=FID, **self.string_args)
                if not os.path.exists(dbfFile1) and not os.path.exists(dbfFile1[0:-3] + 'csv'):
                    print(dbfFile1)
                    arcpy.gp.ExtractByMask_sa(band_folder, iterationFile, outFolder1)
                    arcpy.gp.RasterCalculator_sa("Int(\"{}\" * 0)".format(outFolder1), outFolder2)
                    time.sleep(5)
                    arcpy.BuildRasterAttributeTable_management(outFolder2, "NONE")
                    arcpy.gp.ZonalStatisticsAsTable_sa(outFolder2, "VALUE", outFolder1, dbfFile1, "DATA", "ALL")

        logger.info('Performed selected points analysis for scene {scene}'.format(**self.string_args))
        return None

    def arcgis_zstat_analysis(self, logger=defaultLogger):
        if self.string_args['zstat_mode'] == 'poly':
            self.arcgis_zstat_poly_analysis(logger=logger)
        elif self.string_args['zstat_mode'] == 'points':
            self.arcgis_zstat_points_analysis(logger=logger)
        elif self.string_args['zstat_mode'] == 'sel':
            self.arcgis_zstat_selected_points_analysis(logger=logger)

        self.next = 'convert_dbfs_to_csvs'
        return None

    def arcgis_analysis(self, logger=defaultLogger):
        self.arcgis_prepare_toa(logger=logger)

        if self.string_args['bqa_or_rad'] == 'bqa':
            self.arcgis_prepare_bqa(logger=logger)

        self.arcgis_prepare_band_ratios(logger=logger)
        self.arcgis_prepare_band_products(logger=logger)
        self.arcgis_zstat_analysis(logger=logger)

        self.next = 'r_analysis'
        return None

    def convert_dbfs_to_csvs(self, logger=defaultLogger):
        for [band_name, band_folder] in self.band_parameters:
            self.string_args['band'] = band_name
            for dbfFilename in (glob(BANDS_DBF_FOLDER.format(**self.string_args) + '*.dbf')
                + glob(TEMP_DBF_FOLDER.format(**self.string_args) + '*.dbf')
                + glob(SAMPLE_DBF_FOLDER.format(**self.string_args) + '*.dbf')
                + glob(SEL_POINTS_FOLDER.format(**self.string_args) + '*.dbf')
                + glob(SEL_TEMP_DBF_FOLDER.format(**self.string_args) + '*.dbf')):

                ### Code for dbfpy module
                csvFilename = dbfFilename.replace('.dbf', '.csv')
                with open(csvFilename, 'wb') as outCSV:
                    inDBF = dbf.Dbf(dbfFilename)
                    #outCSV = open(csvFilename, 'wb')
                    csvWriter = csv.writer(outCSV)

                    names = [field.name for field in inDBF.header.fields]
                    csvWriter.writerow(names)

                    for rec in inDBF:
                        csvWriter.writerow(rec.fieldData)

                    inDBF.close()

                if os.path.exists(csvFilename):
                    try:
                        os.remove(dbfFilename)
                    except OSError:
                        pass
                    try:
                        os.remove(dbfFilename + '.xml')
                    except OSError:
                        pass
        return None

    def merge_points_csvs(self, logger=defaultLogger):
        #self.string_args['ext'] = 'csv'
        #sample_data = load_csv_as_list((SAMPLE_DBF_FOLDER + SAMPLE_PTS_FILE).format(**self.string_args))

        #for [band_name, band_folder] in self.band_parameters:
            #list_out = [['NID', self.string_args['var'], 'BAND']]
            #self.string_args['band'] = band_name
            #for row in sample_data:
                #NID = row[3]
                #FID = 'FID_{0:0>2}'.format(row[12])
                #varValue = {}
                #varValue['DOC'] = row[9]
                #varValue['CDOM'] = row[10]
                #varValue['CHL'] = row[11]

                #VAR = varValue[self.string_args['var']]
                #band_list = load_csv_as_list((TEMP_DBF_FOLDER + BANDS_FILE_CALC).format(FID=FID, **self.string_args))
                #if VAR != 0:
                    #try:
                        #BAND = band_list[1][6]
                    #except IndexError:
                        #logger.warning('No zstat for polygon {}'.format(FID))
                    #else:
                        #list_out.append([NID, VAR, BAND])

            #write_list_to_csv(list_out, (SAMPLE_DBF_FOLDER + MERGED_FILE).format(**self.string_args))

        return None

    def merge_sel_points_csvs(self, logger=defaultLogger):
        self.string_args['ext']='csv'
        #Create bands file for each band/BR
        for [band_name, band_folder] in self.band_parameters:
            self.string_args['band']=band_name
            header1 = ['CJRS_LAKE', 'COUNT_CDOM', 'CDOM', band_name.upper()]
            header2 = ['CJRS_LAKE', band_name.upper()+'_COUNT', band_name.upper()+'_AREA', band_name.upper()+'_MIN',band_name.upper()+'_MAX',band_name.upper()+'_RANGE',band_name.upper()+'_MEAN', band_name.upper()+'_STD']
            listOut1 = [header1]
            listOut2 = [header2]
            #For each row in SEL_POINTS_FILE, get band value from split DB
            with open((SEL_POINTS_FOLDER + SEL_POINTS_FILE).format(**self.string_args), 'r') as selPointsFile:
                selPointsFile.readline()
                for selPointsRow in selPointsFile:
                    selPointsRow = selPointsRow.split(',')
                    rowOut1 = []
                    rowOut2 = []
                    LID = selPointsRow[3]
                    rowOut1.append(LID)
                    rowOut1.append(selPointsRow[5])
                    rowOut1.append(selPointsRow[6])
                    rowOut2.append(LID)
                    k = len(glob((SEL_SPLIT_FOLDER + 'FID_*.shp').format(**self.string_args))[0].split('\\')[-1]) - 8
                    FID = ('FID_{0:0>' + str(k) + '}').format(selPointsRow[2])
                    with open((SEL_TEMP_DBF_FOLDER + SEL_BANDS_FILE_CALC).format(FID=FID, **self.string_args)) as bandsCalcFile:
                        bandsCalcFile.readline()
                        bandsCalcRow = bandsCalcFile.readline().split(',')
                    if bandsCalcRow[0] is not "":
                        rowOut1.append(bandsCalcRow[6])
                        rowOut2 = rowOut2 + bandsCalcRow[1:8]
                        listOut1.append(rowOut1)
                        listOut2.append(rowOut2)

            write_list_to_csv(listOut1, (SEL_POINTS_FOLDER + SEL_BANDS_FILE).format(**self.string_args))
            write_list_to_csv(listOut2, (SEL_POINTS_FOLDER + SEL_ALL_STATS_FILE).format(**self.string_args))


        #Find band minimums
        for band in self.unique_bands:
            band_name = 'b{}'.format(band)

            self.string_args['band'] = band_name

            header = ['CJRS_LAKE', 'COUNT_CDOM', 'CDOM', 'B{}'.format(band), 'B{}_MIN'.format(band)]

            bandsFileFn = (SEL_POINTS_FOLDER + SEL_BANDS_FILE).format(**self.string_args)
            bandsFileList = load_csv_as_list(bandsFileFn)
            bandsMinList = [header]
            bandValues = []

            for bandsFileRow in bandsFileList[1:]:
                bandValues.append(float(bandsFileRow[3]))

            if len(bandValues) > 0:
                bandMin = np.min(bandValues)
            else:
                bandMin = 0

            for bandsFileRow in bandsFileList[1:]:
                bandsMinList.append(bandsFileRow + [bandMin])

            write_list_to_csv(bandsMinList, (SEL_POINTS_FOLDER + SEL_BANDS_MIN_FILE).format(**self.string_args))


        #Merge all bands
        self.string_args['band']='all'
        fileOut = (SEL_POINTS_FOLDER + SEL_MERGED_FILE).format(**self.string_args)
        filesToMerge = []

        for (band_name, band_folder) in self.band_parameters:
            self.string_args['band'] = band_name
            if len(band_name) < 4:
                filesToMerge.append((SEL_POINTS_FOLDER + SEL_BANDS_MIN_FILE).format(**self.string_args))
            else:
                filesToMerge.append((SEL_POINTS_FOLDER + SEL_BANDS_FILE).format(**self.string_args))

        args = ' '.join((fileOut, filesToMerge[0], filesToMerge[1]))
        os.system('Rscript --arch x64 --vanilla r_scripts\\merge_sel_tables.R {}'.format(args))

        for fileToMerge in filesToMerge[2:]:
            args = ' '.join((fileOut, fileOut, fileToMerge))
            os.system('Rscript --arch x64 --vanilla r_scripts\\merge_sel_tables.R {}'.format(args))

        logger.info('Merged selected points table for scene {scene}.'.format(**self.string_args))

        return None

    def get_sample_data(self, logger=defaultLogger):
        fusionTables = FusionTables()
        service = fusionTables.connect()
        VAR = self.string_args['var']
        sampleDataOut = [['NID', VAR, 'CHL' , 'COUNT_' + VAR]]
        sampleDataOut2 = [['NID', 'MEAN_' + VAR, 'MEDIAN_' + VAR, 'MIN_' + VAR, 'MAX_' + VAR, 'RANGE_' + VAR, 'COUNT_' + VAR, 'STD_' + VAR, 'MEAN_CHL']]
        sampleDataOut3 = ['NID, ' + VAR]
        sampleDataOut4 = [['NID', VAR, 'DATE']]
        self.string_args['ext'] = 'csv'

        sampleFnOut = (SAMPLE_DBF_FOLDER + SAMPLE_DATA_FILE).format(**self.string_args)
        sampleFnOut2 = (SAMPLE_DBF_FOLDER + SAMPLE_STATS_FILE).format(**self.string_args)
        sampleFnOut3 = (SAMPLE_DBF_FOLDER + SAMPLE_ALLDATA_FILE).format(**self.string_args)
        sampleFnOut4 = (SAMPLE_DBF_FOLDER + SAMPLE_DATA_DATES_FILE).format(**self.string_args)


        self.string_args['band'] = 'b{}divb{}'.format(*self.bands['bdivb'][0])
        bands = load_csv_as_list((BANDS_DBF_FOLDER + BANDS_FILE).format(**self.string_args))

        sampleCount=0
        lakeCount=0
        sampledLakeCount=0

        #Pull sample data for lakes in image
        sql = 'SELECT SiteCode, {var}, Date_freef, CHL FROM {fid}'.format(fid=ID_LAKE_SAMPLES, **self.string_args)
        response = service.query().sql(sql=sql).execute()
        sampleData = convert_query_response_to_list(response)

        #Find matching NIDS and calculate mean CDOM for each lake with samples
        for bandsRow in bands[1:]:
            bandNID = bandsRow[0]
            allCDOMs = []
            allCHLs = []
            lakeCount+=1
            for sampleRow in sampleData[1:]:
                sampleNID = sampleRow[0]
                CDOM = float(sampleRow[1])
                CHL = float(sampleRow[3])
                date = sampleRow[2]
                if bandNID == sampleNID:
                    if CDOM != 0 and not math.isnan(CDOM) and CDOM < 45:
                        allCDOMs.append(CDOM)
                        sampleDataOut4.append([bandNID, CDOM, date])
                        sampleCount+=1
                    if CHL != 0 and not math.isnan(CHL):
                        allCHLs.append(CHL)

            if len(allCDOMs) > 0:
                meanCDOM = np.mean(allCDOMs)
                minCDOM = np.min(allCDOMs)
                maxCDOM = np.max(allCDOMs)
                countCDOM = len(allCDOMs)
                medianCDOM = np.median(allCDOMs)
                rangeCDOM = np.ptp(allCDOMs)
                stdCDOM = np.std(allCDOMs)
                if len(allCHLs) > 0:
                    meanCHL = np.mean(allCHLs)
                else:
                    meanCHL = ''
                sampleDataOut.append([bandNID, meanCDOM, meanCHL, countCDOM])
                sampleDataOut2.append([bandNID, meanCDOM, medianCDOM, minCDOM, maxCDOM, rangeCDOM, countCDOM, stdCDOM, meanCHL])
                sampleDataOut3.append(', '.join([str(bandNID)] + [str(CDOM) for CDOM in allCDOMs]))
                sampledLakeCount+=1

        #Write CSV files
        with open(sampleFnOut3, 'w') as fileOut:
            for row in sampleDataOut3:
                fileOut.write(row + '\n')
        write_list_to_csv(sampleDataOut, sampleFnOut)
        write_list_to_csv(sampleDataOut2, sampleFnOut2)
        write_list_to_csv(sampleDataOut4, sampleFnOut4)
        logger.info('Sample data for scene {scene} written.'.format(**self.string_args))

        #Upload lake/sample count to fusion table
        fusionTable = FusionTables()
        service = fusionTable.connect()

        ID_COUNT = (ID_COUNT_CDOM if self.string_args['var'] == 'CDOM' else ID_COUNT_DOC)
        query = 'SELECT Scene_ID FROM {fid}'.format(fid=ID_COUNT)
        response = service.query().sql(sql=query).execute()
        sceneIDs = []
        response_list = convert_query_response_to_list(response)
        for row in response_list[1:]:
            sceneIDs.append(row[0])

        if not self.sceneId in sceneIDs:
            columns = ['Path', 'Row', 'Scene_ID', '{var}_Sample_Count'.format(**self.string_args), '{var}_Lake_Count'.format(**self.string_args),'{var}_Sampled_Lake_Count'.format(**self.string_args)]
            data = [self.sceneId[3:6], self.sceneId[6:9], self.sceneId, str(sampleCount), str(lakeCount),str(sampledLakeCount)]
            listOut = [columns, data]
            fusionTable.insert_list(ID_COUNT, listOut)

        return None

    def r_merge_poly_csvs(self, logger=defaultLogger):

        #Create a file for each band + CDOM or DOC
        self.string_args['ext'] = 'csv'
        band_names = [band_name for [band_name, band_folder] in self.band_parameters]
        for band in band_names:
            self.string_args['band'] = band
            args = [path.format(**self.string_args) for path in [(BANDS_DBF_FOLDER + MERGED_FILE), (SAMPLE_DBF_FOLDER + SAMPLE_DATA_FILE), (BANDS_DBF_FOLDER + BANDS_FILE)]]
            os.system('Rscript --arch x64 --vanilla r_scripts\\merge_tables.R {}'.format(' '.join(args)))

            #Merge CDOM stats and band stats
            filenames = [(BANDS_DBF_FOLDER + ALL_STATS_FILE), (BANDS_DBF_FOLDER + BANDS_FILE_ALL), (SAMPLE_DBF_FOLDER + SAMPLE_STATS_FILE)]
            paths = [filename.format(**self.string_args) for filename in filenames]
            args = ' '.join(paths)
            os.system('Rscript --arch x64 --vanilla r_scripts\\merge_tables.R {}'.format(args))

        #Create a file with all bands + CDOM or DOC
        if len(self.band_parameters) > 1:
            self.string_args['band'] = self.band_parameters[0][0]
            tableIn1 = (BANDS_DBF_FOLDER + MERGED_FILE).format(**self.string_args)
            self.string_args['band'] = self.band_parameters[1][0]
            tableIn2 = (BANDS_DBF_FOLDER + BANDS_FILE).format(**self.string_args)
            self.string_args['band'] = 'all'
            tableOut = (BANDS_DBF_FOLDER + MERGED_FILE).format(**self.string_args)

            os.system('Rscript --arch x64 --vanilla r_scripts\\merge_tables_all_bands.R {} {} {}'.format(tableOut, tableIn1, tableIn2))

            tableIn1 = tableOut

            for [band_name, band_folder] in self.band_parameters[2:]:
                self.string_args['band']=band_name
                tableIn2 = (BANDS_DBF_FOLDER + BANDS_FILE).format(**self.string_args)
                os.system('Rscript --arch x64 --vanilla r_scripts\\merge_tables_all_bands.R {} {} {}'.format(tableOut, tableIn1, tableIn2))

            os.system('Rscript --arch x64 --vanilla r_scripts\\switcheroo.R {}'.format(tableOut))


        logger.info('Merged CSV tables for scene {scene}'.format(**self.string_args))
        return None

    def find_band_minimums(self, logger=defaultLogger):
        headers = []
        data = []
        self.string_args['ext']='csv'
        #For each band, find minimum from BANDS_FILE_ALL
        for band in self.unique_bands:
            band = 'b{}'.format(band)
            headers.append('B{}_MIN'.format(band[1:]))
            self.string_args['band'] = band
            bandsAll = load_csv_as_list((BANDS_DBF_FOLDER + BANDS_FILE_ALL).format(**self.string_args))
            minimums = [float(row[4]) for row in bandsAll[1:]]
            data.append(np.min(minimums))

        #Add scene ID
        headers.append('SCENE_ID')
        data.append(self.sceneId)

        #Add b_mins and scene ids to MERGED_FILE(bands=all)
        self.string_args['band'] = 'all'
        mergedOriginal = load_csv_as_list((BANDS_DBF_FOLDER + MERGED_FILE).format(**self.string_args))

        newMerged = [(dataRow + data) for dataRow in mergedOriginal[1:]]
        newMerged.insert(0,(mergedOriginal[0] + headers))

        write_list_to_csv(newMerged, (BANDS_DBF_FOLDER + MERGED_MIN_FILE).format(**self.string_args))

        os.system('Rscript --arch x64 --vanilla r_scripts\\switcheroo.R {}'.format((BANDS_DBF_FOLDER + MERGED_MIN_FILE).format(**self.string_args)))

        return None

    def r_compute_regression(self, logger=defaultLogger):
        self.string_args['ext'] = 'csv'
        band_names = [band_name for [band_name, band_folder] in self.band_parameters]
        for band in band_names:
            #print('Doing regression for band {} of scene {}'.format(band, self.sceneId))
            self.string_args['band'] = band
            fns1 = [(BANDS_DBF_FOLDER + filename).format(**self.string_args) for filename in [MERGED_FILE, BANDS_FILE]]
            fns2 = [(R_OUTPUT_FOLDER + filename).format(**self.string_args) for filename in [R_MODEL_TXT_FILE, R_MODEL_CSV_FILE, R_PDF_FILE, R_PRED_CSV_FILE]]
            args = fns1 + fns2
            os.system(('Rscript --arch x64 --vanilla r_scripts\\regression.R {args} > ' + R_OUTPUT_FOLDER + R_STDOUT_FILE).format(args=' '.join(args), **self.string_args))
        logger.info('Computed regression for scene {}'.format(self.sceneId))
        return None

    def r_leaps_regression(self, logger=defaultLogger):
        self.string_args['ext']='csv'
        self.string_args['band']='all'
        csvIn = (BANDS_DBF_FOLDER + MERGED_FILE).format(**self.string_args)
        pdfOut = (R_OUTPUT_FOLDER + R_LEAPS_PDF).format(**self.string_args)
        args = ' '.join([csvIn, pdfOut])
        stdOut = R_LEAPS_STDOUT.format(**self.string_args)
        os.system('Rscript --arch x64 --vanilla r_scripts\\leaps.R {0} > {1}'.format(args, stdOut))
        return None

    def r_regression_prep(self, logger=defaultLogger):
        self.convert_dbfs_to_csvs(logger=logger)
        if self.string_args['zstat_mode'] == 'poly':
            self.get_sample_data(logger=logger)
            self.r_merge_poly_csvs(logger=logger)
            self.find_band_minimums(logger=logger)
        elif self.string_args['zstat_mode'] == 'points':
            self.merge_points_csvs(logger=logger)
        elif self.string_args['zstat_mode'] == 'sel':
            self.merge_sel_points_csvs(logger=logger)

    def update_running_estimates(self, logger=defaultLogger):
        self.string_args['band'] = 'b3divb4'
        self.string_args['ext'] = 'csv'

        #For now we only upload lakes that have been sampled
        predictionsCSV = (R_OUTPUT_FOLDER + R_MODEL_CSV_FILE).format(**self.string_args)
        #Columns: NID, Band Ratio, Estimate, Delta
        newEstimates = load_csv_as_list(predictionsCSV)

        fusion = FusionTables()
        service = fusion.connect()

        #Check if scene is already in tab;e
        query = 'SELECT Scene_ID FROM {tableId} WHERE Scene_ID = \'{scene}\''.format(tableId=ID_ESTIMATES, **self.string_args)
        response = service.query().sql(sql=query).execute()

        if not 'rows' in response.keys():
        #if len(response['rows']) > 0:
            query = 'SELECT NID, Scene_ID, Estimates_Count, Zstat_Mode, Running_Estimate, Running_Delta  FROM {tableId} WHERE Zstat_Mode = \'{zstat_mode}\' ORDER BY Estimates_Count DESC'.format(tableId=ID_ESTIMATES, **self.string_args)
            response = service.query().sql(sql=query).execute()
            if 'rows' in response.keys():
                oldEstimates = convert_query_response_to_list(response)
            else:
                oldEstimates = None

            columns = ['NID', 'Scene_ID', 'Estimates_Count', 'Zstat_Mode', 'Estimate', 'Delta', 'Running_Estimate', 'Running_Delta']
            listOut = [columns]

            for newEstimate in newEstimates[1:]:

                newRunning = newEstimate[3]
                newRunningDelta = newEstimate[4]
                estimateCount = 1
                NID = newEstimate[0]

                if oldEstimates is not None:
                    oldEstimate = None
                    for row in oldEstimates[:1]:
                        if row[0] == newEstimate[0]:
                            oldEstimate = row
                            break
                    if oldEstimate is not None:
                        estimateCount = oldEstimate[2] + 1
                        x_a = float(oldEstimate[4])
                        delta_a = float(oldEstimate[5])
                        x_b = float(newEstimate[3])
                        delta_b = float(newEstimate[4])
                        delta_ab = math.sqrt(1.0 / ((1.0 / math.pow(delta_a, 2)) + (1.0 / math.pow(delta_b, 2))))
                        x_ab = math.pow(delta_ab, 2) * (x_a / math.pow(delta_a, 2)+ x_b / math.pow(delta_b, 2))

                        newRunning = x_ab
                        newRunningDelta = delta_ab

                listOut.append([NID, self.sceneId, estimateCount, self.string_args['zstat_mode'], newEstimate[2], newEstimate[3], newRunning, newRunningDelta])

            tempCSV = (TEMP_DBF_FOLDER + 'temp.csv').format(**self.string_args)
            write_list_to_csv(listOut[1:], tempCSV)
            fusion.insert_csv(ID_ESTIMATES, tempCSV)

        self.next = 'clean_up'
        return None

    def clean_up(self, logger=defaultLogger):
        #Delete rasters, temp grids
        if os.path.exists(TEMP_GRID_FOLDER.format(**self.string_args)):
            shutil.rmtree(TEMP_GRID_FOLDER.format(**self.string_args))
        #Delete dbf files
        for [band_name, band_folder] in self.band_parameters:
            self.string_args['band'] = band_name
            for folder in [SAMPLE_DBF_FOLDER, BANDS_DBF_FOLDER]:
                folder = folder.format(**self.string_args)
                if os.path.exists(folder):
                    for filename in glob(folder + '*.dbf'):
                        os.remove(filename)

        self.next = None
        logging.shutdown()
        return None

    def set_us_up_the_bomb(self, logger=defaultLogger):
        self.clean_up(logger=logger)
        return None

    def run_next(self):
        if hasattr(self, self.next) and self.next is not None:
            code = 'self.{}()'.format(self.next)
            logger.info('Running {} for scene {}'.format(self.next, self.sceneId))
            exec(code)
        else:
            logger.warning('Method {} does not exist.'.format(self.next))


def handle_alem_error(e):
    #TODO
    defaultLogger.exception('{}: {}', e.operation, e.msg)
    if e.parentE is not None:
        defaultLogger.exception('Caused by: ', e.parentE)
    sys.exit(1)
    return None


class AlemError(Exception):

    def __init__(self, operation, msg, parentE=None):
        self.operation = operation
        self.msg = msg
        self.parentE = parentE

    def __str__(self):
        return repr(self.msg)
