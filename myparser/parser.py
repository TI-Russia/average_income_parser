import json
import os
from pathlib import Path

import pandas as pd

from myparser.data_cleaner import DataCleaner
from myparser.docx_parser import DocxParser
from myparser.excel_parser import ExcelParser
from myparser.my_logger import get_logger
from myparser.pdf_parser import PdfParser
from myparser.utils import convert_df_to_json

logger = get_logger(__name__)


class Parser:

    def __init__(self) -> None:
        self.pdf_parser = PdfParser()
        self.excel_parser = ExcelParser()
        self.docx_parser = DocxParser()
        self.data_cleaner = DataCleaner()

    def parse_file(self, file: str, out_format='xlsx', destination_folder='parsing_results') -> None:
        
        if not os.path.isfile(file):
            return

        if file.split('.')[-1] not in ['docx', 'xlsx', 'pdf']:
            raise ValueError('Допустимые форматы: .docx, .xlsx, .pdf')

        if file.endswith('.xlsx'):
            dfs = self.excel_parser.parse_file(Path(file))

        elif file.endswith('.docx'):
            dfs = self.docx_parser.parse_file(file)

        elif file.endswith('.pdf'):
            dfs = self.pdf_parser.parse_file(file)

            
        dfs = [self.data_cleaner.clean_df(df) for df in dfs]

        destination_folder = Path(destination_folder)
        
        try:
            os.mkdir(destination_folder)
            logger.debug('создали папку "parsing_results". сохраняем в нее')
        except FileExistsError:
            logger.debug('папка "parsing_results" уже есть. сохраняем в нее')

        df_count = len(dfs)
        total = 0
        if out_format == 'json':
            my_json = [convert_df_to_json(df) for df in dfs if not df.empty] 
            for i, table in enumerate(my_json):
                new_file_name = f'{i}_' + Path(file).stem + '.json'
                with open(destination_folder / new_file_name, 'w') as f:
                    json.dump(table, f)
                    total +=1 
    

        new_filename = Path(file).stem + '.xlsx'
    
        if out_format == 'xlsx':
            for i, df in enumerate(dfs):
                new_filename_with_number = f'{i}_' + new_filename
                new_file_path = destination_folder / new_filename_with_number
                df.to_excel(new_file_path, index=False)
     