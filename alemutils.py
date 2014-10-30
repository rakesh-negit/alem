# -*- coding: utf-8 -*-
import alemobject
from settings import *
import pickle
#import logging
import os
from glob import glob
import shutil
import xml.etree.ElementTree as ET
from dbfpy import dbf
import csv
from utilfunctions import *
import numpy as np
import math

#logger = logging.getLogger(__name__)

def convert_5_to_dn():
    string_args = {'ext':'csv', 'band':'all', 'scene':'all', 'zstat_mode':'pts'}
    fn = (SEL_POINTS_FOLDER + SEL_MERGED_FILE).format(**string_args)

    dataIn = load_csv_as_list(fn)

    header = dataIn[0]
    lines = dataIn[1:]

    fnOut = (SEL_POINTS_FOLDER + '5DN_ALL_ALL_PTS_ORIGINAL_DN.csv')

    newHeader = ('CJRS_LAKE', 'CDOM', 'COUNT_CDOM', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'SCENE_ID')
    eyes = [header.index(columnTitle) for columnTitle in newHeader]

    linesOut = []
    for line in lines:
        lineOut = [line[i] for i in eyes]
        alemObject = alemobject.ALEMObject(lineOut[-1])
        alemObject.string_args = {'scene':alemObject.sceneId}
        alemObject.parse_metadata()
        for i in range(1,9):
            addBand = float(alemObject.metadata['REFLECTANCE_ADD_BAND_{}'.format(i)])
            multBand = float(alemObject.metadata['REFLECTANCE_MULT_BAND_{}'.format(i)])
            bandValue = float(lineOut[i+2])
            newBandValue = (bandValue - addBand) / multBand
            lineOut[i+2] = newBandValue
        linesOut.append(lineOut)

    write_list_to_csv([newHeader] + linesOut, fnOut)


def fix_selected_points_dupes():
    for scene in open((SCENES_FOLDER + 'selected_images_all.txt')):
        scene = scene.strip()
        alemObject = update_instance(scene)
        alemObject.string_args['ext'] = 'csv'
        fn = (SEL_POINTS_FOLDER + SEL_POINTS_FILE).format(**alemObject.string_args)

        tableIn = load_csv_as_list(fn)
        print(tableIn[0])
        print(tableIn[1])

        tableOut = [tableIn[0]]

        cjrs_prev = ''

        tableRows = tableIn[1:]
        tableRows.sort(key=lambda cjrs: cjrs[3])

        for row in tableRows:
            if row[3] != cjrs_prev:
                tableOut.append(row)
            cjrs_prev = row[3]

        write_list_to_csv(tableOut, fn)


def find_new_images_in_metadata():
    metadataFn = SCENES_FOLDER + MD_FILE
    watchFn = SCENES_FOLDER + WATCH_FILE
    outputFn = SCENES_FOLDER + NEW_IMGS_FILE

    tree = ET.parse(metadataFn)
    root = tree.getroot()

    watch=[]
    scenes = list_scenes()

    outputFile = open(outputFn, 'w')

    for row in open(watchFn, 'r'):
        watch.append(row[0:4])

    for child in root:
        if child.tag[-8:] == 'metaData':
            if (child[6].text + child[7].text) in watch and not child[2].text in scenes:
                sceneShort = child[2].text[0:-4]
                scenesShort = [scene[0:-4] for scene in scenes]
                if not sceneShort in scenesShort and not sceneShort[0:2] == 'LT':
                    outputFile.write(child[2].text + '\n')

    outputFile.close()


def init_image(sceneId):
    if not os.path.exists(IMAGE_FOLDER.format(scene=sceneId)):
        os.makedirs(IMAGE_FOLDER.format(scene=sceneId))
    exts = ['_B{}.TIF'.format(i) for i in range(1,12)] + ['.jpg', '_MTL.txt', '_BQA.TIF']
    filenames = [BASE_FOLDER.format(scene=sceneId) + sceneId + ext for ext in exts]
    for filename in filenames:
        if os.path.exists(filename):
            shutil.move(filename, IMAGE_FOLDER.format(scene=sceneId))

    pFilename = BASE_FOLDER.format(scene=sceneId) + 'alemObject.pickle'
    if not os.path.exists(pFilename):
        alemObject = alemobject.ALEMObject(sceneId)
        pickle.dump(alemObject, open(pFilename, 'wb'), pickle.HIGHEST_PROTOCOL)


