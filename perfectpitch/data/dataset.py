import math

import torch
import h5py

from perfectpitch import constants
from perfectpitch.data import utils


class Dataset(torch.utils.data.Dataset):
    def __init__(
        self,
        path,
        audio=False,
        spec=False,
        spec_length=False,
        velocity_min=False,
        velocity_max=False,
        notesequence=False,
        pianoroll=False,
        pad_or_truncate_pianoroll=True,
    ):
        self.__path = path
        self.__audio = audio
        self.__spec = spec
        self.__spec_length = spec_length
        self.__velocity_min = velocity_min
        self.__velocity_max = velocity_max
        self.__notesequence = notesequence
        self.__pianoroll = pianoroll
        self.__pad_or_truncate_pianoroll = pad_or_truncate_pianoroll

        with h5py.File(path, "r") as f:
            if f.attrs["sample_rate"] != constants.SAMPLE_RATE:
                raise ValueError(
                    "dataset sample rate does not match with the model sample rate"
                )

            self.__examples = sorted(f.keys())

    def __len__(self):
        return len(self.__examples)

    def __getitem__(self, index):
        if torch.is_tensor(index):
            index = index.tolist()

        with h5py.File(self.__path, "r") as f:
            example = f[self.__examples[index]]
            audio = example["audio"][...]
            velocity_min = example["velocity_min"][...]
            velocity_max = example["velocity_max"][...]
            pitches = example["pitches"][...]
            intervals = example["intervals"][...]
            velocities = example["velocities"][...]

        data = {}
        if self.__audio:
            data["audio"] = torch.from_numpy(audio)

        if self.__velocity_min:
            data["velocity_min"] = torch.from_numpy(velocity_min)

        if self.__velocity_max:
            data["velocity_max"] = torch.from_numpy(velocity_max)

        if self.__notesequence:
            notesequence = {}
            notesequence["pitches"] = torch.from_numpy(pitches)
            notesequence["intervals"] = torch.from_numpy(intervals)
            notesequence["velocities"] = torch.from_numpy(velocities)
            data["notesequence"] = notesequence

        spec_length = math.ceil(len(audio) / constants.SPEC_HOP_LENGTH)
        if self.__spec_length:
            data["spec_length"] = torch.tensor(spec_length)

        if self.__spec:
            spec = utils.audio_to_spec(audio)
            data["spec"] = torch.from_numpy(spec)

        if self.__pianoroll:
            pianoroll = utils.notesequence_to_pianoroll(
                pitches, intervals, velocities, velocity_max
            )
            data_pianoroll = {}
            data_pianoroll["actives"] = torch.from_numpy(pianoroll["actives"])
            data_pianoroll["onsets"] = torch.from_numpy(pianoroll["onsets"])
            data_pianoroll["offsets"] = torch.from_numpy(pianoroll["offsets"])
            data_pianoroll["velocities"] = torch.from_numpy(pianoroll["velocities"])
            data["pianoroll"] = data_pianoroll

        return data
