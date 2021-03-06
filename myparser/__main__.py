import typer
import os
import pathlib
import traceback

from myparser.parser import Parser
from myparser.my_logger import get_logger
from  myparser.config import config
from tqdm.auto import tqdm

logger = get_logger(__name__)

parser = Parser()
app = typer.Typer()

out_format = config['out_format']

@app.command()
def hello(name: str):
    typer.echo(f"Hello {name}")

@app.command()
def parse_test():
    test_folder = os.path.join('myparser', 'test_data')
    parse_folder(test_folder)


@app.command()
def parse_folder(path):
    cwd = pathlib.Path(__file__).parent.resolve()
    log_file = cwd/'parsing.log'
    
    i=0
    bad_files = []
    for file in tqdm(os.listdir(path), position=0, leave=True):
        try:
            parser.parse_file(os.path.join(path, file), out_format=out_format)
            i+=1
        except Exception as ex:
            bad_files.append(file)
            logger.error('Ошибка!\n %s', traceback.format_exc())
            logger.error('FILE ---   %s', file)
            

        logger.debug('Сохранили логи в %s', log_file)
    
    
    print('\n\n','='*10, sep='')
    logger.debug('Распаршено документов: %s из %s', i, len(os.listdir(path)))
    print(f'Распаршено документов: {i} из {len(os.listdir(path))} ')
    print('Сохранили в /parsing_results')
    if bad_files:
        logger.error("Не вышло распарсить:", bad_files)
    print('='*10)

    
@app.command()
def parse_file(file: str):
    logger.debug('Парсим %s', file)

    cwd = pathlib.Path(__file__).parent.resolve()
    log_file = cwd/'parsing.log'

    try:
        parser.parse_file(file, out_format)

    except Exception as ex:
        logger.error('Ошибка!\n %s', traceback.format_exc())

    logger.debug('Сохранили логи в %s', log_file)


if __name__ == "__main__":
    app()