def init_images(imageListFn):
    imageListFn = (SCENES_FOLDER + imageListFn)
    for sceneId in open(imageListFn, 'r'):
        sceneId = sceneId.strip()
        init_image(sceneId)


def recreate_object(sceneId):
    pFilename = BASE_FOLDER.format(scene=sceneId) + 'alemObject.pickle'
    alemObject = alemobject.ALEMObject(sceneId)
    pickle.dump(alemObject, open(pFilename, 'wb'), pickle.HIGHEST_PROTOCOL)
    return alemObject


def update_instance(alemObject):
    reload(alemobject)
    try:
        newObj = alemobject.ALEMObject(alemObject.sceneId)
    except AttributeError:
        alemObject = load_scene(alemObject)
        newObj = alemobject.ALEMObject(alemObject.sceneId)

    newObj.next = alemObject.next
    if hasattr(alemObject, 'metadata'):
        newObj.metadata = alemObject.metadata
    if hasattr(alemObject, 'string_args'):
        newObj.string_args = alemObject.string_args
    if hasattr(alemObject, 'bands'):
        newObj.bands = alemObject.bands
    if hasattr(alemObject, 'band_parameters'):
        newObj.band_parameters = alemObject.band_parameters
    if hasattr(alemObject, 'unique_bands'):
        newObj.unique_bands = alemObject.unique_bands
    return newObj


def list_scenes():
    scenes = glob(SCENES_FOLDER + 'LC*')
    scenes = [scene[-21:] for scene in scenes]
    return scenes


def load_scene(scene):
    pfn = BASE_FOLDER.format(scene=scene) + 'alemObject.pickle'
    with open(pfn, 'rb') as pf:
        alemObject = pickle.load(pf)
    return alemObject


def pickle_object(alemObject):
    pfn = BASE_FOLDER.format(scene=alemObject.sceneId) + 'alemObject.pickle'
    pickle.dump(alemObject, open(pfn, 'wb'), pickle.HIGHEST_PROTOCOL)


def combine_sel_points_csvs(imagesListFn='images.txt'):

    string_args  = {}
    string_args['scene']='all'
    string_args['band']='all'
    string_args['ext']='csv'
    csvOutFn = (SEL_POINTS_FOLDER + SEL_MERGED_FILE).format(**string_args)
    imagesListFn = (SEL_POINTS_FOLDER + imagesListFn).format(**string_args)

    with open(imagesListFn, 'r') as imagesList:

        h = 0
        data = []

        for sceneId in imagesList:
            string_args['scene'] = sceneId.strip()
            bandsFn = (SEL_POINTS_FOLDER + SEL_MERGED_FILE).format(**string_args)
            with open(bandsFn, 'r') as bandsFile:
                if not h:
                    header = bandsFile.readline().strip()
                    header = header.split(',') + ['SCENE_ID']
                else:
                    bandsFile.readline()
                for row in bandsFile:
                    row = row.strip()
                    rowOut = row.strip().split(',') + [ sceneId.strip() ]
                    data.append(rowOut)

    listOut = [ header ] + data

    write_list_to_csv(listOut, csvOutFn)

    logger.info('Combined selected points merged files.')
    return None


