# AUTOGENERATED! DO NOT EDIT! File to edit: nbdev_nbs/peptide/fragment.ipynb (unless otherwise specified).

__all__ = ['get_charged_frag_types', 'parse_charged_frag_type', 'get_shift_modification_mass',
           'get_by_and_peptide_mass', 'get_peptide_mass_for_same_len_seqs', 'get_by_and_peptide_mass_for_same_len_seqs',
           'init_zero_fragment_dataframe', 'init_fragment_dataframe_from_other', 'init_fragment_by_precursor_dataframe',
           'set_sliced_fragment_dataframe', 'get_sliced_fragment_dataframe', 'concat_precursor_fragment_dataframes',
           'get_fragment_mass_dataframe', 'set_precursor_mz']

# Cell
import numpy as np
import pandas as pd
from typing import List, Union, Tuple, Iterable
import warnings

from alphabase.constants.aa import \
    get_sequence_mass, \
    get_AA_masses_for_same_len_seqs,\
    get_sequence_masses_for_same_len_seqs
from alphabase.constants.modification import \
    get_modification_mass, get_modloss_mass,\
    get_modification_mass_sum
from alphabase.constants.element import \
    MASS_H2O, MASS_PROTON, MASS_NH3, CHEM_MONO_MASS

def get_charged_frag_types(
    frag_types:List[str],
    max_frag_charge:int = 2
)->List[str]:
    '''
    Args:
        frag_types (List[str]): e.g. ['b','y','b_modloss','y_modloss']
        max_frag_charge (int): max fragment charge. (default: 2)
    Returns:
        List[str]: for `frag_types=['b','y','b_modloss','y_modloss']` and `max_frag_charge=2`,
        return `['b_1','b_2','y_1','y_2','b_modloss_1','b_modloss_2','y_modloss_1','y_modloss_2']`.
    '''
    charged_frag_types = []
    for _type in frag_types:
        for _ch in range(1, max_frag_charge+1):
            charged_frag_types.append(f"{_type}_{_ch}")
    return charged_frag_types

def parse_charged_frag_type(
    charged_frag_type: str
)->Tuple[str,int]:
    '''
    Args:
        charged_frag_type (str): e.g. 'y_1', 'b_modloss_1'
    Returns:
        str: fragment type, e.g. 'b','y'
        int: charge state, can be a negative value
    '''
    items = charged_frag_type.split('_')
    _ch = items[-1]
    _type = '_'.join(items[:-1])
    if not _ch[-1].isdigit():
        return _type, int(_ch[:-1])
    else:
        return _type, int(_ch)

def get_shift_modification_mass(
    peplen:int,
    mass_shifts:List[float],
    shift_sites:List[int]
)->np.array:
    '''
    For open-search, we may also get modification
    mass shifts other than mod names.
    Args:
        peplen (int): nAA
        mass_shifts (list of floats): mass shifts on the peptide
        shift_sites (list of int): localized sites of corresponding mass shifts
    Returns:
        np.array: 1-D array with length=`peplen`.
            Masses of modifications (mass shifts) through the peptide,
            `0` if sites has no modifications
    '''
    masses = np.zeros(peplen)
    for site, mass in zip(shift_sites, mass_shifts):
        if site == 0:
            masses[site] += mass
        elif site == -1:
            masses[site] += mass
        else:
            masses[site-1] += mass
    return masses

def get_by_and_peptide_mass(
    sequence: str,
    mod_names: List[str],
    mod_sites: List[int],
    mass_shifts: List[float] = None,
    shift_sites: List[int] = None,
)->Tuple[np.array,np.array,float]:
    '''
    It is highly recommend to use
    `get_by_and_peptide_mass_for_same_len_seqs()`
    as it is much faster
    '''
    residue_masses = get_sequence_mass(sequence)
    mod_masses = get_modification_mass(
        len(sequence), mod_names, mod_sites
    )
    residue_masses += mod_masses
    if mass_shifts:
        mod_masses = get_shift_modification_mass(
            len(sequence), mass_shifts, shift_sites
        )
        residue_masses += mod_masses
    #residue_masses = residue_masses[np.newaxis, ...]
    b_masses = np.cumsum(residue_masses)
    b_masses, pepmass = b_masses[:-1], b_masses[-1]

    pepmass += MASS_H2O
    y_masses = pepmass - b_masses
    return b_masses, y_masses, pepmass

