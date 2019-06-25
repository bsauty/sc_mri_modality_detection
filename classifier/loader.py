import torch
import torch.utils.data as data
import numpy as np
from tqdm import tqdm
import os
import nibabel as nib


class Slice():
    """
    This class defines a slice of MRI, ie. a 2D image stored as an array
    """
    def __init__(self, data, label):
        self.data = data
        self.label = label


class Acquisition():
    """
    This class defines an acquisition, ie. a list of 2D slices.
    There are preprocessing methods :
         - StandardizeTranform
         - CenterCropTransform
         - SliceFilter
         - ToTensor
    And general purpose methods
         - get_modality
         - ToSlices
    """
    def __init__(self, path, modality=None, tensor=None):
        """
        This method loads the slices in the slices attribute from the path.
        At this point it is only a list of arrays and will only be converted
        to tensor after transformations.
        """

        self.path = path
        self.tensor = tensor

        if modality is not None:
            self.modality = modality
        else:
            self.modality = self.get_modality()

        nii_original = nib.load(path).get_data()

        if nii_original.size == 0:
            raise RuntimeError(f"Empty slice in subject {path}.")
        axial_slices = []
        for i in range(nii_original.shape[2]):
            axial_slices.append(nii_original[:, :, i])
        self.slices = axial_slices

    def get_modality(self):
        """
        This method finds the modality of an acquisition based on its name
        """
        if "T1w" in self.path:
            return 0
        if "T2star" in self.path:
            return 1
        if "T2w" in self.path:
            return 2
        raise RuntimeError(f"Incorrect path for {path}.")

    def StandardizeTransform(self):
        """
        This method standardizes each slices individually
        """
        for i in range(len(self.slices)):
            mean, std = self.slices[i].mean(), self.slices[i].std()
            self.slices[i] = (self.slices[i] - mean) / std

    def CenterCropTransform(self, size=128):
        """
        This method centers the image around the center
        """
        for i in range(len(self.slices)):
            y, x = self.slices[i].shape

            startx = x // 2 - (size // 2)
            starty = y // 2 - (size // 2)

            if startx < 0 or starty < 0:
                raise RuntimeError("Negative crop.")

            self.slices[i] = self.slices[i][starty:starty + size,
                             startx:startx + size]

    def SliceFilter(self):
        """
        This method filters empty slices and removes them
        """
        cleaned_slices = []
        for i in range(len(self.slices)):
            if np.count_nonzero(self.slices[i]) > 0:
                cleaned_slices.append(self.slices[i])
        self.slices = cleaned_slices

    def ToTensor(self):
        """
        This method returns the tensor in the correct shape to feed the network for testing
        on whole acquisitions ie. torch.Size([16, 1, 128, 128]) with dtype = float
        """
        slices = np.asarray(self.slices, dtype=np.float32)
        slices = np.expand_dims(slices, axis=1)
        self.tensor = torch.FloatTensor(slices)

    def ToSlices(self):
        """
        This method returns a list of slice elements that we will feed the network for training
        on individual slices
        """
        return ([Slice(self.tensor[i], self.modality) for i in range(len(self.slices))])


class MRIDataset(data.Dataset):
    """
    This class defines our dataset type. Data is comprised of two attributes :
       - data : a list of 2D slices
       - labels : a list of the corresponding labels
    """
    def __init__(self, data=None, label=None):
        if data is None or label is None:
            self.data, self.label = [], []
        else:
            self.data = data
            self.label = label

    def __getitem__(self, index):
        x = self.data[index]
        y = self.label[index]

        return {'data': x, 'label': y}

    def __len__(self):
        return len(self.data)

    def add(self, data, label):
        self.data.append(data)
        self.label.append(label)


def BIDSIterator(paths_centers, type_of_set):
    """
    This function is used to iterate over a BIDS architecture to load all the acquisitions in a dataset as
    defined above
    :param paths_centers: list of paths to centers
    :param type_of_set: string used for displaying purposes
    :return: dataset
    """

    lst_acqs = []                      # This list will contain all the paths to the acquisitions

    ds = MRIDataset()

    # Iteration over the medical centers  ---------------------------------------------------------------------
    for path_center in tqdm(paths_centers,
                            desc="Loading " + type_of_set + " set"):

        sub_list = [sub for sub in os.listdir(path_center) if "sub" in sub]

        # Iteration over the subjects  ------------------------------------------------------------------------
        for subject in sub_list:

            path_subject = os.path.join(path_center, subject, 'anat')
            acq_list = [acq for acq in os.listdir(path_subject) if ".nii.gz" in acq]

            # Iteration over raw list of acquisition  ---------------------------------------------------------
            for acq in acq_list:

                if "MTS" in acq:      # We only consider T1w, T2w and T2s acquisitions
                    continue

                path_acq = os.path.join(path_subject, acq)

                if os.path.exists(path_acq):
                    lst_acqs.append(acq)

    # Adding all the correct acquisitions to the dataset   ---------------------------------------------------
    for acq in tqdm(lst_acqs, unit="subject"):

        try:
            acq.CenterCropTransform()
            acq.StandardizeTransform()
            acq.SliceFilter()
            acq.ToTensor()
        except RuntimeError:
            continue
        else:
            for sl in acq.ToSlices():
                ds.add(sl.data, sl.label)

    return ds
