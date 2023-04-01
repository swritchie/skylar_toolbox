# =============================================================================
# Load libraries
# =============================================================================

import datetime as de
import time

# =============================================================================
# print_sequence
# =============================================================================

def print_sequence(
        name_sr: str,
        sequence):
    '''
    Prints sequence as numbered list

    Parameters
    ----------
    name_sr : str
        Sequence name.
    sequence : TYPE
        Sequence.

    Returns
    -------
    None.

    '''
    len_it = len(sequence)
    len_len_it = len(str(len_it))
    sequence_sr = '\n'.join(
        f'{index_it:0{len_len_it}d}. {element}' 
        for index_it, element in enumerate(iterable=sequence))
    print(f'{name_sr} ({len_it}):\n{sequence_sr}')

# =============================================================================
# time_method
# =============================================================================

def time_method(method):
    def wrap_method(*pargs, **kwargs):
        start_ft = time.perf_counter()
        result = method(*pargs, **kwargs)
        end_ft = time.perf_counter()
        print(f'{method.__qualname__} - {de.timedelta(seconds=end_ft - start_ft)}')
        return result
    return wrap_method
