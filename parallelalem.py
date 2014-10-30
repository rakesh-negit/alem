# Standard
import sys, os, shutil, logging
from multiprocessing import Pool
from glob import glob

# ALEM
import alemutils
from settings import *

logging.basicConfig(format='%(asctime)s %(name)s[%(levelname)s]:%(message)s', level=logging.INFO)

def cat_logs():
    lines = []
    for fn in glob(PARALLEL_LOG_FOLDER + 'LC*'):
        with open(fn, 'r') as f:
            lines = lines + list(f)

    lines.sort()
    with open(PARALLEL_CATLOG, 'w') as fOut:
        for line in lines:
            if line.find('[INFO]') is -1:
                fOut.write(line)

def f(scene, method):
    alemutils.init_image(scene)
    alemObject = alemutils.load_scene(scene)
    alemObject = alemutils.update_instance(alemObject)
    logger=logging.getLogger(alemObject.sceneId)
    fh = logging.FileHandler(PARALLEL_LOG.format(scene=alemObject.sceneId))
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(name)s[%(levelname)s]:%(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.propagate = True
    if os.path.exists(PROCESS_FILE.format(scene=alemObject.sceneId)):
        with open(PROCESS_FILE.format(scene=alemObject.sceneId)) as f:
            fnInProcess = f.readline()
        if os.path.exists(fnInProcess):
            try:
                shutil.rmtree(fnInProcess)
            except WindowsError:
                os.remove(fnInProcess)
        os.remove(PROCESS_FILE.format(scene=alemObject.sceneId))

    try:
        function = getattr(alemObject, method)
        function(logger=logger)
    except:
        logger.error('Error in excecuting {} for scene {}'.format(method, alemObject.sceneId))

    alemutils.pickle_object(alemObject)
    return None

if __name__ == '__main__':
    image_list = SCENES_FOLDER + sys.argv[1]
    method = sys.argv[2]
    pool = Pool(processes=8)

    for scene in open(image_list, 'r'):
        scene=scene.strip()
        args = (scene, method)
        pool.apply_async(f, args)

    pool.close()
    pool.join()
    logging.shutdown()
    cat_logs()

