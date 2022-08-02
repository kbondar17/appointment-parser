from pprint import pprint

import pymorphy2

from parser.parsers.single_appo import SingleAppointment
from parser.tools import NameParser, TextCleaner
from parser.utils import models

morph = pymorphy2.MorphAnalyzer()


class ParseOnePosition:
    def __init__(self) -> None:
        self.file_data: models.FileData = None
        self.name_parser = NameParser()
        self.text_cleaner = TextCleaner()

    def filter_unwanted_lines_in_persons(self, lines: list[str]) -> list[str]:
        res = []
        stop_words = ['Принять к сведению']
        for line in lines:
            for word in stop_words:
                if word not in line:
                    res.append(line)
        return res

    def find_names(self, position: str, raw_persons: list[str]) -> models.AppoitmentLine:
        app_line = models.AppoitmentLine(raw_line=position, position=position)
        filtered_persons = self.filter_unwanted_lines_in_persons(raw_persons)
        for i, pers in enumerate(filtered_persons):
            pers_object = models.Person(raw_name=pers)
            parsed_name = self.name_parser.parse_multiple_appo(pers_object)
            for name in parsed_name:
                name: models.Person
                if '??' not in name.fio['surname']:
                    app_line.appointees.append(name)

        return app_line

    def parse(self, position, persons, file_data: models.FileData) -> models.FileData:
        self.file_data = file_data
        app_line = self.find_names(position=position, raw_persons=persons)
        self.file_data.appointment_lines.append(app_line)

        for line in self.file_data.appointment_lines:
            line.position = self.text_cleaner.remove_unwanted_words(
                line.position)

        return self.file_data


class ParseManyPositions:

    def __init__(self) -> None:
        self.file_data: models.FileData = None
        self.parser = SingleAppointment()

    def parse(self, persons_n_position: list[str], file_data: models.FileData) -> models.FileData:
        '''persons_n_position: список строк где есть имя и, веротяно, назначние. парсим как раньше'''
        self.file_data = file_data
        app_lines = []
        for line in persons_n_position:
            app_lines.append(models.AppoitmentLine(raw_line=line))
        self.file_data.appointment_lines = app_lines
        pprint(self.file_data.dict())
        self.file_data = self.parser.parse(self.file_data)
        return self.file_data


class MultipleAppointment:
    '''достает имена и app lines'''

    def __init__(self) -> None:
        self.file_data: models.FileData = None
        self.one_position_parser = ParseOnePosition()
        self.many_positions_parser = ParseManyPositions()

    @staticmethod
    def check_if_pozition_in_nazhnachit(nazcnach_line: str):
        if not nazcnach_line:
            return False
        if 'Назначить в совет' in nazcnach_line:
            print('назначение одно на всех')
            return True

        for word in nazcnach_line.split():
            if morph.parse(word)[0].tag.case == 'ablt' and word != 'сроком':
                print('назначение одно на всех', word)
                return True

    @staticmethod
    def _find_naznach_line(lines: list[str]) -> str | None:
        for line in lines:
            if 'Назначить' in line or 'назначить' in line:
                return line
        raise ValueError('в файле нет назначить')

    @staticmethod
    def _concat_people_with_naznach(lines: list[str], naznach_line: str) -> list[dict]:
        naznach_line_index = lines.index(naznach_line)
        position = lines[naznach_line_index]
        persons = []
        for line in lines[naznach_line_index:-4]:
            persons.append(line)
        return {'position': position, 'persons': persons}

    @staticmethod
    def _get_people_with_their_positions(lines: list[str], naznach_line: str) -> list[str]:
        naznach_line_index = lines.index(naznach_line)
        res = []
        for line in lines[naznach_line_index+1:-4]:
            res.append(line)
        return res

    def get_app_lines(self, data: models.FileData):
        self.file_data = data
        self.file_data.naznach_line = self._find_naznach_line(
            self.file_data.splitted_text)

        if self.check_if_pozition_in_nazhnachit(self.file_data.naznach_line):
            print('get_app_lines :: должность в назначить!')
            # если ли название должности в строке с "назначить?"
            # если да - то склеиваем эту строчку с каждым назначенцем
            persons_with_positions = self._concat_people_with_naznach(
                self.file_data.splitted_text, self.file_data.naznach_line)

            file_data_with_names_n_positions = self.one_position_parser.parse(
                position=persons_with_positions['position'],
                persons=persons_with_positions['persons'],
                file_data=self.file_data)

        else:
            # если нет - то обрабатываем каждую строку отдельно
            print('get_app_lines :: НЕТ должности в назначить!')
            people_with_their_positions = self._get_people_with_their_positions(
                self.file_data.splitted_text, self.file_data.naznach_line)

            file_data_with_names_n_positions = self.many_positions_parser.parse(
                people_with_their_positions, self.file_data)

        return file_data_with_names_n_positions

    def parse(self, file_data: models.FileData) -> models.FileData:
        file_data_with_app_lines = self.get_app_lines(file_data)
        return file_data_with_app_lines