def r_tree_prep(mode='poly', logger=logger):
    string_args  = {}
    string_args['scene']='all'
    string_args['band']='all'
    string_args['ext']='csv'
    string_args['zstat_mode']='poly'
    string_args['bqa_or_rad']='bqa'
    string_args['var']='CDOM'

    csvInList = glob((R_TREE_FOLDER + '5_*').format(**string_args))
    if len(csvInList) != 1:
        logger.error('Check that there is exactly one 5_ file in tree folder.')
        return None
    csvIn = csvInList[0]
    #csvIn = (COMBINED_FOLDER + MERGED_MIN_FILE).format(**string_args)
    csvOut = (R_TREE_FOLDER + TREE_IN_FILE).format(**string_args)

    os.system('Rscript --arch x64 --vanilla r_scripts\\tree_prep.R {} {}'.format(csvIn, csvOut))

    #allBandsFn = (SEL_POINTS_FOLDER + SEL_MERGED_FILE).format(**string_args)
    treeFn = csvOut
    treeAvgFn = (R_TREE_FOLDER + TREE_IN_AVG_FILE).format(**string_args)

    allBandsList = load_csv_as_list(treeFn)

    treeList = [allBandsList[0]]
    treeAvgList = [allBandsList[0]]

    treeRows = sorted(allBandsList[1:], key=lambda tup: tup[0])

    NID = treeRows[0][0]
    row = [float(value) for value in treeRows[0][1:]]
    rows = [row]
    for treeRow in treeRows[1:]:
        previousNID = NID
        NID = treeRow[0]
        if previousNID == NID:
            row = [float(value) for value in treeRow[1:]]
            rows.append(row)
        else:
            rowStack = np.vstack(rows)
            avgRow = np.median(rowStack, axis=0)
            avgRow = avgRow.tolist()
            #if avgRow[0] < 1.5:
                #avgRow[0] = 'LOW'
            #else:
                #avgRow[0] = 'HIGH'
            treeAvgList.append([previousNID] + avgRow)
            row = [float(value) for value in treeRow[1:]]
            rows = [row]



    write_list_to_csv(treeAvgList, treeAvgFn)

    for allBandsRow in allBandsList[1:]:
        treeRow = allBandsRow
        #if float(treeRow[1]) < 1.5:
            #treeRow[1] = 'LOW'
        #else:
            #treeRow[1] = 'HIGH'
        treeList.append(treeRow)

    write_list_to_csv(treeList, treeFn)

    string_args['bands']='all'

    #Create table with number of scenes and number of CDOM samples by NID
    fnIn = csvIn
    fnOut = (R_TREE_FOLDER + SAMPLE_COUNT_FILE).format(**string_args)

    tableIn = load_csv_as_list(fnIn)
    headerOut = [['NID', 'SCENE_COUNT', 'CDOM_COUNT']]

    NIDs = [row[0] for row in tableIn[1:]]
    NIDs = set(NIDs)

    rowsOut = [[NID, 0, 0] for NID in NIDs]

    for rowOut in rowsOut:
        for rowIn in tableIn[1:]:
            if rowOut[0] == rowIn[0]:
                rowOut[1] = rowOut[1] + 1
                rowOut[2] = rowIn[1]

    tableOut = headerOut + rowsOut
    write_list_to_csv(tableOut, fnOut)

    #Merge 6_ and 14_ files
    tableOut = (R_TREE_FOLDER + AVG_COUNT_FILE).format(**string_args)
    tableIn1 = (R_TREE_FOLDER + SAMPLE_COUNT_FILE).format(**string_args)
    tableIn2 = (R_TREE_FOLDER + TREE_IN_AVG_FILE).format(**string_args)

    args = ' '.join((tableOut, tableIn1, tableIn2))

    os.system('Rscript --arch x64 --vanilla r_scripts\\merge_tables_raw.R {}'.format(args))

    return None

def filter_tree_lakes(logger=logger):
    string_args = {}
    string_args['scene']='all'
    string_args['band']='all'
    string_args['ext']='csv'
    string_args['zstat_mode']='poly'
    string_args['bqa_or_rad']='bqa'
    string_args['var']='CDOM'

    treeFn = (R_TREE_FOLDER + TREE_IN_AVG_FILE).format(**string_args)
    jbLakesFn = (R_TREE_FOLDER + FILTER_LAKES_FILE).format(**string_args)
    jbTreeFn = (R_TREE_FOLDER + R_TREE_FILTER_FILE).format(**string_args)
    remTreeFn = (R_TREE_FOLDER + R_TREE_NONFILTER_FILE).format(**string_args)

    jbLakesList = load_csv_as_list(jbLakesFn)
    treeList = load_csv_as_list(treeFn)
    jbTreeList = [treeList[0]]
    remTreeList = [treeList[0]]

    for treeRow in treeList[1:]:
        jb=0
        for jbLakesRow in jbLakesList:
            if jbLakesRow[0] == treeRow[0]:
                jb=1
                break
        if jb:
            jbTreeList.append(treeRow)
        else:
            remTreeList.append(treeRow)

    write_list_to_csv(jbTreeList, jbTreeFn)
    write_list_to_csv(remTreeList, remTreeFn)
    return None

