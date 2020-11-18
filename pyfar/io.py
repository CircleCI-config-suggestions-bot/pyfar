import scipy.io.wavfile as wavfile
import os.path
import warnings
import numpy as np
import sofa
import json
import copy
import io
import sys

from pyfar import Signal
from pyfar import Coordinates


def read_wav(filename):
    """
    Import a WAV file as signal object.

    This method is based on scipy.io.wavfile.read().

    Parameters
    ----------
    filename : string or open file handle
        Input wav file.

    Returns
    -------
    signal : signal instance
        An audio signal object from the pyfar Signal class
        containing the audio data from the WAV file.

    Notes
    -----
    * This function is based on scipy.io.wavfile.write().
    * This function cannot read wav files with 24-bit data.
    """
    sampling_rate, data = wavfile.read(filename)
    signal = Signal(data.T, sampling_rate, domain='time')
    return signal


def write_wav(signal, filename, overwrite=True):
    """
    Write a signal as a WAV file.

    Parameters
    ----------
    signal : Signal object
        An audio signal object from the pyfar Signal class.

    filename : string or open file handle
        Output wav file.

    overwrite : bool
        Select wether to overwrite the WAV file, if it already exists.
        The default is True.

    Notes
    -----
    * This function is based on scipy.io.wavfile.write().
    * Writes a simple uncompressed WAV file.
    * Signals of shape larger than 1D are flattened.
    * The bits-per-sample and PCM/float will be determined by the data-type.

    Common data types: [1]_

    =====================  ===========  ===========  =============
         WAV format            Min          Max       NumPy dtype
    =====================  ===========  ===========  =============
    32-bit floating-point  -1.0         +1.0         float32
    32-bit PCM             -2147483648  +2147483647  int32
    16-bit PCM             -32768       +32767       int16
    8-bit PCM              0            255          uint8
    =====================  ===========  ===========  =============

    Note that 8-bit PCM is unsigned.

    References
    ----------
    .. [1] IBM Corporation and Microsoft Corporation, "Multimedia Programming
       Interface and Data Specifications 1.0", section "Data Format of the
       Samples", August 1991
       http://www.tactilemedia.com/info/MCI_Control_Info.html

    """
    sampling_rate = signal.sampling_rate
    data = signal.time

    # Reshape to 2D
    data = data.reshape(-1, data.shape[-1])
    warnings.warn("Signal flattened to {data.shape[0]} channels.")

    # Check for .wav file extension
    if filename.split('.')[-1] != 'wav':
        warnings.warn("Extending filename by .wav.")
        filename += '.wav'

    # Check if file exists and for overwrite
    if overwrite is False and os.path.isfile(filename):
        raise FileExistsError(
                "File already exists,"
                "use overwrite option to disable error.")
    else:
        wavfile.write(filename, sampling_rate, data.T)


def read_sofa(filename):
    """
    Import a SOFA file as signal object.

    Parameters
    ----------
    filename : string or open file handle
        Input wav file.

    Returns
    -------
    signal : signal instance
        An audio signal object from the pyfar Signal class
        containing the IR data from the SOFA file.
    source_coordinates: coordinates instance
        An object from the pyfar Coordinates class containing
        the source coordinates from the SOFA file
        with matching domain, convention and unit.
    receiver_coordinates: coordinates instance
        An object from the pyfar Coordinates class containing
        the receiver coordinates from the SOFA file
        with matching domain, convention and unit.

    Notes
    -----
    * This function is based on the python-sofa package.
    * Only SOFA files of DataType 'FIR' are supported.

    References
    ----------
    .. [1] www.sofaconventions.org
    .. [2] “AES69-2015: AES Standard for File Exchange-Spatial Acoustic Data
       File Format.”, 2015.

    """
    sofafile = sofa.Database.open(filename)
    # Check for DataType
    if sofafile.Data.Type == 'FIR':
        domain = 'time'
        data = np.asarray(sofafile.Data.IR)
        sampling_rate = sofafile.Data.SamplingRate.get_values()
        # Check for units
        if sofafile.Data.SamplingRate.Units != 'hertz':
            raise ValueError(
                "SamplingRate:Units"
                "{sofafile.Data.SamplingRate.Units} is not supported.")
    else:
        raise ValueError("DataType {sofafile.Data.Type} is not supported.")
    signal = Signal(data, sampling_rate, domain=domain)

    # Source
    s_values = sofafile.Source.Position.get_values()
    s_domain, s_convention, s_unit = _sofa_pos(sofafile.Source.Position.Type)
    source_coordinates = Coordinates(
            s_values[:, 0],
            s_values[:, 1],
            s_values[:, 2],
            domain=s_domain,
            convention=s_convention,
            unit=s_unit)
    # Receiver
    r_values = sofafile.Receiver.Position.get_values()
    r_domain, r_convention, r_unit = _sofa_pos(sofafile.Receiver.Position.Type)
    receiver_coordinates = Coordinates(
            r_values[:, 0],
            r_values[:, 1],
            r_values[:, 2],
            domain=r_domain,
            convention=r_convention,
            unit=r_unit)

    return signal, source_coordinates, receiver_coordinates


