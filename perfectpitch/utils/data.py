import numpy as np
import tensorflow as tf
import librosa
import note_seq

from perfectpitch import constants


def load_spec(path):
    with tf.io.gfile.GFile(path, "rb") as wav_file:
        audio, _ = librosa.load(wav_file, sr=constants.SAMPLE_RATE)

    spec = librosa.feature.melspectrogram(
        y=audio,
        sr=constants.SAMPLE_RATE,
        hop_length=constants.SPEC_HOP_LENGTH,
        fmin=30.0,
        n_mels=constants.SPEC_DIM,
        htk=True,
    )
    return spec.T


def load_transcription(path):
    with tf.io.gfile.GFile(path, "rb") as midi_file:
        midi = midi_file.read()

    notesequence = note_seq.midi_io.midi_to_note_sequence(midi)
    notesequence = note_seq.apply_sustain_control_changes(notesequence)

    return {
        "pitches": np.array([note.pitch for note in notesequence.notes], np.int8),
        "start_times": np.array(
            [note.start_time for note in notesequence.notes], np.float32
        ),
        "end_times": np.array(
            [note.end_time for note in notesequence.notes], np.float32
        ),
        "velocities": np.array([note.velocity for note in notesequence.notes], np.int8),
    }


def transcription_to_pianoroll(pitches, start_times, end_times, augment=False):
    frame_duration = constants.SPEC_HOP_LENGTH / constants.SAMPLE_RATE

    if augment:
        min_pitch_shift = max(constants.MIN_PITCH - pitches.min(), -5)
        max_pitch_shift = min(constants.MAX_PITCH - pitches.max(), 5)
        pitch_shift = np.random.randint(min_pitch_shift, max_pitch_shift)
        pitches += pitch_shift

        time_scale = np.random.choice([0.8, 0.9, 1.0, 1.1, 1.2])
        start_times *= time_scale
        end_times *= time_scale

    onset_frames = (start_times // frame_duration).astype(np.int32)
    offset_frames = (end_times // frame_duration).astype(np.int32)

    onsets = np.zeros(
        (offset_frames.max() + 1, constants.NUM_PITCHES), dtype=np.float32
    )
    offsets = np.zeros_like(onsets)
    for pitch, onset_frame, offset_frame in zip(pitches, onset_frames, offset_frames):
        if pitch < constants.MIN_PITCH or pitch > constants.MAX_PITCH:
            raise ValueError("pitch is not in valid range")

        if onset_frame == offset_frame:
            continue

        onsets[onset_frame, pitch - constants.MIN_PITCH] = 1
        offsets[offset_frame, pitch - constants.MIN_PITCH] = 1

    return onsets, offsets
