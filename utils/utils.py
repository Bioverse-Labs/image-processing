import os
import logging
import shutil
import settings

from random import shuffle


class Utils:
    """
    Class with essentials and general methods for multiple purposes to support the image processing routines
    """

    def __init__(self):
        """
        Constructor method
        """
        pass

    def check_annotation_extention(self, filepath):
        """
        Check the annotation extension according to the accepted ones in settings

        :param filepath: absolute path to annotated images
        :return: returns the new_filepath if
        """
        path = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)

        for extension in settings.VALID_RASTER_EXTENSION:
            new_filepath = os.path.join(path, name + extension)
            if os.path.exists(new_filepath):
                return new_filepath

        return None

    def split_samples(self, training_folder, validation_folder, percentage):
        """
        Shuffle all images in training_folder, separate a percentage of them, then, move it to validation_folder

        :param training_folder: absolute path to the training folder (raster)
        :param validation_folder: absolute path to the validation folder (labels)
        :param percentage: int 0-100, describing the percentage of images from training_folder will be moved to
                           the validation_folder
        """
        train_image_path = os.path.join(training_folder, "image")
        train_annotation_path = os.path.join(training_folder, "label")
        validation_image_path = os.path.join(validation_folder, "image")
        validation_annotation_path = os.path.join(validation_folder, "label")

        if not os.path.exists(training_folder):
            logging.info(">> Training folder not found: %s", training_folder)
            return
        else:
            if not os.path.exists(train_image_path):
                os.mkdir(train_image_path)

            if not os.path.exists(train_annotation_path):
                os.mkdir(train_annotation_path)

        if not os.path.exists(validation_folder):
            logging.info(">> Validation folder not found: %s", validation_folder)
            return
        else:
            if not os.path.exists(validation_image_path):
                os.mkdir(validation_image_path)

            if not os.path.exists(validation_annotation_path):
                os.mkdir(validation_annotation_path)

        list_of_training_image = os.listdir(train_image_path)
        shuffle(list_of_training_image)
        splitted_percent_for_val = int(round(len(list_of_training_image) * (int(percentage)/100)))

        validation_list = list_of_training_image[-splitted_percent_for_val:]

        for filename in validation_list:
            ext2 = os.path.splitext(filename)[1]

            if ext2.lower() not in settings.VALID_RASTER_EXTENSION:
                continue

            image_train_file = os.path.join(train_image_path, filename)
            image_val_file = os.path.join(train_annotation_path, filename)

            if not os.path.isfile(image_val_file):
                image_val_file = self.check_annotation_extention(image_val_file)

            if image_val_file is None:
                logging.info(">>>> There is no annotation for {} image. Skipped!".format(filename))
            else:
                shutil.move(image_train_file, validation_image_path)
                shutil.move(image_val_file, validation_annotation_path)

    def get_only_certain_extension(self, path, extension):
        """
        List all files in path, with a specific extension

        :param path: absolute path to a certain directory
        :param extension: the file extension to search for
        :return file_list: an array of files with specific extension
        """
        file_list = []
        x = os.listdir(path)
        for i in x:
            if i.endswith(extension):
                file_list.append(i)
        return file_list