def r_tree_testing(logger=logger):
    string_args  = {}
    string_args['scene']='all'
    string_args['band']='all'
    string_args['ext']='csv'
    string_args['zstat_mode']='poly'
    string_args['bqa_or_rad']='bqa'
    string_args['var']='CDOM'

    #treeFn = (R_TREE_FOLDER + TREE_IN_AVG_FILE).format(**string_args)
    treeFn = (R_TREE_FOLDER + R_TREE_FILTER_FILE).format(**string_args)
    treePdf = (R_TREE_FOLDER + R_TREE_BUILD_PDF).format(**string_args)
    predCsv = (R_TREE_FOLDER + R_TREE_TEST_CSV).format(**string_args)
    ktFn = (R_TREE_FOLDER + R_KT_TXT_FILE).format(**string_args)

    args = ' '.join((treeFn, treePdf, predCsv, ktFn))
    outputFolder = (R_TREE_FOLDER + '1_r_tree_testing_output.txt').format(**string_args)

    os.system('Rscript --arch x64 --vanilla r_scripts\\tree_testing.R {} > {}'.format(args, outputFolder))

    return None

def r_tree_prediction(logger=logger):
    string_args = {}
    string_args['scene']='all'
    string_args['band']='all'
    string_args['ext']='csv'
    string_args['zstat_mode']='poly'
    string_args['bqa_or_rad']='bqa'
    string_args['var']='CDOM'

    treeBuildFn = (R_TREE_FOLDER + R_TREE_FILTER_FILE).format(**string_args)
    treePredFn = (R_TREE_FOLDER + R_TREE_NONFILTER_FILE).format(**string_args)
    treePdf = (R_TREE_FOLDER + R_TREE_BUILD_PDF).format(**string_args)
    predCsv = (R_TREE_FOLDER + R_TREE_PRED_CSV).format(**string_args)
    ktFn = (R_TREE_FOLDER + R_KT_TXT_FILE).format(**string_args)

    args = ' '.join((treeBuildFn, treePredFn, treePdf, predCsv, ktFn))

    os.system('Rscript --arch x64 --vanilla r_scripts\\tree_prediction.R {}'.format(args))

def r_tree(logger=logger):
    r_tree_prep()
    filter_tree_lakes()
    r_tree_testing()
    r_tree_prediction()
    return None