def get_peptide_mass_for_same_len_seqs(
    sequences: np.array,
    mod_list: Iterable[str],
    mass_shift_list: Iterable[str]=None
)->np.array:
    '''
    Args:
        mod_list (Iterable[str]): Iterable (list, np.array) of modifications,
            e.g. `['Oxidation@M;Phospho@S','Phospho@S;Deamidated@N']`
        mass_shift_list (Iterable[str]): Iterable of modifications as mass shifts,
            e.g. `['15.9xx;79.9xxx','79.9xx;0.98xx']`
    Returns:
        np.array: peptide masses (1-D array, H2O already added)
    '''
    seq_masses = get_sequence_masses_for_same_len_seqs(
        sequences
    )
    mod_masses = np.zeros_like(seq_masses)
    for i, mods in enumerate(mod_list):
        if mods:
            mod_masses[i] = get_modification_mass_sum(
                mods.split(';')
            )
    if mass_shift_list is not None:
        for i, mass_shifts in enumerate(mass_shift_list):
            if mass_shifts:
                mod_masses[i] += np.sum([
                    float(mass) for mass in mass_shifts.split(';')
                ])
    return seq_masses+mod_masses


def get_by_and_peptide_mass_for_same_len_seqs(
    sequences: np.array,
    mod_list: Iterable[List[str]],
    site_list: Iterable[List[int]],
    mass_shift_list: Iterable[List[float]]=None,
    shift_site_list: Iterable[List[int]]=None,
)->Tuple[np.array,np.array,np.array]:
    '''
    Args:
        sequence (np.array of str): np.array of peptie sequences with same length.
        mod_list (Iterable[List[str]]): Iterable (list, array, ...) of modifications ,
            e.g. `[['Oxidation@M','Phospho@S'],['Phospho@S','Deamidated@N']]`
        site_list (Iterable[List[int]]): Iterable of modification sites
            corresponding to `mod_list`, e.g. `[[3,6],[4,17]]`
        mass_shift_list (Iterable[List[float]]): Iterable of modifications,
            e.g. `[[15.9xx,79.9xx],[79.9xx,0.98xx]]`
        shift_site_list (Iterable[List[int]]): Iterable of modification shift sites
            corresponding to `mod_list`, e.g. `[[3,6],[4,17]]`
    Returns:
        np.array: neutral b fragment masses (2-D array)
        np.array: neutral y fragmnet masses (2-D array)
        np.array: neutral peptide masses (1-D array)
    '''
    residue_masses = get_AA_masses_for_same_len_seqs(sequences)
    mod_masses = np.zeros_like(residue_masses)
    seq_len = len(sequences[0])
    for i, (mods, sites) in enumerate(zip(mod_list, site_list)):
        if mods:
            mod_masses[i,:] = get_modification_mass(
                seq_len,
                mods,
                sites,
            )
    if mass_shift_list is not None:
        for i, (shifts, sites) in enumerate(zip(
            mass_shift_list, shift_site_list
        )):
            if shifts:
                mod_masses[i,:] += get_shift_modification_mass(
                    seq_len,
                    shifts,
                    sites,
                )
    residue_masses += mod_masses

    b_masses = np.cumsum(residue_masses, axis=1)
    b_masses, pepmass = b_masses[:,:-1], b_masses[:,-1:]

    pepmass += MASS_H2O
    y_masses = pepmass - b_masses
    return b_masses, y_masses, pepmass.reshape(-1)

# Cell
def init_zero_fragment_dataframe(
    peplen_array:np.array,
    charged_frag_types:List[str]
)->Tuple[pd.DataFrame, np.array, np.array]:
    '''
    Args:
        peplen_array (np.array): peptide lengths for the fragment dataframe
        charged_frag_types (List[str]):
            `['b_1','b_2','y_1','y_2','b_modloss_1','y_H2O_1'...]`
    Returns:
        pd.DataFrame: `fragment_df` with zero values
        np.array (int64): the start indices point to the `fragment_df` for each peptide
        np.array (int64): the end indices point to the `fragment_df` for each peptide
    '''
    indices = np.zeros(len(peplen_array)+1, dtype=np.int64)
    indices[1:] = peplen_array-1
    indices = np.cumsum(indices)
    fragment_df = pd.DataFrame(
        np.zeros((indices[-1],len(charged_frag_types))),
        columns = charged_frag_types
    )
    return fragment_df, indices[:-1], indices[1:]

