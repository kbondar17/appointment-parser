from pathlib import Path

import enum
import re
from pymorphy2 import MorphAnalyzer
import warnings
from natasha import (PER, Doc, MorphVocab, NamesExtractor, NewsEmbedding,
                     NewsMorphTagger, NewsNERTagger, NewsSyntaxParser,
                     Segmenter)

from parser.utils import models


morph = MorphAnalyzer()


class Gender(enum.Enum):
    male = 'male'
    female = 'female'
    unknown = 'unknown'

warnings.filterwarnings("ignore", category=DeprecationWarning)

segmenter = Segmenter()
morph_vocab = MorphVocab()

emb = NewsEmbedding()
morph_tagger = NewsMorphTagger(emb)
syntax_parser = NewsSyntaxParser(emb)
ner_tagger = NewsNERTagger(emb)

names_extractor = NamesExtractor(morph_vocab)


class NameParser:
    '''получает имя. убирает лишние слова, отдает лемму, имени и пол'''

    def __init__(self) -> None:
        self.unwanted_words_for_names = open(Path(__file__).parent / 'unwanted_words_for_names.txt',
                                             encoding='utf-8').read().split('\n')
        self.male_surname_roditel_endings = {'а': '', 'ого': 'ий', 'ая': 'ай', 'ича': 'ич', 'вну': '????'}
        self.female_surname_roditel_endings = {'ву': 'ва', 'ую': 'ая', 'ну': 'на'}  # ва ?
        self.male = Gender.male
        self.female = Gender.female
        self.unknown_gender = Gender.unknown

    def locate_names_in_string(self, text:str, *args, **kwargs) -> list[models.Person]:
        """находит и возвращает имена в строке """
        # print(text.lower())
        # text += ' Иван Иванович'
        # text += ' золотова александра юрьевича '
        doc = Doc(text)
        doc.segment(segmenter)
        doc.tag_morph(morph_tagger)

        for token in doc.tokens:
            token.lemmatize(morph_vocab)

        doc.parse_syntax(syntax_parser)
        doc.tag_ner(ner_tagger)
        # print(doc.spans)
        # for e in doc.tokens:
        #     print(e)
        # doc.tokens
        for span in doc.spans:
            span.normalize(morph_vocab)
        
        raw_names = []
        # получили списоки имен
        for span in doc.spans:
            # print(span)
            if span.type == PER:
                span.extract_fact(names_extractor)
                # norm_names.append(span.normal)
                raw_names.append(span.text)

        # иногда инициалы, имена и фамилии расклеиваются. склеиваем
        def _concat_name_n_surnames(names: list[str]):
            res = []
            # breakpoint()
            for name in names:
                # если инициалы
                if name.count('.') == 2 and len(name) in range(2, 5):
                    if res and res[-1].count('.') == 0:
                        res[-1] = res[-1] + ' ' + name
                    else:
                        res.append(name)
                # если имя
                else:
                    # если последний элемент списка инициалы
                    if res and res[-1].count('.') > 1 and len(res[-1]) in range(2, 5):
                        res[-1] = res[-1] + name
                    else:
                        # если последний элемент просто фамилия
                        if res and len(res[-1].split()) == 1:
                            res[-1] = res[-1] + ' ' + name
                        else:
                            res.append(name)
            return res

        raw_names = _concat_name_n_surnames(raw_names)

        norm_names = raw_names
        norm_n_raw_names = [models.Person(
            raw_name=raw, parsed_name=norm) for raw, norm in zip(raw_names, norm_names)]
        return norm_n_raw_names

    def remove_unwanted_words_from_name(self, name: str) -> str:
        for word in self.unwanted_words_for_names:
            name = name.replace(word, '')
            name = name.replace(word.title(), '')
        return name

    def split_name(self, raw_name: str) -> dict[str, str]:
        split_name = raw_name.split()
        word_count = len(split_name)
        surname, name, patronic = '??', '??', '??'
        if word_count == 3:
            surname, name, patronic = raw_name.split()
        if raw_name.count('.') >= 1:
            surname = split_name[0]
            name_n_patric = split_name[-1].split('.')
            if len(name_n_patric) == 1:
                name = name_n_patric[0]
                patronic = name_n_patric[0]
            elif len(name_n_patric) > 1:
                name, patronic = name_n_patric[0], name_n_patric[1]

        return {'name': name, 'surname': surname, 'patronic': patronic}

    def guess_gender_rod_padezh(self, split_name: dict[str]) -> Gender:
        if_full_name = len(split_name['name']) + \
                       len(split_name['patronic']) > 4
        if if_full_name:
            gender = self.female if split_name['patronic'][-2] == 'н' else self.male
            return gender

        for ending in self.male_surname_roditel_endings.keys():
            if bool(re.findall(f'{ending}$', split_name['surname'])):
                return self.male

        for ending in self.female_surname_roditel_endings.keys():
            if bool(re.findall(f'{ending}$', split_name['surname'])):
                return self.male
        
        else:
            return self.unknown_gender

    def guess_genre_imen_padezh(self, raw_name:dict[str,str]):
        male_surname_endings = ['ов', 'ий', 'ин']
        female_surname_endings = ['ва', 'ая', 'ина']

        for ending in female_surname_endings:
            if raw_name['surname'].endswith(ending):
                return self.female.value
            
        for ending in male_surname_endings:
            if raw_name['surname'].endswith(ending):
                return self.male.value
        
        else:
            return self.male.unknown.value
        


    def lemmatize_name(self, split_name: dict[str, str], gender: Gender) -> str:
        surname, name, patronic = '??', '??', '??'

        raw_surname, raw_name, raw_patronic = \
            split_name['surname'], split_name['name'], split_name['patronic']

        # FEMALE #
        if gender.value == gender.female.value:
            for raw_ending, norm_ending in self.female_surname_roditel_endings.items():
                surname, was_changed = re.subn(pattern=raw_ending + '$', repl=norm_ending, string=raw_surname)
                if was_changed:
                    break

            patronic = re.sub(
                pattern='вну$', string=raw_patronic, repl='вна')

            parsed_name = morph.parse(raw_name)
            for w in parsed_name:
                if 'femn' in w.tag:
                    name = w.normal_form.title()
                    break

        # MALE #
        elif gender.value == gender.male.value:
            for raw_ending, norm_ending in self.male_surname_roditel_endings.items():
                surname, was_changed = re.subn(pattern=raw_ending + '$', repl=norm_ending, string=raw_surname)
                if was_changed:
                    break

            patronic = re.sub(
                pattern='ича$', string=raw_patronic, repl='ич')
            parsed_name = morph.parse(raw_name)

            for w in parsed_name:
                if 'masc' in w.tag:
                    name = w.normal_form.title()
                    break
        else:
            return ' '.join([raw_surname, raw_name, raw_patronic])

        return ' '.join([surname, name, patronic])

    def parse_multiple_appo(self, person_object:models.Person)->list[models.Person]|None:
        '''определние имен в сырой строке, где нераспознаны имена
            return  list of (lemm_name:str, pers_gender:str, {'surname': '', 'name': '', 'patronymic': ''})
        '''
        try:
            names = self.locate_names_in_string(person_object.raw_name)
            raw_names = [e.raw_name for e in names]
            line_names = []
            for name in raw_names:            
                name = self.remove_unwanted_words_from_name(name)
                split_name = self.split_name(name)
                pers_gender = self.guess_genre_imen_padezh(split_name)
                
                person_object.gender = pers_gender
                person_object.lemm_name = f"{split_name['surname']} {split_name['name']} {split_name['patronic']}" 
                person_object.fio = split_name

                line_names.append(person_object)

            return line_names

        except Exception as ex:
            print('name parser parse_multiple_appo ---', ex)

    def parse(self, raw_name: str) -> tuple|None:
        """!!! только для single appo !!!"""
        """return: (lemm_name:str, pers_gender:str, {'surname': '', 'name': '', 'patronymic': ''}) """
        try:
            raw_name = self.remove_unwanted_words_from_name(raw_name)
            split_name = self.split_name(raw_name)

            pers_gender = self.guess_gender_rod_padezh(split_name)
            lemm_name = self.lemmatize_name(split_name, gender=pers_gender)
            splitted_lemm_name = lemm_name.split()
            fio = {'surname': splitted_lemm_name[0], 'name': splitted_lemm_name[1], 'patronymic': splitted_lemm_name[-1]}
            return (lemm_name, pers_gender.value, fio)
        except Exception as ex:
            print('name parser :: ', ex)
            