def combined_regression(imagesListFn='images.txt', zstat_mode='poly'):
    imagesListFn = COMBINED_FOLDER + imagesListFn
    string_args = {'bqa_or_rad':'bqa', 'zstat_mode':zstat_mode,'ext':'csv'}

    for var in ['CDOM']:
        string_args['var']=var
        #string_args['band']='all'
        #string_args['scene']='all'
        #mergedCSV = (COMBINED_FOLDER + MERGED_FILE).format(**string_args)
        #with open(mergedCSV, 'w') as fOut:
            #k = False
            #for sceneId in open(imagesListFn, 'r'):
                #sceneId = sceneId.strip()
                #string_args['scene'] = sceneId
                #oldFn = (BANDS_DBF_FOLDER + MERGED_FILE).format(**string_args)
                #newFn = (COMBINED_CSV_FOLDER + MERGED_FILE).format(**string_args)
                #shutil.copy(oldFn, newFn)
                #with open(newFn, 'r') as fIn:
                    #if k:
                        #fIn.readline()
                    #k = True
                    #for line in fIn:
                        ##if k:
                            ##line = line.strip() + ', {}\n'.format(sceneId)
                        ##else:
                            ##line = line.strip() + ', SCENEID\n'
                            ##k = True
                        #fOut.write(line.strip() + '\n')

        bands = ['b{}divb{}'.format(x,y) for [x,y] in ALLBXB]
        #bands = ['b3', 'b4', 'b3divb4']

        #Concatenate csv files for each band
        for band in bands:
            string_args['band']=band
            string_args['scene']='all'

            statsCSV = (COMBINED_FOLDER + ALL_STATS_FILE).format(**string_args)
            mergedCSV = (COMBINED_FOLDER + MERGED_FILE).format(**string_args)
            with open(mergedCSV, 'w') as fOut1, open(statsCSV, 'w') as fOut2:
                fOut1.write('NID, {}, CHL, BAND, SCENEID\n'.format(var))
                fOut2.write('NID, COUNT, AREA, MIN, MAX, RANGE, MEAN, STD, SUM, MEAN_{0}, MEDIAN_{0}, MIN_{0}, MAX_{0}, RANGE_{0}, COUNT_{0}, STD_{0},CHL, SCENEID\n'.format(var))
                for sceneId in open(imagesListFn, 'r'):
                    sceneId = sceneId.strip()
                    string_args['scene'] = sceneId

                    #Copy csvs over
                    oldFn = (BANDS_DBF_FOLDER + MERGED_FILE).format(**string_args)
                    newFn1 = (COMBINED_CSV_FOLDER + MERGED_FILE).format(**string_args)
                    shutil.copy(oldFn, newFn1)

                    oldFn = (BANDS_DBF_FOLDER + ALL_STATS_FILE).format(**string_args)
                    newFn2 = (COMBINED_CSV_FOLDER + ALL_STATS_FILE).format(**string_args)
                    shutil.copy(oldFn, newFn2)

                    #Concatenate files
                    for [newFn, fOut] in [[newFn1, fOut1], [newFn2, fOut2]]:
                        with open(newFn, 'r') as fIn:
                            fIn.readline()
                            for line in fIn:
                                line = line.strip() + ', {}\n'.format(sceneId)
                                fOut.write(line)

            #Compute regression
            string_args['scene']='all'
            fns = [R_MODEL_TXT_FILE, R_MODEL_CSV_FILE, R_PDF_FILE, R_PRED_CSV_FILE]
            args = [mergedCSV, mergedCSV] + [(COMBINED_FOLDER + fn).format(**string_args) for fn in fns]
            stdout = (COMBINED_FOLDER + R_STDOUT_FILE).format(**string_args)

            os.system('Rscript --arch x64 --vanilla r_scripts\\regression.R {args} > {stdout}'.format(args=' '.join(args),stdout=stdout))

        #Concatenate merged file for all bands with min band values for DOS
        string_args['band']='all'
        string_args['scene']='all'

        combinedMergedMinFile = (COMBINED_FOLDER + MERGED_MIN_FILE).format(**string_args)

        header=''

        with open(combinedMergedMinFile, 'w') as fOut:

            for sceneId in open(imagesListFn, 'r'):
                string_args['scene'] = sceneId.strip()

                oldFn = (BANDS_DBF_FOLDER + MERGED_MIN_FILE).format(**string_args)
                newFn = (COMBINED_CSV_FOLDER + MERGED_MIN_FILE).format(**string_args)

                shutil.copy(oldFn, newFn)

                with open(newFn, 'r') as fIn:
                    if header == '':
                        header = fIn.readline().strip()
                        fOut.write(header + '\n')
                    else:
                        fIn.readline()
                    for line in fIn:
                        line = line.strip() + '\n'
                        fOut.write(line)

def selected_regression(csvFn):
    csvPath = SELREG_FOLDER + csvFn
    prefix = csvFn[0:-4]

    txtOutput = SELREG_FOLDER + prefix + '_r_model.txt'
    pdfOutput = SELREG_FOLDER + prefix + '_r_plot_output.pdf'
    csvOutput = SELREG_FOLDER + prefix + '_r_output.csv'
    stdOutput = SELREG_FOLDER + prefix + '_r_stdout.txt'

    args = ' '.join([csvPath, txtOutput, csvOutput, pdfOutput])

    os.system('Rscript --arch x64 --vanilla r_scripts\\regression_no_pred.R {0} > {1}'.format(args, stdOutput))