def init_fragment_dataframe_from_other(
    reference_fragment_df: pd.DataFrame
):
    '''
    Init zero fragment dataframe from the `reference_fragment_df`
    '''
    return pd.DataFrame(
        np.zeros_like(reference_fragment_df.values),
        columns = reference_fragment_df.columns
    )

def init_fragment_by_precursor_dataframe(
    precursor_df,
    charged_frag_types: List[str],
    reference_fragment_df: int = None
):
    '''
    Init zero fragment dataframe for the `precursor_df`. If
    the `reference_fragment_df` is provided, it will generate
    the dataframe based on the reference. Otherwise it
    generates the dataframe from scratch.
    Args:
        precursor_df (pd.DataFrame): precursors to generate fragment masses,
            if `precursor_df` contains the 'frag_start_idx' column,
            it is better to provide `reference_fragment_df` as
            `precursor_df.frag_start_idx` and `precursor.frag_end_idx`
            point to the indices in `reference_fragment_df`
        charged_frag_types (List):
            `['b_1+','b_2+','y_1+','y_2+','b_modloss_1+','y_H2O_1+'...]`
        reference_fragment_df (pd.DataFrame): generate fragment_mass_df based
            on this reference (default: None)
    Returns:
        pd.DataFrame: zero `fragment_df` with given `charged_frag_types`
    '''
    if 'frag_start_idx' not in precursor_df.columns:
        fragment_df, start_indices, end_indices = init_zero_fragment_dataframe(
            precursor_df.nAA.values,
            charged_frag_types
        )
        precursor_df['frag_start_idx'] = start_indices
        precursor_df['frag_end_idx'] = end_indices
    else:
        if reference_fragment_df is None:
            warnings.warn(
                "`precursor_df` contains the 'frag_start_idx' column, "\
                "it is better to provide `reference_fragment_df`", RuntimeWarning
            )
            fragment_df = pd.DataFrame(
                np.zeros((
                    precursor_df.frag_end_idx.max(), len(charged_frag_types)
                )),
                columns = charged_frag_types
            )
        else:
            fragment_df = init_fragment_dataframe_from_other(
                reference_fragment_df[charged_frag_types]
            )
    return fragment_df

# Cell
def set_sliced_fragment_dataframe(
    fragment_df: pd.DataFrame,
    values: np.array,
    frag_start_end_list: List[Tuple[int,int]],
    charged_frag_types: List[str],
)->pd.DataFrame:
    '''
    Set the values of the slices `frag_start_end_list=[(start,end),(start,end),...]` of fragment_df.
    Args:
        fragment_df (pd.DataFrame): fragment dataframe to be set
        frag_start_end_list (List[Tuple[int,int]]): e.g. `[(start,end),(start,end),...]`
        charged_frag_types (List[str]): e.g. `['b_1','b_2','y_1','y_2']`
    Returns:
        pd.DataFrame: fragment_df after the values are set
    '''
    frag_slice_list = [slice(start,end) for start,end in frag_start_end_list]
    frag_slices = np.r_[tuple(frag_slice_list)]
    fragment_df.loc[frag_slices, charged_frag_types] = values
    return fragment_df

def get_sliced_fragment_dataframe(
    fragment_df: pd.DataFrame,
    frag_start_end_list:Union[List,np.array],
    charged_frag_types:List = None,
)->pd.DataFrame:
    '''
    Get the sliced fragment_df from `frag_start_end_list=[(start,end),(start,end),...]`.
    Args:
        fragment_df (pd.DataFrame): fragment dataframe to be set
        frag_start_end_list (List[Tuple[int,int]]): e.g. `[(start,end),(start,end),...]`
        charged_frag_types (List[str]): e.g. `['b_1','b_2','y_1','y_2']` (default: None)
    Returns:
        pd.DataFrame: sliced fragment_df. If `charged_frag_types` is None,
        return fragment_df with all columns
    '''
    frag_slice_list = [slice(start,end) for start,end in frag_start_end_list]
    frag_slices = np.r_[tuple(frag_slice_list)]
    if not charged_frag_types:
        charged_frag_types = slice(None)
    return fragment_df.loc[frag_slices, charged_frag_types]

