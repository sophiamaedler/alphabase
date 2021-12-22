# AUTOGENERATED! DO NOT EDIT! File to edit: nbdev_nbs/peptide/precursor.ipynb (unless otherwise specified).

__all__ = ['reset_precursor_df', 'is_precursor_sorted', 'update_precursor_mz', 'calc_precursor_mz']

# Cell
import pandas as pd
import numpy as np

from alphabase.constants.element import (
    MASS_PROTON
)
from alphabase.peptide.mass_calc import (
    calc_peptide_masses_for_same_len_seqs
)

def reset_precursor_df(df:pd.DataFrame):
    """ For faster precursor/fragment calculation """
    df.sort_values('nAA', inplace=True)
    df.reset_index(drop=True, inplace=True)

def is_precursor_sorted(precursor_df: pd.DataFrame):
    return (
        precursor_df.index.values[0] == 0 &
        precursor_df.nAA.is_monotonic &
        np.all(
            np.diff(precursor_df.index.values)==1
        )
    )

def update_precursor_mz(
    precursor_df: pd.DataFrame,
    batch_size = 500000,
)->pd.DataFrame:
    """
    Calculate precursor_mz for the precursor_df
    Args:
        precursor_df (pd.DataFrame):
          precursor_df with the 'charge' column

    Returns:
        pd.DataFrame: precursor_df with 'precursor_mz'
    """

    if 'nAA' not in precursor_df:
        precursor_df['nAA'] = precursor_df.sequence.str.len()
        reset_precursor_df(precursor_df)
        _calc_in_order = True
    elif is_precursor_sorted(precursor_df):
        _calc_in_order = True
    else:
        _calc_in_order = False
    precursor_df['precursor_mz'] = 0.
    _grouped = precursor_df.groupby('nAA')
    for nAA, big_df_group in _grouped:
        for i in range(0, len(big_df_group), batch_size):
            batch_end = i+batch_size

            df_group = big_df_group.iloc[i:batch_end,:]

            pep_mzs = calc_peptide_masses_for_same_len_seqs(
                df_group.sequence.values.astype('U'),
                df_group.mods.values,
                df_group.mod_deltas.values if 'mod_deltas' in df_group.columns else None
            )/df_group.charge + MASS_PROTON
            if _calc_in_order:
                precursor_df.loc[:,'precursor_mz'].values[
                    df_group.index.values[0]:
                    df_group.index.values[-1]+1
                ] = pep_mzs
            else:
                precursor_df.loc[
                    df_group.index, 'precursor_mz'
                ] = pep_mzs
    return precursor_df

calc_precursor_mz = update_precursor_mz