def sel_combine_estimates():
    fnList = SELREG_FOLDER + "files_to_combine.txt"

    rowsIn = []

    for fn in open(fnList, 'r'):
        rowsIn = rowsIn + load_csv_as_list(SELREG_FOLDER + fn.strip())[1:]

    estimates = {}

    for row in rowsIn:
        NID = row[0]
        B = float(row[1])
        meanCDOM = row[2]
        x_1 = float(row[3])
        del_1 = float(row[4])

        if NID not in estimates:
            estimates[NID] = [B, B, meanCDOM, x_1, del_1, 1]
        else:
            estimates[NID][0] = np.min((B, estimates[NID][0]))
            estimates[NID][1] = np.max((B, estimates[NID][1]))
            x_2 = estimates[NID][3]
            del_2 = estimates[NID][4]
            del_12 = math.sqrt(1.0 / ((1.0 / math.pow(del_1, 2)) + (1.0 / math.pow(del_2, 2))))
            x_12 = math.pow(del_12, 2) * (x_1 / math.pow(del_1, 2)+ x_2 / math.pow(del_2, 2))
            estimates[NID][3] = x_12
            estimates[NID][4] = del_12
            estimates[NID][5]+=1

    listOut = [['NID', 'B_MIN', 'B_MAX', 'MEAN_CDOM', 'PREDICTED_CDOM', 'PREDICTED_CDOM_INTERVAL', 'COUNT']]

    for NID in estimates:
        row = [NID] + estimates[NID]
        listOut.append(row)

    write_list_to_csv(listOut, (SELREG_FOLDER + '1_combined_estimates.csv'))


def r_leaps_combined():
    string_args = {'ext':'csv', 'band':'all','scene':'all','bqa_or_rad':'bqa','zstat_mode':'poly','var':'CDOM'}
    csvIn = (COMBINED_FOLDER + MERGED_FILE).format(**string_args)
    pdfOut = (COMBINED_FOLDER + R_LEAPS_PDF).format(**string_args)
    args = ' '.join([csvIn, pdfOut])
    stdOut = (COMBINED_FOLDER + 'leaps_stdout.txt').format(**string_args)
    os.system('Rscript --arch x64 --vanilla r_scripts\\leaps.R {0} > {1}'.format(args, stdOut))
    return None


def convert_dbf_to_csv(folder):
    for dbfFilename in (glob(folder + '*.dbf')):
        inDBF = dbf.Dbf(dbfFilename)
        csvFilename = dbfFilename.replace('.dbf', '.csv')
        outCSV = open(csvFilename, 'wb')
        csvWriter = csv.writer(outCSV)

        names = []
        for field in inDBF.header.fields:
            names.append(field.name)
        csvWriter.writerow(names)

        for rec in inDBF:
            csvWriter.writerow(rec.fieldData)

        inDBF.close()
        outCSV.close()
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


