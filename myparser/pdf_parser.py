import re
import statistics
from pathlib import Path

import pandas as pd
import numpy as np

import pdfplumber

from myparser.my_logger import get_logger
logger = get_logger(__name__)


class PdfParser:

    def convert_pdf_to_dfs(self, filename) -> list[pd.DataFrame]:
        self.pages = [] 
        self.tables = [] 

        with pdfplumber.open(filename) as pdf:
            pages = pdf.pages 
            self.pages = pages
            for page in pages:
                try:
                    page_tables = page.extract_tables()
                    page_tables = [pd.DataFrame(tab).fillna(method='ffill', axis=0) for tab in page_tables]
                    self.tables.append(page_tables)
                except Exception as ex:
                    self.tables.append([pd.DataFrame()]) # если не нашли, добавляем пустой
                    print(page, ex)
    
    @staticmethod
    def get_page_dep(page:pdfplumber.page.Page)->list[str]:
        lines = page.extract_text().split()
        pattern = '(фамилия|имя|фио|ф\.и\.о\.|ф\.и\.о|отчество|должност)'
        res = []
        for line in lines:
            line = line.lower()
            if not bool(re.search(pattern=pattern, string=line)):
                res.append(line)
            else:
                return ' '.join(res)
        return ' '.join(res)
        

    @staticmethod
    def drop_col_with_N(df: pd.DataFrame):
        expr = '(№|п/п)'
        for c in df.columns:

            if re.search(expr, str(c)):
                df.drop(columns=c, inplace=True)

        return df

    @staticmethod
    def drop_short_cols(df: pd.DataFrame):
        df = df.applymap(str)
        df = df.applymap(str)
        bool_df = df.applymap(lambda x: len(x) < 4)
        to_remove = []

        columns_numbers = [x for x in range(df.shape[1])]

        for i in columns_numbers:
            col_len = len(bool_df.iloc[:, i])
            if sum(bool_df.iloc[:, i]) > col_len // 2:
                to_remove.append(i)

        if to_remove:
            for e in to_remove:
                columns_numbers.remove(e)

        return df.iloc[:, columns_numbers]

    def find_and_split_departments(self, df: pd.DataFrame) -> pd.DataFrame:
        """
            разделяет таблицу в случае когда название учреждения поместили в середину вот так:
                -должность-  -имя-  -зарплата-
                        -ГБОУ школа 112-
                    директор     Ваня    100 руб
        """

        def _add_department_info_to_df(df: pd.DataFrame, dep_info: list[dict[int, str]]) -> pd.DataFrame:
            df['department'] = None
            for data in dep_info:
                df.at[data['index'], 'department'] = data['dep']
            df = df.dropna(axis=1, how='all').fillna(method='ffill', axis=0)
            return df

        def _find_department_in_table(df: pd.DataFrame) -> list[dict[int, str]]:
            # [index, department]
            departments_n_indexes = []
            for row in df.itertuples():
                index = row[0]
                row = list(row)[1:-1]
                row = [e for e in row if len(str(e)) > 4]
                if len(set(row)) < 2:
                    if not all([type(e) in [int, float] for e in row]):
                        if statistics.mean([len(e) for e in row]) > 4:
                            departments_n_indexes.append(
                                {'index': index, 'dep': row[0]})
            return departments_n_indexes

        dep_info = _find_department_in_table(df)

        if not dep_info:
            return df

        df = _add_department_info_to_df(df, dep_info)
        return df

    @staticmethod
    def give_numbers_to_unnamed_cols(df) -> pd.DataFrame:
    # нумерует безымянные колонки

        def fun():
            for e in range(100, 200, 3):
                yield e

        numbers = fun()
        df.columns = [e if e else next(numbers) for e in df.columns]
        return df
    
    @staticmethod
    def check_if_columns_ok(cols: tuple) -> bool:
        '''проверяем, есть ли в заголовках таблицы нужная инфа'''

        cols = list(map(str, cols))
        cols = list(map(str.lower, cols))

        ok_cols = 0
        for col in cols:
            name_salary_position_pattern = '(фамилия|имя|фио|ф\.и\.о\.|ф\.и\.о|отчество|плат[ы, а]|заработная|плата|cреднемесячн[ая, ой]|зарплат[а, ной, ы]|должность)'

            res = re.search(pattern=name_salary_position_pattern, string=col)
            if res:
                ok_cols += 1

        if ok_cols > 1:
            return True

        return False


    def find_ok_cols(self, df: pd.DataFrame) -> dict['df':pd.DataFrame, 'if_ok_cols':bool]:
        cols = df.columns
       # если колонки норм, отдаем df
        if self.check_if_columns_ok(cols):
            return {'df': df, 'if_ok_cols': True}

        i = -1
        for _, row in df.iterrows():
            i += 1
            found_cols = self.check_if_columns_ok(list(row))

            if found_cols:
                df.columns = df.iloc[i, :]
                # TODO: возможно тут надо отдавать i+2
                return {'df': df.iloc[i+1:, :], 'if_ok_cols': True}

            if i > 5:
                break

        # если не ок
        return {'df': df, 'if_ok_cols': False}
    


    @staticmethod
    def if_office_in_cols(dfs: list[pd.DataFrame]) -> list[dict[pd.DataFrame, bool]]:

        office_pattern = '(предприяти[е,я]|учреждени[е,я]|юридическ[ие, ое]|организаци|наименование МО)'

        res = []

        if type(dfs) == pd.DataFrame:
            cols = dfs.columns

            cols = list(map(str, cols))
            cols = list(map(str.lower, cols))

            if not any([re.search(pattern=office_pattern, string=col) for col in cols]):
                res.append({'df': dfs, 'has_office': False})
            else:
                res.append({'df': dfs, 'has_office': True})

        elif type(dfs) == list:
            for df in dfs:
                cols = df.columns

                cols = list(map(str, cols))
                cols = list(map(str.lower, cols))

                if not any([re.search(pattern=office_pattern, string=col) for col in cols]):
                    res.append({'df': df, 'has_office': False})
                else:
                    res.append({'df': df, 'has_office': True})

        return res


    def concatenate_if_possible(self, dfs: list[dict['df':pd.DataFrame, 'if_ok_cols':bool]]) -> list[pd.DataFrame]:

        all_oks = [e['if_ok_cols'] for e in dfs]

        if all(all_oks):
            return [e['df'] for e in dfs]

        result_df = []
        df_to_concat = pd.DataFrame()
        for i, df_info in enumerate(dfs):
            # df_info['df'].to_excel(f'concat_test/{i}.xlsx')

            if df_info['if_ok_cols']:
                if not df_to_concat.empty:
                    result_df.append(df_to_concat)
                df_to_concat = df_info['df']

            # оставляем только таблицы, у которых совпадает число колонок
            # с df у которых мы колонки нашли
            # если не нашли колонки и не к чему присоединять - дропаем


            elif not df_info['if_ok_cols'] and not df_to_concat.empty \
                    and len(df_to_concat.columns) == len(df_info['df'].columns):

                df_info['df'].columns = df_to_concat.columns
                df_to_concat = pd.concat([df_to_concat, df_info['df']])
                df_to_concat = df_to_concat.replace(
                    r'^\s*$', np.nan, regex=True)
                df_to_concat = df_to_concat.reset_index(
                    drop=True).fillna(method='ffill', axis=0)

        result_df.append(df_to_concat)

        return result_df
        
    @staticmethod
    def add_file_info(dfs: list[pd.DataFrame], filepath: str) -> list[pd.DataFrame]:
        file = Path(filepath).name
        file_id = file.split('_')[0]
        logger.debug('Нашли в имени файла айди -- %s', file_id)
        for df in dfs:
            df['documentfile_id'] = file_id

        return dfs
        
    def parse_page(self, page:pdfplumber.page.Page, dfs:list[pd.DataFrame]) -> pd.DataFrame:
        dfs = [self.give_numbers_to_unnamed_cols(
            e) for e in dfs]  # именуем безымянные

       # дропаем маленькие колонки
        dfs = [self.drop_col_with_N(e) for e in dfs]
        dfs = [e for e in dfs  if type(e) == pd.DataFrame]
        dfs = [self.drop_short_cols(e) for e in dfs]

        def sjoin(x): return ';'.join(set(x[x.notnull()].astype(str)))
        dfs = [df.groupby(level=0, axis=1, sort=False).apply(
            lambda x: x.apply(sjoin, axis=1)) for df in dfs]

        # у каждой таблицы ищем заголовки. {'df':pd.Dataframe, 'if_ok_cols':bool}
        dfs = [self.find_ok_cols(e) for e in dfs]
        
        at_least_one_table_ok = any([e['if_ok_cols'] for e in dfs])

        if not at_least_one_table_ok: # не нашли заголовки - скпипаем
            logger.warning('Не нашли заголовки таблицы')
            return pd.DataFrame()

        # если таблицы разбиты на несколько страниц - склеиваем
        dfs = self.concatenate_if_possible(dfs)
        dfs = [self.drop_short_cols(e) for e in dfs]

        # проверяем есть ли учреждение {'df':df, 'has_office':bool}
        dfs_with_office = self.if_office_in_cols(
            dfs) 

        if all([e['has_office'] for e in dfs_with_office]):
            return dfs

        department = self.get_page_dep(page=page)
        if department:
            for df in dfs:
                    df['department'] = department
        else:
            for df in dfs:
                df['department'] = 'dep not found'

        return dfs


    def parse_file(self, filename) -> list[pd.DataFrame]:
        self.convert_pdf_to_dfs(filename)
        self.filename = filename
        result = []

        for page, tables in zip(self.pages, self.tables):
            parsed_dfs = self.parse_page(page, tables)                        

            if type(parsed_dfs) == pd.DataFrame and parsed_dfs.empty:
                continue

            result.append(parsed_dfs)
        result = sum(result, []) 
        result = self.add_file_info(result, filename)
        return result

