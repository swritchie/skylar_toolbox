# =============================================================================
# Load libraries
# =============================================================================

import datetime
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
# time_callable
# =============================================================================

def time_callable(callable_):
    def wrap_callable(*pargs, **kwargs):
        start_ft = time.perf_counter()
        result = callable_(*pargs, **kwargs)
        end_ft = time.perf_counter()
        print(f'{callable_.__qualname__} - {datetime.timedelta(seconds=end_ft - start_ft)}')
        return result
    return wrap_callable