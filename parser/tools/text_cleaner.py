import re
from pathlib import Path


class TextCleaner:
    def __init__(self, location: str='') -> None:
        self.unwanted_words = open(Path(
            __file__).parent / 'unwanted_words.txt', encoding='utf-8').read().split('\n')
        self.location = location

    def remove_unwanted_words(self, line: str) -> str:
        line = line.lower()
        line = ' '.join(line.split())
        line = line.replace('.', '')
        line = line.replace(',', '')

        # TODO: unwanted_words = '|'.join(self.unwanted_words)
        for w in self.unwanted_words:
            p = f'(?<!\S)({w})(?!\S)'
            line = re.sub(pattern=p, repl=' ', string=line)

        line = re.sub(string=line, pattern='пунктом .{1,5} статьи .{1,5} конституции российской федерации', repl='')
        line = re.sub(string=line, pattern='\d', repl='')
        line = ' '.join(line.split())
        line = re.sub(string=line, pattern=f'^{self.location}', repl='')
        return line
