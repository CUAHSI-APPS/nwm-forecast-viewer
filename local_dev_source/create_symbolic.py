import os
import exceptions


def create_folder(folder_path):
    if not os.path.isdir(folder_path):
        os.makedirs(folder_path)


def create_symbolic(src_path, dest_path, overwrite=True):
    if os.path.isfile(src_path):
        if os.path.lexists(dest_path):
            if overwrite:
                os.remove(dest_path)
            else:
                return
        os.symlink(src_path, dest_path)
        #os.link(src_path, dest_path)
    else:
        raise exceptions.IOError(src_path)


def create_symbolic_for_AA(data_base_path=None, symbolic_base_path=None, date=None):

    date_folder_name = "nwm.{date}".format(date=date)
    l_list = [{"src_name": "forcing_analysis_assim", "dest_name": "forcing_analysis_assim"},
              {"src_name": "analysis_assim", "dest_name": "analysis_assim"}]

    for l in l_list:
        cfg_path = os.path.join(data_base_path, date_folder_name, l["src_name"])
        symbilic_cfg_path = os.path.join(symbolic_base_path, l["dest_name"])
        create_folder(symbilic_cfg_path)
        file_name_list = os.listdir(cfg_path)
        for file_name in file_name_list:
            file_path = os.path.join(cfg_path, file_name)
            file_name_split_list = file_name.split('.')
            file_name_split_list[0] = ".".join([file_name_split_list[0], "{date}".format(date=date)])
            symbolic_file_name = ".".join(file_name_split_list)
            symbolic_file_path = os.path.join(symbilic_cfg_path, symbolic_file_name)
            create_symbolic(file_path, symbolic_file_path)


def create_symbolic_for_SR_MR_LR(data_base_path=None, symbolic_base_path=None, date=None):

    date_folder_name = "nwm.{date}".format(date=date)
    l_list = [{"src_name": "forcing_short_range", "dest_name": "forcing_short_range"},
              {"src_name": "forcing_medium_range", "dest_name": "forcing_medium_range"},
              {"src_name": "short_range", "dest_name": "short_range"},
              {"src_name": "medium_range", "dest_name": "medium_range"},
              {"src_name": "long_range_mem1", "dest_name": "long_range"},
              {"src_name": "long_range_mem2", "dest_name": "long_range"},
              {"src_name": "long_range_mem3", "dest_name": "long_range"},
              {"src_name": "long_range_mem4", "dest_name": "long_range"}
              ]

    for l in l_list:
        cfg_path = os.path.join(data_base_path, date_folder_name, l["src_name"])
        symbolic_date_folder_path = os.path.join(symbolic_base_path, l["dest_name"], date)

        create_folder(symbolic_date_folder_path)

        file_name_list = os.listdir(cfg_path)
        for file_name in file_name_list:
            file_path = os.path.join(cfg_path, file_name)
            symbolic_file_path = os.path.join(symbolic_date_folder_path, file_name)
            create_symbolic(file_path, symbolic_file_path)


if __name__ == "__main__":

    try:
        data_base_path = "/media/sf_NWM"
        #symbolic_base_path = "/media/sf_nwm_new_data/symbolic/"
        symbolic_base_path = "/projects/water/nwm/data/"

        date_list = ["20180304", "20180305", "20180306", "20180307"]

        for date in date_list:
            create_symbolic_for_AA(data_base_path=data_base_path, symbolic_base_path=symbolic_base_path, date=date)
            create_symbolic_for_SR_MR_LR(data_base_path=data_base_path, symbolic_base_path=symbolic_base_path, date=date)
        print("Done")
    except Exception as ex:
        print(ex.message, type(ex), str(ex))

