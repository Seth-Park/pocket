"""
HICODet dataset under PyTorch framework

Fred Zhang <frederic.zhang@anu.edu.au>

The Australian National University
Australian Centre for Robotic Vision
"""

import os
import json

from .base import ImageDataset

class HICODet(ImageDataset):
    """
    Arguments:
        root(str): Root directory where images are downloaded to
        annFile(str): Path to json annotation file
        transform(callable, optional): A function/transform that  takes in an PIL image
            and returns a transformed version
        target_transform(callable, optional): A function/transform that takes in the
            target and transforms it
        transforms (callable, optional): A function/transform that takes input sample 
            and its target as entry and returns a transformed version.
    """
    def __init__(self, root, annoFile, transform=None, target_transform=None, transforms=None):
        super(HICODet, self).__init__(root, transform, target_transform, transforms)
        with open(annoFile, 'r') as f:
            anno = json.load(f)
        self._idx, self._anno, self._filenames, self._class_corr, self._empty_idx = \
            self.load_annotation_and_metadata(anno)
        self._annoFile = annoFile

    def __len__(self):
        """Return the number of images"""
        return len(self._idx)

    def __getitem__(self, i):
        """
        Arguments:
            i(int): Index to an image
        
        Returns:
            tuple[image, target]
        """
        intra_idx = self._idx[i]
        return self._transforms(
            self.load_image(os.path.join(self._root, self._filenames[intra_idx])), 
            self._anno[intra_idx]
            )

    def __repr__(self):
        """Return the executable string representation"""
        reprstr = self.__class__.__name__ + '(root=\"' + repr(self._root)
        reprstr += '\", annoFile=\"'
        reprstr += repr(self._annoFile)
        reprstr += '\")'
        # Ignore the optional arguments
        return reprstr


    def __str__(self):
        """Return the readable string representation"""
        reprstr = 'Dataset: ' + self.__class__.__name__ + '\n'
        reprstr += '\tNumber of images: {}\n'.format(self.__len__())
        reprstr += '\tImage directory: {}\n'.format(self._root)
        reprstr += '\tAnnotation file: {}\n'.format(self._root)
        return reprstr

    @property
    def class_corr(self):
        """
        Class correspondence matrix in zero-based index
        [
            [hoi_idx, obj_idx, verb_idx],
            ...
        ]
        """
        return self._class_corr.copy()

    @staticmethod
    def load_annotation_and_metadata(f):
        """
        Arguments:
            f(dict): Dictionary loaded from {annoFile}.json

        Returns:
            list[int]: Indices of images with valid interaction instances
            list[dict]: Annotations including bounding box pair coordinates and class index
            list[str]: File names for images
            list[list]: Class index correspondence
            list[int]: Indices of images without valid interation instances
        """
        idx = list(range(len(f['filenames'])))
        for empty_idx in f['empty']:
            idx.remove(empty_idx)

        return idx, f['annotation'], f['filenames'], f['class'], f['empty']
        