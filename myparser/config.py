import pandas as pd
from dotenv import dotenv_values

pd.options.mode.chained_assignment = None  # default='warn'
config = dotenv_values(".env") 