def check_state(imgListFn):
    for mode in ['poly', 'point']:
        csvOutFn = (SCENES_FOLDER + 'check_{}.csv'.format(mode))
        with open(csvOutFn, 'w') as csvOut:
            csvOut.write('SCENE_ID, CFG, DIRS, TOA, BQA, BDIVB, BXB, ZSTAT, R_PREP, R\n')
            for sceneId in open(SCENES_FOLDER + imgListFn, 'r'):
                sceneId = sceneId.strip()
                rowOut = [sceneId]
                obj = load_scene(sceneId)

                if not hasattr(obj, 'string_args'):
                    rowOut+=['n','n','n','n','n','n','n','n',]
                else:
                    rowOut.append('y')

                    _mode = obj.string_args['zstat_mode']
                    obj.string_args['zstat_mode'] = mode

                    #Check that folders exists
                    val = 'y'
                    if not os.path.exists(IMAGE_FOLDER.format(**obj.string_args)) or not os.path.exists(R_LEAPS_FOLDER.format(**obj.string_args)):
                        val = 'n'
                    rowOut.append(val)

                    vals=['y', 'y']

                    #Check TOA and BQA rasters
                    if hasattr(obj, 'unique_bands'):
                        for band in obj.unique_bands:
                            if not os.path.exists(TEMP_GRID_FOLDER.format(**obj.string_args) + 'toa_grids\\toa_rad_b{}'.format(band)):
                                vals[0]='n'
                            if not os.path.exists(TEMP_GRID_FOLDER.format(**obj.string_args) + 'bqa_grids\\toa_bqa_b{}'.format(band)):
                                vals[1]='n'
                    else:
                        vals = ['n', 'n']

                    rowOut+=vals

                    #Check band ratios
                    val = 'y'
                    if hasattr(obj, 'bands') and 'bdivb' in obj.bands.keys():
                        for [x,y] in obj.bands['bdivb']:
                            if not os.path.exists(TEMP_GRID_FOLDER.format(**obj.string_args) + 'br_grids\\b{}divb{}'.format(x,y)):
                                val = 'n'
                    else:
                        val='n'
                    rowOut.append(val)

                    #Check band products
                    val = 'y'
                    if hasattr(obj, 'bands') and 'bxb' in obj.bands.keys():
                        for [x,y] in obj.bands['bxb']:
                            if not os.path.exists(TEMP_GRID_FOLDER.format(**obj.string_args) + 'br_grids\\b{}x{}'.format(x,y)):
                                val = 'n'
                    else:
                        val='n'
                    rowOut.append(val)

                    #Check zstat csvs
                    val = 'y'
                    if hasattr(obj,'band_parameters'):
                        for [band_name, band_folder] in obj.band_parameters:
                            obj.string_args['band'] = band_name
                            FILE_TO_CHECK = (BANDS_FILE_ALL if mode == 'poly' else SAMPLE_PTS_FILE)
                            obj.string_args['ext'] = 'dbf'
                            fn1 = (BANDS_DBF_FOLDER + FILE_TO_CHECK).format(**obj.string_args)
                            obj.string_args['ext'] = 'csv'
                            fn2 = (BANDS_DBF_FOLDER + FILE_TO_CHECK).format(**obj.string_args)
                            if not os.path.exists(fn1) and not os.path.exists(fn2):
                                val = 'n'
                    else:
                        val = 'n'
                    rowOut.append(val)

                    #Check R prep
                    val = 'y'
                    if hasattr(obj, 'band_parameters'):
                        for [band_name, band_folder] in  obj.band_parameters:
                            obj.string_args['band'] = band_name
                            FILE_TO_CHECK = ALL_STATS_FILE
                            obj.string_args['ext'] = 'dbf'
                            fn1 = (BANDS_DBF_FOLDER + FILE_TO_CHECK).format(**obj.string_args)
                            obj.string_args['ext'] = 'csv'
                            fn2 = (BANDS_DBF_FOLDER + FILE_TO_CHECK).format(**obj.string_args)
                            if not os.path.exists(fn1) and not os.path.exists(fn2):
                                val = 'n'

                    obj.string_args['band']='all'
                    fn = (BANDS_DBF_FOLDER + MERGED_FILE).format(**obj.string_args)
                    if not os.path.exists(fn):
                        val = 'n'
                    rowOut.append(val)

                    #Check R output
                    val = 'y'
                    if hasattr(obj, 'band_parameters'):
                        for [band_name, band_folder] in obj.band_parameters:
                            obj.string_args['band'] = band_name
                            obj.string_args['ext'] = 'csv'
                            if not os.path.exists((R_OUTPUT_FOLDER + R_PDF_FILE).format(**obj.string_args)):
                                val = 'n'
                    else:
                        val = 'n'
                    rowOut.append(val)
                    obj.string_args['zstat_mode'] = _mode

                csvOut.write(', '.join(rowOut) + '\n')

