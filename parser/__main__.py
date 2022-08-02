from pathlib import Path

import typer

from parser.decree_parser import Parser

app = typer.Typer()
parser = Parser(word_to_search='назначить')


@app.command()
def folder(folder: str=typer.Option(...), results_file:str=typer.Option(...)):
    if not Path(folder).exists():
        raise FileNotFoundError(f'Путь не существует -- {Path(folder).absolute()}')
    parser.parse_folder(folder, parsing_results_file=results_file)


if __name__ == "__main__":
    app()
