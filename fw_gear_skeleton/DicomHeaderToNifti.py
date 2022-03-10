import glob
import json
import logging
import os
import pydicom
import shutil
import sys
import zipfile

from pathlib import Path

import pydicom.datadict

logging.basicConfig(level='INFO')
log = logging.getLogger(__name__)

WORKING_DIRECTORY = Path('/tmp/dicom')

def prep_dicom(dicom_path, work_dir):
    dicom_path = Path(dicom_path)
    work_dir = Path(work_dir)

    log.info(f'prepping dicom {dicom_path}')

    if not dicom_path.exists():
        log.error(f'provided dicom path {dicom_path} does not exist')
        sys.exit(1)

    if not work_dir.exists():
        log.debug(f'creating working directory {work_dir}')
        work_dir.mkdir(parents=True, exist_ok=True)

    log.debug(f'working directory is {work_dir}')

    if dicom_path.suffix in ['.zip', '.gzip']:
        unzip_dicom_to_dir(dicom_zip=dicom_path, dir=work_dir)

    else:
        copy_dicoms_to_dir(dicom_path=dicom_path, dir=work_dir)




def copy_dicoms_to_dir(dicom_path, dir):
    log.info('copying dicoms to directory')

    for subdir, dirs, files in os.walk(dicom_path):
        if not files:
            log.debug(f'no files found in {subdir}, continuing')
            continue

        files = [f for f in files if f[-4:] in ['.dcm','.img']]

        if files:
            log.debug(f'found dicoms in {subdir}, using these')
            break

    for f in files:
        source = subdir/f
        dest = dir/f
        shutil.move(source, dest)

    log.info('finished')

def find_dicoms(dicom_dir):
    possible_dicom_ext = ['.dcm','.img']
    for pde in possible_dicom_ext:
        dicoms = glob.glob(str(dicom_dir/f'*{pde}'))

        if dicoms:
            break

    if not dicoms:
        log.error(f'no dicoms found in {dicom_dir}')
        sys.exit(1)

    return dicoms


def unzip_dicom_to_dir(dicom_zip,dir):
    log.info('unzipping dicom')
    with zipfile.ZipFile(dicom_zip) as zip:
        for zip_info in zip.infolist():
            if zip_info.filename[-1] == '/':
                continue
            zip_info.filename = os.path.basename(zip_info.filename)
            zip.extract(zip_info, dir)
    log.info('unzipping complete')


def extract_dicom_metadata(dicom_file):
    log.info('extracting metadata')
    if isinstance(dicom_file,list):
        dicom_file = dicom_file[0]

    dicom = pydicom.read_file(dicom_file)
    meta_dict = {}
    print(dicom)
    for element in dicom.elements():

        if isinstance(element,pydicom.dataelem.RawDataElement):
            continue

        if element.description() in ['[Unknown]','Private tag data','Private Creator']:
            continue
        if element.VR in ['OW']:
            continue
        if not element.keyword:
            continue
        if isinstance(element.value,pydicom.sequence.Sequence) or isinstance(element.value, pydicom.sequence.MultiValue) or isinstance(element.value, pydicom.sequence.MutableSequence):
            continue

        meta_dict[str(element.keyword)] = str(element.value)

    return meta_dict


def save_metadata(dicom_metadata, nifti_path):
    log.info('saving metadata')
    nifti_path = Path(nifti_path)
    nifti_name = nifti_path.stem
    nifti_name = nifti_name.replace('.', '_')
    json_file = nifti_path.parent/f'dicom_metadata_{nifti_name}.json'

    with open(json_file, 'w') as jf:
        json.dump(dicom_metadata, jf, indent=2)



def main(dicom_path, nifti_path):

    prep_dicom(dicom_path, WORKING_DIRECTORY)

    dicoms = find_dicoms(WORKING_DIRECTORY)

    dicom_metadata = extract_dicom_metadata(dicoms)

    save_metadata(dicom_metadata, nifti_path)


if __name__=='__main__':
    main(sys.argv[1], sys.argv[2])

