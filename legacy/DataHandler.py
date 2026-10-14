import numpy as np
import pandas as pd
import random


class CokidoDataHandler:
    """
    This class will import all data from Google sheet, transform it where needed and store it for general usage

    important variables
    1)np_availbool : binary matrix with dim0 = parentID, dim1=day
    2)np_costmatrix : matrix used in optimization. normalized by family . The higher the value, the higher the preference. dim0 = parentID, dim1 = day
    3)np_req_presence : array with len=#days containing # parents that must be present on each day
    4)np_presence_req_per_fam : array with the number of days a family must be present.
    5)np_presence_parent : array with the number of days a parent is maximum available. -1 = no specific limit. Only to be used in edge cases
    """

    def __init__(self, sh):
        self.np_presence_req_per_fam = None
        self.np_costmatrix = None
        self.np_req_presence = None
        self.np_availbool = None
        self.df_child = pd.DataFrame()
        self.df_parent = pd.DataFrame()
        self.df_presence = pd.DataFrame()
        self.df_avail = pd.DataFrame()
        self.df_oppas = pd.DataFrame()
        self.df_oppasperdag = pd.DataFrame()
        self.df_fam = pd.DataFrame()
        self.num_days = None
        self.num_families = None
        self.num_parents = None
        self.num_children = None
        self._FACTOR_OUDERSPERKIND = 6
        self._FACTOR_OPPASDAGEN = 5
        self._TEMPRESULT_STRING = '_result_'
        self.sh = sh

    def import_data(self):
        print('importing data from google sheet')
        # import sheetdata
        self.df_child = pd.DataFrame(self.sh.worksheet("children").get_all_records()).sort_values(by=['KidID'])
        self.df_parent = pd.DataFrame(self.sh.worksheet("parents").get_all_records()).sort_values(by=['ParentID'])
        self.df_presence = pd.DataFrame(self.sh.worksheet("presence").get_all_records()).drop(columns=['Name']).replace(
            r'^\s*$', 0, regex=True).sort_values(by=['KidID'])  # Regex is to replace emptty elements with 0
        self.df_avail = pd.DataFrame(self.sh.worksheet("availability").get_all_records()).drop(
            columns=['Name']).replace(r'^\s*$', 0, regex=True).sort_values(by=['ParentID'])  # sort avoids problems
        self.df_avail_fixed = pd.DataFrame(self.sh.worksheet("availability-fix").get_all_records()).drop(
            columns=['Name']).replace(r'^\s*$', float('nan'), regex=True).sort_values(by=['ParentID'])  # sort avoids problems
        self.df_oppas = pd.DataFrame(self.sh.worksheet("oppasdagen").get_all_records()).replace(r'^\s*$', np.nan,
                                                                                                regex=True).sort_values(
            by=['FamID'])
        self.df_oppasperdag = pd.DataFrame(self.sh.worksheet("oppassers_per_dag").get_all_records()).replace(r'^\s*$',
                                                                                                             np.nan,
                                                                                                             regex=True)

        print('import ended, creating derived variables')
        # define derived variables
        self.df_parent.maxdays=self.df_parent.maxdays.replace(r'^\s*$', 1000, regex=True)  # set empty values of maxdays to a very high number
        self.df_parent.mindays=self.df_parent.mindays.replace(r'^\s*$', 0, regex=True)  # set empty values of minimum number of days to 0
        self.num_children = len(self.df_child.index)
        self.num_parents = len(self.df_parent.index)
        self.num_days = len(self.df_presence.columns) - 1
        self.df_child['TotalChildDays'] = self.df_presence.drop(self.df_presence.columns[0], axis=1).sum(axis=1)
        self.num_families = len(self.df_child["FamID"].unique())
        # bereken oppasdagen indien nodig. ratio 1/6 minstens  de data in deze tab moeten wel gelijk lopen met die van de presence tab!
        _tempdf = self.df_presence.loc[:, self.df_presence.columns != 'KidID'].sum().reset_index()
        self.df_oppasperdag['TotalChildren'] = _tempdf.iloc[:, 1]
        self.df_oppasperdag["oppassers"] = self.df_oppasperdag["oppassers"].fillna(
            np.ceil(
                self.df_oppasperdag['TotalChildren'] / self._FACTOR_OUDERSPERKIND))  # vervang niet ingevulde waarden

        del _tempdf

        # Create familymatrixdf_fam
        _df_fam_children = self.df_child.groupby('FamID')[
            'KidID'].count().reset_index()  # get the summarized list of number of children per family
        _df_fam_oppasdagen = self.df_child.groupby('FamID')[
            'TotalChildDays'].sum().reset_index()  # get total number of days for a specific family
        _df_families_parents = self.df_parent.groupby('FamID')[
            'ParentID'].count().reset_index()  # get the summarized list of number of children per family
        _df_fam_names = self.df_parent.groupby('FamID')['Name'].first().reset_index()
        self.df_fam = pd.merge(_df_fam_names, pd.merge(_df_fam_oppasdagen,
                                                       pd.merge(_df_families_parents, _df_fam_children,
                                                                how='outer', on='FamID'), how='outer', on='FamID'),
                               how='outer', on='FamID')  # grote merge

        self.df_fam["oppasdagen"] = self.df_oppas["oppasdagen"]
        self.df_fam = self.df_fam.rename(columns={'ParentID': 'parents', "KidID": "children"})
        self.df_fam.sort_values(by=['FamID'],
                                inplace=True)  # zorg dat ze altijd in dezelfde volgorde zitten wanneer je de waardes gaat schrijven in de google sheet.
        self.df_fam["oppasdagen"] = self.df_fam["oppasdagen"].fillna(round(self.df_fam[
                                                                               'TotalChildDays'] / self._FACTOR_OPPASDAGEN))  # vervang niet ingevulde waarden met een default afgeronde 1/5

        del _df_fam_children, _df_fam_oppasdagen, _df_families_parents, _df_fam_names

        # perform checks on df_fam
        raising = all(i <= j for i, j in zip(self.df_fam.FamID.values, self.df_fam.FamID.values[1:]))
        by_one = all(j - i <= 1 for i, j in zip(self.df_fam.FamID.values, self.df_fam.FamID.values[1:]))
        if (raising and by_one) is False:
            raise Exception(
                'Error in structure of data in sheet parents. Once ordered by parentID FamID is not strictly raising with a maximum of 1. Please check & fix FamID')
        del raising, by_one

        """
        create variables to use with OT tools which is not compatible with pandas
        """
        # availbool dim 0 = parent dim1=day : when is a parent available or not?
        self.np_availbool = self.df_avail.loc[:, self.df_avail.columns != 'ParentID'].ne(0) * 1
        self.np_availbool = self.np_availbool.to_numpy()

        self.np_avail_fixed_bool = self.df_avail_fixed.loc[:, self.df_avail_fixed.columns != 'ParentID'].to_numpy()

        # create costmatrix as array object. Normalize info per family so each family has equal value in optimization
        # impact of this is limited as the hard constraints must be met anyway
        # but it should avoid problems in skewing the optimization more to one group's priority
        _cost = self.df_avail.loc[:, self.df_avail.columns != 'ParentID']
        _cost["FamID"] = self.df_parent["FamID"]  # add family ID, assumes that parent is always in the same order!

        # create temporary list of family/ID - total sum in df_avail for that family as basis for the normalization
        _sum_fam_val = _cost.groupby(["FamID"]).sum().sum(axis=1).reset_index()
        _sum_fam_val.columns = ['FamID', 'family_sum']

        # normalize in matrix _cost
        for _famid in _sum_fam_val["FamID"]:
            _famsum = _sum_fam_val.loc[_sum_fam_val['FamID'] == _famid][
                'family_sum'].sum()  # why sum()? it just works, stupid typing is in the way (I tried value but nope
            _cost.loc[_cost["FamID"] == _famid, _cost.columns != 'FamID'] = _cost.loc[
                _cost["FamID"] == _famid, _cost.columns != 'FamID'].mul(
                100 / _famsum)  # loc creates a copy, so you won't be updating. pretty sure it can be done in a better way

        self.np_costmatrix = _cost.loc[:, self.df_avail.columns != 'FamID'].to_numpy()

        del _cost, _famsum, _sum_fam_val

        # required number of parents on a given day
        self.np_req_presence = self.df_oppasperdag["oppassers"].to_numpy()

        # maximum number of days a family should be present
        self.np_presence_req_per_fam = self.df_fam['oppasdagen'].to_numpy()

        print('derived variables calulated')

    def update_gsheet(self):
        print('writing calculated values to gsheet')
        # Oppasdagen info schrijven/updaten in google sheet
        self.sh.worksheet("oppasdagen").update([self.df_fam.columns.values.tolist()] + self.df_fam.values.tolist())
        self.sh.worksheet("oppassers_per_dag").update(
            [self.df_oppasperdag.columns.values.tolist()] + self.df_oppasperdag.values.tolist())

    """
    Check if a list increases by 0 or 1
    """

    def list_increase_step(self, mylist):
        raising = all(i <= j for i, j in zip(mylist, mylist[1:]))
        by_one = all(j - i <= 1 for i, j in zip(mylist, mylist[1:]))
        res = raising and by_one
        return res

    def write_results(self, scores, _results):
        # remove previous results
        _days = self.df_avail.columns[1:]
        _parents = self.df_parent.Name.values
        worksheets = self.sh.worksheets()
        temp_sheets = []

        for _sheet in worksheets:
            temp_sheets.append(_sheet.title)
        temp_sheets = [s for s in temp_sheets if self._TEMPRESULT_STRING in s]

        for i in temp_sheets:
            self.sh.del_worksheet(self.sh.worksheet(i))
        print('deleted old result sheets')

        for i in _results:
            sheetname = self._TEMPRESULT_STRING + str(random.randint(1, 10000))
            df_result = pd.DataFrame(i)
            df_result.columns = _days
            df_result.replace(to_replace=0, value='', inplace=True)
            df_result.insert(loc=0, column='parentID', value=range(1, len(_parents) + 1, 1))
            df_result.insert(loc=0, column='Name', value=_parents)
            self.sh.add_worksheet(title=sheetname, rows=100, cols=100)
            self.sh.worksheet(sheetname).update([df_result.columns.values.tolist()] + df_result.values.tolist())

        print('new results written')
        del _days, _parents

    """
    get value of the cell D20 in tab Readme.
    """

    def get_runflag(self):
        return self.sh.worksheet("Readme").acell('D20').value

    def set_runflag(self, value):
        self.sh.worksheet("Readme").update('D20', value)