# Cell
def concat_precursor_fragment_dataframes(
    precursor_df_list: List[pd.DataFrame],
    fragment_df_list: List[pd.DataFrame],
    *other_fragment_df_lists
)->Tuple[pd.DataFrame,...]:
    '''
    Since fragment_df is indexed by precursor_df, when we concatenate multiple
    fragment_df, the indexed positions will change for in precursor_dfs,
    this function keeps the correct indexed positions of precursor_df when
    concatenating multiple fragment_df dataframes.
    Args:
        precursor_df_list (List[pd.DataFrame]): precursor dataframe list to concatenate
        fragment_df_list (List[pd.DataFrame]): fragment dataframe list to concatenate
        *other_fragment_df_lists: arbitray other fragment dataframe list to concatenate,
            e.g. fragment_mass_df, fragment_inten_df, ...
    Returns:
        Tuple[pd.DataFrame,...]: concatenated precursor_df, fragment_df, *other_fragment_df ...
    '''
    fragment_df_lens = [len(fragment_df) for fragment_df in fragment_df_list]
    cum_frag_df_lens = np.cumsum(fragment_df_lens)
    for i,precursor_df in enumerate(precursor_df_list[1:]):
        precursor_df[['frag_start_idx','frag_end_idx']] += cum_frag_df_lens[i]
    return pd.concat(precursor_df_list).reset_index(drop=True),\
            pd.concat(fragment_df_list).reset_index(drop=True),\
            *[pd.concat(other_list).reset_index(drop=True) for other_list in other_fragment_df_lists]

