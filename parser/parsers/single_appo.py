import re

import pymorphy2

from parser.tools import NameParser, TextCleaner
from parser.utils import models


morph = pymorphy2.MorphAnalyzer()


class SingleAppointment:
    def __init__(self) -> None:
        self.file_data: models.FileData = None
        self.name_parser = NameParser()
        self.text_cleaner = TextCleaner()
        self.word_to_search = 'назначить'

    def get_appointment_lines(self) -> None:
        # филтруем по поисковому слову
        appointment_lines = [e for e in self.file_data.splitted_text if self.word_to_search.lower() in e
                             or self.word_to_search.capitalize() in e]
        appointment_lines = [models.AppoitmentLine(
            raw_line=line) for line in appointment_lines]
        self.file_data.appointment_lines = appointment_lines

    def find_names_in_line(self) -> None:
        names_located = False
        for line in self.file_data.appointment_lines:
            try:
                line: models.AppoitmentLine
                names = self.name_parser.locate_names_in_string(line.raw_line)
                if names:
                    line.appointees.extend(names)
                    names_located = True
            except Exception as ex:
                print('find_names_in_line---', ex)
        if not names_located:
            ...

    def _check_for_stop_words(self, line: str) -> bool:
        stop = ['при рассмотрении в государственной думе', 'при  рассмотрении законопроекта председателя', 'при рассмотрении палатами',
                'государственной думе', 'официальным представителем', 'стипенди', 'ответственным за', 'членом избирательной комиссии',
                'членами избирательной комиссии', 'Принять к сведению']

        stop: str = '|'.join(stop)
        line = line.lower()
        stop_words_in_line = re.findall(pattern=stop, string=line)
        return bool(stop_words_in_line)

    def get_lemmatize_names_n_genders(self) -> None:
        for line in self.file_data.appointment_lines:
            line: models.AppoitmentLine
            for pers in line.appointees:
                pers.lemm_name, pers.gender, pers.fio = self.name_parser.parse(
                    pers.raw_name)
            for pers in line.resignees:
                pers.lemm_name, pers.gender, pers.fio = self.name_parser.parse(
                    pers.raw_name)

    def get_position_WITH_OUT_dolhznost(self, string) -> str | None:
        '''если есть слово "должность" - ищем название должности по падежу'''
        morph = pymorphy2.MorphAnalyzer()
        string_split = string.split()
        position_found = False

        for i, w in enumerate(string_split):
            if morph.parse(w)[0].tag.case == 'ablt':
                position_index = i
                position_found = True
                break
        if position_found:
            string_split = string_split[position_index:]

            return ' '.join(string_split)

    def find_position(self) -> None:
        position_exists_in_file = False
        for line in self.file_data.appointment_lines:
            line: models.AppoitmentLine
            position = line.raw_line
            position = ' '.join(position.split())
            if self._check_for_stop_words(position):
                continue
            if 'должность' not in position:  # ищем должность по падежу
                position = self.get_position_WITH_OUT_dolhznost(
                    position) or position

            # убираем все что после "освободив". если там есть имя - значит его уволили.
            if 'освободив' in position:
                position, resign_part = position.split(
                    'освободив')[0], position.split('освободив')[1]
                names = self.name_parser.locate_names_in_string(resign_part)
                if names:
                    line.resignees.extend(names)
                    line.appointees = [
                        pers for pers in line.appointees if pers not in line.resignees]

            # убираем из должности имена
            for person in line.appointees:
                name: models.Person
                position = position.replace(person.raw_name, '')

            # убираем из должности лишние слова
            position = position.split('в порядке перевода')[0]
            position = self.text_cleaner.remove_unwanted_words(position)

            # сохранили найденную должность в дата-класс
            line.position = position
            position_exists_in_file = True

        if not position_exists_in_file:
            raise ValueError('No position, or position is in stop words')

    def drop_empty_appoint_lines(self):
        not_empty_lines = []
        for line in self.file_data.appointment_lines:
            if any((line.appointees, line.resignees)):
                not_empty_lines.append(line)
        self.file_data.appointment_lines = not_empty_lines

    def parse(self, file_data: models.FileData):
        self.file_data = file_data
        self.get_appointment_lines()
        self.find_names_in_line()
        # опредяляем пол и переводим в именительный падеж
        self.get_lemmatize_names_n_genders()
        self.find_position()
        self.drop_empty_appoint_lines()
        return self.file_data
