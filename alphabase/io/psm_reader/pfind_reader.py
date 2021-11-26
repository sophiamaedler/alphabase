# AUTOGENERATED! DO NOT EDIT! File to edit: nbdev_nbs/io/psm_reader/pfind_reader.ipynb (unless otherwise specified).

__all__ = ['convert_one_pFind_mod', 'translate_pFind_mod', 'get_pFind_mods', 'remove_pFind_decoy_protein',
           'pFindReader']

# Cell
import pandas as pd
import typing

import alphabase.constants.modification as ap_mod

from alphabase.io.psm_reader.psm_reader import (
    PSMReaderBase, psm_reader_provider,
)


def convert_one_pFind_mod(mod):
    if mod[-1] == ')':
        mod = mod[:(mod.find('(')-1)]
        idx = mod.rfind('[')
        name = mod[:idx]
        site = mod[(idx+1):]
    else:
        idx = mod.rfind('[')
        name = mod[:idx]
        site = mod[(idx+1):-1]
    if len(site) == 1:
        return name + '@' + site
    elif site == 'AnyN-term':
        return name + '@' + 'Any N-term'
    elif site == 'ProteinN-term':
        return name + '@' + 'Protein N-term'
    elif site.startswith('AnyN-term'):
        return name + '@' + site[-1] + '^Any N-term'
    elif site.startswith('ProteinN-term'):
        return name + '@' + site[-1] + '^Protein N-term'
    elif site == 'AnyC-term':
        return name + '@' + 'Any C-term'
    elif site == 'ProteinC-term':
        return name + '@' + 'Protein C-term'
    elif site.startswith('AnyC-term'):
        return name + '@' + site[-1] + '^Any C-term'
    elif site.startswith('ProteinC-term'):
        return name + '@' + site[-1] + '^Protein C-term'
    else:
        return None

def translate_pFind_mod(mod_str):
    if not mod_str: return ""
    ret_mods = []
    for mod in mod_str.split(';'):
        mod = convert_one_pFind_mod(mod)
        if not mod: return pd.NA
        elif mod not in ap_mod.MOD_INFO_DICT: return pd.NA
        else: ret_mods.append(mod)
    return ';'.join(ret_mods)

def get_pFind_mods(pfind_mod_str):
    pfind_mod_str = pfind_mod_str.strip(';')
    if not pfind_mod_str: return "", ""

    items = [item.split(',',3) for item in pfind_mod_str.split(';')]
    items = list(zip(*items))
    return ';'.join(items[1]), ';'.join(items[0])

def remove_pFind_decoy_protein(protein):
    proteins = protein[:-1].split('/')
    return ';'.join([protein for protein in proteins if not protein.startswith('REV_')])


# Cell
class pFindReader(PSMReaderBase):
    def __init__(self, modification_mapping=None):
        super().__init__()

        self.column_mapping = {
            'sequence': 'Sequence',
            'charge': 'Charge',
            'rt': 'RT',
            'rt_norm': 'rt_norm',
            'ccs': 'ccs',
            'raw_name': 'raw_name',
            'query_id': 'File_Name',
            'spec_idx': 'Scan_No',
            'score': 'Final_Score',
            'proteins': 'Proteins',
            'uniprot_ids': 'Proteins',
            'genes': 'Proteins',
            'fdr': 'Q-value',
            'decoy': 'decoy'
        }

    def _translate_modifications(self):
        pass

    def _post_process(self, filename: str, origin_df: pd.DataFrame):
        pass

    def _load_file(self, filename):
        pfind_df = pd.read_csv(filename, index_col=False, sep='\t')
        pfind_df.fillna('', inplace=True)
        pfind_df = pfind_df[pfind_df.Sequence != '']
        pfind_df['raw_name'] = pfind_df['File_Name'].str.split('.').apply(lambda x: x[0])
        pfind_df['Proteins'] = pfind_df['Proteins'].apply(remove_pFind_decoy_protein)
        pfind_df['decoy'] = (pfind_df['Target/Decoy']=='decoy').astype(int)
        return pfind_df

    def _load_modifications(self, pfind_df):
        self._psm_df['mods'], self._psm_df['mod_sites'] = zip(*pfind_df['Modification'].apply(get_pFind_mods))

        self._psm_df['mods'] = self._psm_df['mods'].apply(translate_pFind_mod)
        self._psm_df = self._psm_df[~self._psm_df['mods'].isna()]

psm_reader_provider.register_reader('pfind', pFindReader)