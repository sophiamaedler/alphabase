# AUTOGENERATED! DO NOT EDIT! File to edit: nbdev_nbs/peptide/precursor.ipynb (unless otherwise specified).

__all__ = ['refine_precursor_df', 'is_precursor_refined', 'update_precursor_mz', 'reset_precursor_df',
           'is_precursor_sorted', 'calc_precursor_mz', 'get_mod_seq_hash', 'get_mod_seq_charge_hash', 'hash_mod_seq_df',
           'hash_mod_seq_charge_df', 'hash_precursor_df', 'get_mod_seq_formula', 'get_mod_seq_isotope_distribution',
           'calc_precursor_isotope', 'calc_precursor_isotope_mp']

# Cell
import pandas as pd
import numpy as np

from alphabase.constants.element import (
    MASS_PROTON, MASS_ISOTOPE
)
from alphabase.constants.aa import AA_formula
from alphabase.constants.modification import MOD_formula
from alphabase.constants.isotope import (
    IsotopeDistribution
)
from alphabase.peptide.mass_calc import (
    calc_peptide_masses_for_same_len_seqs
)

def refine_precursor_df(
    df:pd.DataFrame,
    drop_frag_idx = True,
    ensure_data_validity = False,
)->pd.DataFrame:
    """
    Refine df inplace for faster precursor/fragment calculation.
    """
    if ensure_data_validity:
        df.fillna('', inplace=True)
        if 'charge' in df.columns:
            if df.charge.dtype not in [
                'int','int8','int64','int32',
                # np.int64, np.int32, np.int8,
            ]:
                df['charge'] = df['charge'].astype(np.int8)
        if 'mod_sites' in df.columns:
            if df.mod_sites.dtype not in ['O','U']:
                df['mod_sites'] = df.mod_sites.astype('U')

    if 'nAA' not in df.columns:
        df['nAA']= df.sequence.str.len().astype(np.int32)

    if drop_frag_idx and 'frag_start_idx' in df.columns:
        df.drop(columns=[
            'frag_start_idx','frag_end_idx'
        ], inplace=True)

    if not is_precursor_refined(df):
        df.sort_values('nAA', inplace=True)
        df.reset_index(drop=True, inplace=True)

    return df

reset_precursor_df = refine_precursor_df

def is_precursor_refined(precursor_df: pd.DataFrame):
    return (
        (len(precursor_df) == 0) or (
            (precursor_df.index.values[0] == 0) and
            precursor_df.nAA.is_monotonic and
            np.all(
                np.diff(precursor_df.index.values)==1
            )
        )
    )

is_precursor_sorted = is_precursor_refined

def update_precursor_mz(
    precursor_df: pd.DataFrame,
    batch_size = 500000,
)->pd.DataFrame:
    """
    Calculate precursor_mz inplace in the precursor_df

    Args:
        precursor_df (pd.DataFrame):
          precursor_df with the 'charge' column

    Returns:
        pd.DataFrame: precursor_df with 'precursor_mz'
    """

    if 'nAA' not in precursor_df:
        reset_precursor_df(precursor_df)
        _calc_in_order = True
    elif is_precursor_sorted(precursor_df):
        _calc_in_order = True
    else:
        _calc_in_order = False
    precursor_df['precursor_mz'] = 0.
    _grouped = precursor_df.groupby('nAA')
    precursor_mz_idx = precursor_df.columns.get_loc(
        'precursor_mz'
    )
    for nAA, big_df_group in _grouped:
        for i in range(0, len(big_df_group), batch_size):
            batch_end = i+batch_size

            df_group = big_df_group.iloc[i:batch_end,:]

            pep_mzs = calc_peptide_masses_for_same_len_seqs(
                df_group.sequence.values.astype('U'),
                df_group.mods.values,
                df_group.mod_deltas.values if
                'mod_deltas' in df_group.columns else None
            )/df_group.charge + MASS_PROTON
            if _calc_in_order:
                precursor_df.iloc[:,precursor_mz_idx].values[
                    df_group.index.values[0]:
                    df_group.index.values[-1]+1
                ] = pep_mzs
            else:
                precursor_df.loc[
                    df_group.index, 'precursor_mz'
                ] = pep_mzs
    return precursor_df

