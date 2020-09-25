import os
import json
import csv
import datetime


def read_conp_dataset_dir(conp_dataset_dir):

    dataset_dirs_list = os.listdir(conp_dataset_dir + '/projects')

    dataset_descriptor_list =[]

    for dataset in dataset_dirs_list:
        if dataset == '.touchfile':
            continue

        dats_path = conp_dataset_dir + '/projects/' + dataset + '/DATS.json'
        if not (os.path.exists(dats_path)):
            subdataset_content_list = look_for_dats_file_in_subdataset_folders(conp_dataset_dir, dataset)
            dataset_descriptor_list.extend(subdataset_content_list)
            continue

        print('Reading file: ' + dats_path)
        with open(dats_path) as dats_file:
            dats_dict = json.loads(dats_file.read())
            dataset_descriptor_list.append(dats_dict)

    return dataset_descriptor_list


def look_for_dats_file_in_subdataset_folders(conp_dataset_dir, dataset):

    subdataset_dirs_list = os.listdir(conp_dataset_dir + '/projects/' + dataset)

    subdataset_content = []

    for subdataset in subdataset_dirs_list:
        dats_path = conp_dataset_dir + '/projects/' + dataset + '/' + subdataset + '/DATS.json'
        print('Reading file: ' + dats_path)
        with open(dats_path) as dats_file:
            dats_dict = json.loads(dats_file.read())
            subdataset_content.append(dats_dict)

    return subdataset_content


def write_csv_file(csv_file_basename, csv_content):

    csv_file = os.getcwd() + '/' + csv_file_basename + '_' + str(datetime.date.today()) + '.csv'

    with open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(csv_content)