# Cell
def get_fragment_mass_dataframe(
    precursor_df: pd.DataFrame,
    charged_frag_types:List,
    reference_fragment_df: pd.DataFrame = None,
)->Tuple[pd.DataFrame, pd.DataFrame]:
    '''
    Generate fragment mass dataframe for the precursor_df. If
    the `reference_fragment_df` is provided, it will generate
    the mass dataframe based on the reference. Otherwise it
    generates the mass dataframe from scratch.
    Args:
        precursor_df (pd.DataFrame): precursors to generate fragment masses,
            if `precursor_df` contains the 'frag_start_idx' column,
            `reference_fragment_df` must be provided
        charged_frag_types (List):
            `['b_1','b_2','y_1','y_2','b_modloss_1','y_H2O_1'...]`
        reference_fragment_df (pd.DataFrame): generate fragment_mass_df based
            on this reference, as `precursor_df.frag_start_idx` and
            `precursor.frag_end_idx` point to the indices in
            `reference_fragment_df`
    Returns:
        pd.DataFrame: `precursor_df`. `precursor_df` contains the 'charge' column,
        this function will automatically assign the 'precursor_mz' to `precursor_df`
        pd.DataFrame: `fragment_mass_df` with given `charged_frag_types`
    Raises:
        ValueError: when 1. `precursor_df` contains 'frag_start_idx' but
        `reference_fragment_df` is not None; or 2. `reference_fragment_df`
        is None but `precursor_df` does not contain 'frag_start_idx'
    '''
    if reference_fragment_df is None:
        if 'frag_start_idx' in precursor_df.columns:
            raise ValueError(
                "`precursor_df` contains 'frag_start_idx' column, "\
                "please provide `reference_fragment_df` argument"
            )
    else:
        if 'frag_start_idx' not in precursor_df.columns:
            raise ValueError(
                "No column 'frag_start_idx' in `precursor_df` "\
                "to slice the `reference_fragment_df`"
            )

    if reference_fragment_df is not None:
        fragment_mass_df = init_fragment_dataframe_from_other(
            reference_fragment_df[charged_frag_types]
        )
    else:
        fragment_df_list = []

    precursor_df_list = []

    _grouped = precursor_df.groupby('nAA')
    for nAA, df_group in _grouped:
        mod_list = []
        site_list = []
        for mod_names, mod_sites in df_group[
            ['mods', 'mod_sites']
        ].values:
            if mod_names:
                mod_names = mod_names.split(';')
                mod_sites = [int(_site) for _site in mod_sites.split(';')]
            else:
                mod_names = []
                mod_sites = []
            mod_list.append(mod_names)
            site_list.append(mod_sites)

        if 'mass_shifts' in df_group.columns:
            mass_shift_list = []
            shift_site_list = []
            for mass_shifts, shift_sites in df_group[
                ['mass_shifts', 'shift_sites']
            ].values:
                if mass_shifts:
                    mass_shifts = [float(_) for _ in mass_shifts.split(';')]
                    shift_sites = [int(_site) for _site in shift_sites.split(';')]
                else:
                    mass_shifts = []
                    shift_sites = []
                mass_shift_list.append(mass_shifts)
                shift_site_list.append(shift_sites)

            (
                b_mass, y_mass, pepmass
            ) = get_by_and_peptide_mass_for_same_len_seqs(
                df_group.sequence.values.astype('U'),
                mod_list, site_list,
                mass_shift_list,
                shift_site_list
            )
        else:
            (
                b_mass, y_mass, pepmass
            ) = get_by_and_peptide_mass_for_same_len_seqs(
                df_group.sequence.values.astype('U'),
                mod_list, site_list
            )
        b_mass = b_mass.reshape(-1)
        y_mass = y_mass.reshape(-1)

        if (
            'charge' in df_group.columns and
            'precursor_mz' not in df_group.columns
        ):
            df_group['precursor_mz'] = pepmass/df_group[
                'charge'
            ].values + MASS_PROTON

        for charged_frag_type in charged_frag_types:
            if charged_frag_type.startswith('b_modloss'):
                b_modloss = np.concatenate([
                    get_modloss_mass(nAA, mods, sites, True)
                    for mods, sites in zip(mod_list, site_list)
                ])
                break
        for charged_frag_type in charged_frag_types:
            if charged_frag_type.startswith('y_modloss'):
                y_modloss = np.concatenate([
                    get_modloss_mass(nAA, mods, sites, True)
                    for mods, sites in zip(mod_list, site_list)
                ])
                break

        set_values = []
        add_proton = MASS_PROTON
        for charged_frag_type in charged_frag_types:
            frag_type, charge = parse_charged_frag_type(charged_frag_type)
            if frag_type =='b':
                set_values.append(b_mass/charge + add_proton)
            elif frag_type == 'y':
                set_values.append(y_mass/charge + add_proton)
            elif frag_type == 'b_modloss':
                _mass = (b_mass-b_modloss)/charge + add_proton
                _mass[b_modloss == 0] = 0
                set_values.append(_mass)
            elif frag_type == 'y_modloss':
                _mass = (y_mass-y_modloss)/charge + add_proton
                _mass[y_modloss == 0] = 0
                set_values.append(_mass)
            elif frag_type == 'b_H2O':
                _mass = (b_mass-MASS_H2O)/charge + add_proton
                set_values.append(_mass)
            elif frag_type == 'y_H2O':
                _mass = (y_mass-MASS_H2O)/charge + add_proton
                set_values.append(_mass)
            elif frag_type == 'b_NH3':
                _mass = (b_mass-MASS_NH3)/charge + add_proton
                set_values.append(_mass)
            elif frag_type == 'y_NH3':
                _mass = (y_mass-MASS_NH3)/charge + add_proton
                set_values.append(_mass)
            elif frag_type == 'c':
                _mass = (b_mass+MASS_NH3)/charge + add_proton
                set_values.append(_mass)
            elif frag_type == 'z':
                _mass = (
                    y_mass-(MASS_NH3-CHEM_MONO_MASS['H'])
                )/charge + add_proton
                set_values.append(_mass)
            else:
                raise NotImplementedError(
                    f'Fragment type "{frag_type}" is not in fragment_mass_df.'
                )

        if reference_fragment_df is not None:
            set_sliced_fragment_dataframe(
                fragment_mass_df, np.array(set_values).T,
                df_group[['frag_start_idx','frag_end_idx']].values,
                charged_frag_types,
            )
        else:
            _fragment_mass_df = init_fragment_by_precursor_dataframe(
                df_group,
                charged_frag_types
            )
            _fragment_mass_df[:] = np.array(set_values).T
            fragment_df_list.append(_fragment_mass_df)
        precursor_df_list.append(df_group)

    if reference_fragment_df is not None:
        return pd.concat(precursor_df_list), fragment_mass_df
    else:
        return concat_precursor_fragment_dataframes(
            precursor_df_list, fragment_df_list
        )


# Cell
def set_precursor_mz(
    precursor_df: pd.DataFrame
)->pd.DataFrame:
    """
    Calculate precursor_mz for the precursor_df
    Args:
        precursor_df (pd.DataFrame):
          precursor_df with the 'charge' column

    Returns:
        pd.DataFrame: precursor_df with 'precursor_mz'
    """

    precursor_df['precursor_mz'] = 0
    _grouped = precursor_df.groupby('nAA')
    for nAA, df_group in _grouped:

        pepmass = get_peptide_mass_for_same_len_seqs(
            df_group.sequence.values.astype('U'),
            df_group.mods.values,
            df_group.mass_shifts.values if 'mass_shifts' in df_group.columns else None
        )

        precursor_df.loc[
            df_group.index, 'precursor_mz'
        ] = pepmass/df_group.charge + MASS_PROTON
    return precursor_df