calc_precursor_mz = update_precursor_mz

# Cell
from mmh3 import hash64

def get_mod_seq_hash(
    sequence:str, mods:str,
    mod_sites:str,
    *, seed:int=0
)->np.int64:
    """Get hash code value for a peptide:
      (sequence, mods, mod_sites)

    Args:
        sequence (str): amino acid sequence
        mods (str): modification names in AlphaBase format
        mod_sites (str): modification sites in AlphaBase format
        seed (int, optional): seed for hashing
          Defaults to 0.

    Returns:
        np.int64: 64-bit hash code value
    """
    return np.sum([
        hash64(sequence, seed=seed)[0],
        hash64(mods, seed=seed)[0],
        hash64(mod_sites, seed=seed)[0],
    ],dtype=np.int64) # use np.sum to prevent overflow

def get_mod_seq_charge_hash(
    sequence:str, mods:str,
    mod_sites:str, charge:int,
    *, seed=0
):
    """Get hash code value for a precursor:
      (sequence, mods, mod_sites, charge)

    Args:
        sequence (str): amino acid sequence
        mods (str): modification names in AlphaBase format
        mod_sites (str): modification sites in AlphaBase format
        charge (int): precursor charge state
        seed (int, optional): seed for hashing
          Defaults to 0.

    Returns:
        np.int64: 64-bit hash code value
    """
    return np.sum([
        get_mod_seq_hash(
            sequence, mods, mod_sites,
            seed=seed
        ),
        charge,
    ],dtype=np.int64) # use np.sum to prevent overflow

def hash_mod_seq_df(
    precursor_df:pd.DataFrame,
    *, seed=0
):
    """ Internal function """
    hash_vals = precursor_df.sequence.apply(
        lambda x: hash64(x, seed=seed)[0]
    ).astype(np.int64).values
    hash_vals += precursor_df.mods.apply(
        lambda x: hash64(x, seed=seed)[0]
    ).values
    hash_vals += precursor_df.mod_sites.apply(
        lambda x: hash64(x, seed=seed)[0]
    ).values

    precursor_df[
        "mod_seq_hash"
    ] = hash_vals

def hash_mod_seq_charge_df(
    precursor_df:pd.DataFrame,
    *, seed=0
):
    """ Internal function """
    if "mod_seq_hash" not in precursor_df.columns:
        hash_mod_seq_df(precursor_df, seed=seed)
    if "charge" not in precursor_df.columns:
        raise ValueError(
            "DataFrame must contain 'charge' column"
        )

    precursor_df["mod_seq_charge_hash"] = (
        precursor_df["mod_seq_hash"].values
        + precursor_df["charge"].values
    )

def hash_precursor_df(
    precursor_df:pd.DataFrame,
    *, seed:int=0
)->pd.DataFrame:
    """Add columns 'mod_seq_hash' and 'mod_seq_charge_hash'
    into precursor_df (inplace).
    The 64-bit hash function is from mmh3 (mmh3.hash64).

    Args:
        precursor_df (pd.DataFrame): precursor_df
        seed (int, optional): seed for mmh3.hash64.
          Defaults to 0
    """
    hash_mod_seq_df(precursor_df, seed=seed)

    if 'charge' in precursor_df.columns:
        hash_mod_seq_charge_df(precursor_df, seed=seed)
    return precursor_df

# Cell
def get_mod_seq_formula(seq:str, mods:str)->list:
    """ 'PEPTIDE','Acetyl@Any N-term' --> [('C',n), ('H',m), ...] """
    formula = {}
    for aa in seq:
        for chem,n in AA_formula[aa].items():
            if chem in formula:
                formula[chem]+=n
            else:
                formula[chem]=n
    if len(mods) > 0:
        for mod in mods.split(';'):
            for chem,n in MOD_formula[mod].items():
                if chem in formula:
                    formula[chem]+=n
                else:
                    formula[chem]=n
    return list(formula.items())