def _sofa_pos(pos_type):
    if pos_type == 'spherical':
        domain = 'sph'
        convention = 'top_elev'
        unit = 'deg'
    elif pos_type == 'cartesian':
        domain = 'cart'
        convention = 'right'
        unit = 'met'
    else:
        raise ValueError("Position:Type {pos_type} is not supported.")
    return domain, convention, unit


def read(filename):
    """
    Read any compatible haiopy format from disk.

    Parameters
    ----------
    filename : string or open file handle.
        Input file must be haiopy compatible.

    Returns
    -------
    loaded_dict: dictionary containing haiopy types.
    """
    with open(filename, 'r') as f:
        obj_list_encoded = json.load(f)
    obj_list = []
    for obj_dict_encoded in obj_list_encoded:
        obj = _decode(obj_dict_encoded)
        obj_list.append(obj)
    return obj_list


def write(filename, *args):
    """
    Write any compatible haiopy format to disk.

    Parameters
    ----------
    filename : string or open file handle.
        Input file must be haiopy compatible.
    args: Compatible haiopy types:
        -
    """
    out_list = []
    for obj in args:
        obj_dict_encoded = _encode(obj)
        obj_dict_encoded['type'] = type(obj).__name__
        out_list.append(obj_dict_encoded)
    with open(filename, 'w') as f:
        json.dump(out_list, f)


def _encode(obj):
    """
    Iterates over object's dictionary and encodes all numpy.ndarrays
    to be able to store in a json format.

    Parameters
    ----------
    obj: Compatible haiopy type.

    Returns
    ----------
    obj_dict_encoded: dict.
        Json compatible dictionary.
    """
    obj_dict_encoded = copy.deepcopy(obj.__dict__)
    for key, value in obj_dict_encoded.items():
        if isinstance(value, np.ndarray):
            memfile = io.BytesIO()
            np.save(memfile, value, allow_pickle=False)
            memfile.seek(0)
            obj_dict_encoded[key] = memfile.read().decode('latin-1')
    return obj_dict_encoded


def _decode(obj_dict_encoded):
    """
    Iterates over object's encoded dictionary and decodes all
    numpy.ndarrays to be prepare object initialization.

    Parameters
    ----------
    obj_dict_encoded: dict.
        Dictionary of encoded compatible haiopy types.

    Returns
    ----------
    obj_dict: dict.
        Decoded dictionary ready for initialization of haiopy types.
    """
    # Does not have to be copied because read data is thrown away anyway
    obj_dict = obj_dict_encoded
    for key, value in obj_dict_encoded.items():
        if isinstance(value, str) and value.startswith('\x93NUMPY'):
            memfile = io.BytesIO()
            memfile.write(value.encode('latin-1'))
            memfile.seek(0)
            obj_dict[key] = np.load(memfile, allow_pickle=False)
    # TODO: What if there's no such default constructor?
    # Initialize empty object of type
    obj = _str_to_type(obj_dict['type'])()
    del obj_dict['type']
    obj.__dict__.update(obj_dict)
    return obj


def _str_to_type(type_as_string):
    return getattr(sys.modules['pyfar'], type_as_string)
