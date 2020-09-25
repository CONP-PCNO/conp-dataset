import getopt
import sys
import os
import lib.Utility as Utility


def main(argv):

    conp_dataset_dir = parse_input(argv)

    dataset_descriptor_list = Utility.read_conp_dataset_dir(conp_dataset_dir)

    datasets_summary_dict = {}
    i = 0
    for dataset in dataset_descriptor_list:
        datasets_summary_dict[i] = parse_dats_information(dataset)
        i += 1

    csv_content = [
        [
            'Data Provider',
            'Number Of Datasets',
            'Number Of Datasets Requiring Authentication',
            'Total Number Of Files',
            'Total Size (GB)',
            'Keywords Describing The Data'
        ]
    ]
    for data_provider in ['braincode', 'frdr', 'loris', 'osf', 'zenodo']:
        summary_list = get_stats_for_data_provider(datasets_summary_dict, data_provider)
        csv_content.append(summary_list)

    Utility.write_csv_file('summary_statistics_per_data_providers', csv_content)


def parse_input(argv):

    conp_dataset_dir = None

    description = '\nThis tool facilitates the creation of statistics per data providers for reporting purposes.' \
                  ' It will read DATS files and print out a summary per data providers based on the following list' \
                  'of DATS fields present in the DATS. json of every dataset present in the conp-dataset/projects' \
                  'directory.\n Queried fields: <distribution->access->landingPage>; <distributions->access->authorizations>; ' \
                  '<distributions->size>; <extraProperties->files>; <keywords>\n'
    usage = (
        '\n'
        'usage  : python ' + __file__ + ' -d <conp-dataset directory path>\n\n'
        'options: \n'
            '\t-d: path to the conp-dataset directory to parse\n'
    )

    try:
        opts, args = getopt.getopt(argv, "hd:")
    except getopt.GetoptError:
        sys.exit()

    for opt, arg in opts:
        if opt == '-h':
            print(description + usage)
            sys.exit()
        elif opt == '-d':
            conp_dataset_dir = arg

    if not conp_dataset_dir:
        print('a path to the conp-dataset needs to be given as an argument to the script by using the option `-d`')
        print(description + usage)
        sys.exit()

    if not os.path.exists(conp_dataset_dir + '/projects'):
        print(conp_dataset_dir + 'does not appear to be a valid path and does not include a `projects` directory')
        print(description + usage)
        sys.exit()

    return conp_dataset_dir


def parse_dats_information(dats_dict):

    extra_properties = dats_dict['extraProperties']
    keywords = dats_dict['keywords']

    values_dict = {
        'extraProperties': {},
        'keywords': []
    }
    for extra_property in extra_properties:
        values_dict[extra_property['category']] = extra_property['values'][0]['value']
    for keyword in keywords:
        values_dict['keywords'].append(keyword['value'])

    authorization = 'unknown'
    if 'authorizations' in dats_dict['distributions'][0]['access']:
        authorization = dats_dict['distributions'][0]['access']['authorizations'][0]['value']

    return {
        'title'          : dats_dict['title'],
        'data_provider'  : dats_dict['distributions'][0]['access']['landingPage'],
        'authorization'  : authorization,
        'dataset_size'   : dats_dict['distributions'][0]['size'],
        'size_unit'      : dats_dict['distributions'][0]['unit']['value'],
        'number_of_files': values_dict['files']        if 'files'       in values_dict else '',
        'keywords'       : values_dict['keywords']     if 'keywords'    in values_dict else '',
    }


def get_stats_for_data_provider(dataset_summary_dict, data_provider):

    dataset_number  = 0
    requires_login  = 0
    total_size      = 0
    total_files     = 0
    keywords_list   = []

    for index in dataset_summary_dict:

        dataset_dict = dataset_summary_dict[index]
        if data_provider not in dataset_dict['data_provider']:
            continue

        dataset_number += 1
        if isinstance(dataset_dict['number_of_files'], str):
            total_files += int(dataset_dict['number_of_files'].replace(',', ''))
        else:
            total_files += dataset_dict['number_of_files']

        print(dataset_dict['title'])
        print(dataset_dict['data_provider'])
        print('\n')

        if dataset_dict['authorization'].lower() in ['private', 'restricted']:
            requires_login += 1

        if dataset_dict['size_unit'].lower() == 'b':
            total_size += dataset_dict['dataset_size'] / pow(1024, 3)
            print('kb')
            print(dataset_dict['dataset_size'])
            print(dataset_dict['dataset_size'] / pow(1024, 2))
            print('\n')
        elif dataset_dict['size_unit'].lower() == 'kb':
            total_size += dataset_dict['dataset_size'] / pow(1024, 2)
            print('kb')
            print(dataset_dict['dataset_size'])
            print(dataset_dict['dataset_size'] / pow(1024, 2))
            print('\n')
        elif dataset_dict['size_unit'].lower() == 'mb':
            total_size += dataset_dict['dataset_size'] / 1024
            print('mb')
            print(dataset_dict['dataset_size'])
            print(dataset_dict['dataset_size'] / 1024)
            print('\n')
        elif dataset_dict['size_unit'].lower() == 'gb':
            total_size += dataset_dict['dataset_size']
            print('gb')
            print(dataset_dict['dataset_size'])
            print('\n')
        elif dataset_dict['size_unit'].lower() == 'tb':
            total_size += dataset_dict['dataset_size'] * 1024
            print('tb')
            print(dataset_dict['dataset_size'])
            print(dataset_dict['dataset_size'] / 1024)
            print('\n')
        elif dataset_dict['size_unit'].lower() == 'pb':
            total_size += dataset_dict['dataset_size'] * pow(1024, 2)
            print('pb')
            print(dataset_dict['dataset_size'])
            print(dataset_dict['dataset_size'] / 1024)
            print('\n')

        for keyword in dataset_dict['keywords']:
            if keyword not in keywords_list:
                if keyword == 'canadian-open-neuroscience-platform':
                    continue
                keywords_list.append(keyword)

    return [
        data_provider,
        str(dataset_number),
        str(requires_login),
        str(total_files),
        str(round(total_size)),
        ', '.join(keywords_list)
    ]


if __name__ == "__main__":
    main(sys.argv[1:])