def get_mod_seq_isotope_distribution(
    seq_mods:tuple,
    isotope_dist:IsotopeDistribution,
)->tuple:
    """Get isotope abundance distribution by IsotopeDistribution.
    This function is designed for multiprocessing.

    Args:
        seq_mods (tuple): (sequence, mods)
        isotope_dist (IsotopeDistribution):
            see :class:`alphabase.constants.isotope.IsotopeDistribution`

    Returns:
        float: abundance of mono+1 / mono
        float: abundance of mono+2 / mono
        float: abundance of apex / mono
        int: Apex isotope position relative to mono,
             i.e. apex index - mono index and
             0 refers to the position of mono itself.
    """
    dist, mono = isotope_dist.calc_formula_distribution(
        get_mod_seq_formula(*seq_mods)
    )

    apex_idx = np.argmax(dist)

    return (
        dist[mono+1]/dist[mono],
        dist[mono+2]/dist[mono],
        dist[apex_idx]/dist[mono],
        apex_idx-mono
    )

def calc_precursor_isotope(
    precursor_df:pd.DataFrame
):
    """Calculate isotope mz values and relative (to M0) intensity values for precursor_df inplace.

    Args:
        precursor_df (pd.DataFrame): precursor_df to calculate.

    Returns:
        pd.DataFrame: precursor_df with additional columns:
        - isotope_intensity_m1
        - isotope_mz_m1
        - isotope_intensity_m2
        - isotope_mz_m2
        - isotope_apex_intensity
        - isotope_apex_mz
        - isotope_apex_index
    """
    isotope_dist = IsotopeDistribution()

    (
        precursor_df['isotope_intensity_m1'],
        precursor_df['isotope_intensity_m2'],
        precursor_df['isotope_apex_intensity'],
        precursor_df['isotope_apex_index'],
    ) = zip(
        *precursor_df[['sequence','mods']].apply(
            get_mod_seq_isotope_distribution,
            axis=1, isotope_dist=isotope_dist
        )
    )

    precursor_df['isotope_mz_m1'] = (
        precursor_df.precursor_mz +
        MASS_ISOTOPE/precursor_df.charge
    )
    precursor_df['isotope_mz_m2'] = (
        precursor_df.precursor_mz +
        2*MASS_ISOTOPE/precursor_df.charge
    )

    precursor_df['isotope_apex_mz'] = (
        precursor_df.precursor_mz +
        (
            MASS_ISOTOPE
            *precursor_df.isotope_apex_index
            /precursor_df.charge
        )
    )

    return precursor_df

import multiprocessing as mp

def _precursor_df_group(df_group):
    """Internal funciton for multiprocessing"""
    for _, df in df_group:
        yield df

# `process_bar` should be replaced by more advanced tqdm wrappers created by Sander
# I will leave it to alphabase.utils
def calc_precursor_isotope_mp(
    precursor_df:pd.DataFrame,
    processes:int=8,
    process_bar=None,
)->pd.DataFrame:
    """`calc_precursor_isotope()` is not that fast for large dataframes,
    so here we use multiprocessing for faster isotope pattern calculation.
    The speed is acceptable with multiprocessing (3.8 min for 21M precursors, 8 processes).

    Args:
        precursor_df (pd.DataFrame): precursor_df to calculate.
        processes (int, optional): process number. Defaults to 8.
        process_bar (function, optional): The tqdm-based callback function
        to check multiprocessing. Defaults to None.

    Returns:
        pd.DataFrame: precursor_df with additional columns:
        - isotope_intensity_m1
        - isotope_mz_m1
        - isotope_intensity_m2
        - isotope_mz_m2
        - isotope_apex_intensity
        - isotope_apex_mz
        - isotope_apex_index
    """
    df_list = []
    df_group = precursor_df.groupby('nAA')
    with mp.Pool(processes) as p:
        processing = p.imap_unordered(
            calc_precursor_isotope, _precursor_df_group(df_group)
        )
        if process_bar:
            processing = process_bar(processing, df_group.ngroups)
        for df in processing:
            df_list.append(df)
    return pd.concat(df_list)